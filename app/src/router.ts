// Winziger Pfad-Router: vier Ansichten, kein Router-Paket.
export type Route = "diktat" | "patienten" | "rezeption" | "check";

export function routeFromPath(pathname: string): Route {
  if (pathname === "/transfer") return "rezeption";
  if (pathname === "/patienten") return "patienten";
  if (pathname === "/check") return "check";
  return "diktat";
}
