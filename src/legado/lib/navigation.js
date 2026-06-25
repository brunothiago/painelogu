export function resolveCurrentNavPath(pathname) {
  const normalizedPath = String(pathname ?? "")
    .replace(/\/index\.html$/, "")
    .replace(/\.html$/, "")
    .replace(/\/$/, "") || "/";

  return normalizedPath;
}
