"""Błędy warstwy aplikacji (nie-domenowe), od razu z kodem HTTP i stałym kodem błędu."""


class AppError(Exception):
    status_code = 400
    code = "APP_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"


class AuthenticationRequiredError(AppError):
    status_code = 401
    code = "AUTH_REQUIRED"


class InvalidUserError(AppError):
    status_code = 401
    code = "INVALID_USER"


class InvalidCredentialsError(AppError):
    status_code = 401
    code = "INVALID_CREDENTIALS"


class LoginTakenError(AppError):
    status_code = 409
    code = "LOGIN_TAKEN"


class InvalidReferenceError(AppError):
    """Id ze słownika (np. charakter podróży) nie istnieje."""

    status_code = 422
    code = "INVALID_REFERENCE"


class InvalidUploadError(AppError):
    status_code = 422
    code = "INVALID_UPLOAD"


class FileTooLargeError(AppError):
    status_code = 413
    code = "FILE_TOO_LARGE"
