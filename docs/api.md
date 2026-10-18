# API pod ekrany GUI

Pełna, zawsze aktualna specyfikacja (pola, typy, przykłady): **Swagger UI** http://localhost:8000/docs
i `GET /openapi.json`. Ten dokument mapuje endpointy na ekrany frontendu.

Wszystkie ścieżki mają prefiks `/api`. Poza oznaczonymi „publiczny” wymagają nagłówka
`X-User-Id: <id z logowania>`. Kwoty są w PLN (liczby JSON z 2 miejscami po przecinku),
daty w formacie `RRRR-MM-DD`, data z godziną bez strefy: `RRRR-MM-DDTGG:MM:SS`.

## Ekran: logowanie i rejestracja

| Metoda | Ścieżka | Opis |
|---|---|---|
| POST | `/auth/register` | publiczny; `{login, password}` → 201 `{id, login}`; 409 `LOGIN_TAKEN` |
| POST | `/auth/login` | publiczny; `{login, password}` → `{id, login}`; 401 `INVALID_CREDENTIALS` |
| GET | `/users/me` | profil: `{id, login, weather_city}` (sprawdzenie, czy id z localStorage jest ważne) |

Frontend po zalogowaniu zapisuje `id` w `localStorage` i dodaje nagłówek `X-User-Id` do każdego
zapytania. Odpowiedź 401 (`AUTH_REQUIRED`, `INVALID_USER`) → wyloguj i przejdź do logowania.

## Ekran główny „Moje podróże”

| Metoda | Ścieżka | Opis |
|---|---|---|
| GET | `/dashboard` | `{trips: {planned, in_progress, completed, archived}, countdown}` – 4 grupy + odliczanie („za 11 dni: Kraków”) |
| GET | `/weather/current` | widżet pogody dla miasta użytkownika; 503 → komunikat w widżecie |
| GET | `/weather/cities?query=Krak&limit=5` | pole wyszukiwania miasta w widżecie (min. 2 znaki) |
| PUT | `/users/me/weather-city` | zapis wybranego miasta `{name, country, latitude, longitude}` |
| GET | `/exchange-rates` | widżet kursów EUR/USD/GBP → PLN (tabela A NBP); 503 → komunikat |
| GET | `/exchange-rates/convert?amount=100&currency=EUR` | kalkulator walut (nic nie zapisuje) |
| GET | `/stats` | statystyki: podróże w roku, koszt wg charakteru, średni koszt dnia |

Widżety pobieraj niezależnie (osobne `fetch`), żeby awaria jednego API nie psuła ekranu.

## Formularz podróży

| Metoda | Ścieżka | Opis |
|---|---|---|
| GET | `/dictionaries` | publiczny; listy wyboru: `trip_characters`, `transport_means`, `expense_categories` (z id) oraz `trip_statuses`, `trip_types`, `place_kinds`, `sections`, `currencies` (wartość + polska etykieta) |
| POST | `/trips` | utwórz; status zawsze `planned`; zagraniczna dostaje domyślną listę pakowania |
| PUT | `/trips/{trip_id}` | pełna edycja; 409 `TRIP_TYPE_CHANGE_BLOCKED` przy zmianie na krajową z lotami |
| DELETE | `/trips/{trip_id}` | usuń razem ze wszystkim (204) |

## Ekran szczegółów podróży

| Metoda | Ścieżka | Opis |
|---|---|---|
| GET | `/trips/{trip_id}` | dane + pola pomocnicze dla GUI: `status_label`, `allowed_transitions` (przyciski zmiany statusu), `is_read_only` (wyłącz formularze w archiwum), `available_sections` (ukryj „Loty” dla krajowej), `duration_days` |
| POST | `/trips/{trip_id}/status` | `{status}` – tylko wartości z `allowed_transitions`; inaczej 409 |
| GET | `/trips?status=planned` | lista z filtrem statusu |

### Sekcje pozycji (koszt w PLN + ocena 1–5)

Każda sekcja ma te same operacje: `GET` lista, `POST` dodaj (201), `GET /{item_id}`,
`PUT /{item_id}` (pełna edycja), `DELETE /{item_id}` (204).

| Sekcja | Ścieżka | Pola wejściowe |
|---|---|---|
| Loty (tylko zagraniczna) | `/trips/{trip_id}/flights` | `flight_number, departure_airport, arrival_airport, departure_at, arrival_at?, cost, rating?` |
| Transport | `/trips/{trip_id}/transports` | `transport_mean_id, route_from, route_to, travel_date, cost, rating?` |
| Posiłki | `/trips/{trip_id}/meals` | `dish, restaurant_name, meal_date, cost, rating?` (ocena restauracji) |
| Noclegi i atrakcje | `/trips/{trip_id}/places` | `name, kind (accommodation/attraction), visit_date, cost, rating?, note?` |
| Wydatki inne | `/trips/{trip_id}/expenses` | `category_id, description, expense_date?, cost` (bez oceny) |

### Plan, listy, pamiętnik

| Sekcja | Ścieżka | Uwagi |
|---|---|---|
| Plan dnia | `/trips/{trip_id}/plan-points` | `day, planned_time?, place, description?`; dzień poza terminem → 422 `DATE_OUTSIDE_TRIP`; posortowane po dniu i godzinie |
| Chcę odwiedzić | `/trips/{trip_id}/wishlist` | edycja przez **PATCH** (`{"visited": true}` = odhaczenie); niezaliczone na górze |
| Lista pakowania | `/trips/{trip_id}/packing-items` | edycja przez **PATCH** (`{"packed": true}`); `is_default` = dodane automatycznie |
| Pamiętnik | `/trips/{trip_id}/diary-entries` | `entry_date, title?, content` |

### Zdjęcia i album

| Metoda | Ścieżka | Opis |
|---|---|---|
| POST | `/trips/{trip_id}/photos` | `multipart/form-data`: `file`, opcjonalnie `day`, `caption`; 413 `FILE_TOO_LARGE`, 422 `INVALID_UPLOAD` |
| GET | `/trips/{trip_id}/photos` | lista (metadane, `file_url`) |
| GET | `/trips/{trip_id}/album` | `[{day, photos: [...]}]` – album według dni |
| PATCH | `/trips/{trip_id}/photos/{photo_id}` | zmiana `day` / `caption` |
| DELETE | `/trips/{trip_id}/photos/{photo_id}` | usuwa też plik z dysku |
| GET | `/trips/{trip_id}/photos/{photo_id}/file` | sam obraz; wymaga `X-User-Id`, więc w `<img>` użyj `fetch` → `blob` → `URL.createObjectURL()` |

### Kosztorys i rekomendacje

| Metoda | Ścieżka | Opis |
|---|---|---|
| GET | `/trips/{trip_id}/cost-summary` | `total_cost`, `sections[]` (suma, liczba, średnia ocen), `average_rating`, `average_daily_cost`, `budget` (`remaining`, `overrun`, `usage_percent`, `alert_level`: `no_budget` / `ok` / `warning` / `exceeded`) |
| GET | `/trips/{trip_id}/recommendations?min_rating=4&limit=5` | `restaurants`, `places`, `pending_wishlist`, `previous_trips` z wcześniejszych podróży do tego miasta |

## Kody błędów

| HTTP | `code` | Kiedy |
|---|---|---|
| 401 | `AUTH_REQUIRED` | brak nagłówka `X-User-Id` |
| 401 | `INVALID_USER` | nagłówek nie jest liczbą albo użytkownik nie istnieje |
| 401 | `INVALID_CREDENTIALS` | zły login lub hasło |
| 404 | `NOT_FOUND` | brak zasobu albo zasób innego użytkownika |
| 404/405 | `HTTP_404` / `HTTP_405` | nieznana ścieżka / metoda |
| 409 | `LOGIN_TAKEN` | login zajęty |
| 409 | `TRIP_ARCHIVED` | zapis do podróży w archiwum |
| 409 | `INVALID_STATUS_TRANSITION` | przeskok statusu albo ten sam status |
| 409 | `SECTION_NOT_ALLOWED` | lot w podróży krajowej |
| 409 | `TRIP_TYPE_CHANGE_BLOCKED` | zmiana na krajową, gdy są loty |
| 413 | `FILE_TOO_LARGE` | zdjęcie za duże |
| 422 | `VALIDATION_ERROR` | błędne dane; lista `errors: [{field, message, type}]` do podświetlenia pól formularza |
| 422 | `INVALID_REFERENCE` | nieistniejące id ze słownika |
| 422 | `DATE_OUTSIDE_TRIP` | punkt planu poza terminem podróży |
| 422 | `INVALID_UPLOAD` | plik pusty albo nie jest zdjęciem JPG/PNG/GIF/WEBP |
| 503 | `EXTERNAL_API_UNAVAILABLE` | Open-Meteo lub NBP nie odpowiada (pole `service`) |
