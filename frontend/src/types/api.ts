// Typy odpowiedzi API – zgodne ze schematami backendu (backend/app/schemas).

export type TripStatus = "planned" | "in_progress" | "completed" | "archived";
export type TripType = "domestic" | "foreign";
export type Section = "flights" | "transport" | "meals" | "places" | "expenses";

export interface User {
  id: number;
  login: string;
}

export interface DictionaryEntry {
  id: number;
  code: string;
  name: string;
}

export interface Trip {
  id: number;
  name: string;
  destination_city: string;
  destination_country: string;
  start_date: string; // RRRR-MM-DD
  end_date: string;
  trip_type: TripType;
  character: DictionaryEntry;
  status: TripStatus;
  planned_budget: number | null;
  status_label: string;
  trip_type_label: string;
  duration_days: number;
  allowed_transitions: TripStatus[];
  is_read_only: boolean;
  available_sections: Section[];
}

export interface Countdown {
  trip_id: number;
  trip_name: string;
  destination_city: string;
  start_date: string;
  days_left: number;
}

export interface Dashboard {
  trips: Record<TripStatus, Trip[]>;
  countdown: Countdown | null;
}

export interface WeatherCity {
  name: string;
  country: string | null;
  latitude: number;
  longitude: number;
}

/** Wynik wyszukiwania miasta: GET /api/weather/cities */
export interface CitySearchResult extends WeatherCity {
  region: string | null;
}

export interface CurrentWeather {
  temperature_c: number;
  apparent_temperature_c: number | null;
  relative_humidity: number | null;
  wind_speed_kmh: number | null;
  weather_code: number;
  description: string;
  is_day: boolean | null;
  observed_at: string;
}

/** GET /api/weather/current */
export interface WeatherResponse {
  city: WeatherCity;
  weather: CurrentWeather;
}

export interface ExchangeRate {
  code: string;
  currency: string;
  mid: number;
}

/** GET /api/exchange-rates */
export interface ExchangeRates {
  table_no: string;
  effective_date: string; // RRRR-MM-DD
  rates: ExchangeRate[];
}

/** GET /api/exchange-rates/convert */
export interface Conversion {
  amount: number;
  currency: string;
  rate: number;
  amount_pln: number;
  effective_date: string;
}
