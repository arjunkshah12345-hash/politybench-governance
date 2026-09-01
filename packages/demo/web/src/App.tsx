import { useEffect, useMemo, useRef, useState } from "react";
import { useDialKit } from "dialkit";
import type { BenchLive } from "./types";
import { CountryCard, CountryDetail } from "./components/CountryCard";
import { CompareBoard, HeadToHead, MultiCountryChart } from "./components/CompareBoard";
import { Podium } from "./components/Narrative";
import { DuelArena, GameHUD } from "./components/DuelArena";
import { DuelWinner, NewsTicker, OverworldMap, TermEndSplash } from "./components/Overworld";
import { playBeep, MonthNarrator, SpeedControl, ToastStack, useScreenShake, useToasts } from "./components/Fx";
import { BootScreen, Bookmarks, KeyHelp } from "./components/Life";
import {
  CrisisVignette,
  eventMonths,
  loadPrefs,
  NextCrisisChip,
  nextEventMonth,
  PlayheadSparkline,
  savePrefs,
  useAmbientHum,
  ViewWipe,
} from "./components/Stage";

export default function App() {
  const theme = useDialKit("World Theme", {
    skyTop: "#5eb8ff",
    grass: "#5a9e2f",
    panelBg: "#f5e6c8",
    accent: "#e8a838",
    scanlines: [0.025, 0, 0.15],
  });

  const prefs = useMemo(() => loadPrefs(), []);
  const [bench, setBench] = useState<BenchLive | null>(null);
  const [selectedId, setSelectedId] = useState("");
  const [duelRightId, setDuelRightId] = useState("");
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<"world" | "duel" | "compare" | "replay">("world");
  const [playing, setPlaying] = useState(false);
  const [playMonth, setPlayMonth] = useState(0);
  const [speed, setSpeed] = useState(prefs.speed ?? 1);
  const [muted, setMuted] = useState(prefs.muted ?? false);
  const [ambient, setAmbient] = useState(prefs.ambient ?? false);
  const [cinema, setCinema] = useState(false);
  const [director, setDirector] = useState(false);
  const [showTermEnd, setShowTermEnd] = useState(false);
  const [showDuelEnd, setShowDuelEnd] = useState(false);
  const [booting, setBooting] = useState(true);
  const [showHelp, setShowHelp] = useState(false);
  const [bookmarks, setBookmarks] = useState<number[]>(prefs.bookmarks ?? []);
  const { toasts, push } = useToasts();
  const lastEventMonth = useRef(-1);
  const [shakeTick, setShakeTick] = useState(0);
  const shaking = useScreenShake(shakeTick);
  useAmbientHum(ambient, muted);

  useEffect(() => {
    savePrefs({ muted, ambient, speed, bookmarks });
  }, [muted, ambient, speed, bookmarks]);

  const load = () => {
    setLoading(true);
    fetch(`/bench_live.json?t=${Date.now()}`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((j: BenchLive) => {
        setBench(j);
        const sorted = [...j.countries].sort((a, b) => a.rank - b.rank);
        if (sorted[0]) setSelectedId(sorted[0].agent_id);
        if (sorted[1]) setDuelRightId(sorted[1].agent_id);
        else if (sorted[0]) setDuelRightId(sorted[0].agent_id);
      })
      .catch(() => setBench(null))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const countries = bench?.countries ?? [];
  const selected = useMemo(
    () => countries.find((c) => c.agent_id === selectedId) || countries[0],
    [countries, selectedId]
  );
  const duelRight = useMemo(
    () => countries.find((c) => c.agent_id === duelRightId) || countries[1] || countries[0],
    [countries, duelRightId]
  );

  const maxMonth = useMemo(() => {
    if (!selected?.trajectory?.length) return 0;
    const other = duelRight?.trajectory?.length || 0;
    return Math.max(selected.trajectory.length, other) - 1;
  }, [selected, duelRight]);

  const beats = useMemo(
    () => eventMonths(selected, view === "duel" ? duelRight : null),
    [selected, duelRight, view]
  );

  useEffect(() => {
    if (!playing) return;
    const ms = Math.max(60, Math.round((director ? 480 : 220) / speed));
    const id = setInterval(() => {
      setPlayMonth((m) => {
        if (m >= maxMonth) {
          setPlaying(false);
          playBeep("win", muted);
          if (view === "replay") setShowTermEnd(true);
          if (view === "duel") setShowDuelEnd(true);
          return maxMonth;
        }
        if (director) {
          const nxt = nextEventMonth(m, beats, 1);
          if (nxt == null || nxt > maxMonth) {
            setPlaying(false);
            playBeep("win", muted);
            if (view === "replay") setShowTermEnd(true);
            if (view === "duel") setShowDuelEnd(true);
            return maxMonth;
          }
          playBeep("tick", muted);
          return nxt;
        }
        playBeep("tick", muted);
        return m + 1;
      });
    }, ms);
    return () => clearInterval(id);
  }, [playing, maxMonth, view, speed, muted, director, beats]);

  useEffect(() => {
    if (!selected || playMonth === lastEventMonth.current) return;
    lastEventMonth.current = playMonth;
    const hits = [
      ...selected.timeline.filter((e) => Number(e.month) === playMonth),
      ...(duelRight && view === "duel"
        ? duelRight.timeline.filter((e) => Number(e.month) === playMonth)
        : []),
    ];
    for (const e of hits) {
      const warn = e.type === "disaster" || e.type === "epidemic" || e.severity >= 0.6;
      playBeep(warn ? "warn" : "event", muted);
      push(`M${e.month} · ${e.label}`, warn ? "warn" : "info");
      if (warn) setShakeTick((t) => t + 1);
    }
  }, [playMonth, selected, duelRight, view, muted, push]);

  useEffect(() => {
    setPlayMonth(0);
    setPlaying(false);
    setShowTermEnd(false);
    setShowDuelEnd(false);
    lastEventMonth.current = -1;
  }, [selectedId, duelRightId]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (booting) {
        e.preventDefault();
        setBooting(false);
        return;
      }
      if (e.key === "?" || (e.shiftKey && e.key === "/")) {
        e.preventDefault();
        setShowHelp((h) => !h);
        return;
      }
      if (e.key === "b" || e.key === "B") {
        e.preventDefault();
        setBookmarks((marks) =>
          marks.includes(playMonth) ? marks.filter((m) => m !== playMonth) : [...marks, playMonth].sort((a, b) => a - b).slice(-8)
        );
        push(`Bookmark M${playMonth}`, "info");
        return;
      }
      if (e.key === "h" || e.key === "H") {
        e.preventDefault();
        setCinema((c) => !c);
        return;
      }
      if (e.key === "d" || e.key === "D") {
        e.preventDefault();
        setDirector((d) => {
          const next = !d;
          push(next ? "Director mode — jump event→event" : "Director off — month scrub", "info");
          return next;
        });
        return;
      }
      if (e.key === "n" || e.key === "N") {
        e.preventDefault();
        const nxt = nextEventMonth(playMonth, beats, 1);
        if (nxt != null) setPlayMonth(nxt);
        return;
      }
      if (e.key === "p" || e.key === "P") {
        e.preventDefault();
        const prv = nextEventMonth(playMonth, beats, -1);
        if (prv != null) setPlayMonth(prv);
        return;
      }
      if (e.key === "m" || e.key === "M") {
        e.preventDefault();
        setAmbient((a) => {
          const next = !a;
          push(next ? "Ambient hum on" : "Ambient hum off", "info");
          return next;
        });
        return;
      }
      if (e.code === "Space") {
        e.preventDefault();
        setPlaying((p) => !p);
      } else if (e.code === "ArrowRight") {
        setPlayMonth((m) => Math.min(maxMonth, m + 1));
      } else if (e.code === "ArrowLeft") {
        setPlayMonth((m) => Math.max(0, m - 1));
      } else if (e.key === "1") setView("world");
      else if (e.key === "2") setView("duel");
      else if (e.key === "3") setView("compare");
      else if (e.key === "4") setView("replay");
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [maxMonth, booting, playMonth, push, beats]);

  const cssVars = {
    "--sky-top": theme.skyTop,
    "--grass": theme.grass,
    "--panel-bg": theme.panelBg,
    "--accent": theme.accent,
  } as React.CSSProperties;

  const winner = countries.find((c) => c.rank === 1);
  const setViewWipe = (id: typeof view) => setView(id);

  const snapNow = selected?.trajectory[Math.min(playMonth, Math.max(0, (selected?.trajectory.length || 1) - 1))];
  const vignetteCrisis =
    !!selected &&
    (selected.timeline.some(
      (e) => Number(e.month) === playMonth && (e.type === "disaster" || e.type === "epidemic" || e.severity >= 0.6)
    ) ||
      Number(snapNow?.unemployment ?? 0) > 0.18 ||
      Number(snapNow?.debt_gdp ?? 0) > 1.8);
  const vignetteBoom =
    !!selected &&
    Number(snapNow?.trust ?? 0) > 0.75 &&
    Number(snapNow?.unemployment ?? 0) < 0.09 &&
    !vignetteCrisis;

  return (
    <div
      className={`pixel-world bench-world ${shaking ? "screen-shake" : ""} ${cinema ? "cinema" : ""} ${director ? "director-on" : ""}`}
      style={cssVars}
    >
      <div className="crt-overlay" style={{ opacity: theme.scanlines }} />
      <CrisisVignette active={vignetteCrisis} kind="crisis" />
      <CrisisVignette active={vignetteBoom} kind="boom" />
      {booting && <BootScreen onDone={() => setBooting(false)} />}
      <KeyHelp open={showHelp} onClose={() => setShowHelp(false)} />
      <ToastStack toasts={toasts} />
      <ViewWipe token={view} />

      {selected && (view === "replay" || view === "duel") && (
        <>
          <GameHUD country={selected} month={playMonth} />
          <div className="hud-extras">
            <PlayheadSparkline trajectory={selected.trajectory} month={playMonth} />
            <NextCrisisChip
              month={playMonth}
              events={selected.timeline}
              onJump={setPlayMonth}
            />
          </div>
        </>
      )}

      {!cinema && (
      <header className="bench-header">
        <div>
          <p className="sample-badge">◆ COUNTRY GOVERNANCE BENCH ◆</p>
          <h1 className="pixel-title">
            POLITY<span className="gold">BENCH</span>
          </h1>
          <p className="pixel-subtitle">
            {winner
              ? `Champion: ${winner.sprite} ${winner.country_name} · ${winner.evaluation.robust_score_single.toFixed(1)} robust`
              : "Each model runs a nation"}
          </p>
        </div>
        <div className="bench-actions">
          <button type="button" className="pixel-btn refresh" onClick={load}>
            ↻ Reload
          </button>
          <div className="view-tabs">
            {(
              [
                ["world", "World"],
                ["duel", "Duel"],
                ["compare", "Board"],
                ["replay", "Replay"],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                className={view === id ? "active" : ""}
                onClick={() => setViewWipe(id)}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </header>
      )}

      {bench && !cinema && (
        <>
          <NewsTicker countries={countries} month={playMonth} />
          <div className="bench-meta-bar">
            <span>{bench.scenario.replace(/_/g, " ")}</span>
            <span>F{bench.fidelity.replace("F", "")}</span>
            <span>{bench.countries.length} nations</span>
            <span>D director · N/P events · H cinema</span>
            <button type="button" className="pixel-btn mute-btn" onClick={() => setMuted((m) => !m)}>
              {muted ? "🔇" : "🔊"}
            </button>
            <button
              type="button"
              className={`pixel-btn mute-btn ${ambient ? "active" : ""}`}
              onClick={() => setAmbient((a) => !a)}
              title="Ambient hum"
            >
              ♪
            </button>
            <button
              type="button"
              className={`pixel-btn mute-btn ${director ? "active" : ""}`}
              onClick={() => setDirector((d) => !d)}
              title="Director mode"
            >
              ▶▶
            </button>
            <button type="button" className="pixel-btn mute-btn" onClick={() => setCinema(true)} title="Cinema">
              ▢
            </button>
            <button type="button" className="pixel-btn mute-btn" onClick={() => setShowHelp(true)}>
              ?
            </button>
          </div>
        </>
      )}

      {cinema && (
        <button type="button" className="cinema-exit pixel-btn" onClick={() => setCinema(false)}>
          Exit cinema (H)
        </button>
      )}

      {countries.length > 0 && view === "world" && <Podium countries={countries} />}

      {!bench && !loading && (
        <p className="empty-hint">
          Run <code>politybench bench-run</code> then reload.
        </p>
      )}

      {view === "duel" && selected && duelRight && (
        <section className="duel-section">
          <div className="duel-pickers">
            <label>
              Left
              <select value={selectedId} onChange={(e) => setSelectedId(e.target.value)}>
                {countries.map((c) => (
                  <option key={c.agent_id} value={c.agent_id}>
                    #{c.rank} {c.country_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Right
              <select value={duelRightId} onChange={(e) => setDuelRightId(e.target.value)}>
                {countries.map((c) => (
                  <option key={c.agent_id} value={c.agent_id}>
                    #{c.rank} {c.country_name}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="replay-controls duel-speed-row">
            <SpeedControl speed={speed} onChange={setSpeed} />
          </div>
          <DuelArena
            left={selected}
            right={duelRight}
            month={playMonth}
            onMonthChange={setPlayMonth}
            playing={playing}
            onTogglePlay={() => setPlaying((p) => !p)}
          />
        </section>
      )}

      {view === "compare" && countries.length > 0 && (
        <section className="compare-section">
          <CompareBoard countries={countries} />
          {bench && <HeadToHead bench={bench} />}
          <div className="multi-chart-wrap">
            <h3 className="section-title">GDP paths</h3>
            <MultiCountryChart countries={countries} field="gdp" />
          </div>
          <div className="multi-chart-wrap">
            <h3 className="section-title">Trust paths</h3>
            <MultiCountryChart countries={countries} field="trust" />
          </div>
          <div className="multi-chart-wrap">
            <h3 className="section-title">Debt / GDP</h3>
            <MultiCountryChart countries={countries} field="debt_gdp" />
          </div>
        </section>
      )}

      {view === "replay" && selected && (
        <section className="replay-section">
          <div className="replay-picker">
            {countries.map((c) => (
              <button
                key={c.agent_id}
                type="button"
                className={`pixel-btn ${selectedId === c.agent_id ? "active" : ""}`}
                onClick={() => setSelectedId(c.agent_id)}
              >
                {c.sprite} {c.country_name}
              </button>
            ))}
          </div>
          <div className="replay-controls">
            <button type="button" className="pixel-btn active" onClick={() => setPlaying((p) => !p)}>
              {playing ? "❚❚ Pause" : "▶ Play term"}
            </button>
            <button
              type="button"
              className="pixel-btn"
              onClick={() => {
                setPlayMonth(0);
                setPlaying(true);
                lastEventMonth.current = -1;
              }}
            >
              ↺ Restart
            </button>
            <SpeedControl speed={speed} onChange={setSpeed} />
            <button
              type="button"
              className="pixel-btn"
              onClick={() => {
                setBookmarks((marks) =>
                  marks.includes(playMonth)
                    ? marks.filter((m) => m !== playMonth)
                    : [...marks, playMonth].sort((a, b) => a - b).slice(-8)
                );
              }}
            >
              ★ Mark
            </button>
            <span className="muted">
              Month {playMonth}/{maxMonth}
            </span>
          </div>
          <Bookmarks
            marks={bookmarks}
            onJump={setPlayMonth}
            onClear={() => setBookmarks([])}
          />
          <MonthNarrator country={selected} month={playMonth} />
          <CountryDetail
            country={selected}
            month={playMonth}
            onMonthChange={setPlayMonth}
            bookmarks={bookmarks}
          />
        </section>
      )}

      {view === "world" && (
        <main className="bench-layout">
          {countries.length > 0 && (
            <OverworldMap
              countries={countries}
              selectedId={selectedId}
              onSelect={(id) => {
                setSelectedId(id);
                setView("replay");
                setPlayMonth(0);
                setPlaying(true);
              }}
            />
          )}
          <section className="nations-grid">
            <h2 className="section-title">🌍 Nations under test</h2>
            {loading && <p className="muted">Loading bench…</p>}
            <div className="country-grid">
              {countries.map((c) => (
                <CountryCard
                  key={`${c.agent_id}-${c.seed}`}
                  country={c}
                  selected={selected?.agent_id === c.agent_id}
                  onSelect={() => {
                    setSelectedId(c.agent_id);
                    setView("replay");
                    setPlayMonth(0);
                    setPlaying(true);
                  }}
                />
              ))}
            </div>
          </section>

          {selected && (
            <section className="nation-detail-wrap">
              <h2 className="section-title">📋 {selected.country_name}</h2>
              <CountryDetail country={selected} />
            </section>
          )}
        </main>
      )}

      {showTermEnd && selected && view === "replay" && (
        <TermEndSplash country={selected} onClose={() => setShowTermEnd(false)} />
      )}
      {showDuelEnd && selected && duelRight && view === "duel" && (
        <DuelWinner left={selected} right={duelRight} onClose={() => setShowDuelEnd(false)} />
      )}

      {!cinema && (
      <footer className="pixel-footer">
        <span>click a nation → auto-replay · Duel for head-to-head</span>
        <span className="blink">▮</span>
        <span>research sim only</span>
      </footer>
      )}
    </div>
  );
}
