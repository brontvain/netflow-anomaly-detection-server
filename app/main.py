from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List, Optional
import json

from . import models, database
from .netflow_collector import NetflowCollector
from .anomaly_detection import AnomalyDetector

app = FastAPI(title="Netflow v5 Server")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
collector = NetflowCollector()
detector = AnomalyDetector()

@app.on_event("startup")
async def startup_event():
    # Start the Netflow collector
    collector.start()
    
    # Initialize database
    models.Base.metadata.create_all(bind=database.engine)
    
    # Train initial model
    db = database.SessionLocal()
    detector.train(db)
    db.close()

@app.on_event("shutdown")
async def shutdown_event():
    collector.stop()

# API Endpoints
@app.get("/flows/")
def get_flows(
    db: Session = Depends(database.get_db),
    skip: int = 0,
    limit: int = 100,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    is_anomaly: Optional[bool] = None
):
    """Get network flows with optional filtering"""
    query = db.query(models.NetworkFlow)
    
    if start_time:
        query = query.filter(models.NetworkFlow.start_time >= start_time)
    if end_time:
        query = query.filter(models.NetworkFlow.end_time <= end_time)
    if is_anomaly is not None:
        query = query.filter(models.NetworkFlow.is_anomaly == is_anomaly)
    
    return query.offset(skip).limit(limit).all()

@app.get("/flows/stats")
def get_flow_stats(db: Session = Depends(database.get_db)):
    """Get flow statistics"""
    total_flows = db.query(models.NetworkFlow).count()
    anomaly_flows = db.query(models.NetworkFlow).filter(
        models.NetworkFlow.is_anomaly == 1
    ).count()
    
    # Get protocol distribution
    protocol_stats = db.query(
        models.NetworkFlow.protocol,
        func.count(models.NetworkFlow.id)
    ).group_by(models.NetworkFlow.protocol).all()
    
    return {
        "total_flows": total_flows,
        "anomaly_flows": anomaly_flows,
        "protocol_distribution": dict(protocol_stats)
    }

@app.get("/flows/anomalies")
def get_anomalies(
    db: Session = Depends(database.get_db),
    skip: int = 0,
    limit: int = 100
):
    """Get detected anomalies"""
    return db.query(models.NetworkFlow).filter(
        models.NetworkFlow.is_anomaly == 1
    ).offset(skip).limit(limit).all()

@app.post("/model/train")
def train_model(db: Session = Depends(database.get_db)):
    """Retrain the anomaly detection model"""
    success = detector.train(db)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to train model")
    return {"status": "success"}

@app.get("/model/status")
def get_model_status(db: Session = Depends(database.get_db)):
    """Get current model status"""
    model = db.query(models.AnomalyDetectionModel).filter(
        models.AnomalyDetectionModel.is_active == 1
    ).first()
    
    if not model:
        return {"status": "no_active_model"}
    
    return {
        "model_type": model.model_type,
        "last_trained": model.last_trained,
        "parameters": json.loads(model.model_parameters),
        "accuracy": model.accuracy
    }

@app.post("/cleanup")
def cleanup_old_data(db: Session = Depends(database.get_db)):
    """Clean up data older than 5 days"""
    detector.cleanup_old_data(db)
    return {"status": "success"} 