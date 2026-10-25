import { useEffect, useState } from "react";
import type { Photo } from "../../types/api";
import { api } from "../../api/client";
import styles from "./TripCard.module.css";

const PLACEHOLDERS = 5;

// Okładka karty: pierwsze zdjęcie podróży (GET /api/trips/{id}/photos → plik przez fetch → blob).
// Bez zdjęć albo przy błędzie zostaje kolor zastępczy. Dekoracja – opis podróży jest w tekście karty.
export default function TripCover({ tripId }: { tripId: number }) {
  const [src, setSrc] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let objectUrl: string | null = null;
    api
      .get<Photo[]>(`/trips/${tripId}/photos`)
      .then((photos) => (photos.length > 0 ? api.getBlob(photos[0].file_url) : null))
      .then((blob) => {
        if (!blob || cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setSrc(objectUrl);
      })
      .catch(() => {
        // brak zdjęcia nie jest błędem dla użytkownika – zostaje kolor
      });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [tripId]);

  const placeholder = `var(--placeholder-${(tripId % PLACEHOLDERS) + 1})`;
  return (
    <div className={styles.cover} style={{ background: placeholder }} aria-hidden="true">
      {src && <img src={src} alt="" className={styles.coverImage} data-testid="trip-cover-photo" />}
    </div>
  );
}
