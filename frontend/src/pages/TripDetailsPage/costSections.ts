// Przepisy sekcji kosztowych dla CostSection: pola formularza (zgodne z backend/app/schemas/items.py)
// i wygląd pozycji na liście. Nowa sekcja = nowy przepis tutaj + gałąź w TripDetailsPage.
import type { Expense, Flight, Meal, Place, PlaceKind, Transport } from "../../types/api";
import type { SectionConfig } from "../../components/CostSection/CostSection";
import { capitalize, formatDate, formatDateTime } from "../../utils/format";

const MAX_FLIGHT_HOURS = 48;

/** "2026-09-21T10:30" + 48 h → "2026-09-23T10:30" (czas lokalny bez strefy, liczony jak UTC – bez zmian czasu) */
function addHours(local: string, hours: number): string {
  const [date, time] = local.split("T");
  const [y, m, d] = date.split("-").map(Number);
  const [hh, mm] = time.split(":").map(Number);
  return new Date(Date.UTC(y, m - 1, d, hh + hours, mm)).toISOString().slice(0, 16);
}

// Loty – zakładka tylko dla podróży zagranicznej (available_sections z API)
export const FLIGHTS: SectionConfig<Flight> = {
  path: "flights",
  title: "Loty",
  testId: { single: "flight", plural: "flights" },
  texts: {
    add: "Dodaj lot",
    new: "Nowy lot",
    edit: "Edytuj lot",
    remove: "Usuń lot",
    removeTitle: "Usunąć lot?",
    empty: "Nie dodano jeszcze żadnego lotu.",
    loading: "Wczytywanie lotów…",
    loadError: "Nie udało się wczytać lotów.",
    saveError: "Nie udało się zapisać lotu.",
    removeError: "Nie udało się usunąć lotu.",
  },
  fields: [
    { name: "flight_number", label: "Numer lotu", kind: "text", testKey: "number", required: true, requiredMessage: "Podaj numer lotu, np. LO 327.", minLength: 2, maxLength: 10 },
    { name: "departure_airport", label: "Lotnisko wylotu", kind: "text", testKey: "from", required: true, requiredMessage: "Podaj lotnisko wylotu.", maxLength: 100 },
    { name: "arrival_airport", label: "Lotnisko przylotu", kind: "text", testKey: "to", required: true, requiredMessage: "Podaj lotnisko przylotu.", maxLength: 100 },
    { name: "departure_at", label: "Wylot (data i godzina)", kind: "datetime", testKey: "departure", required: true, requiredMessage: "Podaj datę i godzinę wylotu." },
    // Przylot może wypaść po końcu podróży (lot nocny) – zakres od wylotu do wylotu + 48 h (limits)
    { name: "arrival_at", label: "Przylot (opcjonalnie)", kind: "datetime", testKey: "arrival", anyDate: true },
    { name: "cost", label: "Koszt (PLN)", kind: "money", testKey: "cost" },
    { name: "rating", label: "Ocena", kind: "rating", testKey: "rating" },
  ],
  // „Nie wcześniej niż wylot” jak w backendzie (FlightIn.check_times); limit 48 h tylko we frontendzie.
  // Format "RRRR-MM-DDTGG:MM" da się porównać jak tekst.
  validate: (v) => {
    const errors: Record<string, string> = {};
    if (v.departure_at && v.arrival_at) {
      if (v.arrival_at < v.departure_at) errors.arrival_at = "Przylot nie może być wcześniejszy niż wylot.";
      else if (v.arrival_at > addHours(v.departure_at, MAX_FLIGHT_HOURS))
        errors.arrival_at = `Przylot najpóźniej ${MAX_FLIGHT_HOURS} godziny po wylocie.`;
    }
    return errors;
  },
  limits: (v) => ({
    arrival_at: v.departure_at ? { min: v.departure_at, max: addHours(v.departure_at, MAX_FLIGHT_HOURS) } : {},
  }),
  itemTitle: (f) => `${f.departure_airport} → ${f.arrival_airport}`,
  itemMeta: (f) => [
    f.flight_number,
    `wylot ${formatDateTime(f.departure_at)}`,
    ...(f.arrival_at ? [`przylot ${formatDateTime(f.arrival_at)}`] : []),
  ],
  itemRating: (f) => f.rating,
  removeMessage: (f) => `Lot ${f.flight_number} (${f.departure_airport} → ${f.arrival_airport})`,
};

export const MEALS: SectionConfig<Meal> = {
  path: "meals",
  title: "Posiłki",
  testId: { single: "meal", plural: "meals" },
  texts: {
    add: "Dodaj posiłek",
    new: "Nowy posiłek",
    edit: "Edytuj posiłek",
    remove: "Usuń posiłek",
    removeTitle: "Usunąć posiłek?",
    empty: "Nie dodano jeszcze żadnego posiłku.",
    loading: "Wczytywanie posiłków…",
    loadError: "Nie udało się wczytać posiłków.",
    saveError: "Nie udało się zapisać posiłku.",
    removeError: "Nie udało się usunąć posiłku.",
  },
  fields: [
    { name: "dish", label: "Danie", kind: "text", testKey: "dish", required: true, requiredMessage: "Podaj, co było jedzone.", maxLength: 200 },
    { name: "restaurant_name", label: "Restauracja", kind: "text", testKey: "restaurant", required: true, requiredMessage: "Podaj nazwę restauracji.", maxLength: 150 },
    { name: "meal_date", label: "Data", kind: "date", testKey: "date", required: true, requiredMessage: "Podaj datę posiłku." },
    { name: "cost", label: "Koszt (PLN)", kind: "money", testKey: "cost" },
    { name: "rating", label: "Ocena restauracji", kind: "rating", testKey: "rating" },
  ],
  itemTitle: (m) => m.dish,
  itemMeta: (m) => [m.restaurant_name, formatDate(m.meal_date)],
  itemRating: (m) => m.rating,
  removeMessage: (m) => `„${m.dish}” (${m.restaurant_name}, ${formatDate(m.meal_date)})`,
};

export const TRANSPORTS: SectionConfig<Transport> = {
  path: "transports",
  title: "Transport",
  testId: { single: "transport", plural: "transports" },
  texts: {
    add: "Dodaj przejazd",
    new: "Nowy przejazd",
    edit: "Edytuj przejazd",
    remove: "Usuń przejazd",
    removeTitle: "Usunąć przejazd?",
    empty: "Nie dodano jeszcze żadnego przejazdu.",
    loading: "Wczytywanie przejazdów…",
    loadError: "Nie udało się wczytać przejazdów.",
    saveError: "Nie udało się zapisać przejazdu.",
    removeError: "Nie udało się usunąć przejazdu.",
  },
  fields: [
    {
      name: "transport_mean_id",
      label: "Środek transportu",
      kind: "select",
      testKey: "mean",
      required: true,
      requiredMessage: "Wybierz środek transportu.",
      numeric: true,
      options: (d) => d.transport_means.map((m) => ({ value: String(m.id), label: m.name })),
      fromItem: (t: Transport) => t.transport_mean.id,
    },
    { name: "travel_date", label: "Data", kind: "date", testKey: "date", required: true, requiredMessage: "Podaj datę przejazdu." },
    { name: "route_from", label: "Skąd", kind: "text", testKey: "from", required: true, requiredMessage: "Podaj miejsce wyjazdu.", maxLength: 100 },
    { name: "route_to", label: "Dokąd", kind: "text", testKey: "to", required: true, requiredMessage: "Podaj miejsce docelowe.", maxLength: 100 },
    { name: "cost", label: "Koszt (PLN)", kind: "money", testKey: "cost" },
    { name: "rating", label: "Ocena", kind: "rating", testKey: "rating" },
  ],
  itemTitle: (t) => `${t.route_from} → ${t.route_to}`,
  itemMeta: (t) => [t.transport_mean.name, formatDate(t.travel_date)],
  itemRating: (t) => t.rating,
  removeMessage: (t) => `Przejazd „${t.route_from} → ${t.route_to}” (${formatDate(t.travel_date)})`,
};

// Etykiety rodzaju na liście (formularz bierze je ze słownika place_kinds)
const PLACE_KIND_LABEL: Record<PlaceKind, string> = {
  accommodation: "Nocleg",
  attraction: "Atrakcja",
};

export const PLACES: SectionConfig<Place> = {
  path: "places",
  title: "Noclegi i atrakcje",
  testId: { single: "place", plural: "places" },
  texts: {
    add: "Dodaj nocleg lub atrakcję",
    new: "Nowy nocleg lub atrakcja",
    edit: "Edytuj nocleg lub atrakcję",
    remove: "Usuń pozycję",
    removeTitle: "Usunąć pozycję?",
    empty: "Nie dodano jeszcze noclegów ani atrakcji.",
    loading: "Wczytywanie noclegów i atrakcji…",
    loadError: "Nie udało się wczytać noclegów i atrakcji.",
    saveError: "Nie udało się zapisać pozycji.",
    removeError: "Nie udało się usunąć pozycji.",
  },
  fields: [
    { name: "name", label: "Nazwa", kind: "text", testKey: "name", required: true, requiredMessage: "Podaj nazwę miejsca.", maxLength: 150 },
    {
      name: "kind",
      label: "Rodzaj",
      kind: "select",
      testKey: "kind",
      required: true,
      requiredMessage: "Wybierz rodzaj.",
      options: (d) => d.place_kinds.map((k) => ({ value: k.value, label: capitalize(k.label) })),
    },
    { name: "visit_date", label: "Data", kind: "date", testKey: "date", required: true, requiredMessage: "Podaj datę." },
    { name: "cost", label: "Koszt (PLN)", kind: "money", testKey: "cost" },
    { name: "rating", label: "Ocena", kind: "rating", testKey: "rating" },
    { name: "note", label: "Notatka (opcjonalnie)", kind: "textarea", testKey: "note", maxLength: 2000 },
  ],
  itemTitle: (p) => p.name,
  itemMeta: (p) => [PLACE_KIND_LABEL[p.kind], formatDate(p.visit_date)],
  itemRating: (p) => p.rating,
  itemNote: (p) => p.note,
  removeMessage: (p) => `„${p.name}” (${PLACE_KIND_LABEL[p.kind].toLowerCase()}, ${formatDate(p.visit_date)})`,
};

export const EXPENSES: SectionConfig<Expense> = {
  path: "expenses",
  title: "Wydatki inne",
  testId: { single: "expense", plural: "expenses" },
  texts: {
    add: "Dodaj wydatek",
    new: "Nowy wydatek",
    edit: "Edytuj wydatek",
    remove: "Usuń wydatek",
    removeTitle: "Usunąć wydatek?",
    empty: "Nie dodano jeszcze żadnych wydatków.",
    loading: "Wczytywanie wydatków…",
    loadError: "Nie udało się wczytać wydatków.",
    saveError: "Nie udało się zapisać wydatku.",
    removeError: "Nie udało się usunąć wydatku.",
  },
  // Bez oceny; data opcjonalna (np. ubezpieczenie kupione przed wyjazdem)
  fields: [
    { name: "description", label: "Opis", kind: "text", testKey: "description", required: true, requiredMessage: "Podaj, na co był wydatek.", maxLength: 255 },
    {
      name: "category_id",
      label: "Kategoria",
      kind: "select",
      testKey: "category",
      required: true,
      requiredMessage: "Wybierz kategorię.",
      numeric: true,
      options: (d) => d.expense_categories.map((c) => ({ value: String(c.id), label: c.name })),
      fromItem: (e: Expense) => e.category.id,
    },
    // Dowolna data – np. ubezpieczenie albo bilety kupione przed wyjazdem
    { name: "expense_date", label: "Data (opcjonalnie)", kind: "date", testKey: "date", anyDate: true },
    { name: "cost", label: "Kwota (PLN)", kind: "money", testKey: "cost" },
  ],
  itemTitle: (e) => e.description,
  itemMeta: (e) => [e.category.name, e.expense_date ? formatDate(e.expense_date) : "bez daty"],
  removeMessage: (e) => `„${e.description}” (${e.category.name})`,
};
