import type { Citizen } from "../types";

const MOOD_SPRITE: Record<string, string> = {
  happy: "🙂",
  neutral: "😐",
  worried: "😟",
  angry: "😠",
  sick: "🤒",
};

export function CitizenGrid({ citizens }: { citizens: Citizen[] }) {
  return (
    <div className="citizen-grid" title="Representative population sample">
      {citizens.map((c, i) => (
        <span
          key={i}
          className={`citizen mood-${c.mood} ${c.employed ? "employed" : "jobless"}`}
          title={`${c.mood}${c.employed ? "" : " · unemployed"}`}
        >
          {MOOD_SPRITE[c.mood] || "😐"}
        </span>
      ))}
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
