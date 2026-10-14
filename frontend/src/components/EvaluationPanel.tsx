import type { EvaluationReport } from "../types";

export function EvaluationPanel({ report, error }: { report: EvaluationReport | null; error: string }) {
  return (
    <section className="panel">
      <h2>Labeled evaluation</h2>
      {error ? (
        <p className="banner" role="alert">
          {error}
        </p>
      ) : null}
      {!report && !error ? <p>Loading evaluation...</p> : null}
      {report ? (
        <>
          <p className="lede">{report.convention}</p>
          <div className="metrics">
            <Score label="Grounded precision" value={report.grounded.precision} />
            <Score label="Grounded recall" value={report.grounded.recall} />
            <Score label="Thin precision" value={report.thin.precision} />
            <Score label="Thin recall" value={report.thin.recall} />
          </div>
          <p className="counts">
            {report.case_count} cases. Grounded true positives {report.grounded.true_positives} of{" "}
            {report.grounded.gold}. Thin true positives {report.thin.true_positives} of {report.thin.gold}.
          </p>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Case</th>
                  <th>Grounded recall</th>
                  <th>Thin recall</th>
                  <th>Thin false positives</th>
                </tr>
              </thead>
              <tbody>
                {report.cases.map((item) => (
                  <tr key={item.name}>
                    <td>{item.name}</td>
                    <td>{item.grounded.recall.toFixed(3)}</td>
                    <td>{item.thin.recall.toFixed(3)}</td>
                    <td>{item.thin.false_positives.length > 0 ? item.thin.false_positives.join(", ") : "none"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <h3>Failure cases</h3>
          <ul>
            {report.failure_cases.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </>
      ) : null}
    </section>
  );
}

function Score({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value.toFixed(3)}</strong>
    </div>
  );
}
