import { useQuery, useInfiniteQuery } from '@tanstack/react-query';
import { useMemo } from 'react';
import i18n from '@/i18n';
import { getNews, getIndices, INDEX_SYMBOLS, fallbackIndex, normalizeIndexSymbol } from '../utils/api';
import { fetchMarketStatus } from '@/lib/marketUtils';
import type { IndexData } from '@/types/market';

interface MarketStatusData {
  market?: string;
  afterHours?: boolean;
  earlyHours?: boolean;
  [key: string]: unknown;
}

interface NewsSentimentItem {
  ticker: string;
  sentiment: string;
  reasoning?: string;
}

interface NewsItem {
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

interface DashboardData {
  indices: IndexData[] | undefined;
  indicesLoading: boolean;
  newsItems: NewsItem[];
  newsLoading: boolean;
  curatedItems: NewsItem[];
  curatedLoading: boolean;
  curatedHasNextPage: boolean;
  curatedIsFetchingNextPage: boolean;
  curatedFetchNextPage: () => void;
  marketStatus: MarketStatusData | null;
  marketStatusRef: { current: MarketStatusData | null };
}

function mapNewsResults(results: Record<string, unknown>[]): NewsItem[] {
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

/**
 * Formats a given timestamp to a relative time string. Outside React render —
 * components consuming the result via this hook re-render on locale switch
 * because their parent calls useTranslation, which is what makes the freshly
 * resolved string reach the DOM.
 */
function formatRelativeTime(timestamp: string | number | null | undefined): string {
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

/**
 * useDashboardData Hook
 * Uses TanStack Query to manage fetching, caching, and auto-polling of data.
 * Eliminates race conditions and reduces boilerplate of manual useEffects.
 */
export function useDashboardData(): DashboardData {
  // 1. Market Status (Polls every 60s, cached globally)
  const { data: marketStatus = null } = useQuery<MarketStatusData | null>({
    queryKey: ['dashboard', 'marketStatus'],
    queryFn: fetchMarketStatus,
    refetchInterval: 60000,
    refetchIntervalInBackground: false,
    staleTime: 30000,
  });

  // 2. Market Indices (Adaptive Polling: 30s open / 60s closed)
  const isMarketOpen = marketStatus?.market === 'open' ||
    (marketStatus && !marketStatus.afterHours && !marketStatus.earlyHours && marketStatus.market !== 'closed');

  const { data: indices, isLoading: indicesLoading } = useQuery<IndexData[]>({
    queryKey: ['dashboard', 'indices', INDEX_SYMBOLS],
    queryFn: async () => {
      const { indices: next } = await getIndices(INDEX_SYMBOLS);
      return next;
    },
    // Using placeholderData provides standard fallback values instantly 
    // without populating the cache as "fresh", thereby triggering an immediate background fetch
    placeholderData: (): IndexData[] => INDEX_SYMBOLS.map((s) => fallbackIndex(normalizeIndexSymbol(s))),
    refetchInterval: isMarketOpen ? 30000 : 60000,
    refetchIntervalInBackground: false,
    staleTime: 10000,
  });

  // 3. News Feed (Fetched once, cached for 5 minutes)
  const { data: newsItems = [], isLoading: newsLoading } = useQuery<NewsItem[]>({
    queryKey: ['dashboard', 'news'],
    queryFn: async (): Promise<NewsItem[]> => {
      const data = await getNews({ limit: 50 });
      return data.results?.length ? mapNewsResults(data.results) : [];
    },
    staleTime: 5 * 60 * 1000, // 5 minutes fresh cache
  });

  // 4. Curated "Top" Feed (TickerTick) — cursor-paginated for infinite scroll.
  const curated = useInfiniteQuery({
    queryKey: ['dashboard', 'curatedNews'],
    queryFn: ({ pageParam }) => getNews({ provider: 'tickertick', limit: 50, cursor: pageParam }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
    staleTime: 5 * 60 * 1000, // 5 minutes fresh cache
  });

  // Flatten loaded pages, de-duping by id (guards against feed rotation between
  // page fetches reintroducing a story).
  const curatedItems = useMemo<NewsItem[]>(() => {
    const rows = curated.data?.pages.flatMap((p) => p.results) ?? [];
    const seen = new Set<string>();
    const unique = rows.filter((r) => {
      const id = r.id as string;
      if (!id || seen.has(id)) return false;
      seen.add(id);
      return true;
    });
    return mapNewsResults(unique);
  }, [curated.data]);

  return {
    indices,
    indicesLoading,
    newsItems,
    newsLoading,
    curatedItems,
    curatedLoading: curated.isLoading,
    curatedHasNextPage: !!curated.hasNextPage,
    curatedIsFetchingNextPage: curated.isFetchingNextPage,
    curatedFetchNextPage: () => {
      void curated.fetchNextPage();
    },
    marketStatus,
    // Kept for backward compatibility with components that might use MarketStatusRef
    marketStatusRef: { current: marketStatus }
  };
}
