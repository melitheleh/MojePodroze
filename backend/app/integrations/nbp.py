"""Klient API NBP: kursy średnie z tabeli A. API nie wymaga klucza."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

import httpx

from app.integrations.errors import ExternalServiceError

SERVICE_NAME = "NBP"
UNAVAILABLE_MESSAGE = "Serwis kursów walut NBP jest chwilowo niedostępny."
INVALID_RESPONSE_MESSAGE = "Serwis kursów walut NBP zwrócił nieprawidłowe dane."
DEFAULT_CURRENCIES: tuple[str, ...] = ("EUR", "USD", "GBP")


@dataclass(frozen=True)
class ExchangeRate:
    code: str
    currency: str
    mid: Decimal


@dataclass(frozen=True)
class ExchangeRatesTable:
    table_no: str
    effective_date: date
    rates: tuple[ExchangeRate, ...]

    def rate_for(self, code: str) -> ExchangeRate:
        for rate in self.rates:
            if rate.code == code:
                return rate
        raise KeyError(code)


def parse_table_a(payload: Any, codes: Sequence[str] = DEFAULT_CURRENCIES) -> ExchangeRatesTable:
    """Odpowiedź NBP to lista z jedną tabelą: ``[{"no", "effectiveDate", "rates": [...]}]``."""
    try:
        table = payload[0]
        by_code = {rate["code"]: rate for rate in table["rates"]}
        rates = tuple(
            ExchangeRate(
                code=code,
                currency=str(by_code[code]["currency"]),
                # str() chroni przed niedokładnością liczb zmiennoprzecinkowych
                mid=Decimal(str(by_code[code]["mid"])),
            )
            for code in codes
        )
        return ExchangeRatesTable(
            table_no=str(table["no"]),
            effective_date=date.fromisoformat(table["effectiveDate"]),
            rates=rates,
        )
    except (KeyError, IndexError, TypeError, ValueError, ArithmeticError) as exc:
        raise ExternalServiceError(SERVICE_NAME, INVALID_RESPONSE_MESSAGE) from exc


class NbpClient:
    def __init__(self, http: httpx.Client, table_url: str) -> None:
        self._http = http
        self._table_url = table_url

    def get_rates(self, codes: Sequence[str] = DEFAULT_CURRENCIES) -> ExchangeRatesTable:
        try:
            response = self._http.get(self._table_url, params={"format": "json"})
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ExternalServiceError(SERVICE_NAME, UNAVAILABLE_MESSAGE) from exc
        return parse_table_a(payload, codes)
