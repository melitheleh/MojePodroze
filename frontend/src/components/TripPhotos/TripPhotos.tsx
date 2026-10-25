import { useEffect, useState } from "react";
import type { Photo } from "../../types/api";
import { api, ApiError } from "../../api/client";
import styles from "./TripPhotos.module.css";

/** Jedno zdjęcie: plik wymaga nagłówka X-User-Id, więc fetch → blob → URL.createObjectURL */
function PhotoImage({ photo, alt }: { photo: Photo; alt: string }) {
  const [src, setSrc] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let objectUrl: string | null = null;
    api
      .getBlob(photo.file_url)
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setSrc(objectUrl);
      })
      .catch(() => {
        // zostaje szare pole – błąd jednego zdjęcia nie psuje reszty
      });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [photo.file_url]);

  return src ? <img src={src} alt={alt} className={styles.image} /> : <div className={styles.image} aria-hidden="true" />;
}

interface Props {
  tripId: number;
  /** Zmiana wartości wczytuje zdjęcia ponownie (np. po wgraniu nowych) */
  refreshKey?: number;
  /** Pokaż przyciski usuwania (edycja podróży) */
  editable?: boolean;
  /** Wywoływane po usunięciu zdjęcia (np. odświeżenie okładki) */
  onChange?: () => void;
}

type LoadState =
  | { status: "loading" }
  | { status: "ready"; photos: Photo[] }
  | { status: "error"; message: string };

// Siatka wszystkich zdjęć podróży: GET /api/trips/{id}/photos, usuwanie: DELETE …/photos/{photoId}.
export default function TripPhotos({ tripId, refreshKey = 0, editable = false, onChange }: Props) {
  const [load, setLoad] = useState<LoadState>({ status: "loading" });
  const [deleteError, setDeleteError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .get<Photo[]>(`/trips/${tripId}/photos`)
      .then((photos) => {
        if (!cancelled) setLoad({ status: "ready", photos });
      })
      .catch((error: unknown) => {
        if (!cancelled)
          setLoad({ status: "error", message: error instanceof ApiError ? error.message : "Nie udało się wczytać zdjęć." });
      });
    return () => {
      cancelled = true;
    };
  }, [tripId, refreshKey]);

  async function remove(photo: Photo, label: string) {
    if (!window.confirm(`Usunąć ${label}? Tego nie da się cofnąć.`)) return;
    setDeleteError(null);
    try {
      await api.delete(`/trips/${tripId}/photos/${photo.id}`);
      setLoad((current) =>
        current.status === "ready" ? { status: "ready", photos: current.photos.filter((p) => p.id !== photo.id) } : current,
      );
      onChange?.();
    } catch (error) {
      setDeleteError(error instanceof ApiError ? error.message : "Nie udało się usunąć zdjęcia.");
    }
  }

  if (load.status === "loading") {
    return (
      <p className={styles.muted} role="status" data-testid="trip-photos-loading">
        Wczytywanie zdjęć…
      </p>
    );
  }
  if (load.status === "error") {
    return (
      <p className={styles.error} role="alert" data-testid="trip-photos-error">
        {load.message}
      </p>
    );
  }
  if (load.photos.length === 0) {
    return (
      <p className={styles.muted} data-testid="trip-photos-empty">
        Ta podróż nie ma jeszcze zdjęć.
      </p>
    );
  }

  return (
    <>
      {deleteError && (
        <p className={styles.error} role="alert" data-testid="photo-delete-error">
          {deleteError}
        </p>
      )}
      <ul className={styles.grid} aria-label="Zdjęcia podróży" data-testid="trip-photo-list">
        {load.photos.map((photo, index) => {
          const label = photo.caption ?? `zdjęcie ${index + 1}`;
          return (
            <li key={photo.id} className={styles.item} data-testid={`photo-${photo.id}`}>
              <PhotoImage photo={photo} alt={photo.caption ?? `Zdjęcie ${index + 1} z podróży`} />
              {index === 0 && <span className={styles.badge}>Okładka</span>}
              {editable && (
                <button
                  type="button"
                  className={styles.remove}
                  onClick={() => remove(photo, label)}
                  aria-label={`Usuń ${label}`}
                  data-testid={`btn-delete-photo-${photo.id}`}
                >
                  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.4" aria-hidden="true">
                    <path d="M6 6l12 12M18 6L6 18" strokeLinecap="round" />
                  </svg>
                </button>
              )}
            </li>
          );
        })}
      </ul>
    </>
  );
}
