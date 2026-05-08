#!/usr/bin/env python3
"""
Database migration script to add new indexes and update schema
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import engine
from app.models import Base
from sqlalchemy import inspect, text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_index_exists(connection, index_name):
    """Check if an index exists"""
    result = connection.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_indexes
            WHERE indexname = :index_name
        );
    """), {"index_name": index_name})
    return result.scalar()


def migrate():
    """Run database migrations"""
    logger.info("Starting database migration...")

    with engine.connect() as connection:
        # Start transaction
        trans = connection.begin()

        try:
            # Add indexes if they don't exist
            indexes_to_create = [
                ("CREATE INDEX IF NOT EXISTS idx_network_flows_src_ip ON network_flows(src_ip);", "idx_network_flows_src_ip"),
                ("CREATE INDEX IF NOT EXISTS idx_network_flows_dst_ip ON network_flows(dst_ip);", "idx_network_flows_dst_ip"),
                ("CREATE INDEX IF NOT EXISTS idx_network_flows_protocol ON network_flows(protocol);", "idx_network_flows_protocol"),
                ("CREATE INDEX IF NOT EXISTS idx_network_flows_start_time ON network_flows(start_time);", "idx_network_flows_start_time"),
                ("CREATE INDEX IF NOT EXISTS idx_network_flows_created_at ON network_flows(created_at);", "idx_network_flows_created_at"),
                ("CREATE INDEX IF NOT EXISTS idx_network_flows_is_anomaly ON network_flows(is_anomaly);", "idx_network_flows_is_anomaly"),
                ("CREATE INDEX IF NOT EXISTS idx_created_anomaly ON network_flows(created_at, is_anomaly);", "idx_created_anomaly"),
                ("CREATE INDEX IF NOT EXISTS idx_src_dst_ip ON network_flows(src_ip, dst_ip);", "idx_src_dst_ip"),
                ("CREATE INDEX IF NOT EXISTS idx_time_range ON network_flows(start_time, end_time);", "idx_time_range"),
            ]

            for sql, index_name in indexes_to_create:
                logger.info(f"Creating index: {index_name}")
                connection.execute(text(sql))

            # Commit transaction
            trans.commit()
            logger.info("Migration completed successfully!")

        except Exception as e:
            trans.rollback()
            logger.error(f"Migration failed: {e}")
            raise


if __name__ == "__main__":
    migrate()
