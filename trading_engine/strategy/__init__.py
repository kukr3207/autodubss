"""Reusable signal generation, sizing, and execution wiring."""

from .base import Strategy
from .breakout import BreakoutStrategy
from .composite import CompositeStrategy, ConsensusMode
from .moving_average import MovingAverageCrossStrategy
from .runner import StrategyRunner
from .signals import Signal, SignalAction
from .sizing import CashFractionSizer, FixedQuantitySizer, NotionalSizer, PositionSizer

__all__ = [
    "BreakoutStrategy",
    "CashFractionSizer",
    "CompositeStrategy",
    "ConsensusMode",
    "FixedQuantitySizer",
    "MovingAverageCrossStrategy",
    "NotionalSizer",
    "PositionSizer",
    "Signal",
    "SignalAction",
    "Strategy",
    "StrategyRunner",
]
