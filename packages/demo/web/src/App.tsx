import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type Results = {
  scenario: string;
  seeds: number;
  robust_scores: Record<string, number>;
  mean_utility: Record<string, number>;
  mean_dims: Record<string, Record<string, number>>;
  pareto_frontier: string[];
  weight_sensitivity: Record<string, { mean_rank: number; p_top1: number; rank_interval: number[] }>;
  paired_rule_vs_hold?: { paired_mean_diff: number; bootstrap_ci95: number[]; prob_superiority: number };
};

const DIMS = [
  "economic",
  "human",
  "stability",
  "equity",
  "resilience",
  "legitimacy",
  "environment",
] as const;

const FALLBACK: Results = {
  scenario: "macro_fiscal_crisis",
  seeds: 8,
  robust_scores: { hold_policy: 61.2, rule_based: 68.4, random_valid: 58.1, simple_mpc: 69.0 },
  mean_utility: { hold_policy: 0.62, rule_based: 0.70, random_valid: 0.59, simple_mpc: 0.71 },
  mean_dims: {
    rule_based: {
      economic: 0.56,
      human: 0.81,
      stability: 0.79,
      equity: 0.35,
      resilience: 0.91,
      legitimacy: 0.99,
      environment: 0.63,
    },
    hold_policy: {
      economic: 0.48,
      human: 0.78,
      stability: 0.72,
      equity: 0.30,
      resilience: 0.85,
      legitimacy: 0.96,
      environment: 0.58,
    },
  },
  pareto_frontier: ["rule_based", "simple_mpc"],
  weight_sensitivity: {
    rule_based: { mean_rank: 1.4, p_top1: 0.55, rank_interval: [1, 3] },
    simple_mpc: { mean_rank: 1.6, p_top1: 0.40, rank_interval: [1, 3] },
  },
};

export default function App() {
  const [data, setData] = useState<Results>(FALLBACK);
  const [agent, setAgent] = useState("rule_based");

  useEffect(() => {
    fetch("/latest_results.json")
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((j) => {
        setData(j);
        const first = Object.keys(j.mean_dims || {})[0];
        if (first) setAgent(first);
      })
      .catch(() => undefined);
  }, []);

  const dims = data.mean_dims[agent] || data.mean_dims.rule_based || FALLBACK.mean_dims.rule_based;
  const chartData = useMemo(
    () =>
      Object.entries(data.robust_scores).map(([name, score]) => ({
        name,
        score: Number(score.toFixed(2)),
        utility: Number((data.mean_utility[name] || 0).toFixed(3)),
      })),
    [data]
  );

  return (
    <div className="shell">
      <header className="hero">
        <p className="muted" style={{ margin: 0, letterSpacing: "0.08em", textTransform: "uppercase", fontSize: "0.75rem" }}>
          Research benchmark
        </p>
        <h1 className="brand">PolityBench</h1>
        <p className="tag">
          Longitudinal evaluation of constitutionally constrained AI executive agents under
          uncertainty — not a civilization game, not a policy oracle.
        </p>
        <span className="warn">
          A high score is never evidence that an AI should govern a real country.
        </span>
      </header>

      <div className="grid">
        <section className="panel span-4">
          <h2>Official robust score</h2>
          <p className="kpi">
            {(data.robust_scores[agent] ?? 0).toFixed(1)}
            <small> / 100</small>
          </p>
          <p className="muted">
            0.75·E[G] + 0.25·CVaR₁₀% − penalties · scenario <strong>{data.scenario}</strong> ·{" "}
            {data.seeds} paired seeds
          </p>
          <label className="muted" style={{ display: "block", marginTop: "0.8rem" }}>
            Agent{" "}
            <select value={agent} onChange={(e) => setAgent(e.target.value)}>
              {Object.keys(data.robust_scores).map((a) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </select>
          </label>
        </section>

        <section className="panel span-8">
          <h2>Dimension vector</h2>
          <div className="scores">
            {DIMS.map((d) => (
              <div className="row" key={d}>
                <span>{d}</span>
                <div className="bar">
                  <span style={{ width: `${Math.round((dims[d] || 0) * 100)}%` }} />
                </div>
                <span>{(dims[d] || 0).toFixed(2)}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="panel span-7">
          <h2>Agent comparison</h2>
          <div style={{ width: "100%", height: 280 }}>
            <ResponsiveContainer>
              <LineChart data={chartData}>
                <CartesianGrid stroke="rgba(20,32,26,0.08)" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="score" name="Robust score" stroke="#1f6f5b" strokeWidth={2} dot />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>

        <section className="panel span-5">
          <h2>Pareto & sensitivity</h2>
          <p className="muted">Frontier: {(data.pareto_frontier || []).join(", ") || "—"}</p>
          <table className="table">
            <thead>
              <tr>
                <th>Agent</th>
                <th>Mean rank</th>
                <th>P(top-1)</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(data.weight_sensitivity || {}).map(([a, s]) => (
                <tr key={a}>
                  <td>{a}</td>
                  <td>{s.mean_rank.toFixed(2)}</td>
                  <td>{(s.p_top1 * 100).toFixed(0)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
          {data.paired_rule_vs_hold && (
            <p className="muted" style={{ marginTop: "0.8rem" }}>
              Rule vs hold Δ={data.paired_rule_vs_hold.paired_mean_diff.toFixed(3)} · P(sup)=
              {(data.paired_rule_vs_hold.prob_superiority * 100).toFixed(0)}%
            </p>
          )}
        </section>

        <section className="panel span-12">
          <h2>Construct</h2>
          <p className="muted" style={{ margin: 0, maxWidth: "52rem" }}>
            Agents receive delayed, noisy observations and issue constrained policy bundles. The
            hybrid kernel couples national accounts, weighted households, institutions, health,
            infrastructure, and shocks. Historical Greece and Japan GEJE cases validate the
            simulator; leaderboard scenarios remain synthetic.
          </p>
        </section>
      </div>
    </div>
  );
}
