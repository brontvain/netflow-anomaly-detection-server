import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from . import models
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AnomalyDetector:
    def __init__(self, contamination=0.1):
        self.model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )
        self.scaler = StandardScaler()
        self.is_trained = False

    def prepare_features(self, flows):
        """Prepare features for anomaly detection"""
        features = []
        for flow in flows:
            feature_vector = [
                flow.src_port,
                flow.dst_port,
                flow.protocol,
                flow.packets,
                flow.bytes,
                flow.src_as,
                flow.dst_as
            ]
            features.append(feature_vector)
        return np.array(features)

    def train(self, db: Session):
        """Train the anomaly detection model"""
        try:
            # Get flows from the last 24 hours for training
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            flows = db.query(models.NetworkFlow).filter(
                models.NetworkFlow.created_at >= cutoff_time
            ).all()

            if len(flows) < 100:
                logger.warning("Not enough data for training")
                return False

            # Prepare features
            X = self.prepare_features(flows)
            
            # Scale features
            X_scaled = self.scaler.fit_transform(X)
            
            # Train model
            self.model.fit(X_scaled)
            self.is_trained = True

            # Save model metadata
            model_metadata = models.AnomalyDetectionModel(
                model_type="isolation_forest",
                last_trained=datetime.utcnow(),
                model_parameters=json.dumps({
                    "contamination": self.model.contamination,
                    "n_estimators": self.model.n_estimators
                }),
                is_active=1
            )
            db.add(model_metadata)
            db.commit()

            logger.info("Anomaly detection model trained successfully")
            return True

        except Exception as e:
            logger.error(f"Error training model: {e}")
            return False

    def detect_anomalies(self, db: Session, flows):
        """Detect anomalies in network flows"""
        if not self.is_trained:
            logger.warning("Model not trained yet")
            return []

        try:
            # Prepare features
            X = self.prepare_features(flows)
            
            # Scale features
            X_scaled = self.scaler.transform(X)
            
            # Predict anomalies
            predictions = self.model.predict(X_scaled)
            scores = self.model.score_samples(X_scaled)
            
            # Update flows with anomaly information
            for i, flow in enumerate(flows):
                flow.is_anomaly = 1 if predictions[i] == -1 else 0
                flow.anomaly_score = float(scores[i])
                
                if predictions[i] == -1:
                    # Determine anomaly type
                    if flow.dst_port > 1024 and flow.dst_port not in [80, 443, 22, 53]:
                        flow.anomaly_type = "unusual_port"
                    elif flow.protocol not in [1, 6, 17]:  # ICMP, TCP, UDP
                        flow.anomaly_type = "unusual_protocol"
                    else:
                        flow.anomaly_type = "general_anomaly"

            db.commit()
            return flows

        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
            return []

    def cleanup_old_data(self, db: Session):
        """Remove data older than 5 days"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=5)
            db.query(models.NetworkFlow).filter(
                models.NetworkFlow.created_at < cutoff_time
            ).delete()
            db.commit()
            logger.info("Cleaned up old data successfully")
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}") 