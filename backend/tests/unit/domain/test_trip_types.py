"""Reguły typu podróży: lista pakowania i blokada zmiany typu."""

import pytest

from app.domain.enums import Section, TripType
from app.domain.errors import TripTypeChangeBlockedError
from app.domain.trip_types import (
    FOREIGN_PACKING_DEFAULTS,
    DomesticTripPolicy,
    ForeignTripPolicy,
    ensure_type_change_allowed,
    missing_default_packing_items,
    policy_for,
)


def test_policy_for_returns_matching_policy() -> None:
    assert isinstance(policy_for(TripType.DOMESTIC), DomesticTripPolicy)
    assert isinstance(policy_for(TripType.FOREIGN), ForeignTripPolicy)


def test_policies_expose_allowed_sections() -> None:
    assert Section.FLIGHTS not in policy_for(TripType.DOMESTIC).allowed_sections()
    assert Section.FLIGHTS in policy_for(TripType.FOREIGN).allowed_sections()


def test_foreign_trip_gets_passport_insurance_and_adapter() -> None:
    assert policy_for(TripType.FOREIGN).default_packing_items() == (
        "Paszport lub dowód osobisty",
        "Ubezpieczenie podróżne",
        "Przejściówka do gniazdka",
    )


def test_domestic_trip_has_no_default_packing_items() -> None:
    assert policy_for(TripType.DOMESTIC).default_packing_items() == ()
    assert missing_default_packing_items(TripType.DOMESTIC, []) == []


def test_all_defaults_are_missing_on_empty_list() -> None:
    assert missing_default_packing_items(TripType.FOREIGN, []) == list(FOREIGN_PACKING_DEFAULTS)


def test_existing_items_are_not_duplicated_ignoring_case_and_spaces() -> None:
    existing = ["  paszport LUB dowód   osobisty ", "Krem z filtrem"]
    assert missing_default_packing_items(TripType.FOREIGN, existing) == [
        "Ubezpieczenie podróżne",
        "Przejściówka do gniazdka",
    ]


def test_nothing_missing_when_all_defaults_present() -> None:
    assert missing_default_packing_items(TripType.FOREIGN, FOREIGN_PACKING_DEFAULTS) == []


def test_change_to_domestic_is_blocked_when_trip_has_flights() -> None:
    with pytest.raises(TripTypeChangeBlockedError) as error:
        ensure_type_change_allowed(TripType.DOMESTIC, {Section.FLIGHTS: 1})
    assert error.value.code == "TRIP_TYPE_CHANGE_BLOCKED"
    assert "Loty" in error.value.message
    assert "Usuń je najpierw" in error.value.message


def test_change_to_domestic_is_allowed_without_flights() -> None:
    ensure_type_change_allowed(
        TripType.DOMESTIC, {Section.FLIGHTS: 0, Section.MEALS: 3, Section.TRANSPORT: 1}
    )


def test_change_to_domestic_is_allowed_with_empty_counts() -> None:
    ensure_type_change_allowed(TripType.DOMESTIC, {})


def test_change_to_foreign_is_always_allowed() -> None:
    ensure_type_change_allowed(TripType.FOREIGN, dict.fromkeys(Section, 5))
