from fastapi import FastAPI, Depends, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel, Field
import json
import asyncio

from . import models, database
from .config import settings
from .netflow_collector import NetflowCollector
from .anomaly_detection import AnomalyDetector
from .logging_config import setup_logging
from .metrics import metrics_endpoint, api_requests, api_request_duration
import time
import logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Netflow v5 Server with Anomaly Detection",
    description="High-performance NetFlow v5 collector and analyzer with ML-based anomaly detection",
    version="2.0.0"
)

# CORS middleware with configurable origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
collector = NetflowCollector()
detector = AnomalyDetector()


# Pydantic models for request validation
class FlowQuery(BaseModel):
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=100, ge=1, le=1000)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_anomaly: Optional[bool] = None


class FlowStatsResponse(BaseModel):
    total_flows: int
    anomaly_flows: int
    anomaly_rate: float
    protocol_distribution: dict


class ModelStatusResponse(BaseModel):
    status: str
    model_type: Optional[str] = None
    last_trained: Optional[datetime] = None
    parameters: Optional[dict] = None
    accuracy: Optional[float] = None


class HealthResponse(BaseModel):
    status: str
    collector_running: bool
    model_trained: bool
    database_connected: bool


# Middleware for metrics
@app.middleware("http")
async def metrics_middleware(request, call_next):
    start_time = time.time()

    response = await call_next(request)

    duration = time.time() - start_time
    api_requests.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()

    api_request_duration.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)

    return response


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("Starting Netflow v5 Server...")

    # Start the Netflow collector
    await collector.start()

    # Initialize database
    models.Base.metadata.create_all(bind=database.engine)

    # Train model in background if not already trained
    if not detector.is_trained:
        asyncio.create_task(train_model_background())

    logger.info("Application startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down...")
    await collector.stop()
    logger.info("Shutdown complete")


async def train_model_background():
    """Train model in background task"""
    await asyncio.sleep(5)  # Wait for some data to be collected
    logger.info("Starting background model training...")

    db = database.SessionLocal()
    try:
        detector.train(db)
    except Exception as e:
        logger.error(f"Background training failed: {e}")
    finally:
        db.close()


# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for monitoring and load balancers"""
    db_connected = True
    try:
        db = database.SessionLocal()
        db.execute("SELECT 1")
        db.close()
    except Exception as e:
        db_connected = False
        logger.error(f"Database health check failed: {e}")

    return HealthResponse(
        status="healthy" if db_connected else "unhealthy",
        collector_running=collector.running,
        model_trained=detector.is_trained,
        database_connected=db_connected
    )


# Prometheus metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return metrics_endpoint()


# API Endpoints
@app.get("/flows/")
async def get_flows(
    db: Session = Depends(database.get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    is_anomaly: Optional[bool] = None
):
    """Get network flows with optional filtering"""
    # Enforce max limit
    limit = min(limit, settings.API_MAX_QUERY_LIMIT)

    query = db.query(models.NetworkFlow)

    if start_time:
        query = query.filter(models.NetworkFlow.start_time >= start_time)
    if end_time:
        query = query.filter(models.NetworkFlow.end_time <= end_time)
    if is_anomaly is not None:
        query = query.filter(models.NetworkFlow.is_anomaly == (1 if is_anomaly else 0))

    # Order by most recent first
    query = query.order_by(models.NetworkFlow.created_at.desc())

    return query.offset(skip).limit(limit).all()


@app.get("/flows/stats", response_model=FlowStatsResponse)
async def get_flow_stats(db: Session = Depends(database.get_db)):
    """Get flow statistics"""
    total_flows = db.query(models.NetworkFlow).count()
    anomaly_flows = db.query(models.NetworkFlow).filter(
        models.NetworkFlow.is_anomaly == 1
    ).count()

    anomaly_rate = anomaly_flows / total_flows if total_flows > 0 else 0.0

    # Get protocol distribution
    protocol_stats = db.query(
        models.NetworkFlow.protocol,
        func.count(models.NetworkFlow.id)
    ).group_by(models.NetworkFlow.protocol).all()

    # Map protocol numbers to names
    protocol_names = {1: "ICMP", 6: "TCP", 17: "UDP"}
    protocol_dist = {
        protocol_names.get(proto, f"Protocol_{proto}"): count
        for proto, count in protocol_stats
    }

    return FlowStatsResponse(
        total_flows=total_flows,
        anomaly_flows=anomaly_flows,
        anomaly_rate=anomaly_rate,
        protocol_distribution=protocol_dist
    )


@app.get("/flows/anomalies")
async def get_anomalies(
    db: Session = Depends(database.get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get detected anomalies"""
    limit = min(limit, settings.API_MAX_QUERY_LIMIT)

    return db.query(models.NetworkFlow).filter(
        models.NetworkFlow.is_anomaly == 1
    ).order_by(models.NetworkFlow.created_at.desc()).offset(skip).limit(limit).all()


@app.post("/flows/detect")
async def detect_anomalies_endpoint(
    background_tasks: BackgroundTasks,
    db: Session = Depends(database.get_db),
    limit: int = Query(1000, ge=1, le=10000)
):
    """Run anomaly detection on recent unprocessed flows"""
    if not detector.is_trained:
        raise HTTPException(status_code=503, detail="Model not trained yet")

    # Get recent flows without anomaly detection
    flows = db.query(models.NetworkFlow).filter(
        models.NetworkFlow.is_anomaly == 0,
        models.NetworkFlow.anomaly_score.is_(None)
    ).limit(limit).all()

    if not flows:
        return {"status": "no_flows_to_process", "processed": 0}

    # Run detection
    detector.detect_anomalies(db, flows)

    return {"status": "success", "processed": len(flows)}


@app.post("/model/train")
async def train_model(background_tasks: BackgroundTasks, db: Session = Depends(database.get_db)):
    """Retrain the anomaly detection model"""
    # Run training in background
    background_tasks.add_task(train_model_task, db)
    return {"status": "training_started"}


def train_model_task(db: Session):
    """Background task for model training"""
    success = detector.train(db)
    if success:
        logger.info("Model training completed successfully")
    else:
        logger.error("Model training failed")


@app.get("/model/status", response_model=ModelStatusResponse)
async def get_model_status(db: Session = Depends(database.get_db)):
    """Get current model status"""
    model = db.query(models.AnomalyDetectionModel).filter(
        models.AnomalyDetectionModel.is_active == 1
    ).first()

    if not model:
        return ModelStatusResponse(status="no_active_model")

    return ModelStatusResponse(
        status="active",
        model_type=model.model_type,
        last_trained=model.last_trained,
        parameters=json.loads(model.model_parameters),
        accuracy=model.accuracy
    )


@app.post("/cleanup")
async def cleanup_old_data(
    background_tasks: BackgroundTasks,
    db: Session = Depends(database.get_db)
):
    """Clean up data older than configured retention period"""
    deleted_count = detector.cleanup_old_data(db)
    return {"status": "success", "deleted_records": deleted_count}


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "Netflow v5 Server with Anomaly Detection",
        "version": "2.0.0",
        "status": "operational",
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics",
            "flows": "/flows/",
            "stats": "/flows/stats",
            "anomalies": "/flows/anomalies",
            "model_status": "/model/status",
            "docs": "/docs"
        }
    }
