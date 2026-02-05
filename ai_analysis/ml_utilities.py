"""
ML Model Utilities and Validation - Phase 7

Provides:
- Statistical validation
- Model caching
- Data normalization
- Model evaluation metrics
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import statistics
from functools import wraps
import json

logger = logging.getLogger(__name__)


# ===== CACHING UTILITIES =====

class PredictionCache:
    """Simple cache for model predictions"""
    
    def __init__(self, ttl_minutes: int = 60):
        self.cache: Dict[str, Tuple[Any, datetime]] = {}
        self.ttl = timedelta(minutes=ttl_minutes)
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired"""
        if key not in self.cache:
            return None
        
        value, timestamp = self.cache[key]
        if datetime.now() - timestamp > self.ttl:
            del self.cache[key]
            return None
        
        return value
    
    def set(self, key: str, value: Any):
        """Cache a value"""
        self.cache[key] = (value, datetime.now())
    
    def clear(self):
        """Clear all cache"""
        self.cache.clear()
    
    def cleanup_expired(self):
        """Remove expired entries"""
        now = datetime.now()
        expired_keys = [
            k for k, (_, ts) in self.cache.items()
            if now - ts > self.ttl
        ]
        for key in expired_keys:
            del self.cache[key]
        
        return len(expired_keys)


def cached_prediction(ttl_minutes: int = 60):
    """Decorator for caching prediction results"""
    cache = PredictionCache(ttl_minutes)
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Check cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_value
            
            # Compute and cache
            result = func(*args, **kwargs)
            cache.set(cache_key, result)
            return result
        
        return wrapper
    return decorator


# ===== DATA VALIDATION =====

class DataValidator:
    """Validates audit metrics for ML processing"""
    
    @staticmethod
    def validate_score(score: float) -> bool:
        """Validate audit score"""
        return isinstance(score, (int, float)) and 0 <= score <= 100
    
    @staticmethod
    def validate_findings(count: int) -> bool:
        """Validate findings count"""
        return isinstance(count, int) and count >= 0
    
    @staticmethod
    def validate_audit_metrics(metrics: Dict) -> Tuple[bool, List[str]]:
        """Validate complete audit metrics"""
        errors = []
        
        # Required fields
        required_fields = [
            'overall_score', 'security_score', 'code_quality_score',
            'ip_legal_score', 'team_sustainability_score',
            'findings_count', 'critical_findings'
        ]
        
        for field in required_fields:
            if field not in metrics:
                errors.append(f"Missing required field: {field}")
        
        # Validate score ranges
        score_fields = [k for k in metrics.keys() if 'score' in k]
        for field in score_fields:
            if not DataValidator.validate_score(metrics.get(field, -1)):
                errors.append(f"Invalid score in {field}: {metrics.get(field)}")
        
        # Validate counts
        if not DataValidator.validate_findings(metrics.get('findings_count', -1)):
            errors.append(f"Invalid findings_count")
        
        if not DataValidator.validate_findings(metrics.get('critical_findings', -1)):
            errors.append(f"Invalid critical_findings")
        
        return len(errors) == 0, errors


# ===== DATA NORMALIZATION =====

class DataNormalizer:
    """Normalizes audit data for ML models"""
    
    def __init__(self):
        self.score_min = 0
        self.score_max = 100
        self.findings_mean = 0
        self.findings_std = 1
    
    def fit(self, metrics_list: List[Dict]):
        """Learn normalization parameters from data"""
        if not metrics_list:
            return
        
        findings = [m.get('findings_count', 0) for m in metrics_list]
        
        if findings:
            self.findings_mean = statistics.mean(findings)
            if len(findings) > 1:
                self.findings_std = statistics.stdev(findings)
            else:
                self.findings_std = 1
        
        logger.info(f"Fitted normalizer - findings_mean: {self.findings_mean}, std: {self.findings_std}")
    
    def normalize_score(self, score: float) -> float:
        """Normalize score to 0-1 range"""
        if self.score_max == self.score_min:
            return 0.0
        return (score - self.score_min) / (self.score_max - self.score_min)
    
    def denormalize_score(self, normalized: float) -> float:
        """Denormalize score from 0-1 range"""
        return normalized * (self.score_max - self.score_min) + self.score_min
    
    def normalize_findings(self, count: int) -> float:
        """Normalize findings count using z-score"""
        if self.findings_std == 0:
            return 0.0
        return (count - self.findings_mean) / self.findings_std
    
    def normalize_metrics(self, metrics: Dict) -> Dict:
        """Normalize all metrics"""
        return {
            'overall_score_norm': self.normalize_score(metrics.get('overall_score', 0)),
            'findings_norm': self.normalize_findings(metrics.get('findings_count', 0)),
            'critical_findings_norm': self.normalize_findings(metrics.get('critical_findings', 0)),
            'score_variance': metrics.get('score_variance', 0) / 100  # Normalize to 0-1
        }


# ===== STATISTICAL VALIDATION =====

class StatisticalValidator:
    """Validates model outputs using statistical tests"""
    
    @staticmethod
    def validate_prediction_confidence(
        predicted_score: float,
        confidence: float,
        data_points: int
    ) -> bool:
        """Validate prediction confidence based on data points"""
        # Need at least 3 data points for meaningful prediction
        if data_points < 3:
            return confidence <= 0.5
        
        # Confidence should be reasonable
        return 0 <= confidence <= 1
    
    @staticmethod
    def validate_anomaly_score(
        anomaly_score: float,
        historical_variance: float
    ) -> bool:
        """Validate anomaly score makes sense"""
        # Anomaly score should be 0-1
        if not (0 <= anomaly_score <= 1):
            return False
        
        # If very low variance, anomaly score should be low
        if historical_variance < 1:
            return anomaly_score < 0.5
        
        return True
    
    @staticmethod
    def validate_cluster_size(
        cluster_size: int,
        total_repositories: int
    ) -> bool:
        """Validate cluster size"""
        if total_repositories == 0:
            return cluster_size == 0
        
        # Cluster should have at least 1 item
        # and at most all items
        return 1 <= cluster_size <= total_repositories
    
    @staticmethod
    def calculate_confidence_interval(
        values: List[float],
        confidence_level: float = 0.95
    ) -> Tuple[float, float]:
        """Calculate confidence interval for values"""
        if len(values) < 2:
            mean = statistics.mean(values) if values else 0
            return (mean, mean)
        
        mean = statistics.mean(values)
        std_dev = statistics.stdev(values)
        
        # Simple 95% confidence interval (±1.96 * std_error)
        std_error = std_dev / (len(values) ** 0.5)
        margin = 1.96 * std_error
        
        return (mean - margin, mean + margin)


# ===== MODEL EVALUATION =====

class ModelEvaluator:
    """Evaluates ML model performance"""
    
    def __init__(self):
        self.predictions_log: List[Dict] = []
    
    def log_prediction(
        self,
        repository: str,
        actual_score: float,
        predicted_score: float,
        confidence: float,
        model_name: str
    ):
        """Log prediction for evaluation"""
        self.predictions_log.append({
            'repository': repository,
            'actual': actual_score,
            'predicted': predicted_score,
            'confidence': confidence,
            'model': model_name,
            'timestamp': datetime.now().isoformat(),
            'error': abs(actual_score - predicted_score)
        })
    
    def calculate_mae(self) -> Optional[float]:
        """Calculate Mean Absolute Error"""
        if not self.predictions_log:
            return None
        
        errors = [p['error'] for p in self.predictions_log]
        return statistics.mean(errors)
    
    def calculate_rmse(self) -> Optional[float]:
        """Calculate Root Mean Squared Error"""
        if not self.predictions_log:
            return None
        
        squared_errors = [p['error'] ** 2 for p in self.predictions_log]
        return (statistics.mean(squared_errors)) ** 0.5
    
    def calculate_accuracy(self, tolerance: float = 5.0) -> Optional[float]:
        """Calculate accuracy (% within tolerance)"""
        if not self.predictions_log:
            return None
        
        accurate = sum(1 for p in self.predictions_log if p['error'] <= tolerance)
        return (accurate / len(self.predictions_log)) * 100
    
    def get_performance_summary(self) -> Dict:
        """Get comprehensive performance summary"""
        return {
            'total_predictions': len(self.predictions_log),
            'mean_absolute_error': round(self.calculate_mae(), 2) if self.predictions_log else None,
            'root_mean_squared_error': round(self.calculate_rmse(), 2) if self.predictions_log else None,
            'accuracy_within_5': round(self.calculate_accuracy(5), 1) if self.predictions_log else None,
            'accuracy_within_10': round(self.calculate_accuracy(10), 1) if self.predictions_log else None,
            'average_confidence': round(
                statistics.mean([p['confidence'] for p in self.predictions_log]),
                2
            ) if self.predictions_log else None
        }
    
    def clear_log(self):
        """Clear prediction log"""
        self.predictions_log.clear()


# ===== QUALITY METRICS =====

class QualityMetrics:
    """Calculates quality metrics for audit data"""
    
    @staticmethod
    def data_completeness(metrics: Dict) -> float:
        """Calculate % of non-null required fields"""
        required_fields = [
            'overall_score', 'security_score', 'code_quality_score',
            'findings_count', 'critical_findings'
        ]
        
        present = sum(1 for f in required_fields if f in metrics and metrics[f] is not None)
        return (present / len(required_fields)) * 100
    
    @staticmethod
    def score_consistency(scores: List[float]) -> float:
        """Calculate score consistency (inverse of coefficient of variation)"""
        if len(scores) < 2:
            return 100.0
        
        mean = statistics.mean(scores)
        if mean == 0:
            return 0.0
        
        std_dev = statistics.stdev(scores)
        cv = (std_dev / mean) * 100  # Coefficient of variation
        
        # Convert to consistency (0-100)
        consistency = max(0, 100 - cv)
        return round(consistency, 1)
    
    @staticmethod
    def outlier_detection(values: List[float]) -> List[int]:
        """Detect outliers using IQR method"""
        if len(values) < 4:
            return []
        
        sorted_vals = sorted(values)
        q1_idx = len(sorted_vals) // 4
        q3_idx = (3 * len(sorted_vals)) // 4
        
        q1 = sorted_vals[q1_idx]
        q3 = sorted_vals[q3_idx]
        iqr = q3 - q1
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        outliers = [i for i, v in enumerate(values) if v < lower_bound or v > upper_bound]
        return outliers


# ===== UTILITY FUNCTIONS =====

def calculate_model_readiness(
    data_points: int,
    data_completeness: float,
    data_consistency: float
) -> Dict[str, Any]:
    """Calculate if model is ready for production"""
    
    readiness_score = 0.0
    warnings = []
    
    # Check data quantity
    if data_points >= 50:
        readiness_score += 30
    elif data_points >= 20:
        readiness_score += 15
        warnings.append("Limited historical data (<50 audits)")
    else:
        warnings.append("Very limited data (<20 audits)")
    
    # Check completeness
    if data_completeness >= 95:
        readiness_score += 30
    elif data_completeness >= 80:
        readiness_score += 15
        warnings.append("Data missing some fields")
    else:
        warnings.append("Significant missing data")
    
    # Check consistency
    if data_consistency >= 90:
        readiness_score += 30
    elif data_consistency >= 70:
        readiness_score += 15
        warnings.append("Inconsistent data patterns")
    else:
        warnings.append("Highly variable data")
    
    # Remaining 10%
    readiness_score += 10
    
    return {
        'readiness_score': round(min(100, readiness_score), 1),
        'is_production_ready': readiness_score >= 75,
        'warnings': warnings,
        'recommendation': 'Ready for production' if readiness_score >= 75 else 'Needs more data'
    }


def export_model_metrics(metrics: Dict) -> str:
    """Export metrics as JSON"""
    return json.dumps(metrics, indent=2, default=str)


def log_model_performance(model_name: str, metrics: Dict):
    """Log model performance to logger"""
    logger.info(f"Model Performance - {model_name}")
    for key, value in metrics.items():
        logger.info(f"  {key}: {value}")
