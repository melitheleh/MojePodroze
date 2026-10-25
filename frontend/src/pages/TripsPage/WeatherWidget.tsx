import { useId, useState } from "react";
import Widget from "../../components/Widget/Widget";
import styles from "./TripsPage.module.css";

// TODO: GET /api/weather/current, wyszukiwanie miasta: GET /api/weather/cities, zapis: PUT /api/users/me/weather-city
export default function WeatherWidget() {
  const [city, setCity] = useState("Warszawa");
  const id = useId();

  return (
    <Widget title="Pogoda" accent="--widget-weather" testId="widget-weather">
      <label htmlFor={id} className={styles.label}>
        Miasto
      </label>
      <input
        id={id}
        type="text"
        className={styles.field}
        value={city}
        onChange={(e) => setCity(e.target.value)}
        data-testid="input-weather-city"
      />
      <p className={styles.weather} data-testid="weather-current">
        <span className={styles.temperature}>12°C</span> <span className={styles.muted}>pochmurno</span>
      </p>
    </Widget>
  );
}
