import { useEffect, useMemo, useRef, useState } from "react";
import type { CountryReport } from "../types";
import { VoxelTown, MonthScrubber } from "./VoxelTown";
import { MoodBar } from "./CitizenGrid";
import { duelCallout, narrativeFor } from "./Narrative";
import { ComboMeter, FloatingDeltas } from "./Fx";
import { dayPhase, weatherFor } from "./Life";
import { Gauge, DualRadar } from "./Stage";

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
  leading,
}: {
  country: CountryReport;
  month: number;
  side: "left" | "right";
  leading: boolean;
}) {
  const snap = country.trajectory[Math.min(month, Math.max(0, country.trajectory.length - 1))] || {};
  const prev = country.trajectory[Math.max(0, month - 1)] || {};
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
    <div className={`arena-panel side-${side} rank-${country.rank} ${leading ? "leading" : ""}`}>
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

      <div className="arena-town-wrap">
        <VoxelTown
          terrain={country.terrain}
          damage={damage}
          trust={trust}
          unemployment={unemp}
          poverty={poverty}
          debtGdp={debt}
          calendarMonth={Number(snap.month || 6)}
          dayPhase={dayPhase(month)}
          weather={weatherFor(Number(snap.month || 6), country.timeline, month)}
        />
        <FloatingDeltas prev={prev} next={snap} />
        {leading && <span className="lead-crown">👑 LEAD</span>}
      </div>

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

function liveUtility(c: CountryReport, month: number): number {
  const snap = c.trajectory[Math.min(month, Math.max(0, c.trajectory.length - 1))] || {};
  const u = 1 - Number(snap.unemployment ?? 0.1);
  const t = Number(snap.trust ?? 0.5);
  const d = Math.max(0, 2 - Number(snap.debt_gdp ?? 1)) / 2;
  const g0 = Number(c.trajectory[0]?.gdp || 1);
  const g = Number(snap.gdp || g0) / Math.max(g0, 1e-9);
  return Math.max(0, Math.min(1, 0.35 * g + 0.25 * u + 0.25 * t + 0.15 * d));
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

  const leftLive = liveUtility(left, month);
  const rightLive = liveUtility(right, month);
  const leftLeading = leftLive >= rightLive;
  const raceSum = leftLive + rightLive || 1;
  const leftRace = (leftLive / raceSum) * 100;

  const [streak, setStreak] = useState(0);
  const [streakSide, setStreakSide] = useState<"left" | "right">("left");
  const prevLead = useRef<"left" | "right" | null>(null);

  useEffect(() => {
    const lead: "left" | "right" = leftLeading ? "left" : "right";
    if (prevLead.current === null) {
      prevLead.current = lead;
      setStreak(1);
      setStreakSide(lead);
      return;
    }
    if (prevLead.current === lead) {
      setStreak((s) => s + 1);
    } else {
      prevLead.current = lead;
      setStreak(1);
      setStreakSide(lead);
    }
  }, [month, leftLeading]);

  const callout = duelCallout(left, right, month);
  const streakNation = streakSide === "left" ? left.country_name : right.country_name;

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
            prevLead.current = null;
            setStreak(0);
          }}
        >
          ↺ Start
        </button>
        <span className="muted">
          Month {month}/{maxMonth} · space to play · ← → scrub
        </span>
        <ComboMeter streak={streak} label={`${streakNation} hold`} />
      </div>

      <div className="duel-race">
        <span>{left.sprite}</span>
        <div className="race-track">
          <div className="race-left" style={{ width: `${leftRace}%` }} />
          <span className="race-mid">LIVE SCORE</span>
        </div>
        <span>{right.sprite}</span>
      </div>
      <div className="duel-race-nums">
        <strong>{(leftLive * 100).toFixed(0)}</strong>
        <span>composite health</span>
        <strong>{(rightLive * 100).toFixed(0)}</strong>
      </div>

      <div className="duel-tug">
        <span>{left.sprite}</span>
        <div className="tug-track">
          <div className="tug-left" style={{ width: `${leftShare}%` }} />
        </div>
        <span>{right.sprite}</span>
      </div>
      <p className="tug-label">GDP tug-of-war</p>

      <div className="duel-callout" key={month}>
        {callout}
      </div>

      <DualRadar left={left.evaluation.dims} right={right.evaluation.dims} />

      <div className="duel-grid">
        <NationArenaPanel country={left} month={month} side="left" leading={leftLeading} />
        <div className="duel-vs">VS</div>
        <NationArenaPanel country={right} month={month} side="right" leading={!leftLeading} />
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
  const u = Number(snap.unemployment ?? 0);
  const debt = Number(snap.debt_gdp ?? 0);
  const trust = Number(snap.trust ?? 0);
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
      <div className="hud-gauges">
        <Gauge label="U%" value={u} max={0.3} warnAt={0.14} format={(v) => `${(v * 100).toFixed(0)}`} />
        <Gauge label="DEBT" value={debt} max={2.5} warnAt={1.5} format={(v) => `${v.toFixed(1)}×`} />
        <Gauge label="TRUST" value={trust} max={1} warnAt={0.4} invertWarn format={(v) => `${(v * 100).toFixed(0)}`} />
      </div>
    </div>
  );
}
