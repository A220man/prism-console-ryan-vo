import type { Analysis, CommandRecord } from "../types";

type CatalogReportProps = {
  report: Analysis | null;
  onExport: (id: number) => void;
};

export function CatalogReport({ report, onExport }: CatalogReportProps) {
  if (!report) {
    return (
      <section className="panel">
        <h2>Catalog</h2>
        <p className="empty">No catalog yet. Submit an inventory to score commands.</p>
      </section>
    );
  }
  const commands = report.grounded.commands ?? [];
  return (
    <section className="panel">
      <div className="section-head">
        <h2>Catalog for {report.application}</h2>
        <button type="button" onClick={() => onExport(report.id)}>
          Export JSON
        </button>
      </div>
      <div className="metrics">
        <Metric label="Grounded coverage" value={report.grounded.coverage} />
        <Metric label="Grounded correctness" value={report.grounded.correctness} />
        <Metric label="Thin coverage" value={report.thin.coverage} />
        <Metric label="Thin correctness" value={report.thin.correctness} />
      </div>
      <p className="counts">
        Grounded {report.grounded.executable} executable of {report.grounded.proposed} proposed across{" "}
        {report.surface_count} surfaces. Thin baseline {report.thin.executable} executable of{" "}
        {report.thin.proposed} proposed.
      </p>
      {report.notices.length > 0 ? (
        <ul className="notices">
          {report.notices.map((notice) => (
            <li key={notice}>{notice}</li>
          ))}
        </ul>
      ) : null}
      {commands.length === 0 ? (
        <p className="empty">No commands for this inventory.</p>
      ) : (
        <CommandTable commands={commands} />
      )}
      <details>
        <summary>
          Thin baseline commands ({report.thin.executable} executable of {report.thin.proposed})
        </summary>
        <CommandTable commands={report.thin.commands ?? []} />
      </details>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value.toFixed(3)}</strong>
    </div>
  );
}

function CommandTable({ commands }: { commands: CommandRecord[] }) {
  if (commands.length === 0) {
    return <p className="empty">No commands.</p>;
  }
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Command</th>
            <th>Executable</th>
            <th>Why</th>
            <th>Invocation</th>
          </tr>
        </thead>
        <tbody>
          {commands.map((command) => (
            <tr key={`${command.path}-${command.surface_id ?? command.verb}`}>
              <td>{command.path || "(unnamed)"}</td>
              <td className={command.executable ? "yes" : "no"}>{command.executable ? "Yes" : "No"}</td>
              <td>{command.reasons.length > 0 ? command.reasons.join("; ") : "Bound"}</td>
              <td>
                <code>{command.invocation}</code>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
