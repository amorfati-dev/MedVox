// Winziger Pfad-Router: drei Ansichten, kein Router-Paket.
import { useEffect, useState } from "react";

export type Route = "diktat" | "rezeption" | "check";

export function routeFromPath(pathname: string): Route {
  if (pathname === "/transfer") return "rezeption";
  if (pathname === "/check") return "check";
  return "diktat";
}

export function useRoute(): Route {
  const [route, setRoute] = useState<Route>(() => routeFromPath(window.location.pathname));
  useEffect(() => {
    const update = () => setRoute(routeFromPath(window.location.pathname));
    window.addEventListener("popstate", update);
    return () => window.removeEventListener("popstate", update);
  }, []);
  return route;
}
