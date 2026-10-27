import { useEffect, useId, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { useNavigate } from "react-router";
import type { Dashboard, TripStatus } from "../../types/api";
import { api, ApiError } from "../../api/client";
import TripCard from "../../components/TripCard/TripCard";
import NextTripWidget from "./NextTripWidget";
import WeatherWidget from "./WeatherWidget";
import RatesWidget from "./RatesWidget";
import { useTabIndicator } from "../../hooks/useTabIndicator";
import styles from "./TripsPage.module.css";

/** Zakładka: jeden status albo „Wszystkie” */
type TabKey = TripStatus | "all";

const STATUSES: TripStatus[] = ["planned", "in_progress", "completed", "archived"];

const TABS: { status: TabKey; label: string }[] = [
  { status: "all", label: "Wszystkie" },
  { status: "planned", label: "W planie" },
  { status: "in_progress", label: "W trakcie" },
  { status: "completed", label: "Zrealizowane" },
  { status: "archived", label: "Archiwum" },
];

const EMPTY_TEXT: Record<TabKey, string> = {
  all: "Nie masz jeszcze żadnych podróży. Dodaj pierwszą przyciskiem „Nowa podróż”.",
  planned: "Nie masz zaplanowanych podróży. Dodaj pierwszą przyciskiem „Nowa podróż”.",
  in_progress: "Żadna podróż nie trwa w tej chwili.",
  completed: "Nie masz jeszcze zrealizowanych podróży.",
  archived: "Archiwum jest puste.",
};

type LoadState =
  | { status: "loading" }
  | { status: "ready"; data: Dashboard }
  | { status: "error"; message: string };

export default function TripsPage() {
  const [load, setLoad] = useState<LoadState>({ status: "loading" });
  const [reloadKey, setReloadKey] = useState(0);

  // Pobranie danych ekranu z GET /api/dashboard (ponownie po kliknięciu „Spróbuj ponownie”)
  useEffect(() => {
    let cancelled = false;
    api
      .get<Dashboard>("/dashboard")
      .then((data) => {
        if (!cancelled) setLoad({ status: "ready", data });
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        const message =
          error instanceof ApiError && error.status === 401
            ? "Nie jesteś zalogowana. Zaloguj się, aby zobaczyć swoje podróże."
            : error instanceof ApiError
              ? error.message
              : "Nie udało się wczytać podróży.";
        setLoad({ status: "error", message });
      });
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  function retry() {
    setLoad({ status: "loading" });
    setReloadKey((key) => key + 1);
  }

  const dashboard: Dashboard =
    load.status === "ready"
      ? load.data
      : { trips: { planned: [], in_progress: [], completed: [], archived: [] }, countdown: null };

  const navigate = useNavigate();
  const [active, setActive] = useState<TabKey>("all");
  const [query, setQuery] = useState("");
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const idPrefix = useId();
  const indicatorRef = useTabIndicator(
    tabRefs,
    TABS.findIndex((t) => t.status === active),
  );

  const q = query.trim().toLowerCase();
  // „Wszystkie” = grupy z dashboardu po kolei: w planie, w trakcie, zrealizowane, archiwum
  const tripsFor = (key: TabKey) => (key === "all" ? STATUSES.flatMap((s) => dashboard.trips[s]) : dashboard.trips[key]);
  const trips = tripsFor(active).filter(
    (t) => !q || t.name.toLowerCase().includes(q) || t.destination_city.toLowerCase().includes(q),
  );

  // Strzałki w lewo/prawo przełączają zakładki (wzorzec WAI-ARIA „Tabs”)
  function onTabKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    let next: number;
    if (event.key === "ArrowRight") next = (index + 1) % TABS.length;
    else if (event.key === "ArrowLeft") next = (index - 1 + TABS.length) % TABS.length;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = TABS.length - 1;
    else return;
    event.preventDefault();
    setActive(TABS[next].status);
    tabRefs.current[next]?.focus();
  }

  return (
    <div className={styles.page}>
      <section className={styles.content} aria-labelledby={`${idPrefix}-heading`}>
        <h1 id={`${idPrefix}-heading`} className="visually-hidden">
          Moje podróże
        </h1>

        <div className={styles.toolbar}>
          <div className={styles.search}>
            <label htmlFor={`${idPrefix}-search`} className={styles.label}>
              Szukaj podróży
            </label>
            <input
              id={`${idPrefix}-search`}
              type="search"
              className={styles.field}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              data-testid="input-search"
            />
          </div>
          <button
            type="button"
            className={styles.primary}
            onClick={() => navigate("/podroze/nowa")}
            data-testid="btn-new-trip"
          >
            <svg
              viewBox="0 0 24 24"
              width="18"
              height="18"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.4"
              aria-hidden="true"
            >
              <path d="M12 5v14M5 12h14" strokeLinecap="round" />
            </svg>
            Nowa podróż
          </button>
        </div>

        <div role="tablist" aria-label="Status podróży" className={styles.tabs}>
          <span ref={indicatorRef} className={styles.tabIndicator} aria-hidden="true" />
          {TABS.map((tab, index) => {
            const selected = tab.status === active;
            return (
              <button
                key={tab.status}
                ref={(el) => {
                  tabRefs.current[index] = el;
                }}
                type="button"
                role="tab"
                id={`${idPrefix}-tab-${tab.status}`}
                aria-selected={selected}
                aria-controls={`${idPrefix}-panel`}
                tabIndex={selected ? 0 : -1}
                className={selected ? `${styles.tab} ${styles.tabActive}` : styles.tab}
                onClick={() => setActive(tab.status)}
                onKeyDown={(e) => onTabKeyDown(e, index)}
                data-testid={`status-tab-${tab.status.replace("_", "-")}`}
              >
                {tab.label} {tripsFor(tab.status).length}
              </button>
            );
          })}
        </div>

        <div
          key={active}
          role="tabpanel"
          id={`${idPrefix}-panel`}
          aria-labelledby={`${idPrefix}-tab-${active}`}
          className={styles.list}
        >
          {load.status === "loading" ? (
            <p className={styles.empty} role="status" data-testid="trips-loading">
              Wczytywanie podróży…
            </p>
          ) : load.status === "error" ? (
            <div className={styles.error} role="alert" data-testid="trips-error">
              <p>{load.message}</p>
              <button type="button" className={styles.secondary} onClick={retry} data-testid="trips-retry">
                Spróbuj ponownie
              </button>
            </div>
          ) : trips.length > 0 ? (
            trips.map((trip) => <TripCard key={trip.id} trip={trip} />)
          ) : (
            <p className={styles.empty} data-testid="trips-empty">
              {q ? `Brak podróży pasujących do „${query.trim()}”.` : EMPTY_TEXT[active]}
            </p>
          )}
        </div>
      </section>

      <aside className={styles.aside} aria-label="Widżety">
        <div className={styles.nextTrip}>
          <NextTripWidget countdown={dashboard.countdown} />
        </div>
        <WeatherWidget />
        <RatesWidget />
      </aside>
    </div>
  );
}
