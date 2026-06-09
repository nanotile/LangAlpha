import i18n from '@/i18n';

/** How often the dashboard news feeds re-poll their warm server buffer. */
export const NEWS_POLL_INTERVAL_MS = 60000;
/** Staleness window for news queries — just under the poll interval so an open
 *  tab refetches on the poll cadence, not on every remount. */
export const NEWS_STALE_MS = 55000;

export interface NewsSentimentItem {
  ticker: string;
  sentiment: string;
  reasoning?: string;
}

/** Normalized news row shared by every dashboard news feed (market, curated,
 *  portfolio, watchlist). Produced by mapNewsResults from the /news payload. */
export interface DashboardNewsItem {
  id: string;
  title: string;
  time: string;
  publishedAt: string | null;
  isHot: boolean;
  source: string;
  favicon: string | null;
  image: string | null;
  tickers: string[];
  articleUrl?: string | null;
  // Inlined article body — lets the detail modal render without a by-id fetch.
  author?: string | null;
  description?: string | null;
  keywords?: string[];
  sentiments?: NewsSentimentItem[] | null;
}

/**
 * Formats a timestamp to a localized relative time string. Computed outside
 * React render — consumers re-render on locale switch because their parent calls
 * useTranslation, which is what makes the freshly resolved string reach the DOM.
 */
export function formatRelativeTime(timestamp: string | number | null | undefined): string {
  if (!timestamp) return '';
  const now = new Date();
  const then = new Date(timestamp);
  const diffMs = now.getTime() - then.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return i18n.t('dashboard.widgets.common.relativeNow');
  let when: string;
  if (diffMin < 60) when = `${diffMin}m`;
  else {
    const diffHr = Math.floor(diffMin / 60);
    if (diffHr < 24) when = `${diffHr}h`;
    else when = `${Math.floor(diffHr / 24)}d`;
  }
  return i18n.t('dashboard.widgets.common.relativePast', { when });
}

/** Map raw /news results into the normalized DashboardNewsItem shape. */
export function mapNewsResults(results: Record<string, unknown>[]): DashboardNewsItem[] {
  return results.map((r) => ({
    id: r.id as string,
    title: r.title as string,
    time: formatRelativeTime(r.published_at as string | null | undefined),
    publishedAt: (r.published_at as string) || null,
    isHot: r.has_sentiment as boolean,
    source: (r.source as Record<string, unknown> | undefined)?.name as string || '',
    favicon: (r.source as Record<string, unknown> | undefined)?.favicon_url as string || null,
    image: r.image_url as string || null,
    tickers: (r.tickers as string[]) || [],
    articleUrl: (r.article_url as string) || null,
    author: (r.author as string) ?? null,
    description: (r.description as string) ?? null,
    keywords: (r.keywords as string[]) || [],
    sentiments: (r.sentiments as NewsSentimentItem[]) ?? null,
  }));
}
