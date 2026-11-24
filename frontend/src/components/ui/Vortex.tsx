import type { CSSProperties } from "react";

/** Concentric broken rings turning at different speeds: the sign-in screen's single decorative element. */
export function Vortex({ size = 320 }: { size?: number }) {
  const rings = [
    { r: 150, dash: "2 14", dur: 90, stroke: "var(--cyan)", w: 1.5, reverse: false },
    { r: 124, dash: "60 40", dur: 60, stroke: "var(--azure)", w: 2, reverse: true },
    { r: 98, dash: "18 22", dur: 38, stroke: "var(--violet)", w: 2.5, reverse: false },
    { r: 72, dash: "90 30", dur: 26, stroke: "var(--cyan)", w: 3, reverse: true },
    { r: 46, dash: "30 18", dur: 16, stroke: "var(--azure)", w: 3.5, reverse: false },
  ];
  return (
    <svg width={size} height={size} viewBox="-160 -160 320 320" role="img" aria-label="XVORTEX">
      {rings.map((ring) => (
        <circle
          key={ring.r}
          r={ring.r}
          fill="none"
          stroke={`rgb(${ring.stroke})`}
          strokeWidth={ring.w}
          strokeDasharray={ring.dash}
          strokeLinecap="round"
          opacity={0.85}
          className={`vortex-ring${ring.reverse ? " reverse" : ""}`}
          style={{ "--dur": `${ring.dur}s` } as CSSProperties}
        />
      ))}
      <circle r="10" fill="rgb(var(--cyan))" opacity="0.9" />
    </svg>
  );
}
