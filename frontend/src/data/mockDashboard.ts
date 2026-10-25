// Dane przykładowe, dopóki ekran nie jest podłączony do API (GET /api/dashboard).
import type { Dashboard, ExchangeRate, Trip } from "../types/api";

const city: Trip["character"] = { id: 3, code: "city", name: "Miasto" };
const mountains: Trip["character"] = { id: 1, code: "mountains", name: "Góry" };
const sea: Trip["character"] = { id: 2, code: "sea", name: "Morze" };

function trip(
  partial: Omit<Trip, "status_label" | "trip_type_label" | "allowed_transitions" | "is_read_only" | "available_sections">,
): Trip {
  const labels = {
    planned: "w planie",
    in_progress: "w trakcie",
    completed: "zrealizowana",
    archived: "archiwum",
  } as const;
  return {
    ...partial,
    status_label: labels[partial.status],
    trip_type_label: partial.trip_type === "foreign" ? "zagraniczna" : "krajowa",
    allowed_transitions: [],
    is_read_only: partial.status === "archived",
    available_sections: partial.trip_type === "foreign"
      ? ["flights", "transport", "meals", "places", "expenses"]
      : ["transport", "meals", "places", "expenses"],
  };
}

export const mockDashboard: Dashboard = {
  trips: {
    planned: [
      trip({ id: 1, name: "Rzym – długi weekend", destination_city: "Rzym", destination_country: "Włochy", start_date: "2026-11-12", end_date: "2026-11-15", trip_type: "foreign", character: city, status: "planned", planned_budget: 3800, duration_days: 4 }),
      trip({ id: 2, name: "Tatry – zima", destination_city: "Zakopane", destination_country: "Polska", start_date: "2026-12-20", end_date: "2026-12-27", trip_type: "domestic", character: mountains, status: "planned", planned_budget: null, duration_days: 8 }),
      trip({ id: 3, name: "Lizbona – wiosna", destination_city: "Lizbona", destination_country: "Portugalia", start_date: "2027-03-03", end_date: "2027-03-08", trip_type: "foreign", character: city, status: "planned", planned_budget: null, duration_days: 6 }),
    ],
    in_progress: [
      trip({ id: 4, name: "Hel – rowerem", destination_city: "Hel", destination_country: "Polska", start_date: "2026-10-14", end_date: "2026-10-19", trip_type: "domestic", character: sea, status: "in_progress", planned_budget: null, duration_days: 6 }),
    ],
    completed: [],
    archived: [
      trip({ id: 5, name: "Paryż – wiosna 2025", destination_city: "Paryż", destination_country: "Francja", start_date: "2025-04-04", end_date: "2025-04-08", trip_type: "foreign", character: city, status: "archived", planned_budget: 4500, duration_days: 5 }),
    ],
  },
  countdown: { trip_id: 1, trip_name: "Rzym – długi weekend", destination_city: "Rzym", start_date: "2026-11-12", days_left: 25 },
};

export const mockRates: ExchangeRate[] = [
  { code: "EUR", currency: "euro", mid: 4.27 },
  { code: "USD", currency: "dolar amerykański", mid: 3.68 },
  { code: "GBP", currency: "funt szterling", mid: 4.93 },
];
