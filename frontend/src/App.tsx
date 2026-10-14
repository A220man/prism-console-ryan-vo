import { useEffect, useState } from "react";
import {
  createAnalysis,
  downloadExport,
  errorMessage,
  getAnalysis,
  getEvaluation,
  getHealth,
  getSample,
  listAnalyses,
} from "./api";
import { CatalogReport } from "./components/CatalogReport";
import { EvaluationPanel } from "./components/EvaluationPanel";
import { HistoryList } from "./components/HistoryList";
import { InventoryPanel } from "./components/InventoryPanel";
import type { Analysis, AnalysisList, EvaluationReport } from "./types";

export function App() {
  const [version, setVersion] = useState("");
  const [draft, setDraft] = useState("");
  const [formError, setFormError] = useState("");
  const [busy, setBusy] = useState(false);
  const [report, setReport] = useState<Analysis | null>(null);
  const [page, setPage] = useState<AnalysisList | null>(null);
  const [listLoading, setListLoading] = useState(true);
  const [listError, setListError] = useState("");
  const [query, setQuery] = useState("");
  const [evaluation, setEvaluation] = useState<EvaluationReport | null>(null);
  const [evaluationError, setEvaluationError] = useState("");

  async function refresh(application: string, offset: number) {
    setListLoading(true);
    try {
      const next = await listAnalyses(application, offset);
      setPage(next);
      setListError("");
    } catch (error) {
      setListError(errorMessage(error));
    } finally {
      setListLoading(false);
    }
  }

  useEffect(() => {
    getHealth()
      .then((health) => setVersion(health.version))
      .catch(() => setVersion(""));
    void refresh("", 0);
    getEvaluation()
      .then(setEvaluation)
      .catch((error) => setEvaluationError(errorMessage(error)));
  }, []);

  async function loadSample(kind: "surfaces" | "python") {
    setFormError("");
    try {
      const sample = await getSample(kind);
      setDraft(JSON.stringify(sample, null, 2));
    } catch (error) {
      setFormError(errorMessage(error));
    }
  }

  async function buildCatalog() {
    let payload: unknown;
    try {
      payload = JSON.parse(draft);
    } catch {
      setFormError("Inventory JSON could not be parsed");
      return;
    }
    setBusy(true);
    setFormError("");
    try {
      const created = await createAnalysis(payload);
      setReport(created);
      await refresh(query, 0);
    } catch (error) {
      setFormError(errorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  async function openAnalysis(id: number) {
    setFormError("");
    try {
      setReport(await getAnalysis(id));
    } catch (error) {
      setFormError(errorMessage(error));
    }
  }

  async function exportReport(id: number) {
    if (!report) {
      return;
    }
    try {
      await downloadExport(id, report.application);
    } catch (error) {
      setFormError(errorMessage(error));
    }
  }

  return (
    <main>
      <header>
        <div>
          <p className="eyebrow">CLI catalog check</p>
          <h1>Prism Console</h1>
        </div>
        {version ? <p className="version">Version {version}</p> : null}
      </header>
      <p className="intro">
        Score a command catalog against the handlers an application already exposes, then compare it with a
        thin start/stop/status/chat/meeting baseline.
      </p>
      <div className="layout">
        <InventoryPanel
          draft={draft}
          busy={busy}
          error={formError}
          onDraft={setDraft}
          onLoad={(kind) => void loadSample(kind)}
          onSubmit={() => void buildCatalog()}
        />
        <HistoryList
          page={page}
          loading={listLoading}
          error={listError}
          query={query}
          onQuery={setQuery}
          onSearch={() => void refresh(query, 0)}
          onOpen={(id) => void openAnalysis(id)}
          onPage={(offset) => void refresh(query, offset)}
        />
      </div>
      <CatalogReport report={report} onExport={(id) => void exportReport(id)} />
      <EvaluationPanel report={evaluation} error={evaluationError} />
    </main>
  );
}
