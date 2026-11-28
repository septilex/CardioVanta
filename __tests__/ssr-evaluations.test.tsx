/**
 * #52 Server-side rendering: /research/evaluations is rendered per request from the live research API,
 * never at build time, and reports honestly when it cannot load data.
 */
import { render, screen, within } from "@testing-library/react";
import Page, { dynamic } from "../src/app/research/evaluations/page";
import { loadEvaluationsOnServer } from "../src/lib/serverResearch";

jest.mock("next/navigation", () => ({ ...jest.requireActual("next/navigation"), usePathname: () => "/research/evaluations" }));

const DATA = {
  evaluations: [{ version: "1.1.0", cohort: "cleveland_dev", cohort_name: "Cleveland development rows", n_patients: 242,
                  method: "nested_cv", metric: "roc_auc", value: 0.911, source: "reports/h2_1.md", evaluated_on: "2026-11-15" }],
  version_coverage: [{ version: "1.1.1", serialization: "portable_json", calibration: "sigmoid", evaluation_count: 0, cohorts: [] }],
  unevaluated_cohorts: [{ code: "hungary", name: "Hungarian Institute of Cardiology", country: "Hungary", n_patients: 294, role: "external" }],
};
const fetchMock = jest.fn();
const ORIGIN = process.env.RESEARCH_API_ORIGIN;

beforeEach(() => { fetchMock.mockReset(); global.fetch = fetchMock as unknown as typeof fetch; process.env.RESEARCH_API_ORIGIN = "http://backend:8000"; });
afterAll(() => { process.env.RESEARCH_API_ORIGIN = ORIGIN; });
const ok = (body: unknown, status = 200) => ({ ok: status < 400, status, json: async () => body });

test("the route is rendered dynamically, on every request", () => {
  expect(dynamic).toBe("force-dynamic");
});

test("the server reads the live API with no-store and renders the table into the HTML", async () => {
  fetchMock.mockResolvedValue(ok(DATA));
  render(await Page());
  expect(fetchMock).toHaveBeenCalledWith("http://backend:8000/api/v1/research/evaluations", expect.objectContaining({ cache: "no-store" }));
  const table = screen.getByRole("table");
  expect(within(table).getByText("ROC-AUC")).toBeInTheDocument();
  expect(within(table).getByText("0.911")).toBeInTheDocument();
  expect(screen.getByText(/Hungarian Institute of Cardiology \(294 patients\)/)).toBeInTheDocument();
  expect(screen.getByText(/Rendered on the server for this request at/)).toBeInTheDocument();
});

test("each request renders again with fresh data and a new timestamp", async () => {
  fetchMock.mockResolvedValue(ok(DATA));
  const first = render(await Page());
  const firstTime = first.container.querySelector("time")?.getAttribute("dateTime");
  first.unmount();
  await new Promise((r) => setTimeout(r, 5));
  render(await Page());
  expect(fetchMock).toHaveBeenCalledTimes(2);
  expect(document.querySelector("time")?.getAttribute("dateTime")).not.toBe(firstTime);
});

test.each([
  ["not configured", undefined, null, /not configured in this environment/],
  ["unsafe origin", "http://backend:8000/elsewhere?x=", null, /not configured in this environment/],
  ["database down", "http://backend:8000", ok({ detail: "down", code: "research_database_unavailable" }, 503), /temporarily unavailable/],
  ["malformed body", "http://backend:8000", ok({ unexpected: true }), /could not be loaded right now/],
])("%s: says so instead of rendering numbers", async (_name, origin, response, message) => {
  if (origin === undefined) delete process.env.RESEARCH_API_ORIGIN; else process.env.RESEARCH_API_ORIGIN = origin;
  if (response) fetchMock.mockResolvedValue(response);
  render(await Page());
  expect(screen.queryByRole("table")).toBeNull();
  expect(screen.getByRole("status")).toHaveTextContent(message);
  if (!response) expect(fetchMock).not.toHaveBeenCalled();
});

test("network failure and timeout are reported without details", async () => {
  fetchMock.mockRejectedValue(new Error("connect ECONNREFUSED 10.0.0.5:8000"));
  const result = await loadEvaluationsOnServer();
  expect(result).toEqual({ kind: "unavailable", message: "Research data could not be loaded right now." });
});
