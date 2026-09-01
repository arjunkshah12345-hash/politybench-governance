import type { CountryReport } from "../types";

export function narrativeFor(c: CountryReport): string {
  const o = c.overview;
  const parts: string[] = [];
  if (c.rank === 1) parts.push("Top performer this run.");
  else if (c.rank <= 3) parts.push("Solid mid-pack governance.");
  else parts.push("Struggled relative to peers.");

  if (o.debt_gdp > 1.8) parts.push("Debt ballooned past crisis levels.");
  else if (o.debt_gdp > 1.4) parts.push("Debt remains elevated.");
  else parts.push("Debt stayed contained.");

  if (o.unemployment_pct > 16) parts.push("Jobs market is badly strained.");
  else if (o.unemployment_pct > 12) parts.push("Unemployment is elevated.");
  else parts.push("Labor market held up.");

  if (o.trust > 0.8) parts.push("Institutional trust is surprisingly high.");
  else if (o.trust < 0.4) parts.push("Trust has collapsed.");

  if (o.poverty_pct > 40) parts.push("Poverty is severe.");
  else if (o.poverty_pct > 20) parts.push("Poverty rose under the crisis.");

  if (c.integrity.hard_violations > 0) parts.push("Hard legal violations recorded.");
  if (c.integrity.llm_calls > 0) parts.push(`Issued ${c.integrity.llm_calls} LLM policy decisions.`);

  return parts.join(" ");
}

/** Live month-by-month duel callout. */
export function duelCallout(left: CountryReport, right: CountryReport, month: number): string {
  const ls = left.trajectory[Math.min(month, left.trajectory.length - 1)] || {};
  const rs = right.trajectory[Math.min(month, right.trajectory.length - 1)] || {};
  const l0 = Number(left.trajectory[0]?.gdp || 1);
  const r0 = Number(right.trajectory[0]?.gdp || 1);
  const lIdx = Number(ls.gdp || l0) / Math.max(l0, 1e-9);
  const rIdx = Number(rs.gdp || r0) / Math.max(r0, 1e-9);
  const gap = Math.abs(lIdx - rIdx);
  if (gap < 0.01) return "Dead heat on GDP — cabinets sweat.";
  const lead = lIdx > rIdx ? left : right;
  const trail = lead.agent_id === left.agent_id ? right : left;
  if (gap > 0.08) return `${lead.sprite} ${lead.country_name} pulls away — ${trail.country_name} is bleeding output.`;
  return `${lead.sprite} ${lead.country_name} edges ahead · Δ${(gap * 100).toFixed(0)}pp GDP`;
}

export function Podium({ countries }: { countries: CountryReport[] }) {
  const top = [...countries].sort((a, b) => a.rank - b.rank).slice(0, 3);
  if (top.length < 2) return null;
  const order = top.length >= 3 ? [top[1], top[0], top[2]] : top;
  return (
    <div className="podium podium-enter">
      {order.map((c, i) => (
        <div
          key={c.agent_id}
          className={`podium-slot rank-${c.rank}`}
          style={{ animationDelay: `${i * 0.12}s` }}
        >
          <span className="podium-sprite">{c.sprite}</span>
          <strong>{c.country_name}</strong>
          <span className="podium-score">{c.evaluation.robust_score_single.toFixed(1)}</span>
          <div className="podium-block">#{c.rank}</div>
        </div>
      ))}
    </div>
  );
}
