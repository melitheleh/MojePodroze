import { useId, useState } from "react";
import { mockRates } from "../../data/mockDashboard";
import { formatPln, formatRate } from "../../utils/format";
import Widget from "../../components/Widget/Widget";
import styles from "./TripsPage.module.css";

// TODO: GET /api/exchange-rates; przeliczenie: GET /api/exchange-rates/convert
export default function RatesWidget() {
  const [amount, setAmount] = useState("100");
  const id = useId();
  const eur = mockRates.find((r) => r.code === "EUR");
  const value = Number.parseFloat(amount.replace(",", "."));
  const result = eur && Number.isFinite(value) ? formatPln(value * eur.mid) : "–";

  return (
    <Widget title="Kursy NBP" accent="--widget-rates" testId="widget-nbp">
      <ul className={styles.rates}>
        {mockRates.map((rate) => (
          <li key={rate.code}>
            <abbr title={rate.currency}>{rate.code}</abbr> {formatRate(rate.mid)}
          </li>
        ))}
      </ul>
      <label htmlFor={id} className={styles.label}>
        Kwota w EUR
      </label>
      <div className={styles.converter}>
        <input
          id={id}
          type="text"
          inputMode="decimal"
          className={styles.field}
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          data-testid="input-eur-amount"
        />
        <output htmlFor={id} className={styles.result} aria-live="polite" data-testid="eur-result">
          = {result}
        </output>
      </div>
    </Widget>
  );
}
