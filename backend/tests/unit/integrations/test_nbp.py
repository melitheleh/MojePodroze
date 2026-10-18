"""Parsowanie tabeli A NBP i klient HTTP (bez sieci: httpx.MockTransport)."""

from datetime import date
from decimal import Decimal
from typing import Any

import httpx
import pytest

from app.integrations.errors import ExternalServiceError
from app.integrations.nbp import ExchangeRate, NbpClient, parse_table_a

NBP_RESPONSE = [
    {
        "table": "A",
        "no": "203/A/NBP/2027",
        "effectiveDate": "2027-04-20",
        "rates": [
            {"currency": "bat (Tajlandia)", "code": "THB", "mid": 0.1123},
            {"currency": "dolar amerykański", "code": "USD", "mid": 3.9876},
            {"currency": "euro", "code": "EUR", "mid": 4.2954},
            {"currency": "funt szterling", "code": "GBP", "mid": 5.0123},
        ],
    }
]


def test_parse_table_a_returns_eur_usd_gbp_in_order() -> None:
    table = parse_table_a(NBP_RESPONSE)
    assert table.table_no == "203/A/NBP/2027"
    assert table.effective_date == date(2027, 4, 20)
    assert [rate.code for rate in table.rates] == ["EUR", "USD", "GBP"]
    assert table.rates[0] == ExchangeRate("EUR", "euro", Decimal("4.2954"))


def test_mid_is_exact_decimal_not_float() -> None:
    rate = parse_table_a(NBP_RESPONSE).rate_for("USD")
    assert rate.mid == Decimal("3.9876")
    assert isinstance(rate.mid, Decimal)


def test_rate_for_unknown_code_raises_key_error() -> None:
    with pytest.raises(KeyError):
        parse_table_a(NBP_RESPONSE).rate_for("CHF")


def test_custom_currency_list() -> None:
    assert [r.code for r in parse_table_a(NBP_RESPONSE, codes=["THB"]).rates] == ["THB"]


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {},
        None,
        [{"no": "1", "effectiveDate": "2027-04-20", "rates": []}],  # brak EUR
        [{"no": "1", "effectiveDate": "zła data", "rates": NBP_RESPONSE[0]["rates"]}],
        [
            {
                "no": "1",
                "effectiveDate": "2027-04-20",
                "rates": [
                    {"currency": "euro", "code": "EUR", "mid": "abc"},
                    {"currency": "d", "code": "USD", "mid": 1},
                    {"currency": "f", "code": "GBP", "mid": 1},
                ],
            }
        ],
    ],
)
def test_parse_table_a_rejects_invalid_payload(payload: Any) -> None:
    with pytest.raises(ExternalServiceError) as error:
        parse_table_a(payload)
    assert error.value.service == "NBP"


def test_client_requests_json_format() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=NBP_RESPONSE)

    client = NbpClient(httpx.Client(transport=httpx.MockTransport(handler)), "https://nbp.test/A/")
    assert client.get_rates().rate_for("GBP").mid == Decimal("5.0123")
    assert requests[0].url.params["format"] == "json"


@pytest.mark.parametrize("status_code", [404, 500, 503])
def test_client_wraps_http_errors(status_code: int) -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(status_code))
    client = NbpClient(httpx.Client(transport=transport), "https://nbp.test/A/")
    with pytest.raises(ExternalServiceError) as error:
        client.get_rates()
    assert "niedostępny" in error.value.message


def test_client_wraps_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    client = NbpClient(httpx.Client(transport=httpx.MockTransport(handler)), "https://nbp.test/A/")
    with pytest.raises(ExternalServiceError):
        client.get_rates()
