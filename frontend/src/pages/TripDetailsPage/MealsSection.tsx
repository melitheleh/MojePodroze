import { useEffect, useId, useState } from "react";
import type { FormEvent } from "react";
import type { Meal, MealInput } from "../../types/api";
import { api, ApiError } from "../../api/client";
import { formatDate, formatPln } from "../../utils/format";
import { useConfirm } from "../../hooks/useConfirm";
import styles from "./MealsSection.module.css";

type FieldName = "dish" | "restaurant_name" | "meal_date" | "cost";
type FieldErrors = Partial<Record<FieldName, string>>;

interface FormValues {
  dish: string;
  restaurant_name: string;
  meal_date: string;
  cost: string;
  rating: string; // "" = bez oceny
}

type LoadState =
  | { status: "loading" }
  | { status: "ready"; meals: Meal[] }
  | { status: "error"; message: string };

/** Formularz zamknięty, dodawanie albo edycja wybranego posiłku */
type FormMode = { kind: "closed" } | { kind: "add" } | { kind: "edit"; meal: Meal };

// Koszt jak w backendzie: liczba ≥ 0, najwyżej 2 miejsca po przecinku (przecinek albo kropka)
const COST_PATTERN = /^\d{1,10}([.,]\d{1,2})?$/;

// Te same zasady co w backendzie (backend/app/schemas/items.py) – tu, żeby pokazać błąd po polsku przy polu.
function validate(values: FormValues): FieldErrors {
  const errors: FieldErrors = {};
  if (values.dish.trim() === "") errors.dish = "Podaj, co było jedzone.";
  else if (values.dish.trim().length > 200) errors.dish = "Najwyżej 200 znaków.";
  if (values.restaurant_name.trim() === "") errors.restaurant_name = "Podaj nazwę restauracji.";
  else if (values.restaurant_name.trim().length > 150) errors.restaurant_name = "Najwyżej 150 znaków.";
  if (values.meal_date === "") errors.meal_date = "Podaj datę posiłku.";
  if (!COST_PATTERN.test(values.cost.trim())) errors.cost = "Podaj kwotę, np. 45 albo 45,50.";
  return errors;
}

function toInput(values: FormValues): MealInput {
  return {
    dish: values.dish.trim(),
    restaurant_name: values.restaurant_name.trim(),
    meal_date: values.meal_date,
    cost: Number(values.cost.trim().replace(",", ".")),
    rating: values.rating === "" ? null : Number(values.rating),
  };
}

function toValues(meal: Meal): FormValues {
  return {
    dish: meal.dish,
    restaurant_name: meal.restaurant_name,
    meal_date: meal.meal_date,
    cost: String(meal.cost).replace(".", ","),
    rating: meal.rating === null ? "" : String(meal.rating),
  };
}

function emptyValues(day: string): FormValues {
  return { dish: "", restaurant_name: "", meal_date: day, cost: "", rating: "" };
}

/** Ocena jako gwiazdki (dekoracja) + napis dla czytników ekranu */
function Rating({ value }: { value: number | null }) {
  if (value === null) return <span className={styles.muted}>bez oceny</span>;
  return (
    <span className={styles.rating}>
      <span aria-hidden="true">{"★".repeat(value) + "☆".repeat(5 - value)}</span>
      <span className="visually-hidden">ocena {value} na 5</span>
    </span>
  );
}

interface Props {
  tripId: number;
  /** Archiwum: lista bez formularza i przycisków */
  readOnly: boolean;
  /** Domyślna data nowego posiłku */
  defaultDate: string;
}

// Zakładka „Posiłki”: lista z GET /api/trips/{id}/meals, dodawanie (POST), edycja (PUT), usuwanie (DELETE).
export default function MealsSection({ tripId, readOnly, defaultDate }: Props) {
  const [load, setLoad] = useState<LoadState>({ status: "loading" });
  const [reloadKey, setReloadKey] = useState(0);
  const [mode, setMode] = useState<FormMode>({ kind: "closed" });
  const [values, setValues] = useState<FormValues>(emptyValues(defaultDate));
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const idPrefix = useId();
  const { confirm, confirmDialog } = useConfirm();

  useEffect(() => {
    let cancelled = false;
    api
      .get<Meal[]>(`/trips/${tripId}/meals`)
      .then((meals) => {
        if (!cancelled) setLoad({ status: "ready", meals });
      })
      .catch((error: unknown) => {
        if (!cancelled)
          setLoad({
            status: "error",
            message: error instanceof ApiError ? error.message : "Nie udało się wczytać posiłków.",
          });
      });
    return () => {
      cancelled = true;
    };
  }, [tripId, reloadKey]);

  function set<K extends keyof FormValues>(field: K, value: FormValues[K]) {
    setValues((v) => ({ ...v, [field]: value }));
  }

  function openForm(next: FormMode) {
    setMode(next);
    setValues(next.kind === "edit" ? toValues(next.meal) : emptyValues(defaultDate));
    setFieldErrors({});
    setFormError(null);
  }

  // Wspólne atrybuty pola: id, opis błędu dla czytników ekranu, data-testid
  function fieldProps(field: FieldName, testId: string) {
    const error = fieldErrors[field];
    return {
      id: `${idPrefix}-${field}`,
      "aria-invalid": error ? true : undefined,
      "aria-describedby": error ? `${idPrefix}-${field}-error` : undefined,
      "data-testid": testId,
    };
  }

  function fieldError(field: FieldName) {
    const error = fieldErrors[field];
    if (!error) return null;
    return (
      <p
        id={`${idPrefix}-${field}-error`}
        className={styles.fieldError}
        data-testid={`error-meal-${field.replaceAll("_", "-")}`}
      >
        {error}
      </p>
    );
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const errors = validate(values);
    setFieldErrors(errors);
    setFormError(null);
    if (Object.keys(errors).length > 0) {
      setFormError("Popraw zaznaczone pola.");
      return;
    }

    setSaving(true);
    try {
      if (mode.kind === "edit") await api.put<Meal>(`/trips/${tripId}/meals/${mode.meal.id}`, toInput(values));
      else await api.post<Meal>(`/trips/${tripId}/meals`, toInput(values));
      // Lista od nowa z backendu – zachowuje jego sortowanie (po dacie)
      const meals = await api.get<Meal[]>(`/trips/${tripId}/meals`);
      setLoad({ status: "ready", meals });
      setMode({ kind: "closed" });
    } catch (error) {
      if (error instanceof ApiError && error.errors.length > 0) {
        const serverErrors: FieldErrors = {};
        for (const e of error.errors) serverErrors[e.field as FieldName] = "Nieprawidłowa wartość.";
        setFieldErrors(serverErrors);
      }
      setFormError(error instanceof ApiError ? error.message : "Nie udało się zapisać posiłku.");
    } finally {
      setSaving(false);
    }
  }

  async function deleteMeal(meal: Meal) {
    const confirmed = await confirm({
      title: "Usunąć posiłek?",
      message: `„${meal.dish}” (${meal.restaurant_name}, ${formatDate(meal.meal_date)}) zniknie z listy i z kosztorysu.`,
      confirmLabel: "Usuń posiłek",
    });
    if (!confirmed) return;
    setDeletingId(meal.id);
    setDeleteError(null);
    try {
      await api.delete(`/trips/${tripId}/meals/${meal.id}`);
      setLoad((l) => (l.status === "ready" ? { ...l, meals: l.meals.filter((m) => m.id !== meal.id) } : l));
      if (mode.kind === "edit" && mode.meal.id === meal.id) setMode({ kind: "closed" });
    } catch (error) {
      setDeleteError(error instanceof ApiError ? error.message : "Nie udało się usunąć posiłku.");
    } finally {
      setDeletingId(null);
    }
  }

  if (load.status === "loading") {
    return (
      <p className={styles.muted} role="status" data-testid="meals-loading">
        Wczytywanie posiłków…
      </p>
    );
  }

  if (load.status === "error") {
    return (
      <div className={styles.error} role="alert" data-testid="meals-error">
        <p>{load.message}</p>
        <button
          type="button"
          className={styles.secondary}
          onClick={() => {
            setLoad({ status: "loading" });
            setReloadKey((k) => k + 1);
          }}
          data-testid="meals-retry"
        >
          Spróbuj ponownie
        </button>
      </div>
    );
  }

  const meals = load.meals;
  const total = meals.reduce((sum, m) => sum + m.cost, 0);

  return (
    <section className={styles.section} aria-labelledby={`${idPrefix}-title`} data-testid="meals-section">
      <div className={styles.head}>
        <h2 id={`${idPrefix}-title`} className={styles.title}>
          Posiłki
        </h2>
        {!readOnly && mode.kind === "closed" && (
          <button
            type="button"
            className={styles.primary}
            onClick={() => openForm({ kind: "add" })}
            data-testid="btn-add-meal"
          >
            Dodaj posiłek
          </button>
        )}
      </div>

      {!readOnly && mode.kind !== "closed" && (
        <form className={styles.form} onSubmit={onSubmit} noValidate data-testid="meal-form">
          <h3 className={styles.formTitle}>{mode.kind === "edit" ? "Edytuj posiłek" : "Nowy posiłek"}</h3>
          {formError && (
            <p className={styles.error} role="alert" data-testid="meal-form-error">
              {formError}
            </p>
          )}
          <div className={styles.grid}>
            <div className={styles.fieldGroup}>
              <label htmlFor={`${idPrefix}-dish`} className={styles.label}>
                Danie
              </label>
              <input
                {...fieldProps("dish", "input-meal-dish")}
                className={styles.field}
                value={values.dish}
                onChange={(e) => set("dish", e.target.value)}
              />
              {fieldError("dish")}
            </div>
            <div className={styles.fieldGroup}>
              <label htmlFor={`${idPrefix}-restaurant_name`} className={styles.label}>
                Restauracja
              </label>
              <input
                {...fieldProps("restaurant_name", "input-meal-restaurant")}
                className={styles.field}
                value={values.restaurant_name}
                onChange={(e) => set("restaurant_name", e.target.value)}
              />
              {fieldError("restaurant_name")}
            </div>
            <div className={styles.fieldGroup}>
              <label htmlFor={`${idPrefix}-meal_date`} className={styles.label}>
                Data
              </label>
              <input
                {...fieldProps("meal_date", "input-meal-date")}
                type="date"
                className={styles.field}
                value={values.meal_date}
                onChange={(e) => set("meal_date", e.target.value)}
              />
              {fieldError("meal_date")}
            </div>
            <div className={styles.fieldGroup}>
              <label htmlFor={`${idPrefix}-cost`} className={styles.label}>
                Koszt (PLN)
              </label>
              <input
                {...fieldProps("cost", "input-meal-cost")}
                inputMode="decimal"
                className={styles.field}
                value={values.cost}
                onChange={(e) => set("cost", e.target.value)}
              />
              {fieldError("cost")}
            </div>
            <div className={styles.fieldGroup}>
              <label htmlFor={`${idPrefix}-rating`} className={styles.label}>
                Ocena restauracji
              </label>
              <select
                id={`${idPrefix}-rating`}
                className={styles.field}
                value={values.rating}
                onChange={(e) => set("rating", e.target.value)}
                data-testid="select-meal-rating"
              >
                <option value="">bez oceny</option>
                {[5, 4, 3, 2, 1].map((n) => (
                  <option key={n} value={n}>
                    {n} / 5
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className={styles.actions}>
            <button
              type="button"
              className={styles.secondary}
              onClick={() => setMode({ kind: "closed" })}
              data-testid="btn-cancel-meal"
            >
              Anuluj
            </button>
            <button type="submit" className={styles.primary} disabled={saving} data-testid="btn-save-meal">
              {saving ? "Zapisywanie…" : mode.kind === "edit" ? "Zapisz zmiany" : "Dodaj"}
            </button>
          </div>
        </form>
      )}

      {deleteError && (
        <p className={styles.error} role="alert" data-testid="meal-delete-error">
          {deleteError}
        </p>
      )}

      {meals.length === 0 ? (
        <p className={styles.muted} data-testid="meals-empty">
          Nie dodano jeszcze żadnego posiłku.
        </p>
      ) : (
        <>
          <ul className={styles.list} data-testid="meal-list">
            {meals.map((meal) => (
              <li key={meal.id} className={styles.item} data-testid={`meal-${meal.id}`}>
                <div className={styles.itemText}>
                  <p className={styles.itemTitle}>{meal.dish}</p>
                  <p className={styles.itemMeta}>
                    {meal.restaurant_name}
                    <span aria-hidden="true"> · </span>
                    <span className="visually-hidden">, </span>
                    {formatDate(meal.meal_date)}
                  </p>
                  <Rating value={meal.rating} />
                </div>
                <p className={styles.cost}>{formatPln(meal.cost)}</p>
                {!readOnly && (
                  <div className={styles.itemActions}>
                    <button
                      type="button"
                      className={styles.small}
                      onClick={() => openForm({ kind: "edit", meal })}
                      aria-label={`Edytuj posiłek „${meal.dish}”`}
                      data-testid={`btn-edit-meal-${meal.id}`}
                    >
                      Edytuj
                    </button>
                    <button
                      type="button"
                      className={styles.danger}
                      onClick={() => deleteMeal(meal)}
                      disabled={deletingId === meal.id}
                      aria-label={`Usuń posiłek „${meal.dish}”`}
                      data-testid={`btn-delete-meal-${meal.id}`}
                    >
                      Usuń
                    </button>
                  </div>
                )}
              </li>
            ))}
          </ul>
          <p className={styles.total}>
            Razem: <strong data-testid="meals-total">{formatPln(total)}</strong>
          </p>
        </>
      )}
      {confirmDialog}
    </section>
  );
}
