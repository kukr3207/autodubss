"""Historical tail-risk and deterministic portfolio stress calculations."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING
from types import MappingProxyType
from typing import Any, Dict, Iterable, Mapping, Sequence, Tuple

from ..errors import ValidationError
from ..validation import clean_text, decimal_value
from ..domain.portfolio import PortfolioSnapshot


@dataclass(frozen=True)
class TailRisk:
    confidence: Decimal
    value_at_risk: Decimal
    expected_shortfall: Decimal
    observations: int

    def as_dict(self) -> Dict[str, Any]:
        return {
            "confidence": format(self.confidence, "f"),
            "valueAtRisk": format(self.value_at_risk, "f"),
            "expectedShortfall": format(self.expected_shortfall, "f"),
            "observations": self.observations,
        }


def historical_tail_risk(
    returns: Sequence[Decimal],
    portfolio_value: Decimal,
    confidence: Decimal = Decimal("0.95"),
) -> TailRisk:
    checked = tuple(decimal_value(value, "return") for value in returns)
    if not checked:
        raise ValidationError("returns cannot be empty")
    value = decimal_value(portfolio_value, "portfolio_value", positive=True, allow_zero=False)
    level = decimal_value(confidence, "confidence", positive=True, allow_zero=False)
    if level >= 1:
        raise ValidationError("confidence must be below one")
    losses = sorted((-item * value for item in checked), reverse=True)
    tail_fraction = Decimal("1") - level
    tail_count = max(
        1,
        int((Decimal(len(losses)) * tail_fraction).to_integral_value(rounding=ROUND_CEILING)),
    )
    tail = losses[:tail_count]
    var = max(Decimal("0"), tail[-1])
    shortfall = max(Decimal("0"), sum(tail, Decimal("0")) / len(tail))
    return TailRisk(level, var, shortfall, len(checked))


@dataclass(frozen=True)
class StressScenario:
    name: str
    shocks: Mapping[str, Decimal]
    default_shock: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", clean_text(self.name, "name", max_length=100))
        checked = {
            clean_text(key, "instrument key"): decimal_value(value, "shock")
            for key, value in self.shocks.items()
        }
        if any(value <= Decimal("-1") for value in checked.values()):
            raise ValidationError("scenario shocks cannot remove more than all value")
        default = decimal_value(self.default_shock, "default_shock")
        if default <= Decimal("-1"):
            raise ValidationError("default shock cannot remove more than all value")
        object.__setattr__(self, "shocks", MappingProxyType(checked))
        object.__setattr__(self, "default_shock", default)

    def shock_for(self, instrument_key: str) -> Decimal:
        return self.shocks.get(instrument_key, self.default_shock)


@dataclass(frozen=True)
class StressResult:
    scenario: str
    starting_value: Decimal
    stressed_value: Decimal
    profit_loss: Decimal
    by_instrument: Mapping[str, Decimal]

    def __post_init__(self) -> None:
        object.__setattr__(self, "by_instrument", MappingProxyType(dict(self.by_instrument)))

    @property
    def loss_percent(self) -> Decimal:
        if self.starting_value == 0:
            return Decimal("0")
        return -self.profit_loss / self.starting_value * Decimal("100")

    def as_dict(self) -> Dict[str, Any]:
        return {
            "scenario": self.scenario,
            "startingValue": format(self.starting_value, "f"),
            "stressedValue": format(self.stressed_value, "f"),
            "profitLoss": format(self.profit_loss, "f"),
            "lossPercent": format(self.loss_percent, "f"),
            "byInstrument": {
                key: format(value, "f") for key, value in sorted(self.by_instrument.items())
            },
        }


def stress_portfolio(
    portfolio: PortfolioSnapshot,
    scenario: StressScenario,
    *,
    currency: str = "INR",
) -> StressResult:
    if not isinstance(portfolio, PortfolioSnapshot):
        raise ValidationError("portfolio must be PortfolioSnapshot")
    if not isinstance(scenario, StressScenario):
        raise ValidationError("scenario must be StressScenario")
    cash = portfolio.cash_balance(currency).amount
    starting_positions = Decimal("0")
    stressed_positions = Decimal("0")
    impacts: Dict[str, Decimal] = {}
    for position in portfolio.positions:
        if position.instrument.contract.price_currency != currency:
            continue
        market_value = position.market_value.amount
        shock = scenario.shock_for(position.instrument.key)
        impact = market_value * shock
        impacts[position.instrument.key] = impact
        starting_positions += market_value
        stressed_positions += market_value + impact
    starting = cash + starting_positions
    stressed = cash + stressed_positions
    return StressResult(
        scenario.name,
        starting,
        stressed,
        stressed - starting,
        impacts,
    )


def stress_grid(
    portfolio: PortfolioSnapshot,
    scenarios: Iterable[StressScenario],
    *,
    currency: str = "INR",
) -> Tuple[StressResult, ...]:
    checked = tuple(scenarios)
    if not checked:
        raise ValidationError("at least one stress scenario is required")
    if len({item.name for item in checked}) != len(checked):
        raise ValidationError("stress scenario names must be unique")
    return tuple(stress_portfolio(portfolio, item, currency=currency) for item in checked)
