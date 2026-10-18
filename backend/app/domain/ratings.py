"""Średnie ocen: zwykła średnia bez wag, pozycje bez oceny są pomijane."""

from collections.abc import Iterable
from decimal import Decimal

from app.domain.common import round_half_up


def average_rating(ratings: Iterable[int | None]) -> Decimal | None:
    rated = [rating for rating in ratings if rating is not None]
    if not rated:
        return None
    return round_half_up(Decimal(sum(rated)) / Decimal(len(rated)))
