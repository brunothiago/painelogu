export function hexToRgba(hex, alpha) {
  const normalized = hex?.replace("#", "");
  if (!normalized || normalized.length !== 6) return `rgba(53,108,140,${alpha})`;
  const int = Number.parseInt(normalized, 16);
  const r = (int >> 16) & 255;
  const g = (int >> 8) & 255;
  const b = int & 255;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}
