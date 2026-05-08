import socket
import struct
import asyncio
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session
from . import models
from .config import settings
from .metrics import (
    netflow_packets_received,
    netflow_packets_processed,
    netflow_packets_errors,
    netflow_flows_collected,
    db_write_duration,
    db_write_errors,
    db_batch_size
)
import logging
import time

logger = logging.getLogger(__name__)


class NetflowCollector:
    def __init__(self, host=None, port=None):
        self.host = host or settings.NETFLOW_HOST
        self.port = port or settings.NETFLOW_PORT
        self.batch_size = settings.NETFLOW_BATCH_SIZE
        self.batch_timeout = settings.NETFLOW_BATCH_TIMEOUT
        self.socket = None
        self.running = False
        self.task = None
        self.flow_buffer: List[models.NetworkFlow] = []
        self.last_flush = time.time()
        self.lock = asyncio.Lock()

    async def start(self):
        """Start the collector"""
        self.running = True
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 16777216)  # 16MB buffer
        self.socket.bind((self.host, self.port))
        self.socket.setblocking(False)

        # Start collector and flusher tasks
        self.task = asyncio.create_task(self._collect())
        asyncio.create_task(self._periodic_flush())

        logger.info(f"Netflow collector started on {self.host}:{self.port}")

    async def stop(self):
        """Stop the collector"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

        # Flush remaining flows
        await self._flush_buffer()

        if self.socket:
            self.socket.close()

        logger.info("Netflow collector stopped")

    async def _collect(self):
        """Main collection loop using asyncio"""
        loop = asyncio.get_event_loop()

        while self.running:
            try:
                # Non-blocking socket read
                data, addr = await loop.sock_recvfrom(self.socket, 4096)
                netflow_packets_received.inc()

                # Process packet
                await self._process_packet(data, addr)
                netflow_packets_processed.inc()

            except asyncio.CancelledError:
                break
            except BlockingIOError:
                # No data available, yield control
                await asyncio.sleep(0.001)
            except Exception as e:
                netflow_packets_errors.inc()
                logger.error(f"Error processing packet: {e}", exc_info=True)

    async def _process_packet(self, data, addr):
        """Process a single Netflow packet"""
        try:
            # Netflow v5 header (26 bytes)
            if len(data) < 26:
                logger.warning(f"Packet too small for Netflow header: {len(data)} bytes")
                return

            version, count, sys_uptime, unix_secs, unix_nsecs, flow_sequence, engine_type, engine_id, sampling_interval = struct.unpack('!HHIIIIIBB', data[:26])

            if version != 5:
                logger.warning(f"Unsupported Netflow version: {version}")
                return

            # Process each flow record (44 bytes)
            offset = 26
            flows = []

            for _ in range(count):
                flow_data = data[offset:offset+44]
                if len(flow_data) < 44:
                    break

                # Unpack flow record
                flow_record = struct.unpack('!IIIHHIIIHHBBBBHHBBxx', flow_data)

                (src_addr, dst_addr, nexthop, input_if, output_if, packets, bytes_count,
                 first, last, src_port, dst_port, tcp_flags, protocol,
                 tos, src_as, dst_as, src_mask, dst_mask) = flow_record

                # Convert IP addresses to string format
                src_ip = socket.inet_ntoa(struct.pack('!I', src_addr))
                dst_ip = socket.inet_ntoa(struct.pack('!I', dst_addr))

                # Create flow record
                flow = models.NetworkFlow(
                    src_ip=src_ip,
                    dst_ip=dst_ip,
                    src_port=src_port,
                    dst_port=dst_port,
                    protocol=protocol,
                    start_time=datetime.fromtimestamp(unix_secs + first/1000),
                    end_time=datetime.fromtimestamp(unix_secs + last/1000),
                    packets=packets,
                    bytes=bytes_count,
                    flags=tcp_flags,
                    tos=tos,
                    input_snmp=input_if,
                    output_snmp=output_if,
                    src_as=src_as,
                    dst_as=dst_as,
                    src_mask=src_mask,
                    dst_mask=dst_mask
                )

                flows.append(flow)
                offset += 44

            # Add flows to buffer
            if flows:
                await self._add_to_buffer(flows)

        except Exception as e:
            logger.error(f"Error processing flow record: {e}", exc_info=True)

    async def _add_to_buffer(self, flows: List[models.NetworkFlow]):
        """Add flows to buffer and flush if needed"""
        async with self.lock:
            self.flow_buffer.extend(flows)
            netflow_flows_collected.inc(len(flows))

            # Flush if buffer is full
            if len(self.flow_buffer) >= self.batch_size:
                await self._flush_buffer()

    async def _periodic_flush(self):
        """Periodically flush buffer based on timeout"""
        while self.running:
            await asyncio.sleep(self.batch_timeout)

            current_time = time.time()
            if current_time - self.last_flush >= self.batch_timeout:
                if self.flow_buffer:
                    await self._flush_buffer()

    async def _flush_buffer(self):
        """Flush buffered flows to database"""
        async with self.lock:
            if not self.flow_buffer:
                return

            flows_to_save = self.flow_buffer.copy()
            self.flow_buffer.clear()

        # Save to database in thread pool
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._save_flows_sync, flows_to_save)

        self.last_flush = time.time()

    def _save_flows_sync(self, flows: List[models.NetworkFlow]):
        """Save flows to database synchronously (called from thread pool)"""
        from .database import SessionLocal

        start_time = time.time()

        try:
            db = SessionLocal()
            try:
                # Bulk insert for performance
                db.bulk_save_objects(flows)
                db.commit()

                duration = time.time() - start_time
                db_write_duration.observe(duration)
                db_batch_size.observe(len(flows))

                logger.debug(f"Saved {len(flows)} flows to database in {duration:.3f}s")

            except Exception as e:
                db.rollback()
                db_write_errors.inc()
                logger.error(f"Error saving flows to database: {e}", exc_info=True)
            finally:
                db.close()

        except Exception as e:
            db_write_errors.inc()
            logger.error(f"Database session error: {e}", exc_info=True)
