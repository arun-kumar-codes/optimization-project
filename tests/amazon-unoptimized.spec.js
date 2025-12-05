import { test, expect } from '@playwright/test';

test.describe('Amazon - Comprehensive E2E Flow (Unoptimized)', () => {
  test('complex navigation and shopping exploration flow - UNOPTIMIZED', async ({ page }) => {
    test.setTimeout(120000);
    await page.goto('https://www.amazon.com/');
    await page.waitForLoadState('load');
    await new Promise(resolve => setTimeout(resolve, 2000));
    await expect(page).toHaveTitle(/Amazon/i);
    await new Promise(resolve => setTimeout(resolve, 1000));
    const searchBox = page.locator('#twotabsearchtextbox, input[name="field-keywords"]').first();
    await new Promise(resolve => setTimeout(resolve, 1000));
    await expect(searchBox).toBeVisible();
    await new Promise(resolve => setTimeout(resolve, 500));
    await searchBox.fill('laptop');
    await new Promise(resolve => setTimeout(resolve, 500));
    await searchBox.press('Enter');
    await page.waitForLoadState('load');
    await new Promise(resolve => setTimeout(resolve, 2000));
    await expect(page).toHaveURL(/s\?k=laptop/i);
    await new Promise(resolve => setTimeout(resolve, 1000));
    const productCards = page.locator('[data-component-type="s-search-result"], .s-result-item').first();
    if (await productCards.isVisible({ timeout: 5000 }).catch(() => false)) {
      await new Promise(resolve => setTimeout(resolve, 500));
      await productCards.scrollIntoViewIfNeeded();
      await new Promise(resolve => setTimeout(resolve, 1000));
      const firstProduct = page.locator('[data-component-type="s-search-result"], .s-result-item').first();
      if (await firstProduct.isVisible({ timeout: 2000 }).catch(() => false)) {
        await new Promise(resolve => setTimeout(resolve, 500));
        const productLink = firstProduct.locator('h2 a, a[href*="/dp/"]').first();
        if (await productLink.isVisible({ timeout: 2000 }).catch(() => false)) {
          await new Promise(resolve => setTimeout(resolve, 500));
          await productLink.click();
          await page.waitForLoadState('load');
          await new Promise(resolve => setTimeout(resolve, 2000));
          await expect(page).toHaveURL(/\/dp\//);
          await new Promise(resolve => setTimeout(resolve, 1000));
          await page.goBack({ waitUntil: 'load' });
          await new Promise(resolve => setTimeout(resolve, 2000));
        }
      }
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
    await page.goto('https://www.amazon.com/');
    await page.waitForLoadState('load');
    await new Promise(resolve => setTimeout(resolve, 2000));
    const allMenu = page.locator('#nav-hamburger-menu, #nav-main').first();
    if (await allMenu.isVisible({ timeout: 3000 }).catch(() => false)) {
      await new Promise(resolve => setTimeout(resolve, 500));
      await allMenu.click();
      await new Promise(resolve => setTimeout(resolve, 1500));
      const electronicsLink = page.locator('a:has-text("Electronics"), a[href*="electronics"]').first();
      if (await electronicsLink.isVisible({ timeout: 2000 }).catch(() => false)) {
        await new Promise(resolve => setTimeout(resolve, 500));
        await electronicsLink.click();
        await page.waitForLoadState('load');
        await new Promise(resolve => setTimeout(resolve, 2000));
        await expect(page).toHaveURL(/electronics/i);
        await new Promise(resolve => setTimeout(resolve, 1000));
        await page.goBack({ waitUntil: 'load' });
        await new Promise(resolve => setTimeout(resolve, 2000));
      } else {
        await page.keyboard.press('Escape');
        await new Promise(resolve => setTimeout(resolve, 500));
      }
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
    await page.goto('https://www.amazon.com/s?k=books');
    await page.waitForLoadState('load');
    await new Promise(resolve => setTimeout(resolve, 2000));
    const sortDropdown = page.locator('#s-result-sort-select, select[name="s"]').first();
    if (await sortDropdown.isVisible({ timeout: 3000 }).catch(() => false)) {
      await new Promise(resolve => setTimeout(resolve, 500));
      await sortDropdown.selectOption({ index: 1 });
      await page.waitForLoadState('load');
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
    const priceFilter = page.locator('input[name*="price"], [aria-label*="price"]').first();
    if (await priceFilter.isVisible({ timeout: 3000 }).catch(() => false)) {
      await new Promise(resolve => setTimeout(resolve, 500));
      await priceFilter.scrollIntoViewIfNeeded();
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
    await page.goto('https://www.amazon.com/gp/bestsellers');
    await page.waitForLoadState('load');
    await new Promise(resolve => setTimeout(resolve, 2000));
    const bestsellerCategory = page.locator('a[href*="bestsellers"], .zg-item').first();
    if (await bestsellerCategory.isVisible({ timeout: 3000 }).catch(() => false)) {
      await new Promise(resolve => setTimeout(resolve, 500));
      await bestsellerCategory.click();
      await page.waitForLoadState('load');
      await new Promise(resolve => setTimeout(resolve, 2000));
      await page.goBack({ waitUntil: 'load' });
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
    await page.goto('https://www.amazon.com/');
    await page.waitForLoadState('load');
    await new Promise(resolve => setTimeout(resolve, 2000));
    const dealsLink = page.locator('a:has-text("Today\'s Deals"), a[href*="deals"]').first();
    if (await dealsLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      await new Promise(resolve => setTimeout(resolve, 500));
      await dealsLink.click();
      await page.waitForLoadState('load');
      await new Promise(resolve => setTimeout(resolve, 2000));
      await expect(page).toHaveURL(/deals/i);
      await new Promise(resolve => setTimeout(resolve, 1000));
      await page.goBack({ waitUntil: 'load' });
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
    await page.goto('https://www.amazon.com/s?k=smartphone');
    await page.waitForLoadState('load');
    await new Promise(resolve => setTimeout(resolve, 2000));
    const brandFilter = page.locator('input[type="checkbox"][name*="brand"], li[aria-label*="Brand"]').first();
    if (await brandFilter.isVisible({ timeout: 3000 }).catch(() => false)) {
      await new Promise(resolve => setTimeout(resolve, 500));
      await brandFilter.scrollIntoViewIfNeeded();
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
    await page.goto('https://www.amazon.com/');
    await page.waitForLoadState('load');
    await new Promise(resolve => setTimeout(resolve, 2000));
    const footerLinks = page.locator('footer a, [role="contentinfo"] a').first();
    if (await footerLinks.isVisible({ timeout: 3000 }).catch(() => false)) {
      await new Promise(resolve => setTimeout(resolve, 500));
      const helpLink = page.locator('footer a:has-text("Help"), a[href*="help"]').first();
      if (await helpLink.isVisible({ timeout: 2000 }).catch(() => false)) {
        await new Promise(resolve => setTimeout(resolve, 500));
        await helpLink.click();
        await page.waitForLoadState('load');
        await new Promise(resolve => setTimeout(resolve, 2000));
        await page.goBack({ waitUntil: 'load' });
        await new Promise(resolve => setTimeout(resolve, 2000));
      }
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
    await page.goto('https://www.amazon.com/s?k=electronics');
    await page.waitForLoadState('load');
    await new Promise(resolve => setTimeout(resolve, 2000));
    const pagination = page.locator('a[aria-label*="Next"], .a-pagination .a-last').first();
    if (await pagination.isVisible({ timeout: 3000 }).catch(() => false)) {
      await new Promise(resolve => setTimeout(resolve, 500));
      await pagination.click();
      await page.waitForLoadState('load');
      await new Promise(resolve => setTimeout(resolve, 2000));
      await page.goBack({ waitUntil: 'load' });
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
    await page.goto('https://www.amazon.com/');
    await page.waitForLoadState('load');
    await new Promise(resolve => setTimeout(resolve, 2000));
    const totalLinks = await page.locator('a[href]').count();
    console.log(`Comprehensive Amazon test completed!`);
    console.log(`Total links found: ${totalLinks}`);
    console.log(`Unoptimized test completed (no optimizations applied)`);
  });
});






