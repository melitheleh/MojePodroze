"""Album zdjęć układany automatycznie według dni."""

from collections import defaultdict
from collections.abc import Callable, Iterable
from datetime import date


def group_by_day[T](items: Iterable[T], day_of: Callable[[T], date]) -> list[tuple[date, list[T]]]:
    """Grupuje elementy po dniu; dni rosnąco, kolejność wewnątrz dnia jak na wejściu."""
    groups: dict[date, list[T]] = defaultdict(list)
    for item in items:
        groups[day_of(item)].append(item)
    return sorted(groups.items(), key=lambda pair: pair[0])
