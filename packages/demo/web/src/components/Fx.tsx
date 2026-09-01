import { useEffect, useRef, useState, type CSSProperties } from "react";

/** Tiny Web Audio blips — no assets required. */
export function playBeep(kind: "tick" | "event" | "win" | "warn" = "tick", muted = false) {
  if (muted || typeof window === "undefined") return;
  try {
    const Ctx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    const ctx = new Ctx();
    const o = ctx.createOscillator();
    const g = ctx.createGain();
    o.connect(g);
    g.connect(ctx.destination);
    const now = ctx.currentTime;
    if (kind === "tick") {
      o.frequency.value = 520;
      g.gain.setValueAtTime(0.03, now);
      g.gain.exponentialRampToValueAtTime(0.001, now + 0.06);
      o.start(now);
      o.stop(now + 0.07);
    } else if (kind === "event") {
      o.type = "square";
      o.frequency.value = 280;
      g.gain.setValueAtTime(0.05, now);
      g.gain.exponentialRampToValueAtTime(0.001, now + 0.18);
      o.start(now);
      o.stop(now + 0.2);
    } else if (kind === "warn") {
      o.type = "sawtooth";
      o.frequency.value = 160;
      g.gain.setValueAtTime(0.04, now);
      g.gain.exponentialRampToValueAtTime(0.001, now + 0.25);
      o.start(now);
      o.stop(now + 0.26);
    } else {
      o.type = "triangle";
      o.frequency.setValueAtTime(440, now);
      o.frequency.linearRampToValueAtTime(880, now + 0.2);
      g.gain.setValueAtTime(0.05, now);
      g.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
      o.start(now);
      o.stop(now + 0.36);
    }
    setTimeout(() => ctx.close().catch(() => undefined), 500);
  } catch {
    /* ignore autoplay blocks */
  }
}

export type Toast = { id: number; text: string; kind: string };

export function ToastStack({ toasts }: { toasts: Toast[] }) {
  return (
    <div className="toast-stack">
      {toasts.map((t) => (
        <div key={t.id} className={`toast toast-${t.kind}`}>
          {t.text}
        </div>
      ))}
    </div>
  );
}

export function useToasts() {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const idRef = useRef(0);
  const push = (text: string, kind = "info") => {
    const id = ++idRef.current;
    setToasts((t) => [...t.slice(-4), { id, text, kind }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 2800);
  };
  return { toasts, push };
}

export function FloatingDeltas({
  prev,
  next,
}: {
  prev?: Record<string, number>;
  next?: Record<string, number>;
}) {
  const [flashes, setFlashes] = useState<Array<{ id: number; label: string; up: boolean }>>([]);
  const idRef = useRef(0);
  const monthKey = next?.month ?? -1;

  useEffect(() => {
    if (!prev || !next || monthKey < 0) return;
    const checks: Array<[string, string, number]> = [
      ["unemployment", "Jobs", -1],
      ["trust", "Trust", 1],
      ["debt_gdp", "Debt", -1],
      ["gdp", "GDP", 1],
    ];
    const out: Array<{ id: number; label: string; up: boolean }> = [];
    for (const [key, label, goodDir] of checks) {
      const a = Number(prev[key] ?? 0);
      const b = Number(next[key] ?? 0);
      const d = b - a;
      if (Math.abs(d) < 0.002) continue;
      const up = goodDir > 0 ? d > 0 : d < 0;
      out.push({ id: ++idRef.current, label: `${label} ${d > 0 ? "▲" : "▼"}`, up });
    }
    if (!out.length) return;
    setFlashes(out);
    const t = setTimeout(() => setFlashes([]), 900);
    return () => clearTimeout(t);
  }, [monthKey]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!flashes.length) return null;
  return (
    <div className="float-deltas">
      {flashes.map((f) => (
        <span key={f.id} className={f.up ? "up" : "down"}>
          {f.label}
        </span>
      ))}
    </div>
  );
}

export function CabinetQuestLog({
  policyLog,
  timeline,
  month,
}: {
  policyLog?: Array<{ month?: number; source: string; label: string }>;
  timeline: Array<{ month: number; type: string; label: string }>;
  month: number;
}) {
  const items = [
    ...timeline
      .filter((e) => Number(e.month) <= month)
      .map((e) => ({
        key: `e-${e.month}-${e.type}`,
        icon: e.type === "disaster" ? "💥" : e.type === "fiscal" ? "📉" : e.type === "epidemic" ? "🦠" : "📌",
        title: e.label,
        meta: `M${e.month}`,
        done: Number(e.month) < month,
        active: Number(e.month) === month,
      })),
    ...(policyLog || [])
      .filter((p) => (p.month ?? 0) <= month)
      .slice(-6)
      .map((p, i) => ({
        key: `p-${i}-${p.month}`,
        icon: p.source === "llm" ? "🤖" : "📜",
        title: p.label,
        meta: `M${p.month ?? "?"} · ${p.source}`,
        done: true,
        active: false,
      })),
  ].slice(-10);

  return (
    <div className="quest-log">
      <h4>📜 Cabinet quest log</h4>
      <ul>
        {items.length === 0 && <li className="muted">No entries yet — play the term.</li>}
        {items.map((it) => (
          <li key={it.key} className={`${it.done ? "done" : ""} ${it.active ? "active" : ""}`}>
            <span>{it.icon}</span>
            <span>{it.title}</span>
            <small>{it.meta}</small>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function SpeedControl({
  speed,
  onChange,
}: {
  speed: number;
  onChange: (s: number) => void;
}) {
  return (
    <div className="speed-control">
      {[0.5, 1, 2, 4].map((s) => (
        <button
          key={s}
          type="button"
          className={`pixel-btn ${speed === s ? "active" : ""}`}
          onClick={() => onChange(s)}
        >
          {s}×
        </button>
      ))}
    </div>
  );
}

export function useScreenShake(trigger: number) {
  const [shaking, setShaking] = useState(false);
  useEffect(() => {
    if (!trigger) return;
    setShaking(true);
    const t = setTimeout(() => setShaking(false), 420);
    return () => clearTimeout(t);
  }, [trigger]);
  return shaking;
}

export function ParticleBurst({ active, kind = "confetti" }: { active: boolean; kind?: "confetti" | "sparks" }) {
  if (!active) return null;
  const n = kind === "confetti" ? 18 : 10;
  return (
    <div className={`particle-burst kind-${kind}`} aria-hidden>
      {Array.from({ length: n }).map((_, i) => (
        <span
          key={i}
          className="particle"
          style={
            {
              "--i": i,
              "--x": `${(i % 6) * 18 - 45}px`,
              "--rot": `${i * 40}deg`,
              animationDelay: `${i * 0.03}s`,
            } as CSSProperties
          }
        />
      ))}
    </div>
  );
}

export function MonthNarrator({
  country,
  month,
}: {
  country: {
    country_name: string;
    sprite: string;
    trajectory: Array<Record<string, number>>;
    timeline: Array<{ month: number; type: string; label: string }>;
    policy_log?: Array<{ month?: number; label: string; source: string }>;
  };
  month: number;
}) {
  const snap = country.trajectory[Math.min(month, Math.max(0, country.trajectory.length - 1))] || {};
  const prev = country.trajectory[Math.max(0, month - 1)] || snap;
  const ev = country.timeline.find((e) => Number(e.month) === month);
  const policy = (country.policy_log || []).find((p) => Number(p.month) === month);

  let line: string;
  if (ev) {
    line = `${country.sprite} Month ${month}: ${ev.label}`;
  } else if (policy) {
    line = `${country.sprite} Cabinet acts — ${policy.label}`;
  } else {
    const du = Number(snap.unemployment ?? 0) - Number(prev.unemployment ?? 0);
    const dt = Number(snap.trust ?? 0) - Number(prev.trust ?? 0);
    const dd = Number(snap.debt_gdp ?? 0) - Number(prev.debt_gdp ?? 0);
    if (du > 0.008) line = `${country.sprite} Joblessness creeps up — streets quiet.`;
    else if (du < -0.008) line = `${country.sprite} Hiring tick — shops reopen a little.`;
    else if (dt < -0.02) line = `${country.sprite} Trust frays in the provinces.`;
    else if (dt > 0.02) line = `${country.sprite} Institutions regain a sliver of faith.`;
    else if (dd > 0.03) line = `${country.sprite} Debt clock ticks louder.`;
    else if (dd < -0.02) line = `${country.sprite} Books tighten — creditors notice.`;
    else line = `${country.sprite} Ordinary month in ${country.country_name} — cabinets grind, markets wait.`;
  }

  return (
    <div className="month-narrator" key={`${country.country_name}-${month}`}>
      <span className="narrator-label">DISPATCH</span>
      <p>{line}</p>
    </div>
  );
}

export function CountUp({ value, decimals = 1 }: { value: number; decimals?: number }) {
  const [shown, setShown] = useState(0);
  useEffect(() => {
    let frame = 0;
    const start = shown;
    const delta = value - start;
    const steps = 24;
    const id = setInterval(() => {
      frame += 1;
      const t = frame / steps;
      const eased = 1 - (1 - t) * (1 - t);
      setShown(start + delta * eased);
      if (frame >= steps) clearInterval(id);
    }, 30);
    return () => clearInterval(id);
    // only re-run when value changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);
  return <>{shown.toFixed(decimals)}</>;
}

export function ComboMeter({ streak, label }: { streak: number; label: string }) {
  if (streak < 2) return null;
  return (
    <div className={`combo-meter ${streak >= 4 ? "hot" : ""}`}>
      <span className="combo-x">{streak}×</span>
      <span>{label}</span>
    </div>
  );
}
