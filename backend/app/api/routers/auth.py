from fastapi import APIRouter, status

from app.api.deps import DbSession
from app.api.responses import CONFLICT, UNAUTHORIZED, VALIDATION
from app.schemas.users import CredentialsIn, UserOut
from app.services import users as users_service

router = APIRouter(prefix="/auth", tags=["Konto"])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Rejestracja",
    description="Zakłada konto. Login musi być unikalny (inaczej 409 LOGIN_TAKEN).",
    responses={**CONFLICT, **VALIDATION},
    name="register",
)
def register(payload: CredentialsIn, db: DbSession) -> UserOut:
    return UserOut.model_validate(users_service.register_user(db, payload.login, payload.password))


@router.post(
    "/login",
    summary="Logowanie",
    description=(
        "Porównuje login i hasło z bazą i zwraca id użytkownika. Frontend zapisuje je "
        "w localStorage i wysyła w nagłówku **X-User-Id** przy każdym kolejnym zapytaniu."
    ),
    responses={**UNAUTHORIZED, **VALIDATION},
    name="login",
)
def login(payload: CredentialsIn, db: DbSession) -> UserOut:
    return UserOut.model_validate(users_service.authenticate(db, payload.login, payload.password))
