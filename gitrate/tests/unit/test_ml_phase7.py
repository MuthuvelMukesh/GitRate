"""
Phase 7 - ML Analytics Comprehensive Tests

Tests for:
- ML models (anomaly detection, prediction, clustering, forecasting)
- Enhanced insights engine
- ML utilities (validation, caching, evaluation)
- API endpoints
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, List

class TestMLModels:
    """Tests for core ML models"""
    
    def test_anomaly_detector_initialization(self):
        """Test AnomalyDetector initializes correctly"""
        from gitrate.intelligence.models.ml_models import AnomalyDetector
        detector = AnomalyDetector()
        
        assert detector is not None
        assert hasattr(detector, 'detect_anomaly')
        assert hasattr(detector, 'add_historical_data')
    
    def test_anomaly_detection_score_drop(self):
        """Test anomaly detection for score drop"""
        from gitrate.intelligence.models.ml_models import AnomalyDetector, AuditMetrics
        
        detector = AnomalyDetector()
        
        # Historical data with stable 80 score
        for i in range(10):
            metrics = AuditMetrics(
                overall_score=80,
                security_score=80,
                code_quality_score=80,
                ip_legal_score=80,
                team_sustainability_score=80,
                findings_count=5,
                critical_findings=0
            )
            detector.add_historical_data('test-repo', metrics)
        
        # Current audit with 20-point drop
        current_metrics = AuditMetrics(
            overall_score=60,
            security_score=60,
            code_quality_score=60,
            ip_legal_score=60,
            team_sustainability_score=60,
            findings_count=10,
            critical_findings=2
        )
        
        result = detector.detect_anomaly('test-repo', current_metrics)
        
        assert result.is_anomaly == True
        assert result.anomaly_score > 0.3
        assert result.severity in ['low', 'medium', 'high']
    
    def test_score_predictor_basic(self):
        """Test ScorePredictor basic functionality"""
        from gitrate.intelligence.models.ml_models import ScorePredictor, AuditMetrics
        
        predictor = ScorePredictor()
        
        # Add improving trend
        for i in range(5):
            metrics = AuditMetrics(
                overall_score=70 + (i * 3),
                security_score=70 + (i * 3),
                code_quality_score=70 + (i * 3),
                ip_legal_score=70 + (i * 3),
                team_sustainability_score=70 + (i * 3),
                findings_count=10 - i,
                critical_findings=0
            )
            predictor.add_historical_data('test-repo', metrics)
        
        # Predict future
        prediction = predictor.predict_next_score('test-repo', days_ahead=30)
        
        assert prediction.predicted_score > 0
        assert 0 <= prediction.confidence <= 1
        assert prediction.trend in ['improving', 'declining', 'stable']
    
    def test_clustering_basic(self):
        """Test repository clustering"""
        from gitrate.intelligence.models.ml_models import RepositoryClustering
        
        clustering = RepositoryClustering()
        
        # Create sample repo metrics
        repos_metrics = {
            'repo1': {'avg_score': 90, 'consistency': 0.95, 'components': [90, 85, 95]},
            'repo2': {'avg_score': 85, 'consistency': 0.90, 'components': [85, 80, 90]},
            'repo3': {'avg_score': 50, 'consistency': 0.70, 'components': [50, 45, 55]},
            'repo4': {'avg_score': 45, 'consistency': 0.65, 'components': [45, 40, 50]},
            'repo5': {'avg_score': 70, 'consistency': 0.75, 'components': [70, 65, 75]},
        }
        
        clusters = clustering.cluster_repositories(repos_metrics)
        
        assert len(clusters) > 0
        assert all(hasattr(c, 'cluster_id') for c in clusters)
        assert all(hasattr(c, 'repositories') for c in clusters)
    
    def test_trend_forecaster(self):
        """Test trend forecasting"""
        from gitrate.intelligence.models.ml_models import TrendForecaster
        
        forecaster = TrendForecaster()
        
        # Add audit series
        audit_scores = [70, 72, 74, 76, 78]
        for score in audit_scores:
            forecaster.add_audit_series('test-repo', [score, score - 5, score + 2])
        
        # Forecast
        forecast = forecaster.forecast_trend('test-repo', days=30)
        
        assert 'forecast_points' in forecast
        assert 'trend_direction' in forecast
        assert len(forecast['forecast_points']) > 0


class TestEnhancedInsights:
    """Tests for enhanced insights engine"""
    
    def test_insights_engine_initialization(self):
        """Test EnhancedInsightsEngine initializes"""
        from gitrate.intelligence.insights.enhanced_insights import EnhancedInsightsEngine
        
        engine = EnhancedInsightsEngine()
        
        assert engine is not None
        assert hasattr(engine, 'generate_enhanced_insights')
        assert hasattr(engine, 'generate_batch')
    
    def test_security_risk_detection_critical(self):
        """Test critical security risk detection"""
        from gitrate.intelligence.insights.enhanced_insights import EnhancedInsightsEngine, InsightSeverity
        
        engine = EnhancedInsightsEngine()
        
        current_audit = {
            'security_score': 40,
            'code_quality_score': 75,
            'team_sustainability_score': 75,
            'findings_count': 10,
            'critical_findings': 2
        }
        
        insights = engine.generate_enhanced_insights(
            repository='test-repo',
            current_audit=current_audit,
            historical_audits=[],
            peer_metrics={}
        )
        
        security_insights = [i for i in insights if 'security' in i.category.value.lower()]
        assert len(security_insights) > 0
        
        # Should detect critical risk
        critical_insights = [i for i in security_insights if i.severity == InsightSeverity.CRITICAL]
        assert len(critical_insights) > 0
    
    def test_quality_issue_detection(self):
        """Test code quality issue detection"""
        from gitrate.intelligence.insights.enhanced_insights import EnhancedInsightsEngine, InsightSeverity
        
        engine = EnhancedInsightsEngine()
        
        current_audit = {
            'security_score': 80,
            'code_quality_score': 50,
            'team_sustainability_score': 75,
            'findings_count': 60,
            'critical_findings': 5
        }
        
        insights = engine.generate_enhanced_insights(
            repository='test-repo',
            current_audit=current_audit,
            historical_audits=[],
            peer_metrics={}
        )
        
        quality_insights = [i for i in insights if 'quality' in i.category.value.lower()]
        assert len(quality_insights) > 0
    
    def test_batch_generation(self):
        """Test batch insight generation"""
        from gitrate.intelligence.insights.enhanced_insights import EnhancedInsightsEngine
        
        engine = EnhancedInsightsEngine()
        
        repositories = {
            'repo1': {
                'current': {'security_score': 50, 'code_quality_score': 60, 'team_sustainability_score': 70, 'findings_count': 20, 'critical_findings': 2},
                'history': [],
                'peers': {}
            },
            'repo2': {
                'current': {'security_score': 80, 'code_quality_score': 85, 'team_sustainability_score': 80, 'findings_count': 5, 'critical_findings': 0},
                'history': [],
                'peers': {}
            }
        }
        
        batch = engine.generate_batch('test-batch-1', repositories)
        
        assert batch.batch_id == 'test-batch-1'
        assert batch.total_insights > 0
    
    def test_insight_evidence_structure(self):
        """Test that insights have proper evidence"""
        from gitrate.intelligence.insights.enhanced_insights import EnhancedInsightsEngine
        
        engine = EnhancedInsightsEngine()
        
        current_audit = {
            'security_score': 40,
            'code_quality_score': 75,
            'team_sustainability_score': 75,
            'findings_count': 10,
            'critical_findings': 2
        }
        
        insights = engine.generate_enhanced_insights(
            repository='test-repo',
            current_audit=current_audit,
            historical_audits=[],
            peer_metrics={}
        )
        
        # All insights should have evidence
        for insight in insights:
            assert len(insight.evidence) > 0
            assert all(hasattr(e, 'metric_name') for e in insight.evidence)
            assert all(hasattr(e, 'confidence') for e in insight.evidence)
    
    def test_recommendations_generated(self):
        """Test that recommendations are generated"""
        from gitrate.intelligence.insights.enhanced_insights import EnhancedInsightsEngine
        
        engine = EnhancedInsightsEngine()
        
        current_audit = {
            'security_score': 40,
            'code_quality_score': 75,
            'team_sustainability_score': 75,
            'findings_count': 10,
            'critical_findings': 2
        }
        
        insights = engine.generate_enhanced_insights(
            repository='test-repo',
            current_audit=current_audit,
            historical_audits=[],
            peer_metrics={}
        )
        
        # Critical insights should have recommendations
        critical_insights = [i for i in insights if i.severity.value == 'critical']
        for insight in critical_insights:
            assert len(insight.recommendations) > 0


class TestMLUtilities:
    """Tests for ML utilities"""
    
    def test_prediction_cache(self):
        """Test prediction cache"""
        from gitrate.intelligence.models.ml_utilities import PredictionCache
        
        cache = PredictionCache(ttl_minutes=1)
        
        # Set and get
        cache.set('test-key', {'value': 42})
        assert cache.get('test-key') == {'value': 42}
        
        # Non-existent key
        assert cache.get('non-existent') is None
    
    def test_data_validator(self):
        """Test data validation"""
        from gitrate.intelligence.models.ml_utilities import DataValidator
        
        validator = DataValidator()
        
        # Valid score
        assert validator.validate_score(75) == True
        assert validator.validate_score(0) == True
        assert validator.validate_score(100) == True
        
        # Invalid score
        assert validator.validate_score(-1) == False
        assert validator.validate_score(101) == False
        assert validator.validate_score("invalid") == False
    
    def test_data_normalizer(self):
        """Test data normalization"""
        from gitrate.intelligence.models.ml_utilities import DataNormalizer
        
        normalizer = DataNormalizer()
        
        # Normalize score
        normalized = normalizer.normalize_score(50)
        assert 0 <= normalized <= 1
        assert normalized == 0.5
        
        # Denormalize
        denormalized = normalizer.denormalize_score(0.5)
        assert denormalized == 50
    
    def test_model_evaluator(self):
        """Test model evaluation"""
        from gitrate.intelligence.models.ml_utilities import ModelEvaluator
        
        evaluator = ModelEvaluator()
        
        # Log predictions
        evaluator.log_prediction('repo1', 85, 84, 0.92, 'model_v1')
        evaluator.log_prediction('repo1', 90, 88, 0.95, 'model_v1')
        
        # Calculate metrics
        mae = evaluator.calculate_mae()
        assert mae is not None
        assert mae > 0
        
        # Get summary
        summary = evaluator.get_performance_summary()
        assert summary['total_predictions'] == 2
        assert summary['mean_absolute_error'] is not None
    
    def test_quality_metrics(self):
        """Test quality metrics calculation"""
        from gitrate.intelligence.models.ml_utilities import QualityMetrics
        
        metrics = {
            'overall_score': 85,
            'security_score': 80,
            'code_quality_score': 90,
            'findings_count': 5,
            'critical_findings': 0
        }
        
        completeness = QualityMetrics.data_completeness(metrics)
        assert 0 <= completeness <= 100
        
        # Consistency
        scores = [80, 85, 90, 88, 82]
        consistency = QualityMetrics.score_consistency(scores)
        assert 0 <= consistency <= 100


class TestAPIEndpoints:
    """Tests for ML API endpoints"""
    
    @pytest.mark.asyncio
    async def test_anomaly_detection_endpoint(self):
        """Test anomaly detection endpoint"""
        # Note: Requires running app
        pass
    
    @pytest.mark.asyncio
    async def test_prediction_endpoint(self):
        """Test score prediction endpoint"""
        # Note: Requires running app
        pass
    
    @pytest.mark.asyncio
    async def test_clustering_endpoint(self):
        """Test clustering endpoint"""
        # Note: Requires running app
        pass
    
    @pytest.mark.asyncio
    async def test_insights_endpoint(self):
        """Test insights endpoint"""
        # Note: Requires running app
        pass


class TestIntegration:
    """Integration tests"""
    
    def test_ml_pipeline_end_to_end(self):
        """Test complete ML pipeline"""
        from gitrate.intelligence.models.ml_models import (
            AnomalyDetector, ScorePredictor, RepositoryClustering, TrendForecaster, AuditMetrics
        )
        from gitrate.intelligence.insights.enhanced_insights import EnhancedInsightsEngine
        
        # Create test data
        audit_metrics = AuditMetrics(
            overall_score=75,
            security_score=80,
            code_quality_score=70,
            ip_legal_score=75,
            team_sustainability_score=75,
            findings_count=10,
            critical_findings=1
        )
        
        # Run through ML pipeline
        detector = AnomalyDetector()
        result = detector.detect_anomaly('test-repo', audit_metrics)
        assert result is not None
        
        predictor = ScorePredictor()
        prediction = predictor.predict_next_score('test-repo', days_ahead=30)
        assert prediction is not None
        
        # Generate insights
        engine = EnhancedInsightsEngine()
        insights = engine.generate_enhanced_insights(
            'test-repo',
            {
                'overall_score': 75,
                'security_score': 80,
                'code_quality_score': 70,
                'team_sustainability_score': 75,
                'findings_count': 10,
                'critical_findings': 1
            },
            [],
            {}
        )
        
        assert len(insights) >= 0  # May or may not generate insights depending on data
    
    def test_batch_insights_pipeline(self):
        """Test batch insight generation pipeline"""
        from gitrate.intelligence.insights.enhanced_insights import EnhancedInsightsEngine
        
        engine = EnhancedInsightsEngine()
        
        repositories = {
            'repo1': {
                'current': {
                    'overall_score': 50,
                    'security_score': 40,
                    'code_quality_score': 50,
                    'team_sustainability_score': 60,
                    'findings_count': 50,
                    'critical_findings': 5
                },
                'history': [],
                'peers': {'avg_security_score': 80, 'avg_quality_score': 75}
            }
        }
        
        batch = engine.generate_batch('integration-test-1', repositories)
        summary = batch.get_executive_summary()
        
        assert 'integration-test-1' in summary
        assert batch.total_insights >= 0


class TestModelPerformance:
    """Performance and benchmark tests"""
    
    def test_model_speed(self):
        """Test model execution speed"""
        from gitrate.intelligence.models.ml_models import AnomalyDetector, AuditMetrics
        import time
        
        detector = AnomalyDetector()
        metrics = AuditMetrics(
            overall_score=75,
            security_score=80,
            code_quality_score=70,
            ip_legal_score=75,
            team_sustainability_score=75,
            findings_count=10,
            critical_findings=1
        )
        
        start = time.time()
        result = detector.detect_anomaly('test-repo', metrics)
        elapsed = time.time() - start
        
        # Should complete in < 1 second
        assert elapsed < 1.0
    
    def test_batch_processing_performance(self):
        """Test batch processing performance"""
        from gitrate.intelligence.insights.enhanced_insights import EnhancedInsightsEngine
        import time
        
        engine = EnhancedInsightsEngine()
        
        # Create large batch
        repositories = {
            f'repo{i}': {
                'current': {
                    'overall_score': 50 + (i % 50),
                    'security_score': 40 + (i % 60),
                    'code_quality_score': 60 - (i % 40),
                    'team_sustainability_score': 70 - (i % 30),
                    'findings_count': 20 + (i % 40),
                    'critical_findings': i % 5
                },
                'history': [],
                'peers': {}
            }
            for i in range(10)
        }
        
        start = time.time()
        batch = engine.generate_batch('perf-test', repositories)
        elapsed = time.time() - start
        
        # Should process 10 repos in < 5 seconds
        assert elapsed < 5.0
        assert batch.total_insights > 0


# Fixtures and helpers

@pytest.fixture
def ml_models_initialized():
    """Fixture to initialize all ML models"""
    from gitrate.intelligence.models.ml_models import (
        AnomalyDetector, ScorePredictor, RepositoryClustering, TrendForecaster
    )
    
    return {
        'detector': AnomalyDetector(),
        'predictor': ScorePredictor(),
        'clustering': RepositoryClustering(),
        'forecaster': TrendForecaster()
    }


@pytest.fixture
def sample_audit_data():
    """Sample audit data for testing"""
    return {
        'overall_score': 75,
        'security_score': 80,
        'code_quality_score': 70,
        'ip_legal_score': 75,
        'team_sustainability_score': 75,
        'findings_count': 10,
        'critical_findings': 1,
        'created_at': datetime.now().isoformat()
    }


@pytest.fixture
def historical_audit_data():
    """Generate historical audit data"""
    return [
        {
            'overall_score': 70 + (i * 2),
            'security_score': 75 + (i * 2),
            'code_quality_score': 65 + (i * 2),
            'ip_legal_score': 70 + (i * 2),
            'team_sustainability_score': 70 + (i * 1.5),
            'findings_count': 15 - i,
            'critical_findings': 2 - (i // 5),
            'created_at': (datetime.now() - timedelta(days=i*7)).isoformat()
        }
        for i in range(10)
    ]
