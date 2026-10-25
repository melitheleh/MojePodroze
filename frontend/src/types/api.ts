// Typy odpowiedzi API – zgodne ze schematami backendu (backend/app/schemas).

export type TripStatus = "planned" | "in_progress" | "completed" | "archived";
export type TripType = "domestic" | "foreign";
export type Section = "flights" | "transport" | "meals" | "places" | "expenses";

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

export interface ExchangeRate {
  code: string;
  currency: string;
  mid: number;
}
