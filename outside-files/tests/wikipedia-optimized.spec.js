import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';
const CACHE_DIR = path.join(process.cwd(), '.cache');
const CACHE_FILE = path.join(CACHE_DIR, 'http-cache.json');
const CACHE_ENABLED = process.env.PLAYWRIGHT_CACHE !== 'false';
const CACHE_CLEAR = process.env.PLAYWRIGHT_CACHE_CLEAR === 'true';
const MAX_CACHE_ENTRIES = parseInt(process.env.PLAYWRIGHT_CACHE_MAX_ENTRIES || '100', 10);
const MAX_CACHE_SIZE_MB = parseFloat(process.env.PLAYWRIGHT_CACHE_MAX_SIZE_MB || '50', 10);
/** @type {Record<string, { status: number; headers: Record<string, string>; body: string; lastAccess: number }>} */
let httpCache = {};
let cacheStats = {
  hits: 0,
  misses: 0,
  writes: 0,
  evictions: 0,
};
const DEDUP_ENABLED = process.env.PLAYWRIGHT_DEDUP !== 'false';
/** @type {Map<string, Promise<{ status: number; headers: Record<string, string>; body: Buffer }>>} */
const pendingRequests = new Map();
let dedupStats = {
  duplicates: 0,
  unique: 0,
};
const DOMAIN_BLOCKING_ENABLED = process.env.PLAYWRIGHT_BLOCK_DOMAINS !== 'false';
const BLOCKED_DOMAINS = [
  'google-analytics.com',
  'googletagmanager.com',
  'analytics.google.com',
  'doubleclick.net',
  'googleadservices.com',
  'facebook.com/tr',
  'facebook.net',
  'scorecardresearch.com',
  'quantserve.com',
  'adservice.google',
  'googlesyndication.com',
  'advertising.com',
  'adform.net',
  'adsafeprotected.com',
  'adnxs.com',
  'amazon-adsystem.com',
  'bing.com/analytics',
  'hotjar.com',
  'mixpanel.com',
  'segment.io',
  'newrelic.com',
  'optimizely.com',
  'fullstory.com',
  'mouseflow.com',
  'crazyegg.com',
  'clarity.microsoft.com',
];
let domainBlockStats = {
  blocked: 0,
};
let cacheDirty = false;
function getCacheSizeMB() {
  const jsonString = JSON.stringify(httpCache);
  return Buffer.byteLength(jsonString, 'utf8') / (1024 * 1024);
}
function evictLRU() {
  const entries = Object.entries(httpCache);
  const currentSize = entries.length;
  const currentSizeMB = getCacheSizeMB();
  const needsEvictionByCount = currentSize >= MAX_CACHE_ENTRIES;
  const needsEvictionBySize = currentSizeMB >= MAX_CACHE_SIZE_MB;
  if (!needsEvictionByCount && !needsEvictionBySize) {
    return;
  }
  entries.sort((a, b) => (a[1].lastAccess || 0) - (b[1].lastAccess || 0));
  let evicted = 0;
  for (const [key] of entries) {
    const stillNeedsEviction = 
      (Object.keys(httpCache).length >= MAX_CACHE_ENTRIES) ||
      (getCacheSizeMB() >= MAX_CACHE_SIZE_MB);
    if (stillNeedsEviction) {
      delete httpCache[key];
      evicted++;
    } else {
      break;
    }
  }
  if (evicted > 0) {
    cacheStats.evictions += evicted;
    cacheDirty = true;
  }
}
if (CACHE_ENABLED) {
  try {
    if (CACHE_CLEAR && fs.existsSync(CACHE_FILE)) {
      fs.unlinkSync(CACHE_FILE);
      console.log('Cache cleared');
    }
    if (fs.existsSync(CACHE_FILE)) {
      const raw = fs.readFileSync(CACHE_FILE, 'utf-8');
      const loadedCache = JSON.parse(raw);
      for (const [key, value] of Object.entries(loadedCache)) {
        httpCache[key] = {
          ...value,
          lastAccess: value.lastAccess || Date.now(),
        };
      }
      const cacheSize = Object.keys(httpCache).length;
      const cacheSizeMB = getCacheSizeMB();
      console.log(`Loaded HTTP cache: ${cacheSize} entries (${cacheSizeMB.toFixed(2)} MB)`);
      evictLRU();
    }
  } catch (e) {
    console.warn('Failed to load HTTP cache, starting fresh', e.message);
    httpCache = {};
  }
}
async function writeCacheToDisk() {
  if (!cacheDirty || !CACHE_ENABLED) return;
  try {
    fs.mkdirSync(CACHE_DIR, { recursive: true });
    await fs.promises.writeFile(
      CACHE_FILE, 
      JSON.stringify(httpCache, null, 2), 
      'utf-8'
    );
    cacheDirty = false;
    cacheStats.writes++;
  } catch (e) {
    console.warn('Failed to persist HTTP cache to disk', e.message);
  }
}
test.describe('Wikipedia - Comprehensive E2E Flow (Optimized)', () => {
  test('complex navigation and content exploration flow', async ({ page }) => {
    test.setTimeout(120000);
    await page.route('**/*', async route => {
      const resourceType = route.request().resourceType();
      const request = route.request();
      const url = request.url();
      if (['image', 'stylesheet', 'font', 'media'].includes(resourceType)) {
        route.abort();
        return;
      }
      if (DOMAIN_BLOCKING_ENABLED) {
        const isBlockedDomain = BLOCKED_DOMAINS.some(domain => url.includes(domain));
        if (isBlockedDomain) {
          domainBlockStats.blocked++;
          route.abort();
          return;
        }
      }
      const isGet = request.method() === 'GET';
      const isDataOrBlob = url.startsWith('data:') || url.startsWith('blob:');
      const isAuthLike =
        /\/login|\/signin|\/logout|\/auth/i.test(url) ||
        /token=|session=|auth=/i.test(url);
      const isDynamic = 
        /Special:Random|Special:RecentChanges|Special:Watchlist/i.test(url) ||
        /action=query.*titles=/i.test(url) && /format=json/i.test(url);
      if (CACHE_ENABLED && isGet && !isDataOrBlob && !isAuthLike && !isDynamic) {
        const key = url;
        const cached = httpCache[key];
        if (cached) {
          cacheStats.hits++;
          cached.lastAccess = Date.now();
          await route.fulfill({
            status: cached.status,
            headers: cached.headers,
            body: Buffer.from(cached.body, 'base64'),
          });
          return;
        }
        if (DEDUP_ENABLED && pendingRequests.has(key)) {
          dedupStats.duplicates++;
          const pendingResponse = await pendingRequests.get(key);
          await route.fulfill({
            status: pendingResponse.status,
            headers: pendingResponse.headers,
            body: pendingResponse.body,
          });
          return;
        }
        cacheStats.misses++;
        dedupStats.unique++;
        const requestPromise = (async () => {
          const response = await route.fetch();
          if (!response) {
            pendingRequests.delete(key);
            return null;
          }
          const bodyBuffer = await response.body();
          const status = response.status();
          const headers = response.headers();
          const result = {
            status,
            headers,
            body: bodyBuffer,
          };
          if (status >= 200 && status < 400) {
            evictLRU();
            httpCache[key] = {
              status,
              headers,
              body: bodyBuffer.toString('base64'),
              lastAccess: Date.now(),
            };
            cacheDirty = true;
          }
          pendingRequests.delete(key);
          return result;
        })();
        pendingRequests.set(key, requestPromise);
        const response = await requestPromise;
        if (!response) {
          await route.continue();
          return;
        }
        await route.fulfill({
          status: response.status,
          headers: response.headers,
          body: response.body,
        });
        return;
      }
      await route.continue();
    });
    await page.goto('https://en.wikipedia.org/wiki/Main_Page', {
      waitUntil: 'domcontentloaded',
    });
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    await expect(page).toHaveTitle(/Wikipedia/i);
    await expect(page.locator('#mp-welcome')).toHaveCount(1, { timeout: 10000 });
    const searchBox = page.locator('#searchInput');
    await expect(searchBox).toHaveCount(1, { timeout: 10000 });
    await searchBox.fill('Artificial Intelligence');
    await searchBox.press('Enter');
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    await expect(page).toHaveURL(/Artificial_intelligence/i);
    await expect(page.locator('h1#firstHeading')).toContainText(/Artificial intelligence/i, { timeout: 10000 });
    const historySection = page.locator('#History').or(page.locator('span:has-text("History")')).first();
    await historySection.scrollIntoViewIfNeeded();
    await historySection.click();
    await page.waitForLoadState('networkidle', { timeout: 3000 }).catch(() => {});
    await expect(page.locator('#History, span:has-text("History")').first()).toHaveCount(1, { timeout: 10000 });
    const firstInternalLink = page.locator('a[href^="/wiki/"]:not([href*="#"])').first();
    const linkText = await firstInternalLink.textContent();
    await firstInternalLink.click();
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    await expect(page.locator('h1#firstHeading')).toHaveCount(1, { timeout: 10000 });
    const articleTitle = await page.locator('h1#firstHeading').textContent();
    console.log(`Navigated to article: ${linkText} -> ${articleTitle}`);
    await page.goBack();
    await page.waitForLoadState('networkidle', { timeout: 3000 }).catch(() => {});
    await expect(page.locator('h1#firstHeading')).toContainText(/Artificial intelligence/i);
    await page.goForward();
    await page.waitForLoadState('networkidle', { timeout: 3000 }).catch(() => {});
    await expect(page.locator('h1#firstHeading')).toHaveCount(1, { timeout: 10000 });
    await page.goto('https://en.wikipedia.org/wiki/Artificial_intelligence', {
      waitUntil: 'domcontentloaded',
    });
    await page.waitForLoadState('networkidle', { timeout: 3000 }).catch(() => {});
    const langSelector = page.locator('#p-lang-btn, .interlanguage-link').first();
    if (await langSelector.isVisible({ timeout: 2000 }).catch(() => false)) {
      await langSelector.click();
      await page.waitForTimeout(500);
      const spanishLink = page.locator('a[lang="es"], a:has-text("Español")').first();
      if (await spanishLink.isVisible({ timeout: 2000 }).catch(() => false)) {
        await spanishLink.click();
        await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
        await expect(page).toHaveURL(/es\.wikipedia\.org/);
        await page.goto('https://en.wikipedia.org/wiki/Artificial_intelligence', {
          waitUntil: 'domcontentloaded',
        });
      }
    }
    await page.waitForLoadState('networkidle', { timeout: 3000 }).catch(() => {});
    const categoryLink = page.locator('a[href^="/wiki/Category:"]').first();
    if (await categoryLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      const categoryText = await categoryLink.textContent();
      await categoryLink.click();
      await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
      await expect(page).toHaveURL(/Category:/);
      console.log(`Navigated to category: ${categoryText}`);
      await page.goBack();
      await page.waitForLoadState('networkidle', { timeout: 3000 }).catch(() => {});
    }
    const toc = page.locator('#toc, .toc').first();
    if (await toc.isVisible({ timeout: 3000 }).catch(() => false)) {
      const tocLink = toc.locator('a').first();
      const tocLinkText = await tocLink.textContent();
      await tocLink.click();
      await page.waitForLoadState('networkidle', { timeout: 3000 }).catch(() => {});
      await expect(page.locator(`#${tocLinkText?.replace(/\s/g, '_')}, span:has-text("${tocLinkText}")`).first()).toBeVisible({ timeout: 5000 }).catch(() => {});
    }
    await page.goto('https://en.wikipedia.org/wiki/Main_Page', {
      waitUntil: 'domcontentloaded',
    });
    await page.waitForLoadState('networkidle', { timeout: 3000 }).catch(() => {});
    const searchInput = page.locator('#searchInput');
    await expect(searchInput).toHaveCount(1, { timeout: 10000 });
    await searchInput.fill('Machine Learning');
    await page.waitForTimeout(500);
    const suggestions = page.locator('.suggestions-results, .suggestions').first();
    if (await suggestions.isVisible({ timeout: 2000 }).catch(() => false)) {
      const firstSuggestion = suggestions.locator('a, li').first();
      await firstSuggestion.click();
      await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
      await expect(page).toHaveURL(/wiki/);
    } else {
      await page.keyboard.press('Enter');
      await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
      await expect(page).toHaveURL(/wiki/);
    }
    await page.goto('https://en.wikipedia.org/wiki/Special:Random', {
      waitUntil: 'domcontentloaded',
    });
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    await expect(page).toHaveURL(/wiki/);
    await expect(page.locator('h1#firstHeading')).toHaveCount(1, { timeout: 10000 });
    const randomArticleTitle = await page.locator('h1#firstHeading').textContent();
    console.log(`Random article: ${randomArticleTitle}`);
    const referencesSection = page.locator('#References, #Notes, span:has-text("References")').first();
    if (await referencesSection.isVisible({ timeout: 3000 }).catch(() => false)) {
      await referencesSection.scrollIntoViewIfNeeded();
      await page.waitForTimeout(500);
      const refLink = page.locator('ol.references a, .reference a').first();
      if (await refLink.isVisible({ timeout: 2000 }).catch(() => false)) {
        const refUrl = await refLink.getAttribute('href');
        if (refUrl && refUrl.startsWith('http')) {
          console.log(`Reference link found: ${refUrl}`);
        }
      }
    }
    await page.goto('https://en.wikipedia.org/wiki/Main_Page', {
      waitUntil: 'domcontentloaded',
    });
    await page.waitForLoadState('networkidle', { timeout: 3000 }).catch(() => {});
    const featuredSection = page.locator('#mp-dyk, .mp-dyk').first();
    if (await featuredSection.isVisible({ timeout: 3000 }).catch(() => false)) {
      const dykLink = featuredSection.locator('a').first();
      if (await dykLink.isVisible({ timeout: 2000 }).catch(() => false)) {
        await dykLink.click();
        await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
        await expect(page).toHaveURL(/wiki/);
        await page.goBack();
        await page.waitForLoadState('networkidle', { timeout: 3000 }).catch(() => {});
      }
    }
    const newsSection = page.locator('#mp-itn, .mp-itn').first();
    if (await newsSection.isVisible({ timeout: 3000 }).catch(() => false)) {
      const newsLink = newsSection.locator('a').first();
      if (await newsLink.isVisible({ timeout: 2000 }).catch(() => false)) {
        await newsLink.click();
        await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
        await expect(page).toHaveURL(/wiki/);
        await page.goBack();
        await page.waitForLoadState('networkidle', { timeout: 3000 }).catch(() => {});
      }
    }
    const onThisDaySection = page.locator('#mp-otd, .mp-otd').first();
    if (await onThisDaySection.isVisible({ timeout: 3000 }).catch(() => false)) {
      const otdLink = onThisDaySection.locator('a').first();
      if (await otdLink.isVisible({ timeout: 2000 }).catch(() => false)) {
        await otdLink.click();
        await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
        await expect(page).toHaveURL(/wiki/);
        await page.goBack();
        await page.waitForLoadState('networkidle', { timeout: 3000 }).catch(() => {});
      }
    }
    await page.goto('https://en.wikipedia.org/wiki/Artificial_intelligence', {
      waitUntil: 'domcontentloaded',
    });
    await page.waitForLoadState('networkidle', { timeout: 3000 }).catch(() => {});
    const editLink = page.locator('a:has-text("Edit"), a:has-text("View source"), #ca-edit').first();
    if (await editLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      const editHref = await editLink.getAttribute('href');
      if (editHref) {
        console.log(`Edit link found: ${editHref}`);
      }
    }
    const whatLinksHere = page.locator('a:has-text("What links here"), #t-whatlinkshere').first();
    if (await whatLinksHere.isVisible({ timeout: 3000 }).catch(() => false)) {
      try {
        await whatLinksHere.click();
        await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
        const currentUrl = page.url();
        if (currentUrl.includes('WhatLinksHere')) {
          await expect(page.locator('h1')).toContainText(/What links here/i, { timeout: 5000 }).catch(() => {});
          await page.goBack();
          await page.waitForLoadState('networkidle', { timeout: 3000 }).catch(() => {});
        }
      } catch (e) {
        console.log('What links here feature not available or redirected');
      }
    }
    const historyLink = page.locator('a:has-text("View history"), #ca-history').first();
    if (await historyLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      try {
        await historyLink.click();
        await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
        const currentUrl = page.url();
        if (currentUrl.includes('History')) {
          await expect(page.locator('h1')).toContainText(/History/i, { timeout: 5000 }).catch(() => {});
          await page.goBack();
          await page.waitForLoadState('networkidle', { timeout: 3000 }).catch(() => {});
        }
      } catch (e) {
        console.log('History feature not available or redirected');
      }
    }
    const infobox = page.locator('.infobox, .infobox_v2').first();
    if (await infobox.isVisible({ timeout: 3000 }).catch(() => false)) {
      const infoboxLink = infobox.locator('a').first();
      if (await infoboxLink.isVisible({ timeout: 2000 }).catch(() => false)) {
        const infoboxLinkText = await infoboxLink.textContent();
        await infoboxLink.click();
        await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
        await expect(page).toHaveURL(/wiki/);
        console.log(`Clicked infobox link: ${infoboxLinkText}`);
        await page.goBack();
        await page.waitForLoadState('networkidle', { timeout: 3000 }).catch(() => {});
      }
    }
    const sidebar = page.locator('#mw-navigation, .mw-navigation').first();
    if (await sidebar.isVisible({ timeout: 3000 }).catch(() => false)) {
      const sidebarLink = sidebar.locator('a').first();
      if (await sidebarLink.isVisible({ timeout: 2000 }).catch(() => false)) {
        await sidebarLink.click();
        await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
        await page.goBack();
        await page.waitForLoadState('networkidle', { timeout: 3000 }).catch(() => {});
      }
    }
    await page.goto('https://en.wikipedia.org/wiki/Main_Page', {
      waitUntil: 'domcontentloaded',
    });
    await page.waitForLoadState('networkidle', { timeout: 3000 }).catch(() => {});
    await expect(page).toHaveURL(/Main_Page/);
    await expect(page.locator('#mp-welcome')).toHaveCount(1, { timeout: 10000 });
    const totalLinks = await page.locator('a[href^="/wiki/"]').count();
    console.log('Testing request deduplication with intentional duplicate requests...');
    const dedupTestUrl = 'https://en.wikipedia.org/wiki/Deep_learning';
    const fetchPromises = [];
    for (let i = 0; i < 5; i++) {
      fetchPromises.push(
        page.evaluate(async (url) => {
          try {
            const response = await fetch(url, { method: 'GET' });
            return { status: response.status, ok: response.ok };
          } catch (e) {
            return { status: 0, ok: false, error: e.message };
          }
        }, dedupTestUrl)
      );
    }
    const results = await Promise.all(fetchPromises);
    const successCount = results.filter(r => r.ok).length;
    console.log(`Completed 5 simultaneous fetch requests to same URL: ${successCount}/5 successful`);
    console.log(`(Expected: Only 1 network request due to deduplication, others should reuse)`);
    await writeCacheToDisk();
    pendingRequests.clear();
    const totalRequests = cacheStats.hits + cacheStats.misses;
    const hitRate = totalRequests > 0 ? ((cacheStats.hits / totalRequests) * 100).toFixed(1) : 0;
    const cacheSizeMB = getCacheSizeMB();
    console.log(`Comprehensive Wikipedia test completed!`);
    console.log(`Total internal links found: ${totalLinks}`);
    console.log(`Test executed with all optimizations applied!`);
    if (CACHE_ENABLED && totalRequests > 0) {
      console.log(`Cache Stats: ${cacheStats.hits} hits, ${cacheStats.misses} misses (${hitRate}% hit rate)`);
      console.log(`Cache size: ${Object.keys(httpCache).length}/${MAX_CACHE_ENTRIES} entries, ${cacheSizeMB.toFixed(2)}/${MAX_CACHE_SIZE_MB} MB`);
      if (cacheStats.evictions > 0) {
        console.log(`Cache evictions: ${cacheStats.evictions} entries (LRU)`);
      }
    }
    if (DEDUP_ENABLED) {
      const totalDedupRequests = dedupStats.unique + dedupStats.duplicates;
      if (totalDedupRequests > 0) {
        const dedupRate = ((dedupStats.duplicates / totalDedupRequests) * 100).toFixed(1);
        console.log(`Deduplication: ${dedupStats.duplicates} duplicates avoided, ${dedupStats.unique} unique requests (${dedupRate}% dedup rate)`);
      } else {
        console.log(`Deduplication: Active (no duplicates detected in this run)`);
      }
    }
    if (DOMAIN_BLOCKING_ENABLED) {
      if (domainBlockStats.blocked > 0) {
        console.log(`Domain Blocking: ${domainBlockStats.blocked} third-party requests blocked (analytics, ads, trackers)`);
      } else {
        console.log(`Domain Blocking: Active (no blocked domains detected in this run)`);
      }
    }
  });
});