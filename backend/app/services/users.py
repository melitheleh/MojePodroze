import secrets

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import InvalidCredentialsError, LoginTakenError
from app.db.models import User
from app.schemas.users import WeatherCity

INVALID_CREDENTIALS_MESSAGE = "Nieprawidłowy login lub hasło."


def _login_taken(login: str) -> LoginTakenError:
    return LoginTakenError(f"Login „{login}” jest już zajęty.")


def find_by_login(db: Session, login: str) -> User | None:
    return db.scalar(select(User).where(User.login == login))


def register_user(db: Session, login: str, password: str) -> User:
    """Zakłada konto. Hasło jest zapisywane jawnym tekstem (świadome uproszczenie projektu)."""
    if find_by_login(db, login) is not None:
        raise _login_taken(login)
    user = User(login=login, password=password)
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:  # dwa równoczesne zapytania z tym samym loginem
        db.rollback()
        raise _login_taken(login) from exc
    db.refresh(user)
    return user


def authenticate(db: Session, login: str, password: str) -> User:
    user = find_by_login(db, login)
    # compare_digest na bajtach: działa też dla haseł z polskimi znakami.
    if user is None or not secrets.compare_digest(user.password.encode(), password.encode()):
        raise InvalidCredentialsError(INVALID_CREDENTIALS_MESSAGE)
    return user


def update_weather_city(db: Session, user: User, city: WeatherCity) -> User:
    user.weather_city_name = city.name
    user.weather_country = city.country
    user.weather_latitude = city.latitude
    user.weather_longitude = city.longitude
    db.commit()
    db.refresh(user)
    return user
