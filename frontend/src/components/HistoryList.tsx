import type { AnalysisList } from "../types";

type HistoryListProps = {
  page: AnalysisList | null;
  loading: boolean;
  error: string;
  query: string;
  onQuery: (value: string) => void;
  onSearch: () => void;
  onOpen: (id: number) => void;
  onPage: (offset: number) => void;
};

export function HistoryList({
  page,
  loading,
  error,
  query,
  onQuery,
  onSearch,
  onOpen,
  onPage,
}: HistoryListProps) {
  const offset = page?.offset ?? 0;
  const total = page?.total ?? 0;
  const count = page?.items.length ?? 0;
  return (
    <section className="panel">
      <h2>Saved analyses</h2>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          onSearch();
        }}
      >
        <label htmlFor="application-filter">Filter by application</label>
        <div className="actions">
          <input
            id="application-filter"
            value={query}
            onChange={(event) => onQuery(event.target.value)}
          />
          <button type="submit">Search</button>
        </div>
      </form>
      {error ? (
        <p className="banner" role="alert">
          {error}
        </p>
      ) : null}
      {loading ? <p>Loading analyses...</p> : null}
      {!loading && page && page.items.length === 0 ? <p className="empty">No analyses yet.</p> : null}
      {!loading && page && page.items.length > 0 ? (
        <>
          <ul className="history">
            {page.items.map((item) => (
              <li key={item.id}>
                <button type="button" onClick={() => onOpen(item.id)}>
                  <span>{item.application}</span>
                  <small>
                    {item.created_at} · coverage {item.grounded.coverage.toFixed(3)}
                  </small>
                </button>
              </li>
            ))}
          </ul>
          <div className="actions">
            <button type="button" disabled={offset === 0} onClick={() => onPage(Math.max(0, offset - page.limit))}>
              Previous
            </button>
            <button
              type="button"
              disabled={offset + count >= total}
              onClick={() => onPage(offset + page.limit)}
            >
              Next
            </button>
            <span>
              Showing {offset + 1}–{offset + count} of {total}
            </span>
          </div>
        </>
      ) : null}
    </section>
  );
}
