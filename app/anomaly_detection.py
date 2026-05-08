import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from . import models
from .config import settings
from .metrics import (
    anomalies_detected,
    anomaly_detection_duration,
    model_training_duration,
    model_training_samples,
    model_last_trained
)
import json
import logging
import joblib
import os
import time

logger = logging.getLogger(__name__)


class AnomalyDetector:
    def __init__(self):
        self.model = None
        self.scaler = None
        self.is_trained = False
        self.contamination = settings.MODEL_CONTAMINATION
        self.n_estimators = settings.MODEL_N_ESTIMATORS

        # Ensure model directory exists
        os.makedirs(os.path.dirname(settings.MODEL_PATH), exist_ok=True)

        # Try to load existing model
        self._load_model()

    def _load_model(self):
        """Load pre-trained model from disk"""
        try:
            if os.path.exists(settings.MODEL_PATH) and os.path.exists(settings.SCALER_PATH):
                self.model = joblib.load(settings.MODEL_PATH)
                self.scaler = joblib.load(settings.SCALER_PATH)
                self.is_trained = True
                logger.info("Loaded pre-trained anomaly detection model")
                return True
        except Exception as e:
            logger.warning(f"Could not load existing model: {e}")

        # Initialize new model
        self.model = IsolationForest(
            contamination=self.contamination,
            random_state=42,
            n_estimators=self.n_estimators,
            n_jobs=-1
        )
        self.scaler = StandardScaler()
        return False

    def _save_model(self):
        """Save trained model to disk"""
        try:
            joblib.dump(self.model, settings.MODEL_PATH)
            joblib.dump(self.scaler, settings.SCALER_PATH)
            logger.info(f"Saved model to {settings.MODEL_PATH}")
        except Exception as e:
            logger.error(f"Error saving model: {e}")

    def prepare_features(self, flows):
        """Prepare enhanced features for anomaly detection"""
        features = []

        for flow in flows:
            # Calculate derived features
            duration = (flow.end_time - flow.start_time).total_seconds()
            bytes_per_packet = flow.bytes / max(flow.packets, 1)

            # Time-based features
            hour = flow.start_time.hour
            day_of_week = flow.start_time.weekday()

            # Port characteristics
            src_port_is_ephemeral = 1 if flow.src_port > 1024 else 0
            dst_port_is_ephemeral = 1 if flow.dst_port > 1024 else 0
            dst_port_is_common = 1 if flow.dst_port in [80, 443, 22, 53, 21, 25] else 0

            # Protocol encoding (TCP=6, UDP=17, ICMP=1)
            is_tcp = 1 if flow.protocol == 6 else 0
            is_udp = 1 if flow.protocol == 17 else 0
            is_icmp = 1 if flow.protocol == 1 else 0

            feature_vector = [
                flow.src_port,
                flow.dst_port,
                flow.protocol,
                flow.packets,
                flow.bytes,
                flow.src_as,
                flow.dst_as,
                duration,  # Flow duration
                bytes_per_packet,  # Bytes per packet ratio
                hour,  # Hour of day
                day_of_week,  # Day of week
                src_port_is_ephemeral,
                dst_port_is_ephemeral,
                dst_port_is_common,
                is_tcp,
                is_udp,
                is_icmp,
                flow.flags if flow.flags else 0,
                flow.tos if flow.tos else 0
            ]
            features.append(feature_vector)

        return np.array(features)

    def train(self, db: Session):
        """Train the anomaly detection model with validation"""
        start_time = time.time()

        try:
            # Get flows from configured training period
            cutoff_time = datetime.utcnow() - timedelta(hours=settings.MODEL_TRAINING_HOURS)
            flows = db.query(models.NetworkFlow).filter(
                models.NetworkFlow.created_at >= cutoff_time
            ).all()

            if len(flows) < settings.MODEL_MIN_TRAINING_SAMPLES:
                logger.warning(f"Not enough data for training: {len(flows)} < {settings.MODEL_MIN_TRAINING_SAMPLES}")
                return False

            logger.info(f"Training model with {len(flows)} samples")
            model_training_samples.set(len(flows))

            # Prepare features
            X = self.prepare_features(flows)

            # Split for validation
            X_train, X_test = train_test_split(X, test_size=0.2, random_state=42)

            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)

            # Train model
            self.model.fit(X_train_scaled)
            self.is_trained = True

            # Calculate validation metrics
            train_predictions = self.model.predict(X_train_scaled)
            test_predictions = self.model.predict(X_test_scaled)

            train_anomalies = np.sum(train_predictions == -1)
            test_anomalies = np.sum(test_predictions == -1)

            train_anomaly_rate = train_anomalies / len(train_predictions)
            test_anomaly_rate = test_anomalies / len(test_predictions)

            # Simple accuracy: how close to expected contamination rate
            accuracy = 1.0 - abs(test_anomaly_rate - self.contamination)

            logger.info(f"Training anomaly rate: {train_anomaly_rate:.3f}")
            logger.info(f"Test anomaly rate: {test_anomaly_rate:.3f}")
            logger.info(f"Model accuracy score: {accuracy:.3f}")

            # Save model to disk
            self._save_model()

            # Save model metadata to database
            # Deactivate old models
            db.query(models.AnomalyDetectionModel).update({"is_active": 0})

            model_metadata = models.AnomalyDetectionModel(
                model_type="isolation_forest",
                last_trained=datetime.utcnow(),
                model_parameters=json.dumps({
                    "contamination": self.contamination,
                    "n_estimators": self.n_estimators,
                    "train_samples": len(X_train),
                    "test_samples": len(X_test),
                    "train_anomaly_rate": float(train_anomaly_rate),
                    "test_anomaly_rate": float(test_anomaly_rate)
                }),
                accuracy=accuracy,
                is_active=1
            )
            db.add(model_metadata)
            db.commit()

            duration = time.time() - start_time
            model_training_duration.observe(duration)
            model_last_trained.set(time.time())

            logger.info(f"Model trained successfully in {duration:.2f}s")
            return True

        except Exception as e:
            logger.error(f"Error training model: {e}", exc_info=True)
            return False

    def detect_anomalies(self, db: Session, flows):
        """Detect anomalies in network flows with bulk update"""
        if not self.is_trained:
            logger.warning("Model not trained yet")
            return []

        start_time = time.time()

        try:
            # Prepare features
            X = self.prepare_features(flows)

            # Scale features
            X_scaled = self.scaler.transform(X)

            # Predict anomalies
            predictions = self.model.predict(X_scaled)
            scores = self.model.score_samples(X_scaled)

            # Prepare bulk updates
            updates = []
            anomaly_count = 0

            for i, flow in enumerate(flows):
                is_anomaly = 1 if predictions[i] == -1 else 0

                update_dict = {
                    'id': flow.id,
                    'is_anomaly': is_anomaly,
                    'anomaly_score': float(scores[i])
                }

                if is_anomaly:
                    anomaly_count += 1
                    # Determine anomaly type
                    if flow.dst_port > 1024 and flow.dst_port not in [80, 443, 22, 53]:
                        update_dict['anomaly_type'] = "unusual_port"
                    elif flow.protocol not in [1, 6, 17]:  # ICMP, TCP, UDP
                        update_dict['anomaly_type'] = "unusual_protocol"
                    elif flow.packets > 10000:
                        update_dict['anomaly_type'] = "high_packet_count"
                    elif flow.bytes > 10000000:  # 10MB
                        update_dict['anomaly_type'] = "high_byte_count"
                    else:
                        update_dict['anomaly_type'] = "general_anomaly"

                updates.append(update_dict)

            # Bulk update
            if updates:
                db.bulk_update_mappings(models.NetworkFlow, updates)
                db.commit()

            # Update metrics
            anomalies_detected.inc(anomaly_count)
            duration = time.time() - start_time
            anomaly_detection_duration.observe(duration)

            logger.info(f"Detected {anomaly_count} anomalies in {len(flows)} flows ({duration:.3f}s)")

            return flows

        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}", exc_info=True)
            return []

    def cleanup_old_data(self, db: Session):
        """Remove data older than configured retention period"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=settings.DATA_RETENTION_DAYS)
            deleted_count = db.query(models.NetworkFlow).filter(
                models.NetworkFlow.created_at < cutoff_time
            ).delete(synchronize_session=False)
            db.commit()
            logger.info(f"Cleaned up {deleted_count} old records")
            return deleted_count
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
            db.rollback()
            return 0
