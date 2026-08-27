"""Composable pre-trade risk checks."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Iterable, List, Optional, Protocol, Sequence, Tuple

from ..errors import RiskRejectedError, ValidationError
from ..validation import aware_time, integer_value
from ..domain.orders import OrderRequest, OrderStatus
from ..domain.portfolio import PortfolioSnapshot
from ..market.models import Quote
from .circuit import CircuitBreaker
from .exposure import projected_exposure, projected_position_quantity
from .models import RiskDecision, RiskLimits, RiskSeverity, RiskViolation


class RiskRule(Protocol):
    name: str

    def evaluate(self, context: "RiskContext") -> Optional[RiskViolation]:
        ...


class RiskContext:
    def __init__(
        self,
        request: OrderRequest,
        portfolio: PortfolioSnapshot,
        quote: Quote,
        limits: RiskLimits,
        at: datetime,
        open_order_count: int,
    ) -> None:
        self.request = request
        self.portfolio = portfolio
        self.quote = quote
        self.limits = limits
        self.at = aware_time(at, "at")
        self.open_order_count = integer_value(open_order_count, "open_order_count", minimum=0)


class OrderQuantityRule:
    name = "max_order_quantity"

    def evaluate(self, context: RiskContext) -> Optional[RiskViolation]:
        if context.request.quantity <= context.limits.max_order_quantity:
            return None
        return RiskViolation(
            self.name,
            "order quantity exceeds the configured maximum",
            RiskSeverity.BLOCK,
            str(context.request.quantity),
            str(context.limits.max_order_quantity),
        )


class OrderNotionalRule:
    name = "max_order_notional"

    def evaluate(self, context: RiskContext) -> Optional[RiskViolation]:
        price = context.quote.executable_price(context.request.side)
        notional = context.request.instrument.notional(price, context.request.quantity)
        if notional <= context.limits.max_order_notional:
            return None
        return RiskViolation(
            self.name,
            "order notional exceeds the configured maximum",
            RiskSeverity.BLOCK,
            format(notional, "f"),
            format(context.limits.max_order_notional, "f"),
        )


class PositionQuantityRule:
    name = "max_position_quantity"

    def evaluate(self, context: RiskContext) -> Optional[RiskViolation]:
        projected = projected_position_quantity(context.portfolio, context.request)
        if abs(projected) <= context.limits.max_position_quantity:
            return None
        return RiskViolation(
            self.name,
            "projected position exceeds the configured maximum",
            RiskSeverity.BLOCK,
            str(projected),
            str(context.limits.max_position_quantity),
        )


class GrossExposureRule:
    name = "max_gross_exposure"

    def evaluate(self, context: RiskContext) -> Optional[RiskViolation]:
        exposure = projected_exposure(context.portfolio, context.request, context.quote)
        if exposure.gross <= context.limits.max_gross_exposure:
            return None
        return RiskViolation(
            self.name,
            "projected gross exposure exceeds the configured maximum",
            RiskSeverity.BLOCK,
            format(exposure.gross, "f"),
            format(context.limits.max_gross_exposure, "f"),
        )


class NetExposureRule:
    name = "max_net_exposure"

    def evaluate(self, context: RiskContext) -> Optional[RiskViolation]:
        exposure = projected_exposure(context.portfolio, context.request, context.quote)
        if abs(exposure.net) <= context.limits.max_net_exposure:
            return None
        return RiskViolation(
            self.name,
            "projected net exposure exceeds the configured maximum",
            RiskSeverity.BLOCK,
            format(exposure.net, "f"),
            format(context.limits.max_net_exposure, "f"),
        )


class DailyLossRule:
    name = "max_daily_loss"

    def evaluate(self, context: RiskContext) -> Optional[RiskViolation]:
        realized = sum(
            (position.realized_pnl for position in context.portfolio.positions),
            Decimal("0"),
        )
        if realized >= -context.limits.max_daily_loss:
            return None
        return RiskViolation(
            self.name,
            "daily realized loss has reached the configured stop",
            RiskSeverity.BLOCK,
            format(realized, "f"),
            format(-context.limits.max_daily_loss, "f"),
        )


class OpenOrderRule:
    name = "max_open_orders"

    def evaluate(self, context: RiskContext) -> Optional[RiskViolation]:
        projected = context.open_order_count + 1
        if projected <= context.limits.max_open_orders:
            return None
        return RiskViolation(
            self.name,
            "too many orders are already open",
            RiskSeverity.BLOCK,
            str(projected),
            str(context.limits.max_open_orders),
        )


class QuoteFreshnessRule:
    name = "quote_freshness"

    def evaluate(self, context: RiskContext) -> Optional[RiskViolation]:
        age = context.at - context.quote.observed_at
        maximum = timedelta(seconds=context.limits.max_quote_age_seconds)
        if timedelta(0) <= age <= maximum:
            return None
        return RiskViolation(
            self.name,
            "market quote is stale or from the future",
            RiskSeverity.BLOCK,
            str(age.total_seconds()),
            str(maximum.total_seconds()),
        )


class PriceBandRule:
    name = "price_band"

    def evaluate(self, context: RiskContext) -> Optional[RiskViolation]:
        request = context.request
        reference = context.quote.midpoint
        requested = request.limit_price or request.stop_price
        if requested is None:
            return None
        deviation = abs(requested - reference) / reference * Decimal("100")
        if deviation <= context.limits.price_band_percent:
            return None
        return RiskViolation(
            self.name,
            "order price lies outside the allowed market band",
            RiskSeverity.BLOCK,
            format(deviation, "f"),
            format(context.limits.price_band_percent, "f"),
        )


DEFAULT_RULES: Tuple[RiskRule, ...] = (
    OrderQuantityRule(),
    OrderNotionalRule(),
    PositionQuantityRule(),
    GrossExposureRule(),
    NetExposureRule(),
    DailyLossRule(),
    OpenOrderRule(),
    QuoteFreshnessRule(),
    PriceBandRule(),
)


class RiskEngine:
    def __init__(
        self,
        limits: RiskLimits,
        *,
        rules: Optional[Iterable[RiskRule]] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ) -> None:
        if not isinstance(limits, RiskLimits):
            raise ValidationError("limits must be RiskLimits")
        self.limits = limits
        self.rules = tuple(DEFAULT_RULES if rules is None else rules)
        if not self.rules:
            raise ValidationError("risk engine requires at least one rule")
        if not all(callable(getattr(rule, "evaluate", None)) for rule in self.rules):
            raise ValidationError("every risk rule must define evaluate")
        self.circuit_breaker = circuit_breaker

    def evaluate(
        self,
        request: OrderRequest,
        portfolio: PortfolioSnapshot,
        quote: Quote,
        at: datetime,
        *,
        open_order_count: int = 0,
    ) -> RiskDecision:
        if request.instrument.key != quote.instrument.key:
            raise ValidationError("quote instrument must match request")
        context = RiskContext(
            request,
            portfolio,
            quote,
            self.limits,
            at,
            open_order_count,
        )
        violations: List[RiskViolation] = []
        if self.circuit_breaker is not None and not self.circuit_breaker.allow(context.at):
            violations.append(
                RiskViolation(
                    "circuit_breaker",
                    "trading is paused while the circuit is open",
                    RiskSeverity.BLOCK,
                )
            )
        for rule in self.rules:
            violation = rule.evaluate(context)
            if violation is not None:
                violations.append(violation)
        return RiskDecision(request, tuple(violations))

    def require_allowed(self, *args, **kwargs) -> RiskDecision:
        decision = self.evaluate(*args, **kwargs)
        if not decision.allowed:
            raise RiskRejectedError(
                "order failed pre-trade risk checks",
                [item.as_dict() for item in decision.violations],
            )
        return decision
