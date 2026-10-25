import { Link } from "react-router";
import type { Trip } from "../../types/api";
import { capitalize, formatDate } from "../../utils/format";
import StatusLabel from "../StatusLabel/StatusLabel";
import styles from "./TripCard.module.css";

const PLACEHOLDERS = 5;

export default function TripCard({ trip }: { trip: Trip }) {
  const placeholder = `var(--placeholder-${(trip.id % PLACEHOLDERS) + 1})`;

  return (
    <Link to={`/podroze/${trip.id}`} className={styles.card} data-testid="trip-card">
      <div className={styles.body}>
        <StatusLabel status={trip.status} label={trip.status_label} />
        <h2 className={styles.title}>{trip.name}</h2>
        <p className={styles.meta}>
          {formatDate(trip.start_date)} – {formatDate(trip.end_date)}
          <span aria-hidden="true"> · </span>
          <span className="visually-hidden">, </span>
          {capitalize(trip.trip_type_label)}
          <span aria-hidden="true"> · </span>
          <span className="visually-hidden">, </span>
          {trip.character.name}
        </p>
      </div>
      {/* Miejsce na zdjęcie okładkowe – na razie kolor zastępczy (dekoracja, bez opisu) */}
      <div className={styles.cover} style={{ background: placeholder }} aria-hidden="true" />
    </Link>
  );
}
