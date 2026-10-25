# Styl wizualny frontendu – odświeżony „Trouvaille”

Wzór dla frontendu aplikacji „Moje podróże”. Bazą są makiety wybrane przez grupę
([makiety-styl-trouvaille.pdf](makiety-styl-trouvaille.pdf), 11 ekranów) – **układ ekranów zostaje
taki jak w makietach**. Zmiany względem makiet:

- zaokrąglone rogi kart, widżetów i przycisków,
- przyciski w kolorze szałwii zamiast czarnego,
- bez różowego akcentu w trybie jasnym (aktywna zakładka podkreślona szałwią),
- tryb ciemny na zielonkawym graficie zamiast czerni, z przygaszonym różem tylko do wyróżnienia,
- wyraźniejsze linie pól i widoczny fokus – zgodność z **WCAG 2.0, poziom AA**.

Odświeżone ekrany (lista podróży: desktop, telefon, tryb ciemny) są na kanwie projektu
„Moje podróże – odświeżony Trouvaille” w claude.ai.

## Technologia stylów

Bez frameworka CSS. **CSS Modules** (wbudowane w Vite) + globalne **tokeny jako zmienne CSS**:

```
frontend/src/
├── styles/
│   ├── tokens.css      ← zmienne z sekcji „Tokeny” (+ tryb ciemny)
│   └── global.css      ← fonty, reset, body, fokus
└── components/
    └── TripCard/
        ├── TripCard.tsx
        └── TripCard.module.css
```

## Tokeny (zmienne CSS)

```css
:root {
  /* fonty */
  --font-body: "Raleway", system-ui, sans-serif;
  --font-logo: "Yellowtail", cursive;

  /* tło i powierzchnie */
  --color-bg: #ffffff;
  --color-surface: #ffffff;              /* karty i widżety (odcina je cień) */
  --color-brand-panel: #4e5d56;          /* panel na ekranie logowania */

  /* tekst */
  --color-text: #27302c;                 /* ciemny szarozielony zamiast czerni */
  --color-text-muted: #5f6b65;           /* etykiety, daty, opisy */
  --color-text-on-accent: #ffffff;

  /* przyciski i akcent */
  --color-accent: #5f7a6c;               /* szałwia: przycisk główny, aktywna zakładka, fokus */
  --color-btn-secondary-border: #5f7a6c; /* przycisk poboczny: biały z obrysem */

  /* linie */
  --color-field-line: #7d8882;           /* linia pod polem formularza (3,7 : 1) */
  --color-divider: rgba(39, 48, 44, 0.1);/* linie podziału, nagłówek */

  /* statusy podróży (kreska pod etykietą, zawsze z napisem obok);
     nazwa = wartość statusu z API, podkreślnik zamieniony na myślnik */
  --status-planned: #3b6df5;             /* W PLANIE */
  --status-in-progress: #f1b647;         /* W TRAKCIE */
  --status-completed: #17a34a;           /* ZREALIZOWANA */
  --status-archived: #8a8a94;            /* ARCHIWUM */

  /* kreska pod tytułem widżetu */
  --widget-next-trip: #f1b647;           /* „Najbliższa podróż” */
  --widget-weather: #3b6df5;             /* „Pogoda” */
  --widget-rates: #17a34a;               /* „Kursy NBP” */

  /* komunikaty */
  --color-warning-bg: #fef3c6;
  --color-warning-bar: #d97605;
  --color-error-bg: #fee2e1;
  --color-error-text: #942827;

  /* miniatury zastępcze (gdy brak zdjęcia) */
  --placeholder-1: #c8a178;
  --placeholder-2: #7f9ab7;
  --placeholder-3: #d7a8a0;
  --placeholder-4: #9fb8a6;
  --placeholder-5: #b8b0d6;

  /* kształt */
  --radius-card: 16px;                   /* karty, widżety */
  --radius-button: 12px;                 /* przyciski */
  --radius-small: 10px;                  /* małe przyciski, pozycje menu */
  --shadow-card: 0 1px 3px rgba(39, 48, 44, 0.05), 0 8px 24px rgba(39, 48, 44, 0.07);
  --shadow-card-hover: 0 2px 4px rgba(39, 48, 44, 0.05), 0 14px 32px rgba(39, 48, 44, 0.10);

  /* fokus */
  --focus-ring: #5f7a6c;

  /* szerokość strony i marginesy boczne (na telefonie, do 640 px: 16px) */
  --page-width: 1280px;
  --page-padding: 32px;
}

[data-theme="dark"] {
  --color-bg: #18201c;                   /* głęboki zielonkawy grafit, nie czerń */
  --color-surface: #212b26;
  --color-text: #e8ece9;
  --color-text-muted: #a7b3ac;           /* opisy */
  --color-text-soft: #c9d1cc;            /* nieaktywne pozycje menu */
  --color-field-line: #7a8680;
  --color-divider: rgba(255, 255, 255, 0.08);
  --color-btn-secondary-border: #9fb8a6;
  --status-planned: #7b9bf5;             /* jaśniejszy niebieski na ciemnym tle */
  --widget-weather: #7b9bf5;
  --focus-ring: #9fb8a6;
  --shadow-card: 0 1px 2px rgba(0, 0, 0, 0.3), 0 8px 24px rgba(0, 0, 0, 0.25);
  --shadow-card-hover: 0 2px 4px rgba(0, 0, 0, 0.35), 0 14px 32px rgba(0, 0, 0, 0.35);

  /* przygaszony róż – tylko wyróżnienie aktywnej opcji / propozycji */
  --color-highlight-bg: #3a2a33;
  --color-highlight-border: rgba(242, 201, 220, 0.35);
  --color-highlight-text: #f6d6e5;
  --color-suggestion-bg: rgba(216, 167, 191, 0.1);
}
```

Przycisk główny w obu trybach: tło `--color-accent` (#5f7a6c), biały tekst.

## Typografia

| Rola | Krój | Uwagi |
|---|---|---|
| Logo „Moje podróże” | Yellowtail (Google Fonts) | tylko logo |
| Cały interfejs | **Raleway** (Google Fonts) | `font-variant-numeric: lining-nums` – równe cyfry w datach i kwotach |
| Etykiety pól i statusów | Raleway 600, WERSALIKI, 12 px, `letter-spacing: 0.1em` | kolor `--color-text-muted`, kreska 2 px pod etykietą statusu |
| Tytuł karty podróży | Raleway 500, 24 px | |
| Duże liczby (temperatura, sumy) | Raleway 700, 34 px | |

## Układ (jak w makietach)

- Górny pasek: logo, „Moje podróże”, „Statystyki”, po prawej „Wyloguj”; cienka linia pod spodem.
- Lista podróży: kolumna główna (wyszukiwarka + „+ Nowa podróż”, zakładki statusów z licznikami,
  karty) i kolumna widżetów (najbliższa podróż, pogoda, kursy NBP).
- Karta podróży: tekst po lewej (status, tytuł, daty · typ · charakter), zdjęcie po prawej (~38%).
- Pola formularzy: etykieta WERSALIKAMI nad polem, linia pod polem, bez ramki.
- Zakładki: aktywna pogrubiona i podkreślona kreską 2 px w kolorze szałwii.
- Po najechaniu karta lekko się unosi (cień `--shadow-card-hover`, przesunięcie 2 px).
- Mobile: jedna kolumna, zakładki przewijane w poziomie (z „Archiwum”), kafel „Najbliższa podróż” nad listą.

## Dostępność – WCAG 2.0, poziom AA

Kontrasty (sprawdzone, minimum dla tekstu 4,5 : 1):

| Para | Kontrast |
|---|---|
| tekst #27302c na bieli | 13,6 : 1 |
| opis #5f6b65 na bieli | 5,6 : 1 |
| biały tekst na szałwii #5f7a6c | 4,7 : 1 |
| tryb ciemny: tekst #e8ece9 na karcie #212b26 | 12,2 : 1 |
| tryb ciemny: opis #a7b3ac na karcie | 6,7 : 1 |
| tryb ciemny: aktywna opcja #f6d6e5 na #3a2a33 | 10,1 : 1 |
| linia pola #7d8882 na bieli / #7a8680 na #18201c | 3,7 : 1 / 4,4 : 1 |

Fokus (kryterium 2.4.7):

```css
a:focus-visible,
button:focus-visible {
  outline: 3px solid var(--focus-ring);
  outline-offset: 3px;
  border-radius: var(--radius-button);
}
input:focus,
select:focus {
  outline: none;
  border-bottom-color: var(--focus-ring);
  box-shadow: 0 2px 0 0 var(--focus-ring);   /* linia pogrubia się do 3 px */
}
```

Zasady przy kodowaniu:

- każde pole ma `<label>` (etykieta widoczna albo ukryta wizualnie, np. przy wyszukiwarce),
- zdjęcia mają `alt` z opisem (podpis z albumu), dekoracyjne – `alt=""`,
- `<html lang="pl">`,
- wszystko obsługiwane z klawiatury (Tab, Enter, Spacja), zakładki z `role="tab"` i `aria-selected`,
- błędy formularzy opisane tekstem przy polu, nie tylko kolorem,
- status podróży zawsze jako napis + kolorowa kreska (kolor nie jest jedyną informacją),
- strona działa po powiększeniu tekstu do 200%.

## Testy (Playwright)

Elementy interaktywne mają `data-testid`, np. `trip-card`, `status-tab-planned`, `status-tab-in-progress`,
`status-tab-completed`, `status-tab-archived`, `btn-new-trip`, `input-search`, `input-weather-city`,
`input-eur-amount`, `eur-result`, `widget-next-trip`, `widget-weather`, `widget-nbp`,
`weather-error`, `weather-retry`, `theme-light`, `theme-dark`, `nav-trips`, `nav-stats`, `btn-logout`,
`trip-status`, `countdown`, `weather-current`, `trips-loading`, `trips-error`, `trips-retry`, `trips-empty`.

## Do dopilnowania

- Archiwum: pola i przyciski edycji ukryte lub zablokowane.
- Zakładka „Loty” tylko dla podróży zagranicznych.
