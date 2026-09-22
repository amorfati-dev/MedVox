// Winziger Pfad-Router: drei Ansichten, kein Router-Paket.
import { useEffect, useState } from "react";

export type Route = "diktat" | "rezeption" | "check";

export function routeFromPath(pathname: string): Route {
  const p = pathname.replace(/\/+$/, "");
  if (p === "/transfer") return "rezeption";
  if (p === "/check") return "check";
  return "diktat";
}

export function navigate(path: string): void {
  window.history.pushState(null, "", path);
  window.dispatchEvent(new PopStateEvent("popstate"));
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
