import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";
import "@testing-library/jest-dom/vitest";
import { App } from "./App";

const emptyList = { items: [], total: 0, limit: 20, offset: 0 };

const evaluation = {
  case_count: 1,
  convention: "Predictions are executable command paths.",
  grounded: { true_positives: 1, predicted: 1, gold: 1, precision: 1, recall: 1, f1: 1 },
  thin: { true_positives: 1, predicted: 2, gold: 4, precision: 0.5, recall: 0.071429, f1: 0.125 },
  cases: [
    {
      name: "lane-desk",
      gold: ["notes create_note"],
      grounded: {
        predicted: ["notes create_note"],
        false_positives: [],
        false_negatives: [],
        true_positives: 1,
        predicted_count: 1,
        gold: 1,
        precision: 1,
        recall: 1,
        f1: 1,
      },
      thin: {
        predicted: [],
        false_positives: ["app status"],
        false_negatives: ["notes create_note"],
        true_positives: 0,
        precision: 0,
        recall: 0,
        f1: 0,
      },
    },
  ],
  failure_cases: ["Executable means the argv binds to a declared surface. The target application is not launched."],
};

const created = {
  id: 3,
  application: "lane-desk",
  executable_name: "lane_desk",
  created_at: "2026-10-14T00:00:00Z",
  surface_count: 1,
  notices: [],
  grounded: {
    proposed: 1,
    executable: 1,
    surfaces_covered: 1,
    coverage: 1,
    correctness: 1,
    commands: [
      {
        path: "notes create_note",
        surface_id: "notes.create",
        group: "notes",
        verb: "create_note",
        handler: "createNote",
        kind: "ipc",
        summary: "Create a note",
        method: null,
        route: null,
        executable: true,
        reasons: [],
        argv: ["--title", "sample"],
        invocation: "lane_desk notes create_note --title sample",
        bound: { title: "sample" },
      },
    ],
  },
  thin: {
    proposed: 5,
    executable: 0,
    surfaces_covered: 0,
    coverage: 0,
    correctness: 0,
    commands: [],
  },
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function installFetch() {
  const calls: { url: string; init?: RequestInit }[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      calls.push({ url: String(url), init });
      const method = init?.method ?? "GET";
      if (method === "POST" && url === "/api/analyses") {
        return jsonResponse(created);
      }
      if (String(url).startsWith("/api/analyses")) {
        return jsonResponse(emptyList);
      }
      if (url === "/api/health") {
        return jsonResponse({ status: "ok", version: "1.0.0" });
      }
      if (url === "/api/evaluation") {
        return jsonResponse(evaluation);
      }
      return jsonResponse({ error: "not found", field: "" }, 404);
    }),
  );
  return calls;
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

test("shows an empty catalog and an empty history", async () => {
  installFetch();
  render(<App />);
  expect(await screen.findByText("No analyses yet.")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Prism Console" })).toBeInTheDocument();
  expect(screen.getByText("No catalog yet. Submit an inventory to score commands.")).toBeInTheDocument();
});

test("rejects inventory text that is not JSON", async () => {
  const calls = installFetch();
  const user = userEvent.setup();
  render(<App />);
  await screen.findByText("No analyses yet.");
  await user.type(screen.getByLabelText("Inventory JSON"), "not-json");
  await user.click(screen.getByRole("button", { name: "Build catalog" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Inventory JSON could not be parsed");
  expect(calls.some((call) => call.init?.method === "POST")).toBe(false);
});

test("renders the command and scores returned by the API", async () => {
  installFetch();
  const user = userEvent.setup();
  render(<App />);
  await screen.findByText("No analyses yet.");
  await user.click(screen.getByLabelText("Inventory JSON"));
  await user.paste('{"application":"lane-desk","surfaces":[]}');
  await user.click(screen.getByRole("button", { name: "Build catalog" }));
  expect(await screen.findByText("lane_desk notes create_note --title sample")).toBeInTheDocument();
  expect(screen.getByText("Grounded coverage").parentElement).toHaveTextContent("1.000");
  expect(screen.getByText("Thin recall", { selector: "span" }).parentElement).toHaveTextContent("0.071");
  expect(screen.getByText("app status")).toBeInTheDocument();
});

test("sends the application filter to the history endpoint", async () => {
  const calls = installFetch();
  const user = userEvent.setup();
  render(<App />);
  await screen.findByText("No analyses yet.");
  await user.type(screen.getByLabelText("Filter by application"), "lane");
  await user.click(screen.getByRole("button", { name: "Search" }));
  await waitFor(() => {
    expect(calls.some((call) => call.url.includes("application=lane"))).toBe(true);
  });
});
