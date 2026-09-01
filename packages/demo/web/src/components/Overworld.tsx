import type { CountryReport } from "../types";
import { useState } from "react";
import { CountUp, ParticleBurst } from "./Fx";
import { AchievementBadges, HighlightReel } from "./Life";
import { narrativeFor } from "./Narrative";

const PLACES: Array<{ top: string; left: string }> = [
  { top: "18%", left: "12%" },
  { top: "22%", left: "48%" },
  { top: "38%", left: "72%" },
  { top: "52%", left: "22%" },
  { top: "58%", left: "55%" },
  { top: "28%", left: "32%" },
];

function MiniPath({ traj }: { traj: Array<Record<string, number>> }) {
  const vals = traj.map((r) => Number(r.gdp ?? 0));
  if (vals.length < 2) return null;
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const range = max - min || 1;
  const pts = vals
    .map((v, i) => {
      const x = (i / (vals.length - 1)) * 40;
      const y = 14 - ((v - min) / range) * 12;
      return `${x},${y}`;
    })
    .join(" ");
  return (
    <svg className="ow-path" viewBox="0 0 40 16" aria-hidden>
      <polyline points={pts} fill="none" stroke="#ffe566" strokeWidth="1.5" />
    </svg>
  );
}

export function OverworldMap({
  countries,
  selectedId,
  onSelect,
}: {
  countries: CountryReport[];
  selectedId: string;
  onSelect: (id: string) => void;
}) {
  const [boat, setBoat] = useState<{ top: string; left: string } | null>(null);

  const sailTo = (id: string, pos: { top: string; left: string }) => {
    setBoat(pos);
    setTimeout(() => {
      setBoat(null);
      onSelect(id);
    }, 650);
  };

  return (
    <div className="overworld">
      <div className="overworld-sea">
        <div className="ow-wave w1" />
        <div className="ow-wave w2" />
        <svg className="ow-rivals" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden>
          {(() => {
            const ranked = [...countries].sort((a, b) => a.rank - b.rank).slice(0, 3);
            if (ranked.length < 2) return null;
            const posOf = (id: string) => {
              const idx = countries.findIndex((c) => c.agent_id === id);
              return PLACES[Math.max(0, idx) % PLACES.length];
            };
            const champ = posOf(ranked[0].agent_id);
            return ranked.slice(1).map((c) => {
              const b = posOf(c.agent_id);
              return (
                <line
                  key={c.agent_id}
                  x1={parseFloat(champ.left)}
                  y1={parseFloat(champ.top)}
                  x2={parseFloat(b.left)}
                  y2={parseFloat(b.top)}
                  className="ow-rival-line"
                />
              );
            });
          })()}
        </svg>
        {boat && (
          <span className="ow-boat" style={boat} aria-hidden>
            ⛵
          </span>
        )}
        {countries.map((c, i) => {
          const pos = PLACES[i % PLACES.length];
          const o = c.overview;
          const crisis = o.debt_gdp > 1.5 || o.unemployment_pct > 15;
          const boom = o.trust > 0.7 && o.unemployment_pct < 10;
          return (
            <button
              key={c.agent_id}
              type="button"
              className={`ow-island terrain-${c.terrain} ${selectedId === c.agent_id ? "selected" : ""} ${crisis ? "crisis" : ""} ${boom ? "boom" : ""}`}
              style={pos}
              onClick={() => sailTo(c.agent_id, pos)}
              disabled={!!boat}
            >
              <span className="ow-flag" style={{ background: `linear-gradient(180deg, ${c.flag[0]} 50%, ${c.flag[2] || c.flag[0]} 50%)` }} />
              <span className="ow-sprite">{c.sprite}</span>
              <span className="ow-name">{c.country_name}</span>
              <span className="ow-rank">
                #{c.rank} · {c.evaluation.robust_score_single.toFixed(0)}
              </span>
              <MiniPath traj={c.trajectory} />
            </button>
          );
        })}
        <div className="ow-compass">N</div>
      </div>
      <p className="ow-hint">Gold dashed lines = top-3 rivalry · sail to replay a term</p>
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
    const t = Number(snap.trust || 0);
    if (u > 0.16) return [`${c.sprite} ${c.country_name}: unemployment ${(u * 100).toFixed(0)}%`];
    if (d > 1.6) return [`${c.sprite} ${c.country_name}: debt ${d.toFixed(1)}× GDP`];
    if (t < 0.35) return [`${c.sprite} ${c.country_name}: trust freefall`];
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
        <div className="ticker-text">
          {line}   ★   {line}
        </div>
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
        <ParticleBurst active kind="confetti" />
        <p className="sample-badge">TERM COMPLETE</p>
        <h2>
          {country.sprite} {country.country_name}
        </h2>
        <p className="term-grade">
          Grade {country.grade} · Rank #{country.rank} ·{" "}
          <CountUp value={country.evaluation.robust_score_single} /> robust
        </p>
        <p>{narrativeFor(country)}</p>
        <div className="term-stats">
          <span>GDP {country.overview.gdp_index}%</span>
          <span>U {country.overview.unemployment_pct.toFixed(1)}%</span>
          <span>Trust {(country.overview.trust * 100).toFixed(0)}</span>
          <span>Debt {country.overview.debt_gdp.toFixed(2)}×</span>
        </div>
        <HighlightReel country={country} />
        <AchievementBadges country={country} />
        <button type="button" className="pixel-btn active" onClick={onClose}>
          Continue
        </button>
      </div>
    </div>
  );
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
  const winner =
    left.evaluation.robust_score_single >= right.evaluation.robust_score_single ? left : right;
  const loser = winner.agent_id === left.agent_id ? right : left;
  const delta = Math.abs(left.evaluation.robust_score_single - right.evaluation.robust_score_single);
  return (
    <div className="term-splash" role="dialog">
      <div className="term-card">
        <ParticleBurst active kind="confetti" />
        <p className="sample-badge">DUEL RESULT</p>
        <h2>
          {winner.sprite} {winner.country_name} wins
        </h2>
        <p className="term-grade">
          <CountUp value={winner.evaluation.robust_score_single} /> vs{" "}
          <CountUp value={loser.evaluation.robust_score_single} /> · Δ {delta.toFixed(1)}
        </p>
        <p>{narrativeFor(winner)}</p>
        <AchievementBadges country={winner} />
        <button type="button" className="pixel-btn active" onClick={onClose}>
          Close
        </button>
      </div>
    </div>
  );
}
