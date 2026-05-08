from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, create_engine, Index
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class NetworkFlow(Base):
    __tablename__ = "network_flows"

    id = Column(Integer, primary_key=True, index=True)
    src_ip = Column(String, index=True)
    dst_ip = Column(String, index=True)
    src_port = Column(Integer)
    dst_port = Column(Integer)
    protocol = Column(Integer, index=True)
    start_time = Column(DateTime, index=True)
    end_time = Column(DateTime)
    packets = Column(Integer)
    bytes = Column(Integer)
    flags = Column(Integer)
    tos = Column(Integer)
    input_snmp = Column(Integer)
    output_snmp = Column(Integer)
    src_as = Column(Integer)
    dst_as = Column(Integer)
    src_mask = Column(Integer)
    dst_mask = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Anomaly detection fields
    is_anomaly = Column(Integer, default=0, index=True)  # 0: normal, 1: anomaly
    anomaly_score = Column(Float, nullable=True)
    anomaly_type = Column(String, nullable=True)  # e.g., "unusual_port", "unusual_protocol"

    # Composite indexes for common queries
    __table_args__ = (
        Index('idx_created_anomaly', 'created_at', 'is_anomaly'),
        Index('idx_src_dst_ip', 'src_ip', 'dst_ip'),
        Index('idx_time_range', 'start_time', 'end_time'),
    )

class AnomalyDetectionModel(Base):
    __tablename__ = "anomaly_detection_models"

    id = Column(Integer, primary_key=True, index=True)
    model_type = Column(String)  # e.g., "isolation_forest", "one_class_svm"
    created_at = Column(DateTime, default=datetime.utcnow)
    last_trained = Column(DateTime)
    model_parameters = Column(String)  # JSON string of model parameters
    accuracy = Column(Float, nullable=True)
    is_active = Column(Integer, default=1)  # 0: inactive, 1: active 