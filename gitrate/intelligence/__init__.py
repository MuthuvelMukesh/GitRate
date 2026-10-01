"""Intelligence layer: one architecture for detectors, ML models, scoring and confidence.

Layout
------
``detectors``   Deterministic detectors grouped by domain (security, quality, team,
                trend, anomaly, benchmark).
``insights``    Legacy insight engines, retained for backward compatibility.  They
                delegate to ``detectors`` so there is a single implementation.
``models``      Statistical/ML models (anomaly detection, forecasting, clustering).
``scoring``     Configurable scoring profiles and score composition.
``confidence``  Confidence and data-completeness methodology.
``recommendations`` Remediation recommendations derived from findings.
"""

__all__: list[str] = []
