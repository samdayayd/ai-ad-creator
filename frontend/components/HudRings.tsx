/**
 * Purely decorative Jarvis-style HUD: three concentric rotating rings, a
 * static tick-mark bezel, a radar sweep, and a pulsing core. All CSS/SVG,
 * no canvas/WebGL — cheap to render and safe behind real content since
 * it's aria-hidden and pointer-events: none (see .hud-rings in globals.css).
 */
export default function HudRings({ className = "" }: { className?: string }) {
  const ticks = Array.from({ length: 24 }, (_, i) => {
    const angle = (i * 360) / 24;
    const rad = (angle * Math.PI) / 180;
    const rOuter = 150;
    const rInner = i % 6 === 0 ? 132 : 141;
    const cx = 200;
    const cy = 200;
    return (
      <line
        key={i}
        x1={cx + rOuter * Math.cos(rad)}
        y1={cy + rOuter * Math.sin(rad)}
        x2={cx + rInner * Math.cos(rad)}
        y2={cy + rInner * Math.sin(rad)}
      />
    );
  });

  return (
    <div className={`hud-rings ${className}`} aria-hidden="true">
      <div className="hud-sweep" />
      <svg viewBox="0 0 400 400" className="hud-rings-svg">
        <circle className="hud-ring-outer" cx="200" cy="200" r="188" />
        <circle className="hud-ring-mid" cx="200" cy="200" r="150" />
        <g className="hud-ring-ticks">{ticks}</g>
        <circle className="hud-ring-inner" cx="200" cy="200" r="108" />
        <circle className="hud-core" cx="200" cy="200" r="5" />
      </svg>
    </div>
  );
}
