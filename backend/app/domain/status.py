"""Cykl życia podróży jako maszyna stanów.

w planie ⇄ w trakcie ⇄ zrealizowana ⇄ archiwum

Przejście jest zawsze o jeden krok do przodu albo wstecz. Archiwum jest tylko do odczytu.
"""

from app.domain.enums import TripStatus
from app.domain.errors import InvalidStatusTransitionError, TripReadOnlyError

STATUS_FLOW: tuple[TripStatus, ...] = (
    TripStatus.PLANNED,
    TripStatus.IN_PROGRESS,
    TripStatus.COMPLETED,
    TripStatus.ARCHIVED,
)

ARCHIVED_MESSAGE = (
    "Podróż jest w archiwum i jest tylko do odczytu. "
    "Aby wprowadzić zmiany, cofnij ją najpierw do statusu „zrealizowana”."
)


def allowed_transitions(current: TripStatus) -> tuple[TripStatus, ...]:
    """Statusy, na które można przejść z ``current`` (sąsiedzi w ``STATUS_FLOW``)."""
    position = STATUS_FLOW.index(current)
    neighbours: list[TripStatus] = []
    if position > 0:
        neighbours.append(STATUS_FLOW[position - 1])
    if position < len(STATUS_FLOW) - 1:
        neighbours.append(STATUS_FLOW[position + 1])
    return tuple(neighbours)


def can_transition(current: TripStatus, target: TripStatus) -> bool:
    return target in allowed_transitions(current)


def ensure_transition_allowed(current: TripStatus, target: TripStatus) -> None:
    if not can_transition(current, target):
        raise InvalidStatusTransitionError(
            f"Nie można zmienić statusu z „{current.label}” na „{target.label}”. "
            "Status zmienia się zawsze o jeden krok do przodu albo wstecz."
        )


def is_read_only(status: TripStatus) -> bool:
    return status is TripStatus.ARCHIVED


def ensure_editable(status: TripStatus) -> None:
    if is_read_only(status):
        raise TripReadOnlyError(ARCHIVED_MESSAGE)
