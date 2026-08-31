import { useMemo } from "react";
import type { CountryReport } from "../types";
import { VoxelTown, MonthScrubber } from "./VoxelTown";
import { MoodBar } from "./CitizenGrid";
import { narrativeFor } from "./Narrative";

function LiveStat({ label, value, warn }: { label: string; value: string; warn?: boolean }) {
  return (
    <div className={`live-stat ${warn ? "warn" : ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function NationArenaPanel({
  country,
  month,
  side,
}: {
  country: CountryReport;
  month: number;
  side: "left" | "right";
}) {
  const snap = country.trajectory[Math.min(month, Math.max(0, country.trajectory.length - 1))] || {};
  const unemp = Number(snap.unemployment ?? country.overview.unemployment_pct / 100);
  const trust = Number(snap.trust ?? country.overview.trust);
  const debt = Number(snap.debt_gdp ?? country.overview.debt_gdp);
  const damage = Number(snap.damage ?? country.overview.damage);
  const poverty = Number(snap.poverty ?? country.overview.poverty_pct / 100);
  const gdp0 = Number(country.trajectory[0]?.gdp || 1);
  const gdpNow = Number(snap.gdp || gdp0);
  const gdpIdx = (gdpNow / Math.max(gdp0, 1e-9)) * 100;

  const eventNow = country.timeline.find((e) => Number(e.month) === month);

  return (
    <div className={`arena-panel side-${side} rank-${country.rank}`}>
      <div className="arena-head">
        <span className="arena-sprite">{country.sprite}</span>
        <div>
          <h3>{country.country_name}</h3>
          <p>
            {country.model} · grade {country.grade} · #{country.rank}
          </p>
        </div>
        <div className="arena-score">{country.evaluation.robust_score_single.toFixed(1)}</div>
      </div>

      <VoxelTown
        terrain={country.terrain}
        damage={damage}
        trust={trust}
        unemployment={unemp}
        poverty={poverty}
        debtGdp={debt}
      />

      <div className="live-stat-row">
        <LiveStat label="GDP" value={`${gdpIdx.toFixed(0)}%`} warn={gdpIdx < 85} />
        <LiveStat label="Jobs" value={`${((1 - unemp) * 100).toFixed(0)}%`} warn={unemp > 0.14} />
        <LiveStat label="Trust" value={`${(trust * 100).toFixed(0)}`} warn={trust < 0.4} />
        <LiveStat label="Debt" value={`${debt.toFixed(2)}×`} warn={debt > 1.4} />
      </div>

      <MoodBar summary={country.mood_summary || {}} />

      {eventNow && (
        <div className={`arena-event evt-${eventNow.type}`}>⚡ {eventNow.label}</div>
      )}

      <p className="arena-blurb">{narrativeFor(country)}</p>
    </div>
  );
}

export function DuelArena({
  left,
  right,
  month,
  onMonthChange,
  playing,
  onTogglePlay,
}: {
  left: CountryReport;
  right: CountryReport;
  month: number;
  onMonthChange: (m: number) => void;
  playing: boolean;
  onTogglePlay: () => void;
}) {
  const maxMonth = useMemo(
    () => Math.max(left.trajectory.length, right.trajectory.length) - 1,
    [left, right]
  );
  const traj = left.trajectory.length >= right.trajectory.length ? left.trajectory : right.trajectory;

  const leftSnap = left.trajectory[Math.min(month, left.trajectory.length - 1)];
  const rightSnap = right.trajectory[Math.min(month, right.trajectory.length - 1)];
  const leftGdp = Number(leftSnap?.gdp || 0);
  const rightGdp = Number(rightSnap?.gdp || 0);
  const sum = leftGdp + rightGdp || 1;
  const leftShare = (leftGdp / sum) * 100;

  return (
    <div className="duel-arena">
      <div className="duel-controls">
        <button type="button" className="pixel-btn active" onClick={onTogglePlay}>
          {playing ? "❚❚ Pause" : "▶ Duel play"}
        </button>
        <button
          type="button"
          className="pixel-btn"
          onClick={() => {
            onMonthChange(0);
          }}
        >
          ↺ Start
        </button>
        <span className="muted">
          Month {month}/{maxMonth} · space to play · ← → scrub
        </span>
      </div>

      <div className="duel-tug">
        <span>{left.sprite}</span>
        <div className="tug-track">
          <div className="tug-left" style={{ width: `${leftShare}%` }} />
        </div>
        <span>{right.sprite}</span>
      </div>
      <p className="tug-label">GDP tug-of-war at this month</p>

      <div className="duel-grid">
        <NationArenaPanel country={left} month={month} side="left" />
        <div className="duel-vs">VS</div>
        <NationArenaPanel country={right} month={month} side="right" />
      </div>

      <MonthScrubber
        trajectory={traj}
        month={Math.min(month, traj.length - 1)}
        onChange={onMonthChange}
        events={[...left.timeline, ...right.timeline]}
      />
    </div>
  );
}

export function GameHUD({ country, month }: { country: CountryReport; month?: number }) {
  const idx = month ?? country.trajectory.length - 1;
  const snap = country.trajectory[Math.min(Math.max(0, idx), country.trajectory.length - 1)] || {};
  return (
    <div className="game-hud">
      <div className="hud-cell">
        <span>LEADER</span>
        <strong>
          {country.sprite} {country.country_name}
        </strong>
      </div>
      <div className="hud-cell">
        <span>SCORE</span>
        <strong>{country.evaluation.robust_score_single.toFixed(1)}</strong>
      </div>
      <div className="hud-cell">
        <span>U%</span>
        <strong>{(Number(snap.unemployment ?? 0) * 100).toFixed(1)}</strong>
      </div>
      <div className="hud-cell">
        <span>DEBT</span>
        <strong>{Number(snap.debt_gdp ?? 0).toFixed(2)}×</strong>
      </div>
      <div className="hud-cell">
        <span>TRUST</span>
        <strong>{(Number(snap.trust ?? 0) * 100).toFixed(0)}</strong>
      </div>
    </div>
  );
}
