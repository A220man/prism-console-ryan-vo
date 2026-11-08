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
import { ReplayPanel } from "./components/ReplayPanel";
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
    setListError("");
    try {
      const data = await listAnalyses(application, offset);
      setPage(data);
    } catch (e) {
      setListError(errorMessage(e));
    } finally {
      setListLoading(false);
    }
  }

  useEffect(() => {
    getHealth().then((h) => setVersion(h.version)).catch(() => {});
    void refresh("lane-desk", 0);
    getEvaluation()
      .then((e) => setEvaluation(e))
      .catch((e) => setEvaluationError(errorMessage(e)));
  }, []);

  async function loadSample(kind: "surfaces" | "python") {
    const sample = await getSample(kind);
    setDraft(JSON.stringify(sample, null, 2));
  }

  async function buildCatalog() {
    setBusy(true);
    setFormError("");
    let payload: unknown;
    try {
      payload = JSON.parse(draft);
    } catch {
      setFormError("Inventory JSON could not be parsed");
      setBusy(false);
      return;
    }
    try {
      const created = await createAnalysis(payload);
      setReport(created);
      void refresh(created.application, 0);
    } catch (e) {
      setFormError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  async function openAnalysis(id: number) {
    const data = await getAnalysis(id);
    setReport(data);
  }

  async function exportReport(id: number) {
    await downloadExport(id, report?.application ?? "lane-desk");
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
      <ReplayPanel report={report} />
      <EvaluationPanel report={evaluation} error={evaluationError} />
    </main>
  );
}

