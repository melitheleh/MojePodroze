"""Reguły zależne od typu podróży (krajowa / zagraniczna), zrealizowane polimorficznie."""

from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from types import MappingProxyType
from typing import ClassVar

from app.domain.common import normalize_name
from app.domain.enums import Section, TripType
from app.domain.errors import TripTypeChangeBlockedError
from app.domain.items import allowed_sections, is_section_allowed

FOREIGN_PACKING_DEFAULTS: tuple[str, ...] = (
    "Paszport lub dowód osobisty",
    "Ubezpieczenie podróżne",
    "Przejściówka do gniazdka",
)


class TripTypePolicy(ABC):
    trip_type: ClassVar[TripType]

    def allowed_sections(self) -> tuple[Section, ...]:
        return allowed_sections(self.trip_type)

    @abstractmethod
    def default_packing_items(self) -> tuple[str, ...]:
        """Rzeczy dodawane automatycznie do listy pakowania."""


class DomesticTripPolicy(TripTypePolicy):
    trip_type = TripType.DOMESTIC

    def default_packing_items(self) -> tuple[str, ...]:
        return ()


class ForeignTripPolicy(TripTypePolicy):
    trip_type = TripType.FOREIGN

    def default_packing_items(self) -> tuple[str, ...]:
        return FOREIGN_PACKING_DEFAULTS


_POLICIES: Mapping[TripType, TripTypePolicy] = MappingProxyType(
    {policy.trip_type: policy for policy in (DomesticTripPolicy(), ForeignTripPolicy())}
)


def policy_for(trip_type: TripType) -> TripTypePolicy:
    return _POLICIES[trip_type]


def missing_default_packing_items(trip_type: TripType, existing_names: Iterable[str]) -> list[str]:
    """Domyślne rzeczy do spakowania, których jeszcze nie ma na liście.

    Porównanie nazw ignoruje wielkość liter i nadmiarowe spacje.
    """
    existing = {normalize_name(name) for name in existing_names}
    return [
        name
        for name in policy_for(trip_type).default_packing_items()
        if normalize_name(name) not in existing
    ]


def ensure_type_change_allowed(new_type: TripType, item_counts: Mapping[Section, int]) -> None:
    """Blokuje zmianę typu, jeśli podróż ma pozycje w sekcjach niedozwolonych dla nowego typu.

    Przykład: zagraniczna → krajowa, gdy są już loty: „usuń najpierw loty”.
    """
    blocked = [
        section
        for section in Section
        if item_counts.get(section, 0) > 0 and not is_section_allowed(section, new_type)
    ]
    if blocked:
        names = ", ".join(section.label for section in blocked)
        raise TripTypeChangeBlockedError(
            f"Nie można zmienić typu podróży na „{new_type.label}”, bo podróż ma pozycje "
            f"w sekcji: {names}. Usuń je najpierw."
        )
