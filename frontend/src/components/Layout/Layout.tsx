import { Link, NavLink, Outlet } from "react-router";
import styles from "./Layout.module.css";

function navClass({ isActive }: { isActive: boolean }) {
  return isActive ? `${styles.navLink} ${styles.active}` : styles.navLink;
}

export default function Layout() {
  return (
    <>
      <header className={styles.header}>
        <div className={styles.inner}>
          <Link to="/podroze" className={styles.logo}>
            Moje podróże
          </Link>
          <nav aria-label="Główna nawigacja" className={styles.nav}>
            <NavLink to="/podroze" className={navClass} data-testid="nav-trips">
              Moje podróże
            </NavLink>
            <NavLink to="/statystyki" className={navClass} data-testid="nav-stats">
              Statystyki
            </NavLink>
          </nav>
          <button type="button" className={styles.logout} data-testid="btn-logout">
            Wyloguj
          </button>
        </div>
      </header>
      <main className={styles.main}>
        <Outlet />
      </main>
    </>
  );
}
