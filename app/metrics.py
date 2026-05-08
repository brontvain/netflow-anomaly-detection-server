from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
import logging

logger = logging.getLogger(__name__)

# Netflow Collector Metrics
netflow_packets_received = Counter(
    'netflow_packets_received_total',
    'Total number of NetFlow packets received'
)

netflow_packets_processed = Counter(
    'netflow_packets_processed_total',
    'Total number of NetFlow packets successfully processed'
)

netflow_packets_errors = Counter(
    'netflow_packets_errors_total',
    'Total number of NetFlow packet processing errors'
)

netflow_flows_collected = Counter(
    'netflow_flows_collected_total',
    'Total number of network flows collected'
)

# Database Metrics
db_write_duration = Histogram(
    'db_write_duration_seconds',
    'Duration of database write operations',
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

db_write_errors = Counter(
    'db_write_errors_total',
    'Total number of database write errors'
)

db_batch_size = Histogram(
    'db_batch_size',
    'Size of batch database inserts',
    buckets=[10, 50, 100, 250, 500, 1000, 2500, 5000]
)

# Anomaly Detection Metrics
anomalies_detected = Counter(
    'anomalies_detected_total',
    'Total number of anomalies detected'
)

anomaly_detection_duration = Histogram(
    'anomaly_detection_duration_seconds',
    'Duration of anomaly detection operations',
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

model_training_duration = Histogram(
    'model_training_duration_seconds',
    'Duration of model training operations',
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0]
)

model_training_samples = Gauge(
    'model_training_samples',
    'Number of samples used for model training'
)

model_last_trained = Gauge(
    'model_last_trained_timestamp',
    'Unix timestamp of last model training'
)

# API Metrics
api_requests = Counter(
    'api_requests_total',
    'Total number of API requests',
    ['method', 'endpoint', 'status']
)

api_request_duration = Histogram(
    'api_request_duration_seconds',
    'Duration of API requests',
    ['method', 'endpoint'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)


def metrics_endpoint():
    """Generate Prometheus metrics endpoint response"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
