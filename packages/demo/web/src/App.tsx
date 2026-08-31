import { useEffect, useMemo, useState } from "react";
import { useDialKit } from "dialkit";
import type { BenchLive } from "./types";
import { CountryCard, CountryDetail } from "./components/CountryCard";
import { CompareBoard, HeadToHead, MultiCountryChart } from "./components/CompareBoard";
import { Podium } from "./components/Narrative";

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
  const [view, setView] = useState<"world" | "compare" | "replay">("world");
  const [playing, setPlaying] = useState(false);
  const [playMonth, setPlayMonth] = useState(0);

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

  const maxMonth = useMemo(() => {
    if (!selected?.trajectory?.length) return 0;
    return selected.trajectory.length - 1;
  }, [selected]);

  useEffect(() => {
    if (!playing || !selected) return;
    const id = setInterval(() => {
      setPlayMonth((m) => {
        if (m >= maxMonth) {
          setPlaying(false);
          return maxMonth;
        }
        return m + 1;
      });
    }, 280);
    return () => clearInterval(id);
  }, [playing, selected, maxMonth]);

  useEffect(() => {
    setPlayMonth(0);
    setPlaying(false);
  }, [selectedId]);

  const cssVars = {
    "--sky-top": theme.skyTop,
    "--grass": theme.grass,
    "--panel-bg": theme.panelBg,
    "--accent": theme.accent,
  } as React.CSSProperties;

  const winner = countries.find((c) => c.rank === 1);

  return (
    <div className="pixel-world bench-world" style={cssVars}>
      <div className="crt-overlay" style={{ opacity: theme.scanlines }} />

      <header className="bench-header">
        <div>
          <p className="sample-badge">◆ COUNTRY GOVERNANCE BENCH ◆</p>
          <h1 className="pixel-title">
            POLITY<span className="gold">BENCH</span>
          </h1>
          <p className="pixel-subtitle">
            {winner
              ? `Champion: ${winner.sprite} ${winner.country_name} (${winner.evaluation.robust_score_single.toFixed(1)})`
              : "Each model runs a nation · citizens · policy · outcomes"}
          </p>
        </div>
        <div className="bench-actions">
          <button type="button" className="pixel-btn refresh" onClick={load}>
            ↻ Reload
          </button>
          <div className="view-tabs">
            {(
              [
                ["world", "World"],
                ["compare", "Compare"],
                ["replay", "Replay"],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                className={view === id ? "active" : ""}
                onClick={() => setView(id)}
              >
                {label}
              </button>
            ))}
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

      {countries.length > 0 && view === "world" && <Podium countries={countries} />}

      {!bench && !loading && (
        <p className="empty-hint">
          Run <code>politybench bench-run</code> then reload.
        </p>
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
          <div className="multi-chart-wrap">
            <h3 className="section-title">Debt / GDP paths</h3>
            <MultiCountryChart countries={countries} field="debt_gdp" />
          </div>
        </section>
      )}

      {view === "replay" && selected && (
        <section className="replay-section">
          <div className="replay-picker">
            {countries.map((c) => (
              <button
                key={c.agent_id}
                type="button"
                className={`pixel-btn ${selectedId === c.agent_id ? "active" : ""}`}
                onClick={() => setSelectedId(c.agent_id)}
              >
                {c.sprite} {c.country_name}
              </button>
            ))}
          </div>
          <div className="replay-stage">
            <div className="replay-controls">
              <button type="button" className="pixel-btn active" onClick={() => setPlaying((p) => !p)}>
                {playing ? "❚❚ Pause" : "▶ Play term"}
              </button>
              <button
                type="button"
                className="pixel-btn"
                onClick={() => {
                  setPlayMonth(0);
                  setPlaying(true);
                }}
              >
                ↺ Restart
              </button>
              <span className="muted">
                Month {playMonth}/{maxMonth} · town + stats animate with the scrubber
              </span>
            </div>
            <CountryDetail country={selected} month={playMonth} onMonthChange={setPlayMonth} />
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
