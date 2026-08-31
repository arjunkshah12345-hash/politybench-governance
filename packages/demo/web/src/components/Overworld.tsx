import type { CountryReport } from "../types";

const PLACES: Array<{ top: string; left: string }> = [
  { top: "18%", left: "12%" },
  { top: "22%", left: "48%" },
  { top: "38%", left: "72%" },
  { top: "52%", left: "22%" },
  { top: "58%", left: "55%" },
  { top: "28%", left: "32%" },
];

export function OverworldMap({
  countries,
  selectedId,
  onSelect,
}: {
  countries: CountryReport[];
  selectedId: string;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="overworld">
      <div className="overworld-sea">
        <div className="ow-wave w1" />
        <div className="ow-wave w2" />
        {countries.map((c, i) => {
          const pos = PLACES[i % PLACES.length];
          const o = c.overview;
          const crisis = o.debt_gdp > 1.5 || o.unemployment_pct > 15;
          return (
            <button
              key={c.agent_id}
              type="button"
              className={`ow-island terrain-${c.terrain} ${selectedId === c.agent_id ? "selected" : ""} ${crisis ? "crisis" : ""}`}
              style={pos}
              onClick={() => onSelect(c.agent_id)}
            >
              <span className="ow-flag" style={{ background: `linear-gradient(180deg, ${c.flag[0]} 50%, ${c.flag[2] || c.flag[0]} 50%)` }} />
              <span className="ow-sprite">{c.sprite}</span>
              <span className="ow-name">{c.country_name}</span>
              <span className="ow-rank">#{c.rank} · {c.evaluation.robust_score_single.toFixed(0)}</span>
            </button>
          );
        })}
        <div className="ow-compass">N</div>
      </div>
      <p className="ow-hint">Click an island to open that nation's term replay</p>
    </div>
  );
}

export function NewsTicker({
  countries,
  month,
}: {
  countries: CountryReport[];
  month: number;
}) {
  const items = countries.flatMap((c) => {
    const ev = c.timeline.filter((e) => Number(e.month) === month);
    if (ev.length) return ev.map((e) => `${c.sprite} ${c.country_name}: ${e.label}`);
    const snap = c.trajectory[Math.min(month, c.trajectory.length - 1)];
    if (!snap) return [];
    const u = Number(snap.unemployment || 0);
    const d = Number(snap.debt_gdp || 0);
    if (u > 0.16) return [`${c.sprite} ${c.country_name}: unemployment ${ (u * 100).toFixed(0)}%`];
    if (d > 1.6) return [`${c.sprite} ${c.country_name}: debt ${d.toFixed(1)}× GDP`];
    return [];
  });
  const line =
    items.length > 0
      ? items.join("   ★   ")
      : "Cabinet wire: no major incidents this month · markets wait · citizens go to work";

  return (
    <div className="news-ticker" aria-live="polite">
      <span className="ticker-label">WIRE</span>
      <div className="ticker-track">
        <div className="ticker-text">{line}   ★   {line}</div>
      </div>
    </div>
  );
}

export function TermEndSplash({
  country,
  onClose,
}: {
  country: CountryReport;
  onClose: () => void;
}) {
  return (
    <div className="term-splash" role="dialog">
      <div className="term-card">
        <p className="sample-badge">TERM COMPLETE</p>
        <h2>
          {country.sprite} {country.country_name}
        </h2>
        <p className="term-grade">
          Grade {country.grade} · Rank #{country.rank} · {country.evaluation.robust_score_single.toFixed(1)}
        </p>
        <p>{narrativeForStatic(country)}</p>
        <button type="button" className="pixel-btn active" onClick={onClose}>
          Continue
        </button>
      </div>
    </div>
  );
}

function narrativeForStatic(c: CountryReport): string {
  const o = c.overview;
  const bits = [];
  if (c.rank === 1) bits.push("This executive led the cohort.");
  if (o.debt_gdp > 1.8) bits.push("The books did not close cleanly.");
  if (o.unemployment_pct > 16) bits.push("Jobs never fully recovered.");
  if (o.trust > 0.8) bits.push("Trust held — rare in this scenario.");
  return bits.join(" ") || "The term is over. Score the record, not the speech.";
}

export function DuelWinner({
  left,
  right,
  onClose,
}: {
  left: CountryReport;
  right: CountryReport;
  onClose: () => void;
}) {
  const winner = left.evaluation.robust_score_single >= right.evaluation.robust_score_single ? left : right;
  const loser = winner.agent_id === left.agent_id ? right : left;
  const delta = Math.abs(left.evaluation.robust_score_single - right.evaluation.robust_score_single);
  return (
    <div className="term-splash" role="dialog">
      <div className="term-card">
        <p className="sample-badge">DUEL RESULT</p>
        <h2>
          {winner.sprite} {winner.country_name} wins
        </h2>
        <p>
          {winner.evaluation.robust_score_single.toFixed(1)} vs {loser.evaluation.robust_score_single.toFixed(1)} · Δ{" "}
          {delta.toFixed(1)}
        </p>
        <button type="button" className="pixel-btn active" onClick={onClose}>
          Close
        </button>
      </div>
    </div>
  );
}
