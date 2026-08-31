import { useEffect, useMemo, useState } from "react";
import { useDialKit } from "dialkit";
import type { BenchLive, CountryReport } from "./types";
import { CountryCard, CountryDetail } from "./components/CountryCard";
import { CompareBoard, HeadToHead, MultiCountryChart } from "./components/CompareBoard";

export default function App() {
  const theme = useDialKit("World Theme", {
    skyTop: "#5eb8ff",
    grass: "#5a9e2f",
    panelBg: "#f5e6c8",
    accent: "#e8a838",
    scanlines: [0.03, 0, 0.18],
  });

  const [bench, setBench] = useState<BenchLive | null>(null);
  const [selectedId, setSelectedId] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<"world" | "compare">("world");

  const load = () => {
    setLoading(true);
    fetch(`/bench_live.json?t=${Date.now()}`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((j: BenchLive) => {
        setBench(j);
        const top = [...j.countries].sort((a, b) => a.rank - b.rank)[0];
        if (top) setSelectedId(top.agent_id);
      })
      .catch(() => setBench(null))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const countries = bench?.countries ?? [];
  const selected = useMemo(
    () => countries.find((c) => c.agent_id === selectedId) || countries[0],
    [countries, selectedId]
  );

  const cssVars = {
    "--sky-top": theme.skyTop,
    "--grass": theme.grass,
    "--panel-bg": theme.panelBg,
    "--accent": theme.accent,
  } as React.CSSProperties;

  return (
    <div className="pixel-world bench-world" style={cssVars}>
      <div className="crt-overlay" style={{ opacity: theme.scanlines }} />

      <header className="bench-header">
        <div>
          <p className="sample-badge">◆ COUNTRY GOVERNANCE BENCH ◆</p>
          <h1 className="pixel-title">
            POLITY<span className="gold">BENCH</span>
          </h1>
          <p className="pixel-subtitle">Each model runs a nation · citizens · policy · outcomes</p>
        </div>
        <div className="bench-actions">
          <button type="button" className="pixel-btn refresh" onClick={load}>
            ↻ Reload
          </button>
          <div className="view-tabs">
            <button type="button" className={view === "world" ? "active" : ""} onClick={() => setView("world")}>
              World
            </button>
            <button type="button" className={view === "compare" ? "active" : ""} onClick={() => setView("compare")}>
              Compare
            </button>
          </div>
        </div>
      </header>

      {bench && (
        <div className="bench-meta-bar">
          <span>{bench.scenario.replace(/_/g, " ")}</span>
          <span>F{bench.fidelity.replace("F", "")}</span>
          <span>{bench.countries.length} nations</span>
          <span>LLM every {bench.llm_interval_months}mo</span>
          <span>{new Date(bench.generated_at).toLocaleString()}</span>
        </div>
      )}

      {!bench && !loading && (
        <p className="empty-hint">Run <code>politybench bench-run</code> then reload.</p>
      )}

      {view === "compare" && countries.length > 0 && (
        <section className="compare-section">
          <CompareBoard countries={countries} />
          {bench && <HeadToHead bench={bench} />}
          <div className="multi-chart-wrap">
            <h3 className="section-title">GDP paths (all nations)</h3>
            <MultiCountryChart countries={countries} field="gdp" />
          </div>
          <div className="multi-chart-wrap">
            <h3 className="section-title">Trust paths</h3>
            <MultiCountryChart countries={countries} field="trust" />
          </div>
        </section>
      )}

      {view === "world" && (
        <main className="bench-layout">
          <section className="nations-grid">
            <h2 className="section-title">🌍 Nations under test</h2>
            {loading && <p className="muted">Loading bench…</p>}
            <div className="country-grid">
              {countries.map((c) => (
                <CountryCard
                  key={`${c.agent_id}-${c.seed}`}
                  country={c}
                  selected={selected?.agent_id === c.agent_id}
                  onSelect={() => setSelectedId(c.agent_id)}
                />
              ))}
            </div>
          </section>

          {selected && (
            <section className="nation-detail-wrap">
              <h2 className="section-title">📋 {selected.country_name} — national dossier</h2>
              <CountryDetail country={selected} />
            </section>
          )}
        </main>
      )}

      <footer className="pixel-footer">
        <span>politybench bench-run · Cursor LLM vs rule-based executives</span>
        <span className="blink">▮</span>
        <span>research sim only</span>
      </footer>
    </div>
  );
}
