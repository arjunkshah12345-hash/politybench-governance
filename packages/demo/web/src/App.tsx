import { useEffect, useMemo, useState } from "react";
import { useDialKit } from "dialkit";
import type { BenchLive } from "./types";
import { CountryCard, CountryDetail } from "./components/CountryCard";
import { CompareBoard, HeadToHead, MultiCountryChart } from "./components/CompareBoard";
import { Podium } from "./components/Narrative";
import { DuelArena, GameHUD } from "./components/DuelArena";
import { DuelWinner, NewsTicker, OverworldMap, TermEndSplash } from "./components/Overworld";

export default function App() {
  const theme = useDialKit("World Theme", {
    skyTop: "#5eb8ff",
    grass: "#5a9e2f",
    panelBg: "#f5e6c8",
    accent: "#e8a838",
    scanlines: [0.025, 0, 0.15],
  });

  const [bench, setBench] = useState<BenchLive | null>(null);
  const [selectedId, setSelectedId] = useState("");
  const [duelRightId, setDuelRightId] = useState("");
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<"world" | "duel" | "compare" | "replay">("world");
  const [playing, setPlaying] = useState(false);
  const [playMonth, setPlayMonth] = useState(0);
  const [showTermEnd, setShowTermEnd] = useState(false);
  const [showDuelEnd, setShowDuelEnd] = useState(false);

  const load = () => {
    setLoading(true);
    fetch(`/bench_live.json?t=${Date.now()}`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((j: BenchLive) => {
        setBench(j);
        const sorted = [...j.countries].sort((a, b) => a.rank - b.rank);
        if (sorted[0]) setSelectedId(sorted[0].agent_id);
        if (sorted[1]) setDuelRightId(sorted[1].agent_id);
        else if (sorted[0]) setDuelRightId(sorted[0].agent_id);
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
  const duelRight = useMemo(
    () => countries.find((c) => c.agent_id === duelRightId) || countries[1] || countries[0],
    [countries, duelRightId]
  );

  const maxMonth = useMemo(() => {
    if (!selected?.trajectory?.length) return 0;
    const other = duelRight?.trajectory?.length || 0;
    return Math.max(selected.trajectory.length, other) - 1;
  }, [selected, duelRight]);

  useEffect(() => {
    if (!playing) return;
    const id = setInterval(() => {
      setPlayMonth((m) => {
        if (m >= maxMonth) {
          setPlaying(false);
          if (view === "replay") setShowTermEnd(true);
          if (view === "duel") setShowDuelEnd(true);
          return maxMonth;
        }
        return m + 1;
      });
    }, 220);
    return () => clearInterval(id);
  }, [playing, maxMonth, view]);

  useEffect(() => {
    setPlayMonth(0);
    setPlaying(false);
    setShowTermEnd(false);
    setShowDuelEnd(false);
  }, [selectedId, duelRightId]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.code === "Space") {
        e.preventDefault();
        setPlaying((p) => !p);
      } else if (e.code === "ArrowRight") {
        setPlayMonth((m) => Math.min(maxMonth, m + 1));
      } else if (e.code === "ArrowLeft") {
        setPlayMonth((m) => Math.max(0, m - 1));
      } else if (e.key === "1") setView("world");
      else if (e.key === "2") setView("duel");
      else if (e.key === "3") setView("compare");
      else if (e.key === "4") setView("replay");
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [maxMonth]);

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

      {selected && (view === "replay" || view === "duel") && (
        <GameHUD country={selected} month={playMonth} />
      )}

      <header className="bench-header">
        <div>
          <p className="sample-badge">◆ COUNTRY GOVERNANCE BENCH ◆</p>
          <h1 className="pixel-title">
            POLITY<span className="gold">BENCH</span>
          </h1>
          <p className="pixel-subtitle">
            {winner
              ? `Champion: ${winner.sprite} ${winner.country_name} · ${winner.evaluation.robust_score_single.toFixed(1)} robust`
              : "Each model runs a nation"}
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
                ["duel", "Duel"],
                ["compare", "Board"],
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
        <>
          <NewsTicker countries={countries} month={playMonth} />
          <div className="bench-meta-bar">
            <span>{bench.scenario.replace(/_/g, " ")}</span>
            <span>F{bench.fidelity.replace("F", "")}</span>
            <span>{bench.countries.length} nations</span>
            <span>keys 1–4 · space play</span>
          </div>
        </>
      )}

      {countries.length > 0 && view === "world" && <Podium countries={countries} />}

      {!bench && !loading && (
        <p className="empty-hint">
          Run <code>politybench bench-run</code> then reload.
        </p>
      )}

      {view === "duel" && selected && duelRight && (
        <section className="duel-section">
          <div className="duel-pickers">
            <label>
              Left
              <select value={selectedId} onChange={(e) => setSelectedId(e.target.value)}>
                {countries.map((c) => (
                  <option key={c.agent_id} value={c.agent_id}>
                    #{c.rank} {c.country_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Right
              <select value={duelRightId} onChange={(e) => setDuelRightId(e.target.value)}>
                {countries.map((c) => (
                  <option key={c.agent_id} value={c.agent_id}>
                    #{c.rank} {c.country_name}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <DuelArena
            left={selected}
            right={duelRight}
            month={playMonth}
            onMonthChange={setPlayMonth}
            playing={playing}
            onTogglePlay={() => setPlaying((p) => !p)}
          />
        </section>
      )}

      {view === "compare" && countries.length > 0 && (
        <section className="compare-section">
          <CompareBoard countries={countries} />
          {bench && <HeadToHead bench={bench} />}
          <div className="multi-chart-wrap">
            <h3 className="section-title">GDP paths</h3>
            <MultiCountryChart countries={countries} field="gdp" />
          </div>
          <div className="multi-chart-wrap">
            <h3 className="section-title">Trust paths</h3>
            <MultiCountryChart countries={countries} field="trust" />
          </div>
          <div className="multi-chart-wrap">
            <h3 className="section-title">Debt / GDP</h3>
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
              Month {playMonth}/{maxMonth}
            </span>
          </div>
          <CountryDetail country={selected} month={playMonth} onMonthChange={setPlayMonth} />
        </section>
      )}

      {view === "world" && (
        <main className="bench-layout">
          {countries.length > 0 && (
            <OverworldMap
              countries={countries}
              selectedId={selectedId}
              onSelect={(id) => {
                setSelectedId(id);
                setView("replay");
                setPlayMonth(0);
                setPlaying(true);
              }}
            />
          )}
          <section className="nations-grid">
            <h2 className="section-title">🌍 Nations under test</h2>
            {loading && <p className="muted">Loading bench…</p>}
            <div className="country-grid">
              {countries.map((c) => (
                <CountryCard
                  key={`${c.agent_id}-${c.seed}`}
                  country={c}
                  selected={selected?.agent_id === c.agent_id}
                  onSelect={() => {
                    setSelectedId(c.agent_id);
                    setView("replay");
                    setPlayMonth(0);
                    setPlaying(true);
                  }}
                />
              ))}
            </div>
          </section>

          {selected && (
            <section className="nation-detail-wrap">
              <h2 className="section-title">📋 {selected.country_name}</h2>
              <CountryDetail country={selected} />
            </section>
          )}
        </main>
      )}

      {showTermEnd && selected && view === "replay" && (
        <TermEndSplash country={selected} onClose={() => setShowTermEnd(false)} />
      )}
      {showDuelEnd && selected && duelRight && view === "duel" && (
        <DuelWinner left={selected} right={duelRight} onClose={() => setShowDuelEnd(false)} />
      )}

      <footer className="pixel-footer">
        <span>click a nation → auto-replay · Duel for head-to-head</span>
        <span className="blink">▮</span>
        <span>research sim only</span>
      </footer>
    </div>
  );
}
