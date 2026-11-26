const c = (name) => `rgb(var(--${name}) / <alpha-value>)`;

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: c("ink"), panel: c("panel"), fg: c("fg"), dim: c("dim"),
        cyan: c("cyan"), azure: c("azure"), violet: c("violet"), danger: c("danger"), line: c("line"),
      },
      fontFamily: {
        sans: ["Sora", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
