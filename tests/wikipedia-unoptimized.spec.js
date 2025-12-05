import { test, expect } from '@playwright/test';
test.describe('Wikipedia - Comprehensive E2E Flow (Unoptimized)', () => {
  test('complex navigation and content exploration flow - UNOPTIMIZED', async ({ page }) => {
    test.setTimeout(120000);
    await page.goto('https://en.wikipedia.org/wiki/Main_Page');
    await page.waitForLoadState('load');
    await new Promise(resolve => setTimeout(resolve, 2000));
    await expect(page).toHaveTitle(/Wikipedia/i);
    await new Promise(resolve => setTimeout(resolve, 1000));
    await expect(page.locator('#mp-welcome')).toBeVisible();
    await new Promise(resolve => setTimeout(resolve, 1000));
    const searchBox = page.locator('#searchInput');
    await expect(searchBox).toBeVisible();
    await new Promise(resolve => setTimeout(resolve, 500));
    await searchBox.fill('Artificial Intelligence');
    await new Promise(resolve => setTimeout(resolve, 500));
    await page.keyboard.press('Enter');
    await page.waitForLoadState('load');
    await new Promise(resolve => setTimeout(resolve, 2000));
    await expect(page).toHaveURL(/Artificial_intelligence/i);
    await expect(page.locator('h1#firstHeading')).toContainText(/Artificial intelligence/i);
    await new Promise(resolve => setTimeout(resolve, 1000));
    await new Promise(resolve => setTimeout(resolve, 1000));
    const historySection = page.locator('#History').or(page.locator('span:has-text("History")')).first();
    await historySection.scrollIntoViewIfNeeded();
    await new Promise(resolve => setTimeout(resolve, 1000));
    await historySection.click();
    await page.waitForLoadState('load');
    await new Promise(resolve => setTimeout(resolve, 2000));
    await expect(page.locator('#History, span:has-text("History")').first()).toBeVisible();
    await new Promise(resolve => setTimeout(resolve, 1000));
    await new Promise(resolve => setTimeout(resolve, 1000));
    const firstInternalLink = page.locator('a[href^="/wiki/"]:not([href*="#"])').first();
    await firstInternalLink.scrollIntoViewIfNeeded();
    await new Promise(resolve => setTimeout(resolve, 500));
    const linkText = await firstInternalLink.textContent();
    await firstInternalLink.click({ force: true });
    await page.waitForLoadState('load');
    await new Promise(resolve => setTimeout(resolve, 2000));
    await expect(page.locator('h1#firstHeading')).toBeVisible();
    console.log(`Navigated to article: ${linkText}`);
    await new Promise(resolve => setTimeout(resolve, 1000));
    await new Promise(resolve => setTimeout(resolve, 500));
    await page.goBack();
    await page.waitForLoadState('load');
    await new Promise(resolve => setTimeout(resolve, 2000));
    await expect(page.locator('h1#firstHeading')).toContainText(/Artificial intelligence/i);
    await new Promise(resolve => setTimeout(resolve, 1000));
    await page.goForward();
    await page.waitForLoadState('load');
    await new Promise(resolve => setTimeout(resolve, 2000));
    await expect(page.locator('h1#firstHeading')).toBeVisible();
    await new Promise(resolve => setTimeout(resolve, 1000));
    await new Promise(resolve => setTimeout(resolve, 1000));
    await page.goto('https://en.wikipedia.org/wiki/Artificial_intelligence');
    await page.waitForLoadState('load');
    await new Promise(resolve => setTimeout(resolve, 2000));
    const langSelector = page.locator('#p-lang-btn, .interlanguage-link').first();
    if (await langSelector.isVisible({ timeout: 2000 }).catch(() => false)) {
      await new Promise(resolve => setTimeout(resolve, 500));
      await langSelector.click();
      await new Promise(resolve => setTimeout(resolve, 1000));
      const spanishLink = page.locator('a[lang="es"], a:has-text("Español")').first();
      if (await spanishLink.isVisible({ timeout: 2000 }).catch(() => false)) {
        await spanishLink.click();
        await page.waitForLoadState('load');
        await new Promise(resolve => setTimeout(resolve, 2000));
        await expect(page).toHaveURL(/es\.wikipedia\.org/);
        await new Promise(resolve => setTimeout(resolve, 1000));
        await page.goto('https://en.wikipedia.org/wiki/Artificial_intelligence');
        await page.waitForLoadState('load');
        await new Promise(resolve => setTimeout(resolve, 2000));
      }
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
    const categoryLink = page.locator('a[href^="/wiki/Category:"]').first();
    if (await categoryLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      await new Promise(resolve => setTimeout(resolve, 500));
      const categoryText = await categoryLink.textContent();
      await categoryLink.click();
      await page.waitForLoadState('load');
      await new Promise(resolve => setTimeout(resolve, 2000));
      await expect(page).toHaveURL(/Category:/);
      console.log(`Navigated to category: ${categoryText}`);
      await new Promise(resolve => setTimeout(resolve, 1000));
      await page.goBack();
      await page.waitForLoadState('load');
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
    const toc = page.locator('#toc, .toc').first();
    if (await toc.isVisible({ timeout: 3000 }).catch(() => false)) {
      await new Promise(resolve => setTimeout(resolve, 500));
      const tocLink = toc.locator('a').first();
      const tocLinkText = await tocLink.textContent();
      await tocLink.click();
      await page.waitForLoadState('load');
      await new Promise(resolve => setTimeout(resolve, 2000));
      await expect(page.locator(`#${tocLinkText?.replace(/\s/g, '_')}, span:has-text("${tocLinkText}")`).first()).toBeVisible({ timeout: 5000 }).catch(() => {});
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
    await page.goto('https://en.wikipedia.org/wiki/Main_Page');
    await page.waitForLoadState('load');
    await new Promise(resolve => setTimeout(resolve, 2000));
    await page.locator('#searchInput').fill('Machine Learning');
    await new Promise(resolve => setTimeout(resolve, 1500));
    const suggestions = page.locator('.suggestions-results, .suggestions').first();
    if (await suggestions.isVisible({ timeout: 2000 }).catch(() => false)) {
      await new Promise(resolve => setTimeout(resolve, 500));
      const firstSuggestion = suggestions.locator('a, li').first();
      await firstSuggestion.click();
      await page.waitForLoadState('load');
      await new Promise(resolve => setTimeout(resolve, 2000));
      await expect(page).toHaveURL(/wiki/);
    } else {
      await page.keyboard.press('Enter');
      await page.waitForLoadState('load');
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
    await new Promise(resolve => setTimeout(resolve, 1000));
    await page.goto('https://en.wikipedia.org/wiki/Special:Random');
    await page.waitForLoadState('load');
    await new Promise(resolve => setTimeout(resolve, 2000));
    await expect(page).toHaveURL(/wiki/);
    await expect(page.locator('h1#firstHeading')).toBeVisible();
    const randomArticleTitle = await page.locator('h1#firstHeading').textContent();
    console.log(`Random article: ${randomArticleTitle}`);
    await new Promise(resolve => setTimeout(resolve, 1000));
    await new Promise(resolve => setTimeout(resolve, 1000));
    const referencesSection = page.locator('#References, #Notes, span:has-text("References")').first();
    if (await referencesSection.isVisible({ timeout: 3000 }).catch(() => false)) {
      await referencesSection.scrollIntoViewIfNeeded();
      await new Promise(resolve => setTimeout(resolve, 1000));
      const refLink = page.locator('ol.references a, .reference a').first();
      if (await refLink.isVisible({ timeout: 2000 }).catch(() => false)) {
        await new Promise(resolve => setTimeout(resolve, 500));
        const refUrl = await refLink.getAttribute('href');
        if (refUrl && refUrl.startsWith('http')) {
          console.log(`Reference link found: ${refUrl}`);
        }
      }
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
    await new Promise(resolve => setTimeout(resolve, 1000));
    await page.goto('https://en.wikipedia.org/wiki/Main_Page');
    await page.waitForLoadState('load');
    await new Promise(resolve => setTimeout(resolve, 2000));
    const featuredSection = page.locator('#mp-dyk, .mp-dyk').first();
    if (await featuredSection.isVisible({ timeout: 3000 }).catch(() => false)) {
      await new Promise(resolve => setTimeout(resolve, 500));
      const dykLink = featuredSection.locator('a').first();
      if (await dykLink.isVisible({ timeout: 2000 }).catch(() => false)) {
        await dykLink.click();
        await page.waitForLoadState('load');
        await new Promise(resolve => setTimeout(resolve, 2000));
        await expect(page).toHaveURL(/wiki/);
        await new Promise(resolve => setTimeout(resolve, 1000));
        await page.goBack();
        await page.waitForLoadState('load');
        await new Promise(resolve => setTimeout(resolve, 2000));
      }
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
    const newsSection = page.locator('#mp-itn, .mp-itn').first();
    if (await newsSection.isVisible({ timeout: 3000 }).catch(() => false)) {
      await new Promise(resolve => setTimeout(resolve, 500));
      const newsLink = newsSection.locator('a').first();
      if (await newsLink.isVisible({ timeout: 2000 }).catch(() => false)) {
        await newsLink.click();
        await page.waitForLoadState('load');
        await new Promise(resolve => setTimeout(resolve, 2000));
        await expect(page).toHaveURL(/wiki/);
        await new Promise(resolve => setTimeout(resolve, 1000));
        await page.goBack();
        await page.waitForLoadState('load');
        await new Promise(resolve => setTimeout(resolve, 2000));
      }
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
    const onThisDaySection = page.locator('#mp-otd, .mp-otd').first();
    if (await onThisDaySection.isVisible({ timeout: 3000 }).catch(() => false)) {
      await new Promise(resolve => setTimeout(resolve, 500));
      const otdLink = onThisDaySection.locator('a').first();
      if (await otdLink.isVisible({ timeout: 2000 }).catch(() => false)) {
        await otdLink.click();
        await page.waitForLoadState('load');
        await new Promise(resolve => setTimeout(resolve, 2000));
        await expect(page).toHaveURL(/wiki/);
        await new Promise(resolve => setTimeout(resolve, 1000));
        await page.goBack();
        await page.waitForLoadState('load');
        await new Promise(resolve => setTimeout(resolve, 2000));
      }
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
    await page.goto('https://en.wikipedia.org/wiki/Artificial_intelligence');
    await page.waitForLoadState('load');
    await new Promise(resolve => setTimeout(resolve, 2000));
    const editLink = page.locator('a:has-text("Edit"), a:has-text("View source"), #ca-edit').first();
    if (await editLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      await new Promise(resolve => setTimeout(resolve, 500));
      const editHref = await editLink.getAttribute('href');
      if (editHref) {
        console.log(`Edit link found: ${editHref}`);
      }
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
    await new Promise(resolve => setTimeout(resolve, 1000));
    const whatLinksHere = page.locator('a:has-text("What links here"), #t-whatlinkshere').first();
    if (await whatLinksHere.isVisible({ timeout: 3000 }).catch(() => false)) {
      await new Promise(resolve => setTimeout(resolve, 500));
      await whatLinksHere.click();
      await page.waitForLoadState('load');
      await new Promise(resolve => setTimeout(resolve, 2000));
      await expect(page).toHaveURL(/Special:WhatLinksHere/);
      await new Promise(resolve => setTimeout(resolve, 1000));
      await expect(page.locator('h1')).toContainText(/What links here/i);
      await new Promise(resolve => setTimeout(resolve, 1000));
      await page.goBack();
      await page.waitForLoadState('load');
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
    const historyLink = page.locator('a:has-text("View history"), #ca-history').first();
    if (await historyLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      try {
        await new Promise(resolve => setTimeout(resolve, 500));
        await historyLink.click();
        await page.waitForLoadState('load');
        await new Promise(resolve => setTimeout(resolve, 2000));
        const currentUrl = page.url();
        if (currentUrl.includes('History')) {
          await expect(page.locator('h1')).toContainText(/History/i, { timeout: 5000 }).catch(() => {});
          await new Promise(resolve => setTimeout(resolve, 1000));
          await page.goBack();
          await page.waitForLoadState('load');
          await new Promise(resolve => setTimeout(resolve, 2000));
        }
      } catch (e) {
        console.log('History feature not available or redirected');
      }
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
    const infobox = page.locator('.infobox, .infobox_v2').first();
    if (await infobox.isVisible({ timeout: 3000 }).catch(() => false)) {
      await new Promise(resolve => setTimeout(resolve, 500));
      const infoboxLink = infobox.locator('a').first();
      if (await infoboxLink.isVisible({ timeout: 2000 }).catch(() => false)) {
        await new Promise(resolve => setTimeout(resolve, 500));
        const infoboxLinkText = await infoboxLink.textContent();
        await infoboxLink.click();
        await page.waitForLoadState('load');
        await new Promise(resolve => setTimeout(resolve, 2000));
        await expect(page).toHaveURL(/wiki/);
        console.log(`Clicked infobox link: ${infoboxLinkText}`);
        await new Promise(resolve => setTimeout(resolve, 1000));
        await page.goBack();
        await page.waitForLoadState('load');
        await new Promise(resolve => setTimeout(resolve, 2000));
      }
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
    const sidebar = page.locator('#mw-navigation, .mw-navigation').first();
    if (await sidebar.isVisible({ timeout: 3000 }).catch(() => false)) {
      await new Promise(resolve => setTimeout(resolve, 500));
      const sidebarLink = sidebar.locator('a').first();
      if (await sidebarLink.isVisible({ timeout: 2000 }).catch(() => false)) {
        await sidebarLink.click();
        await page.waitForLoadState('load');
        await new Promise(resolve => setTimeout(resolve, 2000));
        await page.goBack();
        await page.waitForLoadState('load');
        await new Promise(resolve => setTimeout(resolve, 2000));
      }
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
    await page.goto('https://en.wikipedia.org/wiki/Main_Page');
    await page.waitForLoadState('load');
    await new Promise(resolve => setTimeout(resolve, 2000));
    await expect(page).toHaveURL(/Main_Page/);
    await expect(page.locator('#mp-welcome')).toBeVisible();
    await new Promise(resolve => setTimeout(resolve, 1000));
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
    console.log(`(Note: No deduplication - all 5 requests go to network in unoptimized version)`);
    console.log(`Total internal links found: ${totalLinks}`);
    console.log(`Unoptimized test completed (no optimizations applied)`);
  });
});