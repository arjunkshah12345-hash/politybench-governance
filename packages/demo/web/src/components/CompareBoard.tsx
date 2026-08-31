import type { CountryReport } from "../types";

const MEDALS = ["🥇", "🥈", "🥉"];

export function CompareBoard({ countries }: { countries: CountryReport[] }) {
  const sorted = [...countries].sort((a, b) => a.rank - b.rank);

  return (
    <div className="compare-board">
      <table className="compare-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Nation</th>
            <th>Model</th>
            <th>Grade</th>
            <th>Robust</th>
            <th>GDP</th>
            <th>Jobs</th>
            <th>Trust</th>
            <th>Debt</th>
            <th>Poverty</th>
            <th>Citizens</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((c) => {
            const o = c.overview;
            const happy = ((c.mood_summary?.happy ?? 0) * 100).toFixed(0);
            return (
              <tr key={c.agent_id} className={c.rank === 1 ? "row-gold" : ""}>
                <td>{MEDALS[c.rank - 1] || c.rank}</td>
                <td>
                  {c.sprite} {c.country_name}
                </td>
                <td className="mono">{c.model}</td>
                <td>
                  <span className={`grade grade-${c.grade}`}>{c.grade}</span>
                </td>
                <td>{c.evaluation.robust_score_single.toFixed(1)}</td>
                <td>{o.gdp_index}%</td>
                <td>{(100 - o.unemployment_pct).toFixed(0)}%</td>
                <td>{(o.trust * 100).toFixed(0)}</td>
                <td>{o.debt_gdp.toFixed(1)}×</td>
                <td>{o.poverty_pct.toFixed(0)}%</td>
                <td>{happy}% 😊</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function MultiCountryChart({ countries, field }: { countries: CountryReport[]; field: string }) {
  const series = countries.filter((c) => c.trajectory.length > 1);
  if (!series.length) return null;
  const maxLen = Math.max(...series.map((c) => c.trajectory.length));
  const allVals = series.flatMap((c) => c.trajectory.map((r) => Number(r[field] ?? 0)));
  const min = Math.min(...allVals);
  const max = Math.max(...allVals);
  const range = max - min || 1;
  const colors = ["#58d68d", "#5dade2", "#e74c3c", "#f4d03f", "#bb8fce", "#48c9b0"];

  return (
    <div className="multi-chart">
      <svg viewBox={`0 0 ${maxLen * 10} 100`} preserveAspectRatio="none">
        {series.map((c, idx) => {
          const pts = c.trajectory
            .map((r, i) => {
              const v = Number(r[field] ?? 0);
              const x = i * 10;
              const y = 95 - ((v - min) / range) * 85;
              return `${x},${y}`;
            })
            .join(" ");
          return (
            <polyline
              key={c.agent_id}
              points={pts}
              fill="none"
              stroke={colors[idx % colors.length]}
              strokeWidth="2.5"
              vectorEffect="non-scaling-stroke"
            />
          );
        })}
      </svg>
      <div className="multi-chart-legend">
        {series.map((c, idx) => (
          <span key={c.agent_id} style={{ color: colors[idx % colors.length] }}>
            ■ {c.country_name}
          </span>
        ))}
      </div>
    </div>
  );
}

export function HeadToHead({ bench }: { bench: { summary?: { best_baseline?: { agent: string; robust_score: number }; head_to_head?: Array<{ model: string; vs_baseline: string; score_delta: number; won: boolean }> } } }) {
  const h2h = bench.summary?.head_to_head;
  const best = bench.summary?.best_baseline;
  if (!h2h?.length) return null;
  return (
    <div className="h2h-panel">
      <h3>LLM vs best baseline ({best?.agent ?? "—"} @ {best?.robust_score?.toFixed(1)})</h3>
      <ul>
        {h2h.map((h) => (
          <li key={h.model} className={h.won ? "won" : "lost"}>
            <strong>{h.model}</strong>{" "}
            {h.won ? "▲" : "▼"} {Math.abs(h.score_delta).toFixed(1)} pts
          </li>
        ))}
      </ul>
    </div>
  );
}
