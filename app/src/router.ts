// Winziger Pfad-Router: fünf Ansichten, kein Router-Paket.
export type Route = "diktat" | "patienten" | "behandler" | "rezeption" | "check";

export function routeFromPath(pathname: string): Route {
  if (pathname === "/transfer") return "rezeption";
  if (pathname === "/patienten") return "patienten";
  if (pathname === "/behandler") return "behandler";
  if (pathname === "/check") return "check";
  return "diktat";
}
