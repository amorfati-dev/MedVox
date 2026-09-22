// Winziger Pfad-Router: drei Ansichten, kein Router-Paket.
export type Route = "diktat" | "rezeption" | "check";

export function routeFromPath(pathname: string): Route {
  if (pathname === "/transfer") return "rezeption";
  if (pathname === "/check") return "check";
  return "diktat";
}
