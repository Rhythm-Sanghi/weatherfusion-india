import { NavLink, Outlet } from "react-router-dom";

const navigation = [
  ["Situation", "/"],
  ["Map", "/map"],
  ["Events", "/events"],
  ["Live Feed", "/live-feed"],
  ["Review Queue", "/review"],
  ["Analytics", "/analytics"],
  ["Sources", "/sources"],
  ["System", "/system"],
  ["Architecture", "/architecture"],
] as const;

export function AppShell() {
  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">SIH 26069</p>
          <h1>WeatherFusion India</h1>
        </div>
        <p className="environment-label">Prototype operations console</p>
      </header>
      <div className="workspace">
        <nav aria-label="Primary navigation" className="sidebar">
          {navigation.map(([label, path]) => (
            <NavLink
              className={({ isActive }) => `nav-item${isActive ? " nav-item-active" : ""}`}
              end={path === "/"}
              key={path}
              to={path}
            >
              {label}
            </NavLink>
          ))}
        </nav>
        <main className="content"><Outlet /></main>
      </div>
    </div>
  );
}
