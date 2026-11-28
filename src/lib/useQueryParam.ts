import { useSyncExternalStore } from "react";

const never = () => () => {};

/**
 * Read one query-string parameter in a statically prerendered page. The server snapshot is null (no request URL at
 * build time); during hydration React uses that snapshot and then re-renders with the browser's value, so the HTML
 * never mismatches and no effect has to copy the URL into state. The page does not change its own query string, so
 * there is nothing to subscribe to.
 */
export function useQueryParam(name: string): string | null {
  return useSyncExternalStore(
    never,
    () => new URLSearchParams(window.location.search).get(name),
    () => null,
  );
}
