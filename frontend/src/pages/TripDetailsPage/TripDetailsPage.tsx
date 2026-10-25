import { Link, useParams } from "react-router";

// Szkielet – ekran szczegółów podróży powstanie w kolejnym kroku.
export default function TripDetailsPage() {
  const { tripId } = useParams();
  return (
    <>
      <p>
        <Link to="/podroze">← Moje podróże</Link>
      </p>
      <h1>Podróż nr {tripId}</h1>
    </>
  );
}
