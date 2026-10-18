class ExternalServiceError(Exception):
    """Zewnętrzne API nie odpowiedziało albo zwróciło nieoczekiwane dane (→ HTTP 503)."""

    def __init__(self, service: str, message: str) -> None:
        super().__init__(f"{service}: {message}")
        self.service = service
        self.message = message
