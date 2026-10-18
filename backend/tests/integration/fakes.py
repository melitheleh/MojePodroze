"""Atrapy klientów zewnętrznych API (Open-Meteo, NBP) używane w testach integracyjnych."""

from datetime import date
from decimal import Decimal

from app.integrations.errors import ExternalServiceError
from app.integrations.nbp import ExchangeRate, ExchangeRatesTable
from app.integrations.open_meteo import City, CurrentWeather


class FakeWeatherClient:
    """Atrapa klienta Open-Meteo: zapamiętuje wywołania, może udawać awarię."""

    def __init__(self) -> None:
        self.fail = False
        self.weather_calls: list[tuple[float, float]] = []

    def _check(self) -> None:
        if self.fail:
            raise ExternalServiceError("Open-Meteo", "Serwis pogody jest chwilowo niedostępny.")

    def search_cities(self, query: str, limit: int = 5) -> list[City]:
        self._check()
        cities = [
            City("Kraków", "Polska", "Małopolskie", 50.06143, 19.93658),
            City("Krakow", "Stany Zjednoczone", "Wisconsin", 44.76, -88.39),
        ]
        return [city for city in cities if query.casefold()[:4] in city.name.casefold()][:limit]

    def current_weather(self, latitude: float, longitude: float) -> CurrentWeather:
        self._check()
        self.weather_calls.append((latitude, longitude))
        return CurrentWeather(
            temperature_c=14.3,
            apparent_temperature_c=12.9,
            relative_humidity=61,
            wind_speed_kmh=11.5,
            weather_code=3,
            description="Pochmurno",
            is_day=True,
            observed_at="2027-04-20T12:00",
        )


class FakeRatesClient:
    def __init__(self) -> None:
        self.fail = False

    def get_rates(self) -> ExchangeRatesTable:
        if self.fail:
            raise ExternalServiceError("NBP", "Serwis kursów walut NBP jest chwilowo niedostępny.")
        return ExchangeRatesTable(
            table_no="076/A/NBP/2027",
            effective_date=date(2027, 4, 19),
            rates=(
                ExchangeRate("EUR", "euro", Decimal("4.2954")),
                ExchangeRate("USD", "dolar amerykański", Decimal("3.9876")),
                ExchangeRate("GBP", "funt szterling", Decimal("5.0123")),
            ),
        )
