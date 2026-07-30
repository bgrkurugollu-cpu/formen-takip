export const CATEGORICAL_LIGHT = [
  "#2a78d6",
  "#eb6834",
  "#1baf7a",
  "#eda100",
  "#e87ba4",
  "#008300",
  "#4a3aa7",
  "#e34948",
];

export const CATEGORICAL_DARK = [
  "#3987e5",
  "#d95926",
  "#199e70",
  "#c98500",
  "#d55181",
  "#008300",
  "#9085e9",
  "#e66767",
];

export const SEQUENTIAL_BLUE = {
  100: "#cde2fb", 150: "#b7d3f6", 200: "#9ec5f4", 250: "#86b6ef",
  300: "#6da7ec", 350: "#5598e7", 400: "#3987e5", 450: "#2a78d6",
  500: "#256abf", 550: "#1c5cab", 600: "#184f95", 650: "#104281", 700: "#0d366b",
};

export const CHART_INK = {
  primary: "#0f172a", primaryDark: "#f1f5f9",
  secondary: "#475569", secondaryDark: "#94a3b8",
  muted: "#94a3b8",
  grid: "#e2e8f0", gridDark: "#1f2937",
  axis: "#cbd5e1", axisDark: "#334155",
};

export function categoricalColor(index: number, dark = false): string {
  const palette = dark ? CATEGORICAL_DARK : CATEGORICAL_LIGHT;
  return palette[index % palette.length];
}

export const ACCENT_RED = "#e90128";

export function accentLineColor(dark = false): string {
  return dark ? SEQUENTIAL_BLUE[300] : ACCENT_RED;
}

export function resolveChartInk(dark = false) {
  return {
    primary: dark ? CHART_INK.primaryDark : CHART_INK.primary,
    secondary: dark ? CHART_INK.secondaryDark : CHART_INK.secondary,
    muted: CHART_INK.muted,
    grid: dark ? CHART_INK.gridDark : CHART_INK.grid,
    axis: dark ? CHART_INK.axisDark : CHART_INK.axis,
  };
}
