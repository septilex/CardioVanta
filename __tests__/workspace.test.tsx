import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { Workspace } from "../src/components/research/Workspace";
import { Support } from "../src/components/research/Support";
import * as api from "../src/lib/workspace";

jest.mock("../src/lib/workspace", () => ({
  workspaceBase: "", workspaceRequest: jest.fn(), refreshAccount: jest.fn(), setAccess: jest.fn(),
  afterStatusUpdate: () => Promise.resolve(),
}));
jest.mock("../src/components/research/ImportLive", () => ({ ImportLive: ({ batch }: { batch: api.ImportState }) => <p role="status">{batch.status}: {batch.row_count} rows</p> }));
const request = api.workspaceRequest as jest.Mock;
const refresh = api.refreshAccount as jest.Mock;
const researcher = { id: "synthetic", email: "researcher@example.test", roles: ["researcher"] };

beforeEach(() => { jest.clearAllMocks(); refresh.mockResolvedValue(null); });

test("disabled accounts preserve public assessment access", async () => {
  request.mockResolvedValue({ enabled: false, google: false });
  render(<Workspace />);
  expect(await screen.findByText(/has not been enabled/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Heart Analysis" })).toHaveAttribute("href", "/assessment");
  expect(screen.queryByRole("button", { name: "Sign in" })).not.toBeInTheDocument();
});

test("controlled sign-in submits credentials and displays a safe error", async () => {
  request.mockResolvedValueOnce({ enabled: true, google: true }).mockRejectedValueOnce(new Error("Email or password is incorrect."));
  render(<Workspace />);
  const email = await screen.findByLabelText("Email");
  fireEvent.change(email, { target: { value: "viewer@example.test" } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: "wrong-password" } });
  fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Email or password is incorrect.");
  expect(request).toHaveBeenLastCalledWith("/auth/login", expect.objectContaining({ method: "POST", body: JSON.stringify({ email: "viewer@example.test", password: "wrong-password" }) }));
  expect(screen.getByRole("link", { name: "Continue with Google" })).toHaveAttribute("href", "/api/v1/auth/google");
});

test("registration declares password validation and viewer access", async () => {
  request.mockResolvedValue({ enabled: true, google: false });
  render(<Workspace />);
  fireEvent.click(await screen.findByRole("button", { name: "Create a viewer account" }));
  expect(screen.getByLabelText("Password")).toHaveAttribute("minLength", "12");
  expect(screen.getByText(/New accounts have viewer access/)).toBeInTheDocument();
});

test("viewer has no upload controls", async () => {
  request.mockResolvedValue({ enabled: true, google: false });
  refresh.mockResolvedValue({ ...researcher, roles: ["viewer"] });
  render(<Workspace />);
  expect(await screen.findByText(/Your viewer account/)).toBeInTheDocument();
  expect(screen.queryByLabelText("Research CSV")).not.toBeInTheDocument();
});

test("research CSV workflow creates a batch and submits multipart data", async () => {
  refresh.mockResolvedValue(researcher);
  request.mockImplementation((path: string) => {
    if (path === "/auth/status") return Promise.resolve({ enabled: true, google: false });
    if (path === "/research/imports") return Promise.resolve({ id: "batch", status: "ready", row_count: 0 });
    if (path.endsWith("/file")) return Promise.resolve({ id: "batch", status: "completed", row_count: 2 });
    throw new Error(`Unexpected ${path}`);
  });
  render(<Workspace />);
  const input = await screen.findByLabelText("Research CSV");
  fireEvent.change(input, { target: { files: [new File(["synthetic metadata"], "metrics.csv", { type: "text/csv" })] } });
  fireEvent.submit(input.closest("form")!);
  expect(await screen.findByText("completed: 2 rows")).toBeInTheDocument();
  expect(request).toHaveBeenCalledWith("/research/imports/batch/file", expect.objectContaining({ method: "POST", body: expect.any(FormData) }));
});

test("oversized uploads are rejected before a batch is created", async () => {
  refresh.mockResolvedValue(researcher); request.mockResolvedValue({ enabled: true, google: false });
  render(<Workspace />);
  const input = await screen.findByLabelText("Research CSV");
  fireEvent.change(input, { target: { files: [new File(["x".repeat(262145)], "metrics.csv", { type: "text/csv" })] } });
  fireEvent.submit(input.closest("form")!);
  expect(await screen.findByRole("alert")).toHaveTextContent("no larger than 256 KiB");
  expect(request).not.toHaveBeenCalledWith("/research/imports", expect.anything());
});

test("support displays disabled configuration honestly", async () => {
  request.mockResolvedValue({ enabled: false });
  render(<Support />);
  expect(await screen.findByText(/Test checkout has not been enabled/)).toBeInTheDocument();
});

test("support checkout failure keeps a retryable UI", async () => {
  request.mockResolvedValueOnce({ enabled: true }).mockRejectedValueOnce(new Error("Test checkout is temporarily unavailable."));
  Object.defineProperty(global.crypto, "randomUUID", { configurable: true, value: () => "synthetic-idempotency-key" });
  render(<Support />);
  fireEvent.click(await screen.findByRole("button", { name: "Open test checkout" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("temporarily unavailable");
  await waitFor(() => expect(screen.getByRole("button", { name: "Open test checkout" })).toBeEnabled());
});
