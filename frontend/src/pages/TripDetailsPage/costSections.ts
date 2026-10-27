// Przepisy sekcji kosztowych dla CostSection: pola formularza (zgodne z backend/app/schemas/items.py)
// i wygląd pozycji na liście. Nowa sekcja = nowy przepis tutaj + gałąź w TripDetailsPage.
import type { Meal, Place, PlaceKind, Transport } from "../../types/api";
import type { SectionConfig } from "../../components/CostSection/CostSection";
import { capitalize, formatDate } from "../../utils/format";

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
