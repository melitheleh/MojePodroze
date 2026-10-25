import { Navigate, Route, Routes } from "react-router";
import Layout from "./components/Layout/Layout";
import TripsPage from "./pages/TripsPage/TripsPage";
import TripDetailsPage from "./pages/TripDetailsPage/TripDetailsPage";
import StatsPage from "./pages/StatsPage/StatsPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/podroze" replace />} />
        <Route path="podroze" element={<TripsPage />} />
        <Route path="podroze/:tripId" element={<TripDetailsPage />} />
        <Route path="statystyki" element={<StatsPage />} />
      </Route>
    </Routes>
  );
}
