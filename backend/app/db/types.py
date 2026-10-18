"""Własne typy kolumn."""

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import Dialect, Integer
from sqlalchemy.types import TypeDecorator

GROSZE_IN_ZLOTY = Decimal(100)
CENT = Decimal("0.01")


class Money(TypeDecorator[Decimal]):
    """Kwota w PLN przechowywana w bazie jako liczba całkowita groszy.

    SQLite nie ma typu dziesiętnego, a liczby zmiennoprzecinkowe gubią grosze. Grosze w INTEGER
    dają dokładne sumy także w zapytaniach agregujących (``SUM``).
    """

    impl = Integer
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Dialect) -> int | None:
        if value is None:
            return None
        grosze = (Decimal(value) * GROSZE_IN_ZLOTY).quantize(Decimal(1), rounding=ROUND_HALF_UP)
        return int(grosze)

    def process_result_value(self, value: Any, dialect: Dialect) -> Decimal | None:
        if value is None:
            return None
        return (Decimal(value) / GROSZE_IN_ZLOTY).quantize(CENT)
