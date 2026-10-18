"""Maszyna stanów podróży: dozwolone kroki do przodu i wstecz, zabronione przeskoki, archiwum."""

import pytest

from app.domain.enums import TripStatus
from app.domain.errors import InvalidStatusTransitionError, TripReadOnlyError
from app.domain.status import (
    STATUS_FLOW,
    allowed_transitions,
    can_transition,
    ensure_editable,
    ensure_transition_allowed,
    is_read_only,
)

PLANNED = TripStatus.PLANNED
IN_PROGRESS = TripStatus.IN_PROGRESS
COMPLETED = TripStatus.COMPLETED
ARCHIVED = TripStatus.ARCHIVED


def test_status_flow_has_expected_order() -> None:
    assert STATUS_FLOW == (PLANNED, IN_PROGRESS, COMPLETED, ARCHIVED)


@pytest.mark.parametrize(
    ("current", "expected"),
    [
        (PLANNED, (IN_PROGRESS,)),
        (IN_PROGRESS, (PLANNED, COMPLETED)),
        (COMPLETED, (IN_PROGRESS, ARCHIVED)),
        (ARCHIVED, (COMPLETED,)),
    ],
)
def test_allowed_transitions_are_direct_neighbours(
    current: TripStatus, expected: tuple[TripStatus, ...]
) -> None:
    assert allowed_transitions(current) == expected


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (PLANNED, IN_PROGRESS),
        (IN_PROGRESS, COMPLETED),
        (COMPLETED, ARCHIVED),
        (ARCHIVED, COMPLETED),  # cofnięcie z archiwum
        (COMPLETED, IN_PROGRESS),
        (IN_PROGRESS, PLANNED),  # omyłkowe „w trakcie”
    ],
)
def test_one_step_forward_or_back_is_allowed(current: TripStatus, target: TripStatus) -> None:
    assert can_transition(current, target)
    ensure_transition_allowed(current, target)  # nie rzuca wyjątku


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (PLANNED, COMPLETED),
        (PLANNED, ARCHIVED),
        (IN_PROGRESS, ARCHIVED),
        (ARCHIVED, PLANNED),
        (ARCHIVED, IN_PROGRESS),
        (COMPLETED, PLANNED),
    ],
)
def test_skipping_stages_is_forbidden(current: TripStatus, target: TripStatus) -> None:
    assert not can_transition(current, target)
    with pytest.raises(InvalidStatusTransitionError) as error:
        ensure_transition_allowed(current, target)
    assert current.label in error.value.message
    assert target.label in error.value.message
    assert error.value.code == "INVALID_STATUS_TRANSITION"


@pytest.mark.parametrize("status", list(TripStatus))
def test_transition_to_same_status_is_forbidden(status: TripStatus) -> None:
    assert not can_transition(status, status)
    with pytest.raises(InvalidStatusTransitionError):
        ensure_transition_allowed(status, status)


@pytest.mark.parametrize(
    ("status", "read_only"),
    [(PLANNED, False), (IN_PROGRESS, False), (COMPLETED, False), (ARCHIVED, True)],
)
def test_only_archive_is_read_only(status: TripStatus, read_only: bool) -> None:
    assert is_read_only(status) is read_only


@pytest.mark.parametrize("status", [PLANNED, IN_PROGRESS, COMPLETED])
def test_completed_and_earlier_trips_are_editable(status: TripStatus) -> None:
    ensure_editable(status)  # nie rzuca wyjątku


def test_archived_trip_cannot_be_edited() -> None:
    with pytest.raises(TripReadOnlyError) as error:
        ensure_editable(ARCHIVED)
    assert error.value.code == "TRIP_ARCHIVED"
    assert "zrealizowana" in error.value.message
