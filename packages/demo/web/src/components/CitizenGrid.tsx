import type { Citizen } from "../types";

const MOOD_SPRITE: Record<string, string> = {
  happy: "🙂",
  neutral: "😐",
  worried: "😟",
  angry: "😠",
  sick: "🤒",
};

const MOOD_COLOR: Record<string, string> = {
  happy: "#58d68d",
  neutral: "#f4d03f",
  worried: "#f5b041",
  angry: "#e74c3c",
  sick: "#bb8fce",
};

export function CitizenGrid({ citizens, size = 64 }: { citizens: Citizen[]; size?: number }) {
  const slice = citizens.slice(0, size);
  return (
    <div
      className="citizen-grid"
      style={{ gridTemplateColumns: `repeat(${Math.min(8, Math.ceil(Math.sqrt(slice.length)))}, 1fr)` }}
      title="Representative population sample"
    >
      {slice.map((c, i) => (
        <span
          key={i}
          className={`citizen mood-${c.mood} ${c.employed ? "employed" : "jobless"}`}
          title={`${c.mood}${c.employed ? "" : " · unemployed"} · decile ${c.cohort}`}
        >
          {MOOD_SPRITE[c.mood] || "😐"}
        </span>
      ))}
    </div>
  );
}

export function MoodBar({ summary }: { summary: Record<string, number> }) {
  const order = ["happy", "neutral", "worried", "angry", "sick"];
  return (
    <div className="mood-bar">
      {order.map((m) =>
        summary[m] ? (
          <span
            key={m}
            className="mood-segment"
            style={{ flex: summary[m], background: MOOD_COLOR[m] }}
            title={`${m}: ${(summary[m] * 100).toFixed(0)}%`}
          />
        ) : null
      )}
    </div>
  );
}

export function CitizenLegend() {
  return (
    <div className="citizen-legend">
      {Object.entries(MOOD_SPRITE).map(([m, s]) => (
        <span key={m}>
          {s} {m}
        </span>
      ))}
    </div>
  );
}
