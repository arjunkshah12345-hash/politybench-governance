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

export function Podium({ countries }: { countries: CountryReport[] }) {
  const top = [...countries].sort((a, b) => a.rank - b.rank).slice(0, 3);
  if (top.length < 2) return null;
  const order = top.length >= 3 ? [top[1], top[0], top[2]] : top;
  return (
    <div className="podium">
      {order.map((c) => (
        <div key={c.agent_id} className={`podium-slot rank-${c.rank}`}>
          <span className="podium-sprite">{c.sprite}</span>
          <strong>{c.country_name}</strong>
          <span className="podium-score">{c.evaluation.robust_score_single.toFixed(1)}</span>
          <div className="podium-block">#{c.rank}</div>
        </div>
      ))}
    </div>
  );
}
