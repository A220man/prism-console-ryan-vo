type InventoryPanelProps = {
  draft: string;
  busy: boolean;
  error: string;
  onDraft: (value: string) => void;
  onLoad: (kind: "surfaces" | "python") => void;
  onSubmit: () => void;
};

export function InventoryPanel({ draft, busy, error, onDraft, onLoad, onSubmit }: InventoryPanelProps) {
  return (
    <section className="panel">
      <h2>Inventory</h2>
      <p className="lede">
        Paste declared surfaces, or a small Python or ipcMain source bundle. The checker does not read a
        repository from disk.
      </p>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit();
        }}
      >
        <label htmlFor="inventory">Inventory JSON</label>
        <textarea
          id="inventory"
          value={draft}
          spellCheck={false}
          onChange={(event) => onDraft(event.target.value)}
        />
        <div className="actions">
          <button type="button" onClick={() => onLoad("surfaces")} disabled={busy}>
            Load surface sample
          </button>
          <button type="button" onClick={() => onLoad("python")} disabled={busy}>
            Load Python sample
          </button>
          <button type="submit" disabled={busy}>
            {busy ? "Building catalog..." : "Build catalog"}
          </button>
        </div>
      </form>
      {error ? (
        <p className="banner" role="alert">
          {error}
        </p>
      ) : null}
    </section>
  );
}
