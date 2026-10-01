"""Insight engines (backward-compatible facade over ``gitrate.intelligence.detectors``)."""

from gitrate.intelligence.insights.enhanced_insights import (
    EnhancedInsight,
    EnhancedInsightsEngine,
    InsightBatch,
    InsightCategory,
    InsightEvidence,
    InsightRecommendation,
    InsightSeverity,
)
from gitrate.intelligence.insights.insights_engine import (
    Insight,
    InsightReport,
    InsightsEngine,
)

__all__ = [
    "EnhancedInsight",
    "EnhancedInsightsEngine",
    "Insight",
    "InsightBatch",
    "InsightCategory",
    "InsightEvidence",
    "InsightRecommendation",
    "InsightReport",
    "InsightsEngine",
    "InsightSeverity",
]
