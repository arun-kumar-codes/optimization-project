import { test, expect } from '@playwright/test';

test.describe('Airbnb - Comprehensive E2E Flow (Unoptimized)', () => {
  test('complex navigation and exploration flow - UNOPTIMIZED', async ({ page }) => {
    test.setTimeout(120000);
    await page.goto('https://www.airbnb.com/');
    await page.waitForLoadState('load');
    await new Promise(resolve => setTimeout(resolve, 2000));
    await expect(page).toHaveTitle(/Airbnb/i);
    await new Promise(resolve => setTimeout(resolve, 1000));
    await page.goto('https://www.airbnb.com/s/Paris--France/homes', {
      waitUntil: 'load',
    });
    await new Promise(resolve => setTimeout(resolve, 2000));
    await new Promise(resolve => setTimeout(resolve, 1000));
    await page.waitForLoadState('load');
    await new Promise(resolve => setTimeout(resolve, 1000));
    const closeModal = page.locator('button[aria-label*="Close"], button[data-testid*="close"], button:has-text("Close")').first();
    if (await closeModal.isVisible({ timeout: 2000 }).catch(() => false)) {
      await new Promise(resolve => setTimeout(resolve, 500));
      await closeModal.click();
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    const listings = page.locator('[data-testid*="listing"], [itemprop="itemListElement"], article a').first();
    if (await listings.isVisible({ timeout: 5000 }).catch(() => false)) {
      await new Promise(resolve => setTimeout(resolve, 500));
      await listings.scrollIntoViewIfNeeded();
      await new Promise(resolve => setTimeout(resolve, 1000));
      const firstListingLink = page.locator('[data-testid*="listing"] a, [itemprop="itemListElement"] a, article a[href*="/rooms/"]').first();
      if (await firstListingLink.isVisible({ timeout: 2000 }).catch(() => false)) {
        await new Promise(resolve => setTimeout(resolve, 500));
        await firstListingLink.click({ force: true });
        await page.waitForLoadState('load');
        await new Promise(resolve => setTimeout(resolve, 2000));
        await expect(page).toHaveURL(/rooms|stays/i, { timeout: 10000 }).catch(() => {});
        await new Promise(resolve => setTimeout(resolve, 1000));
        await page.goBack({ waitUntil: 'load' });
        await new Promise(resolve => setTimeout(resolve, 2000));
      }
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
    await page.goto('https://www.airbnb.com/');
    await page.waitForLoadState('load');
    await new Promise(resolve => setTimeout(resolve, 2000));
    const exploreLink = page.locator('a[href*="experiences"], a:has-text("Experiences")').first();
    if (await exploreLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      await new Promise(resolve => setTimeout(resolve, 500));
      await exploreLink.click();
      await page.waitForLoadState('load');
      await new Promise(resolve => setTimeout(resolve, 2000));
      await expect(page).toHaveURL(/experiences/i);
      await new Promise(resolve => setTimeout(resolve, 1000));
      await page.goBack({ waitUntil: 'load' });
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
    const becomeHostLink = page.locator('a[href*="host"], a:has-text("Become a Host")').first();
    if (await becomeHostLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      await new Promise(resolve => setTimeout(resolve, 500));
      await becomeHostLink.click();
      await page.waitForLoadState('load');
      await new Promise(resolve => setTimeout(resolve, 2000));
      await expect(page).toHaveURL(/host/i);
      await new Promise(resolve => setTimeout(resolve, 1000));
      await page.goBack({ waitUntil: 'load' });
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
    await page.goto('https://www.airbnb.com/s/Paris--France/homes');
    await page.waitForLoadState('load');
    await new Promise(resolve => setTimeout(resolve, 2000));
    const filterButton = page.locator('button:has-text("Filters"), [data-testid*="filter"]').first();
    if (await filterButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      await new Promise(resolve => setTimeout(resolve, 500));
      await filterButton.click();
      await new Promise(resolve => setTimeout(resolve, 1500));
      const priceFilter = page.locator('input[type="range"], [aria-label*="price"]').first();
      if (await priceFilter.isVisible({ timeout: 2000 }).catch(() => false)) {
        console.log('Price filter found');
      }
      await new Promise(resolve => setTimeout(resolve, 500));
      const closeFilter = page.locator('button:has-text("Close"), button[aria-label*="close"]').first();
      if (await closeFilter.isVisible({ timeout: 1000 }).catch(() => false)) {
        await closeFilter.click();
      } else {
        await page.keyboard.press('Escape');
      }
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
    const sortButton = page.locator('button:has-text("Sort"), select[name*="sort"]').first();
    if (await sortButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      await new Promise(resolve => setTimeout(resolve, 500));
      await sortButton.click();
      await new Promise(resolve => setTimeout(resolve, 1000));
      const sortOption = page.locator('button:has-text("Price"), option[value*="price"]').first();
      if (await sortOption.isVisible({ timeout: 2000 }).catch(() => false)) {
        await new Promise(resolve => setTimeout(resolve, 500));
        await sortOption.click();
        await page.waitForLoadState('load');
        await new Promise(resolve => setTimeout(resolve, 2000));
      } else {
        await page.keyboard.press('Escape');
      }
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
    await page.goto('https://www.airbnb.com/');
    await page.waitForLoadState('load');
    await new Promise(resolve => setTimeout(resolve, 2000));
    const footerLinks = page.locator('footer a, [role="contentinfo"] a').first();
    if (await footerLinks.isVisible({ timeout: 3000 }).catch(() => false)) {
      await new Promise(resolve => setTimeout(resolve, 500));
      const supportLink = page.locator('footer a:has-text("Support"), a[href*="support"]').first();
      if (await supportLink.isVisible({ timeout: 2000 }).catch(() => false)) {
        await new Promise(resolve => setTimeout(resolve, 500));
        await supportLink.click();
        await page.waitForLoadState('load');
        await new Promise(resolve => setTimeout(resolve, 2000));
        await page.goBack({ waitUntil: 'load' });
        await new Promise(resolve => setTimeout(resolve, 2000));
      }
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
    await page.goto('https://www.airbnb.com/s/New-York--United-States/homes');
    await page.waitForLoadState('load');
    await new Promise(resolve => setTimeout(resolve, 2000));
    const mapToggle = page.locator('button[aria-label*="map"], button:has-text("Map")').first();
    if (await mapToggle.isVisible({ timeout: 3000 }).catch(() => false)) {
      await new Promise(resolve => setTimeout(resolve, 500));
      await mapToggle.click();
      await new Promise(resolve => setTimeout(resolve, 2000));
      await mapToggle.click();
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
    await page.goto('https://www.airbnb.com/');
    await page.waitForLoadState('load');
    await new Promise(resolve => setTimeout(resolve, 2000));
    const totalLinks = await page.locator('a[href]').count();
    console.log(`Comprehensive Airbnb test completed!`);
    console.log(`Total links found: ${totalLinks}`);
    console.log(`Unoptimized test completed (no optimizations applied)`);
  });
});


