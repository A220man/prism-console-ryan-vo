import { useState } from "react";
import { replayArgv } from "../api";
import { parseArgv } from "../utils/argv";
import type { Analysis, CommandRecord, ReplayResult } from "../types";

type ReplayPanelProps = {
  report: Analysis | null;
};

export function ReplayPanel({ report }: ReplayPanelProps) {
  const [selectedCommand, setSelectedCommand] = useState<CommandRecord | null>(null);
  const [argvInput, setArgvInput] = useState("");
  const [generator, setGenerator] = useState<"grounded" | "thin">("grounded");
  const [result, setResult] = useState<ReplayResult | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (!report) {
    return (
      <section className="panel">
        <h2>Replay argv</h2>
        <p className="empty">No analysis loaded. Open an analysis to replay commands.</p>
      </section>
    );
  }

  const allCommands = [
    ...(report.grounded.commands ?? []),
    ...(report.thin.commands ?? []),
  ];

  const uniqueCommands = allCommands.filter(
    (cmd, idx, arr) => arr.findIndex(c => c.path === cmd.path) === idx
  );

  const handleReplay = async () => {
    if (!selectedCommand) return;
    setLoading(true);
    setError("");
    try {
      const argv = argvInput.trim() ? parseArgv(argvInput.trim()) : [];
      const res = await replayArgv(report.id, selectedCommand.path, argv, generator);
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Replay failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="panel">
      <h2>Replay argv</h2>
      <p className="help">
        Select a command from the catalog, provide argv as space-separated flags (e.g. <code>--title "my note" --body "text"</code>), and click Replay.
      </p>

      <div className="replay-form">
        <div className="form-row">
          <label htmlFor="command-select">Command</label>
          <select
            id="command-select"
            value={selectedCommand?.path || ""}
            onChange={(e) => {
              const path = e.target.value;
              const cmd = uniqueCommands.find(c => c.path === path);
              setSelectedCommand(cmd || null);
              setResult(null);
            }}
          >
            <option value="">-- select a command --</option>
            {uniqueCommands.map((cmd) => {
              const isGrounded = report.grounded.commands?.some(c => c.path === cmd.path);
              return (
                <option key={cmd.path} value={cmd.path}>
                  {cmd.path} ({isGrounded ? "grounded" : "thin"}) - {cmd.executable ? "executable" : "not executable"}
                </option>
              );
            })}
          </select>
        </div>

        <div className="form-row">
          <label htmlFor="generator-select">Generator</label>
          <select
            id="generator-select"
            value={generator}
            onChange={(e) => {
              setGenerator(e.target.value as "grounded" | "thin");
              setResult(null);
            }}
          >
            <option value="grounded">Grounded</option>
            <option value="thin">Thin baseline</option>
          </select>
        </div>

        <div className="form-row">
          <label htmlFor="argv-input">argv</label>
          <input
            id="argv-input"
            type="text"
            value={argvInput}
            onChange={(e) => {
              setArgvInput(e.target.value);
              setResult(null);
            }}
            placeholder="--flag value --flag2 value2"
            disabled={!selectedCommand}
          />
        </div>

        <button type="button" onClick={handleReplay} disabled={!selectedCommand || loading}>
          {loading ? "Replaying..." : "Replay"}
        </button>

        {error && <p className="error">Error: {error}</p>}

        {result && (
          <div className="replay-result" data-success={result.success}>
            <h3>Result</h3>
            <p><strong>Command:</strong> {result.command_path}</p>
            <p><strong>Generator:</strong> {result.generator}</p>
            <p><strong>Success:</strong> {result.success ? "Yes" : "No"}</p>
            {result.bound && Object.keys(result.bound).length > 0 && (
              <div>
                <strong>Bound parameters:</strong>
                <pre>{JSON.stringify(result.bound, null, 2)}</pre>
              </div>
            )}
            {result.reasons && result.reasons.length > 0 && (
              <div>
                <strong>Reasons:</strong>
                <ul>
                  {result.reasons.map((reason, i) => (
                    <li key={i}>{reason}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {selectedCommand && selectedCommand.argv.length > 0 && (
          <details className="hint">
            <summary>Suggested argv for this command</summary>
            <code>{selectedCommand.argv.join(" ")}</code>
          </details>
        )}
      </div>
    </section>
  );
}
