import { useEffect, useMemo, useRef, useState } from "react";
import type { CountryReport } from "../types";

/** CRT boot splash — shows once per session. */
export function BootScreen({ onDone }: { onDone: () => void }) {
  const [phase, setPhase] = useState(0);
  useEffect(() => {
    const t1 = setTimeout(() => setPhase(1), 400);
    const t2 = setTimeout(() => setPhase(2), 1100);
    const t3 = setTimeout(() => onDone(), 2200);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
    };
  }, [onDone]);

  return (
    <div className={`boot-screen phase-${phase}`} role="dialog" onClick={onDone}>
      <div className="boot-scan" />
      <div className="boot-inner">
        {phase >= 0 && <p className="boot-line">POLITYBENCH BIOS v0.1</p>}
        {phase >= 1 && <p className="boot-line">Loading nation kernels… OK</p>}
        {phase >= 2 && (
          <>
            <h1 className="boot-title">
              POLITY<span>BENCH</span>
            </h1>
            <p className="boot-sub">country governance arena · press any key</p>
          </>
        )}
      </div>
    </div>
  );
}

export function KeyHelp({ open, onClose }: { open: boolean; onClose: () => void }) {
  if (!open) return null;
  return (
    <div className="key-help-backdrop" onClick={onClose} role="dialog">
      <div className="key-help" onClick={(e) => e.stopPropagation()}>
        <h3>Controls</h3>
        <ul>
          <li>
            <kbd>1</kbd>–<kbd>4</kbd> World / Duel / Board / Replay
          </li>
          <li>
            <kbd>Space</kbd> Play / pause term
          </li>
          <li>
            <kbd>←</kbd> <kbd>→</kbd> Scrub months
          </li>
          <li>
            <kbd>B</kbd> Bookmark current month
          </li>
          <li>
            <kbd>D</kbd> Director mode (event→event)
          </li>
          <li>
            <kbd>N</kbd> / <kbd>P</kbd> Next / prev event
          </li>
          <li>
            <kbd>H</kbd> Cinema mode (hide chrome)
          </li>
          <li>
            <kbd>M</kbd> Ambient hum
          </li>
          <li>
            <kbd>?</kbd> This help · click outside to close
          </li>
        </ul>
        <button type="button" className="pixel-btn active" onClick={onClose}>
          Got it
        </button>
      </div>
    </div>
  );
}

const BUBBLES: Record<string, string[]> = {
  happy: ["Payday!", "New bakery!", "Trust the cabinet?", "Kids in school"],
  neutral: ["Same old…", "Taxes due", "Markets quiet", "Coffee's cold"],
  worried: ["Rent's up", "Jobs drying", "Heard layoffs", "Debt clock…"],
  angry: ["Enough!", "Where's aid?", "Who decided?", "Protest Fri"],
  sick: ["Clinic wait", "Masks again?", "Can't work", "Fever week"],
  crisis: ["Shelves empty", "Banks closed?", "Power cut", "Stay indoors"],
  boom: ["Hiring!", "Festival!", "Crowded square", "GDP party?"],
};

export function CitizenBubbles({
  unemployment,
  trust,
  debtGdp,
  month,
}: {
  unemployment: number;
  trust: number;
  debtGdp: number;
  month: number;
}) {
  const crisis = debtGdp > 1.5 || unemployment > 0.15;
  const boom = trust > 0.7 && unemployment < 0.1;
  const mood = crisis ? "crisis" : boom ? "boom" : unemployment > 0.14 ? "worried" : trust < 0.4 ? "angry" : trust > 0.65 ? "happy" : "neutral";
  const pool = BUBBLES[mood] || BUBBLES.neutral;
  const shown = useMemo(() => {
    const a = pool[month % pool.length];
    const b = pool[(month + 2) % pool.length];
    return [
      { id: 0, text: a, side: "left" as const },
      { id: 1, text: b, side: "right" as const },
    ];
  }, [pool, month]);

  return (
    <div className="citizen-bubbles" key={month}>
      {shown.map((b) => (
        <span key={b.id} className={`speech-bubble side-${b.side}`}>
          {b.text}
        </span>
      ))}
    </div>
  );
}

export function PolicyFlash({
  country,
  month,
}: {
  country: CountryReport;
  month: number;
}) {
  const hit = (country.policy_log || []).find((p) => Number(p.month) === month);
  if (!hit) return null;
  return (
    <div className="policy-flash" key={`${month}-${hit.label}`}>
      <span className="pf-badge">{hit.source === "llm" ? "LLM" : "RULE"}</span>
      <div>
        <strong>Cabinet decision · M{month}</strong>
        <p>{hit.label}</p>
      </div>
    </div>
  );
}

export type Highlight = { month: number; kind: "peak" | "crash" | "crisis"; label: string; value: string };

export function computeHighlights(country: CountryReport): Highlight[] {
  const traj = country.trajectory;
  if (!traj.length) return [];
  const gdp0 = Number(traj[0]?.gdp || 1);
  let best = 0;
  let worst = 0;
  let bestV = -Infinity;
  let worstV = Infinity;
  traj.forEach((r, i) => {
    const idx = Number(r.gdp || gdp0) / Math.max(gdp0, 1e-9);
    if (idx > bestV) {
      bestV = idx;
      best = i;
    }
    if (idx < worstV) {
      worstV = idx;
      worst = i;
    }
  });
  const crisisEv = [...country.timeline].sort((a, b) => b.severity - a.severity)[0];
  const out: Highlight[] = [
    { month: best, kind: "peak", label: "GDP peak", value: `${(bestV * 100).toFixed(0)}%` },
    { month: worst, kind: "crash", label: "GDP trough", value: `${(worstV * 100).toFixed(0)}%` },
  ];
  if (crisisEv) {
    out.push({
      month: Number(crisisEv.month),
      kind: "crisis",
      label: crisisEv.label.slice(0, 42),
      value: `sev ${(crisisEv.severity * 100).toFixed(0)}`,
    });
  }
  return out;
}

export function HighlightReel({
  country,
  onJump,
}: {
  country: CountryReport;
  onJump?: (m: number) => void;
}) {
  const marks = computeHighlights(country);
  if (!marks.length) return null;
  return (
    <div className="highlight-reel">
      <h4>🎞️ Term highlights</h4>
      <div className="hl-row">
        {marks.map((h) => (
          <button
            key={`${h.kind}-${h.month}`}
            type="button"
            className={`hl-chip kind-${h.kind}`}
            onClick={() => onJump?.(h.month)}
            title={`Jump to month ${h.month}`}
          >
            <span className="hl-m">M{h.month}</span>
            <strong>{h.label}</strong>
            <small>{h.value}</small>
          </button>
        ))}
      </div>
    </div>
  );
}

/** Fake clock from scrub month → dawn / day / dusk / night. */
export function dayPhase(monthIndex: number): "dawn" | "day" | "dusk" | "night" {
  const slot = monthIndex % 4;
  return (["dawn", "day", "dusk", "night"] as const)[slot];
}

export function seasonOf(calendarMonth: number): "winter" | "spring" | "summer" | "autumn" {
  if (calendarMonth <= 2 || calendarMonth === 12) return "winter";
  if (calendarMonth <= 5) return "spring";
  if (calendarMonth <= 8) return "summer";
  return "autumn";
}

export function SeasonFlash({ calendarMonth }: { calendarMonth: number }) {
  const season = seasonOf(calendarMonth);
  const prev = useRef(season);
  const [flash, setFlash] = useState<string | null>(null);
  useEffect(() => {
    if (prev.current === season) return;
    prev.current = season;
    setFlash(season);
    const t = setTimeout(() => setFlash(null), 900);
    return () => clearTimeout(t);
  }, [season]);
  if (!flash) return null;
  return <div className={`season-flash season-${flash}`}>{flash.toUpperCase()}</div>;
}

export function Typewriter({ text, className = "" }: { text: string; className?: string }) {
  const [shown, setShown] = useState("");
  useEffect(() => {
    setShown("");
    let i = 0;
    const id = setInterval(() => {
      i += 1;
      setShown(text.slice(0, i));
      if (i >= text.length) clearInterval(id);
    }, 18);
    return () => clearInterval(id);
  }, [text]);
  return (
    <p className={`typewriter ${className}`}>
      {shown}
      <span className="tw-caret">▮</span>
    </p>
  );
}

export function LeaderPortrait({
  country,
  month,
}: {
  country: CountryReport;
  month: number;
}) {
  const snap = country.trajectory[Math.min(month, Math.max(0, country.trajectory.length - 1))] || {};
  const ev = country.timeline.find((e) => Number(e.month) === month);
  const policy = (country.policy_log || []).find((p) => Number(p.month) === month);
  const u = Number(snap.unemployment ?? 0);
  const t = Number(snap.trust ?? 0.5);
  let line: string;
  if (ev) line = `Address to the nation: ${ev.label}`;
  else if (policy) line = `Today we enact — ${policy.label}`;
  else if (u > 0.16) line = "Work remains scarce. We will not abandon the unemployed.";
  else if (t < 0.4) line = "I hear the anger in the streets. Trust must be rebuilt in deeds.";
  else if (t > 0.75) line = "Our institutions still hold. That is no small victory.";
  else line = `${country.motto}`;

  const face = u > 0.16 ? "😟" : t < 0.4 ? "😠" : t > 0.7 ? "🙂" : country.sprite;

  return (
    <div className="leader-portrait">
      <div className="lp-face" style={{ borderColor: country.flag[0] }}>
        <span>{face}</span>
        <small>{country.leader_title}</small>
      </div>
      <div className="lp-speech">
        <strong>
          {country.sprite} {country.country_name}
        </strong>
        <Typewriter text={line} />
      </div>
    </div>
  );
}

export type Achievement = { id: string; icon: string; title: string; desc: string };

export function computeAchievements(country: CountryReport): Achievement[] {
  const o = country.overview;
  const out: Achievement[] = [];
  if (country.rank === 1) out.push({ id: "champ", icon: "🏆", title: "Champion", desc: "Best robust score this cohort" });
  if (country.grade === "A" || country.grade === "A+")
    out.push({ id: "grade", icon: "📜", title: "Honor roll", desc: `Grade ${country.grade}` });
  if (o.trust > 0.8) out.push({ id: "trust", icon: "🤝", title: "Trusted", desc: "Institutional trust > 80" });
  if (o.debt_gdp < 1.2) out.push({ id: "books", icon: "📗", title: "Balanced books", desc: "Debt kept under 1.2× GDP" });
  if (o.unemployment_pct < 10) out.push({ id: "jobs", icon: "⚒️", title: "Full streets", desc: "Unemployment under 10%" });
  if (o.debt_gdp > 1.8) out.push({ id: "debt", icon: "📉", title: "Debt spiral", desc: "Debt past 1.8× GDP" });
  if (o.unemployment_pct > 16) out.push({ id: "idle", icon: "🏚️", title: "Idle generation", desc: "Joblessness above 16%" });
  if (country.integrity.llm_calls > 0)
    out.push({ id: "llm", icon: "🤖", title: "LLM executive", desc: `${country.integrity.llm_calls} model decisions` });
  if (country.integrity.hard_violations === 0)
    out.push({ id: "clean", icon: "⚖️", title: "Clean record", desc: "No hard legal violations" });
  if (o.poverty_pct < 15) out.push({ id: "fair", icon: "🍞", title: "Bread line short", desc: "Poverty contained" });
  return out.slice(0, 6);
}

export function AchievementBadges({ country }: { country: CountryReport }) {
  const badges = computeAchievements(country);
  if (!badges.length) return null;
  return (
    <div className="achievements">
      <h4>🎖️ Unlocked</h4>
      <div className="ach-row">
        {badges.map((b) => (
          <div key={b.id} className="ach-badge" title={b.desc}>
            <span className="ach-icon">{b.icon}</span>
            <strong>{b.title}</strong>
            <small>{b.desc}</small>
          </div>
        ))}
      </div>
    </div>
  );
}

/** Mood mix inferred from live macro (scrub-reactive). */
export function liveMoodSummary(unemployment: number, trust: number, debtGdp: number): Record<string, number> {
  let happy = Math.max(0, trust * 0.55 - unemployment * 0.8);
  let angry = Math.max(0, (1 - trust) * 0.4 + Math.max(0, unemployment - 0.12) * 1.2);
  let worried = Math.max(0, unemployment * 0.9 + Math.max(0, debtGdp - 1.2) * 0.25);
  let sick = Math.max(0, (debtGdp > 1.7 ? 0.08 : 0) + (unemployment > 0.18 ? 0.06 : 0));
  let neutral = Math.max(0.05, 1 - happy - angry - worried - sick);
  const sum = happy + angry + worried + sick + neutral || 1;
  return {
    happy: happy / sum,
    neutral: neutral / sum,
    worried: worried / sum,
    angry: angry / sum,
    sick: sick / sum,
  };
}

export function Bookmarks({
  marks,
  onJump,
  onClear,
}: {
  marks: number[];
  onJump: (m: number) => void;
  onClear: () => void;
}) {
  if (!marks.length) return null;
  return (
    <div className="bookmarks">
      <span className="bm-label">★ Bookmarks</span>
      {marks.map((m) => (
        <button key={m} type="button" className="pixel-btn" onClick={() => onJump(m)}>
          M{m}
        </button>
      ))}
      <button type="button" className="pixel-btn" onClick={onClear}>
        clear
      </button>
    </div>
  );
}

export function weatherFor(
  calendarMonth: number,
  timeline: Array<{ month: number; type: string; severity: number }>,
  monthIndex: number
): "clear" | "rain" | "storm" | "snow" {
  const hit = timeline.find((e) => Number(e.month) === monthIndex);
  if (hit && (hit.type === "disaster" || hit.severity >= 0.7)) return "storm";
  if (hit && hit.type === "epidemic") return "rain";
  const season = seasonOf(calendarMonth);
  if (season === "winter") return "snow";
  if (season === "autumn" && monthIndex % 5 === 0) return "rain";
  return "clear";
}
