/**
 * Build the served-file URL for a workspace file.
 *
 * Path segments are URI-encoded but slashes are preserved, so a document at
 * `.../wsfiles/{ws}/results/report.html` resolves its relative `charts/x.png`
 * reference to `.../wsfiles/{ws}/results/charts/x.png` with no extra machinery.
 * Built off the same base as the axios client (api/client.ts).
 */
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '';

export function buildWsfilesUrl(
  workspaceId: string,
  filePath: string,
  { injectTheme = false }: { injectTheme?: boolean } = {},
): string {
  const encodedPath = filePath
    .replace(/^\/+/, '')
    .split('/')
    .map(encodeURIComponent)
    .join('/');
  const url = `${API_BASE}/api/v1/wsfiles/${encodeURIComponent(workspaceId)}/${encodedPath}`;
  return injectTheme ? `${url}?inject=theme` : url;
}
