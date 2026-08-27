"""Decimal-safe series, correlation, and profit attribution."""

from .attribution import AttributionItem, AttributionReport, attribute
from .correlation import (
    CorrelationMatrix,
    average,
    correlation,
    correlation_matrix,
    covariance,
    variance,
)
from .series import DecimalSeries, Observation
from .risk import (
    StressResult,
    StressScenario,
    TailRisk,
    historical_tail_risk,
    stress_grid,
    stress_portfolio,
)

__all__ = [
    "AttributionItem",
    "AttributionReport",
    "CorrelationMatrix",
    "DecimalSeries",
    "Observation",
    "StressResult",
    "StressScenario",
    "TailRisk",
    "attribute",
    "average",
    "correlation",
    "correlation_matrix",
    "covariance",
    "historical_tail_risk",
    "stress_grid",
    "stress_portfolio",
    "variance",
]
