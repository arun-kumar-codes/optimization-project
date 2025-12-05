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
test.describe('Amazon - Comprehensive E2E Flow (Optimized)', () => {
  test('complex navigation and shopping exploration flow', async ({ page }) => {
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
        /\/api\/|suggestions|search|recommendations/i.test(url);
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
    await page.goto('https://www.amazon.com/', {
      waitUntil: 'domcontentloaded',
    });
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    await expect(page).toHaveTitle(/Amazon/i);
    const searchBox = page.locator('#twotabsearchtextbox, input[name="field-keywords"]').first();
    await expect(searchBox).toHaveCount(1, { timeout: 10000 });
    await searchBox.fill('laptop');
    await searchBox.press('Enter');
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    await expect(page).toHaveURL(/s\?k=laptop/i);
    const productCards = page.locator('[data-component-type="s-search-result"], .s-result-item').first();
    if (await productCards.isVisible({ timeout: 5000 }).catch(() => false)) {
      await productCards.scrollIntoViewIfNeeded();
      await page.waitForTimeout(500);
      const firstProduct = page.locator('[data-component-type="s-search-result"], .s-result-item').first();
      if (await firstProduct.isVisible({ timeout: 2000 }).catch(() => false)) {
        const productLink = firstProduct.locator('h2 a, a[href*="/dp/"]').first();
        if (await productLink.isVisible({ timeout: 2000 }).catch(() => false)) {
          await productLink.click();
          await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
          await expect(page).toHaveURL(/\/dp\//);
          await page.goBack();
          await page.waitForLoadState('networkidle', { timeout: 3000 }).catch(() => {});
        }
      }
    }
    await page.goto('https://www.amazon.com/', {
      waitUntil: 'domcontentloaded',
    });
    await page.waitForLoadState('networkidle', { timeout: 3000 }).catch(() => {});
    const allMenu = page.locator('#nav-hamburger-menu, #nav-main').first();
    if (await allMenu.isVisible({ timeout: 3000 }).catch(() => false)) {
      await allMenu.click();
      await page.waitForTimeout(1000);
      const electronicsLink = page.locator('a:has-text("Electronics"), a[href*="electronics"]').first();
      if (await electronicsLink.isVisible({ timeout: 2000 }).catch(() => false)) {
        await electronicsLink.click();
        await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
        await expect(page).toHaveURL(/electronics/i);
        await page.goBack();
        await page.waitForLoadState('networkidle', { timeout: 3000 }).catch(() => {});
      } else {
        await page.keyboard.press('Escape');
      }
    }
    await page.goto('https://www.amazon.com/s?k=books', {
      waitUntil: 'domcontentloaded',
    });
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    const sortDropdown = page.locator('#s-result-sort-select, select[name="s"]').first();
    if (await sortDropdown.isVisible({ timeout: 3000 }).catch(() => false)) {
      await sortDropdown.selectOption({ index: 1 });
      await page.waitForLoadState('networkidle', { timeout: 3000 }).catch(() => {});
    }
    const priceFilter = page.locator('input[name*="price"], [aria-label*="price"]').first();
    if (await priceFilter.isVisible({ timeout: 3000 }).catch(() => false)) {
      await priceFilter.scrollIntoViewIfNeeded();
      await page.waitForTimeout(500);
    }
    await page.goto('https://www.amazon.com/gp/bestsellers', {
      waitUntil: 'domcontentloaded',
    });
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    const bestsellerCategory = page.locator('a[href*="bestsellers"], .zg-item').first();
    if (await bestsellerCategory.isVisible({ timeout: 3000 }).catch(() => false)) {
      await bestsellerCategory.click();
      await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
      await page.goBack();
      await page.waitForLoadState('networkidle', { timeout: 3000 }).catch(() => {});
    }
    await page.goto('https://www.amazon.com/', {
      waitUntil: 'domcontentloaded',
    });
    await page.waitForLoadState('networkidle', { timeout: 3000 }).catch(() => {});
    const dealsLink = page.locator('a:has-text("Today\'s Deals"), a[href*="deals"]').first();
    if (await dealsLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      await dealsLink.click();
      await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
      await expect(page).toHaveURL(/deals/i);
      await page.goBack();
      await page.waitForLoadState('networkidle', { timeout: 3000 }).catch(() => {});
    }
    await page.goto('https://www.amazon.com/s?k=smartphone', {
      waitUntil: 'domcontentloaded',
    });
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    const brandFilter = page.locator('input[type="checkbox"][name*="brand"], li[aria-label*="Brand"]').first();
    if (await brandFilter.isVisible({ timeout: 3000 }).catch(() => false)) {
      await brandFilter.scrollIntoViewIfNeeded();
      await page.waitForTimeout(500);
    }
    await page.goto('https://www.amazon.com/', {
      waitUntil: 'domcontentloaded',
    });
    await page.waitForLoadState('networkidle', { timeout: 3000 }).catch(() => {});
    const footerLinks = page.locator('footer a, [role="contentinfo"] a').first();
    if (await footerLinks.isVisible({ timeout: 3000 }).catch(() => false)) {
      const helpLink = page.locator('footer a:has-text("Help"), a[href*="help"]').first();
      if (await helpLink.isVisible({ timeout: 2000 }).catch(() => false)) {
        await helpLink.click();
        await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
        await page.goBack();
        await page.waitForLoadState('networkidle', { timeout: 3000 }).catch(() => {});
      }
    }
    await page.goto('https://www.amazon.com/s?k=electronics', {
      waitUntil: 'domcontentloaded',
    });
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    const pagination = page.locator('a[aria-label*="Next"], .a-pagination .a-last').first();
    if (await pagination.isVisible({ timeout: 3000 }).catch(() => false)) {
      await pagination.click();
      await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
      await page.goBack();
      await page.waitForLoadState('networkidle', { timeout: 3000 }).catch(() => {});
    }
    await page.goto('https://www.amazon.com/', {
      waitUntil: 'domcontentloaded',
    });
    await page.waitForLoadState('networkidle', { timeout: 3000 }).catch(() => {});
    const totalLinks = await page.locator('a[href]').count();
    console.log(`Comprehensive Amazon test completed!`);
    console.log(`Total links found: ${totalLinks}`);
    await writeCacheToDisk();
    pendingRequests.clear();
    const totalRequests = cacheStats.hits + cacheStats.misses;
    const hitRate = totalRequests > 0 ? ((cacheStats.hits / totalRequests) * 100).toFixed(1) : 0;
    const cacheSizeMB = getCacheSizeMB();
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





