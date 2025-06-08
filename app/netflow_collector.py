import socket
import struct
import threading
from datetime import datetime
from sqlalchemy.orm import Session
from . import models
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NetflowCollector:
    def __init__(self, host='0.0.0.0', port=2055):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.host, self.port))
        self.running = False
        self.thread = None

    def start(self):
        """Start the collector in a separate thread"""
        self.running = True
        self.thread = threading.Thread(target=self._collect)
        self.thread.daemon = True
        self.thread.start()
        logger.info(f"Netflow collector started on {self.host}:{self.port}")

    def stop(self):
        """Stop the collector"""
        self.running = False
        if self.thread:
            self.thread.join()
        self.socket.close()
        logger.info("Netflow collector stopped")

    def _collect(self):
        """Main collection loop"""
        while self.running:
            try:
                data, addr = self.socket.recvfrom(4096)
                self._process_packet(data, addr)
            except Exception as e:
                logger.error(f"Error processing packet: {e}")

    def _process_packet(self, data, addr):
        """Process a single Netflow packet"""
        try:
            # Netflow v5 header (26 bytes)
            # Check if we have enough data for the header
            if len(data) < 26:
                logger.warning(f"Packet too small for Netflow header: {len(data)} bytes")
                return
                
            version, count, sys_uptime, unix_secs, unix_nsecs, flow_sequence, engine_type, engine_id, sampling_interval = struct.unpack('!HHIIIIIBB', data[:26])
            
            if version != 5:
                logger.warning(f"Unsupported Netflow version: {version}")
                return

            # Process each flow record (44 bytes actual struct size)
            offset = 26
            for _ in range(count):
                flow_data = data[offset:offset+44]
                if len(flow_data) < 44:
                    break

                # Unpack flow record (Netflow v5 format - 44 bytes actual)  
                # Adjusted format to match actual struct size requirement
                flow_record = struct.unpack('!IIIHHIIIHHBBBBHHBBxx', flow_data)
                
                (src_addr, dst_addr, nexthop, input, output, packets, bytes,
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
                    bytes=bytes,
                    flags=tcp_flags,
                    tos=tos,
                    input_snmp=input,
                    output_snmp=output,
                    src_as=src_as,
                    dst_as=dst_as,
                    src_mask=src_mask,
                    dst_mask=dst_mask
                )

                # Save to database
                self._save_flow(flow)
                offset += 44

        except Exception as e:
            logger.error(f"Error processing flow record: {e}")

    def _save_flow(self, flow):
        """Save flow to database"""
        try:
            from .database import SessionLocal
            db = SessionLocal()
            db.add(flow)
            db.commit()
        except Exception as e:
            logger.error(f"Error saving flow to database: {e}")
        finally:
            db.close() 