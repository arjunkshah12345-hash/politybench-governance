import { useEffect, useMemo, useState } from "react";
import { useDialKit } from "dialkit";
import type { BenchLive, CountryReport } from "./types";
import { CountryCard, CountryDetail } from "./components/CountryCard";

const FALLBACK_COUNTRIES: CountryReport[] = [
  {
    agent_id: "rule_based",
    model: "rule_based",
    seed: 41823,
    scenario: "macro_fiscal_crisis",
    country_name: "Meridian Federation",
    motto: "Rules before rhetoric",
    leader_title: "Chief Administrator",
    sprite: "👨‍⚖️",
    flag: ["#1f6f5b", "#f4d03f", "#1f6f5b"],
    terrain: "coast",
    overview: {
      population: 10_000_000,
      gdp_index: 94,
      unemployment_pct: 11.2,
      debt_gdp: 1.28,
      trust: 0.62,
      poverty_pct: 14,
      infected: 0,
      deaths: 120,
      damage: 0.04,
      inflation_pct: 2.1,
    },
    evaluation: { utility: 0.68, robust_score_single: 64, dims: { economic: 0.56, human: 0.81, stability: 0.79, equity: 0.35, resilience: 0.91, legitimacy: 0.99, environment: 0.63 } },
    citizens: Array.from({ length: 64 }, (_, i) => ({ mood: i % 5 === 0 ? "worried" : "neutral", employed: i % 8 !== 0, cohort: i % 10 })),
    regions: [
      { name: "Capital", population_share: 0.4, gdp_share: 0.5, damage: 0.05, services: 0.9 },
      { name: "Coast", population_share: 0.35, gdp_share: 0.3, damage: 0.08, services: 0.85 },
    ],
    timeline: [{ month: 0, type: "inauguration", label: "Run bench-run to populate", severity: 0.2 }],
    trajectory: [],
    integrity: { hard_violations: 0, rejected_actions: 0, llm_calls: 0 },
  },
];

export default function App() {
  const theme = useDialKit("World Theme", {
    skyTop: "#5eb8ff",
    grass: "#5a9e2f",
    panelBg: "#f5e6c8",
    accent: "#e8a838",
    scanlines: [0.04, 0, 0.2],
  });

  const [bench, setBench] = useState<BenchLive | null>(null);
  const [selectedId, setSelectedId] = useState<string>("rule_based");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/bench_live.json")
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((j: BenchLive) => {
        setBench(j);
        if (j.countries[0]) setSelectedId(j.countries[0].agent_id);
      })
      .catch(() => setBench(null))
      .finally(() => setLoading(false));
  }, []);

  const countries = bench?.countries?.length ? bench.countries : FALLBACK_COUNTRIES;
  const selected = useMemo(
    () => countries.find((c) => c.agent_id === selectedId) || countries[0],
    [countries, selectedId]
  );

  const cssVars = {
    "--sky-top": theme.skyTop,
    "--grass": theme.grass,
    "--panel-bg": theme.panelBg,
    "--accent": theme.accent,
    "--scanline-opacity": theme.scanlines,
  } as React.CSSProperties;

  return (
    <div className="pixel-world bench-world" style={cssVars}>
      <div className="crt-overlay" style={{ opacity: theme.scanlines }} />

      <header className="bench-header">
        <div>
          <p className="sample-badge">◆ LIVE COUNTRY BENCH · SAMPLE UI ◆</p>
          <h1 className="pixel-title">
            POLITY<span className="gold">BENCH</span>
          </h1>
          <p className="pixel-subtitle">Each model governs a nation · citizens · stats · timeline</p>
        </div>
        <div className="bench-meta">
          {bench ? (
            <>
              <span>{bench.scenario.replace(/_/g, " ")}</span>
              <span>F{bench.fidelity.replace("F", "")}</span>
              <span>{bench.countries.length} nations</span>
              <span>{new Date(bench.generated_at).toLocaleString()}</span>
            </>
          ) : (
            <span className="warn-pill">Run: politybench bench-run</span>
          )}
        </div>
      </header>

      {bench?.summary && (
        <div className="pareto-bar">
          <strong>Pareto frontier:</strong> {bench.summary.pareto_frontier.join(" · ")}
          {Object.entries(bench.summary.robust_scores)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 3)
            .map(([a, s]) => (
              <span key={a} className="pareto-chip">
                {a}: {s.toFixed(0)}
              </span>
            ))}
        </div>
      )}

      <main className="bench-layout">
        <section className="nations-grid">
          <h2 className="section-title">🌍 Nations under test</h2>
          {loading && <p className="muted">Loading bench_live.json…</p>}
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
            <h2 className="section-title">📋 National overview</h2>
            <CountryDetail country={selected} />
          </section>
        )}
      </main>

      <footer className="pixel-footer">
        <span>politybench bench-run · Cursor LLM executives vs baselines</span>
        <span className="blink">▮</span>
        <span>research sim — not policy advice</span>
      </footer>
    </div>
  );
}
