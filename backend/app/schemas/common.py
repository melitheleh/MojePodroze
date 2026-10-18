"""Wspólne typy i modele schematów API."""

from decimal import Decimal
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    StringConstraints,
)

# Kwoty wejściowe: nieujemne, maks. 2 miejsca po przecinku.
MoneyIn = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2, examples=[120.5])]
# Liczby dziesiętne w odpowiedziach serializowane jako liczby JSON (wygodniejsze dla frontendu).
DecimalOut = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]
Rating = Annotated[int, Field(ge=1, le=5, description="Ocena w skali 1–5.")]


# Teksty przycinane ze spacji na końcach, niepuste, z limitem długości zgodnym z kolumną w bazie.
ShortName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
TripName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]
LongName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
Note = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2_000)]
LongText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10_000)]


class ApiModel(BaseModel):
    """Bazowy model odpowiedzi czytany wprost z obiektów ORM / dataclass."""

    model_config = ConfigDict(from_attributes=True)


class ErrorResponse(BaseModel):
    detail: str = Field(description="Komunikat błędu do pokazania użytkownikowi.")
    code: str = Field(description="Stały kod błędu, np. TRIP_ARCHIVED.")


class FieldError(BaseModel):
    field: str
    message: str
    type: str


class ValidationErrorResponse(ErrorResponse):
    errors: list[FieldError]


class ExternalErrorResponse(ErrorResponse):
    service: str


class EnumOption(BaseModel):
    value: str
    label: str


def reject_null(value: object) -> object:
    """Walidator dla pól PATCH: pole można pominąć, ale nie można wysłać ``null``."""
    if value is None:
        raise ValueError("Pole nie może być puste (null).")
    return value


# Pola PATCH: można je pominąć, ale nie można wysłać jawnego null.
PatchName = Annotated[Name | None, AfterValidator(reject_null)]
PatchBool = Annotated[bool | None, AfterValidator(reject_null)]
