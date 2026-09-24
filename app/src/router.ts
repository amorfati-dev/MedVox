// Winziger Pfad-Router: sechs Ansichten, kein Router-Paket.
export type Route = "diktat" | "patienten" | "behandler" | "woerterbuch" | "rezeption" | "check";

export function routeFromPath(pathname: string): Route {
  if (pathname === "/transfer") return "rezeption";
  if (pathname === "/patienten") return "patienten";
  if (pathname === "/behandler") return "behandler";
  if (pathname === "/woerterbuch") return "woerterbuch";
  if (pathname === "/check") return "check";
  return "diktat";
}
