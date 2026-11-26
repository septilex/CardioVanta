import { render, screen } from "@testing-library/react";
import PlatformStatusPage from "../src/app/platform-status/page";
import { getPlatformHealth } from "../src/lib/platformStatus";

describe("platform status", () => {
  const priorBackend = process.env.CARDIOVANTA_BACKEND_URL;
  const priorVercel = process.env.VERCEL_URL;

  beforeEach(() => {
    process.env.CARDIOVANTA_BACKEND_URL = "http://backend:8000";
    delete process.env.VERCEL_URL;
  });

  afterAll(() => {
    if (priorBackend === undefined) delete process.env.CARDIOVANTA_BACKEND_URL;
    else process.env.CARDIOVANTA_BACKEND_URL = priorBackend;
    if (priorVercel === undefined) delete process.env.VERCEL_URL;
    else process.env.VERCEL_URL = priorVercel;
  });

  test("reports a healthy backend and model service", async () => {
    const fetcher = jest.fn().mockResolvedValue({ ok: true, json: async () => ({ status: "ok", service: "CardioVanta" }) });
    await expect(getPlatformHealth(fetcher as unknown as typeof fetch)).resolves.toEqual({ backendAvailable: true, modelServiceAvailable: true });
    expect(fetcher).toHaveBeenCalledWith("http://backend:8000/api/v1/health", expect.objectContaining({ cache: "no-store" }));
  });

  test("reports a reached backend with an unavailable model", async () => {
    const fetcher = jest.fn().mockResolvedValue({ ok: false, status: 503 });
    await expect(getPlatformHealth(fetcher as unknown as typeof fetch)).resolves.toEqual({ backendAvailable: true, modelServiceAvailable: false });
  });

  test("fails safely when the health request times out", async () => {
    jest.useFakeTimers();
    const fetcher = jest.fn((_url: RequestInfo | URL, init?: RequestInit) => new Promise<Response>((_resolve, reject) => {
      init?.signal?.addEventListener("abort", () => reject(new Error("aborted")), { once: true });
    }));
    const result = getPlatformHealth(fetcher as unknown as typeof fetch);
    await jest.advanceTimersByTimeAsync(2_500);
    await expect(result).resolves.toEqual({ backendAvailable: false, modelServiceAvailable: false });
    jest.useRealTimers();
  });

  test("fails safely when the backend cannot be reached", async () => {
    const fetcher = jest.fn().mockRejectedValue(new Error("internal address withheld"));
    await expect(getPlatformHealth(fetcher as unknown as typeof fetch)).resolves.toEqual({ backendAvailable: false, modelServiceAvailable: false });
  });

  test("server renders current status and a checked timestamp", async () => {
    Object.defineProperty(globalThis, "fetch", {
      configurable: true,
      value: jest.fn().mockResolvedValue({ ok: true, json: async () => ({ status: "ok", service: "CardioVanta" }) }),
    });
    const view = await PlatformStatusPage();
    render(view);
    expect(screen.getByRole("heading", { name: "Platform status" })).toBeVisible();
    expect(screen.getByText("Backend API")).toBeVisible();
    expect(screen.getAllByText("Available")).toHaveLength(2);
    expect(screen.getByText(/Last checked/).querySelector("time")).toHaveAttribute("datetime");
  });
});
