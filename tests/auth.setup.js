/**
 * Authentication Setup Script
 * 
 * Week 1 Optimization #2: Authentication State Reuse
 * 
 * This script logs in once and saves the authentication state.
 * All subsequent tests will use this saved state, eliminating repeated logins.
 * 
 * Usage:
 * 1. Configure this script in playwright.config.js (see projects section)
 * 2. Run tests - this setup runs automatically before tests
 * 3. All tests will start with authenticated session
 * 
 * Note: This is a template. Customize the selectors and flow for your specific website.
 */

const { test: setup, expect } = require('@playwright/test');
const path = require('path');
const fs = require('fs');

// Path to save authentication state (at project root, not in tests folder)
const authFile = path.join(__dirname, '..', '.auth', 'user.json');

// Ensure .auth directory exists
const ensureAuthDir = () => {
    const authDir = path.dirname(authFile);
    if (!fs.existsSync(authDir)) {
        fs.mkdirSync(authDir, { recursive: true });
    }
};

// Write an empty storage state file (used when auth is skipped)
const writeEmptyState = () => {
    ensureAuthDir();
    fs.writeFileSync(authFile, JSON.stringify({ cookies: [], origins: [] }, null, 2));
    console.log('ℹ️  Created empty auth file - tests will run without authentication');
};

// Check if auth state file exists and is still valid
const isAuthStateValid = () => {
    if (!fs.existsSync(authFile)) {
        return false;
    }
    
    try {
        // Check if file is not empty (empty state means auth was skipped)
        const fileContent = fs.readFileSync(authFile, 'utf8');
        const state = JSON.parse(fileContent);
        if (!state.cookies || state.cookies.length === 0) {
            return false; // Empty state, need to authenticate
        }
        
        // Check if cookies are expired (check cookie expiration dates)
        const now = Date.now() / 1000; // Convert to seconds (cookie expiry is in seconds)
        const hasValidCookies = state.cookies.some(cookie => {
            // If cookie has no expiry or expiry is in the future, it's valid
            return !cookie.expires || cookie.expires > now;
        });
        
        if (!hasValidCookies) {
            console.log('ℹ️  Auth state cookies are expired, will re-authenticate');
            return false;
        }
        
        // Check if file is fresh (default: 60 minutes, configurable via AUTH_EXPIRY_MINUTES)
        // Note: Even if file is old, if cookies are still valid, we can reuse
        const expiryMinutes = parseInt(process.env.AUTH_EXPIRY_MINUTES || '60', 10);
        const fileAge = Date.now() - fs.statSync(authFile).mtimeMs;
        const maxAge = 1000 * 60 * expiryMinutes; // Convert to milliseconds
        
        if (fileAge >= maxAge) {
            console.log('ℹ️  Auth state file is older than', expiryMinutes, 'minutes, will re-authenticate');
            return false;
        }
        
        return true;
    } catch (error) {
        console.log('ℹ️  Error reading auth state file, will re-authenticate:', error.message);
        return false;
    }
};

setup('authenticate', async ({ page }) => {
    // Check if we should reuse existing auth state
    if (isAuthStateValid() && process.env.PLAYWRIGHT_AUTH_FORCE !== 'true') {
        console.log('Reusing existing authentication state (skip login)');
        console.log('To force re-authentication, set PLAYWRIGHT_AUTH_FORCE=true');
        return;
    }
    
    // Defaults for Saucedemo (public demo site)
    const username = process.env.PLAYWRIGHT_AUTH_USERNAME || 'standard_user';
    const password = process.env.PLAYWRIGHT_AUTH_PASSWORD || 'secret_sauce';
    const loginUrl = process.env.PLAYWRIGHT_AUTH_LOGIN_URL || 'https://www.saucedemo.com/';
    const successUrlPattern = process.env.PLAYWRIGHT_AUTH_SUCCESS_URL || '**/inventory.html';
    const usernameSelector = process.env.PLAYWRIGHT_AUTH_USERNAME_SELECTOR || '#user-name';
    const passwordSelector = process.env.PLAYWRIGHT_AUTH_PASSWORD_SELECTOR || '#password';
    const submitSelector = process.env.PLAYWRIGHT_AUTH_SUBMIT_SELECTOR || '#login-button';
    const successSelector = process.env.PLAYWRIGHT_AUTH_SUCCESS_SELECTOR || '.inventory_list';

    // If credentials are explicitly disabled, skip auth
    if (process.env.AUTH_DISABLED === 'true') {
        console.log('Authentication disabled via AUTH_DISABLED=true. Skipping auth setup.');
        writeEmptyState();
        return;
    }

    console.log('Starting authentication...');

    try {
        // Navigate to login page
        await page.goto(loginUrl, { waitUntil: 'domcontentloaded' });

        // Fill credentials
        await page.fill(usernameSelector, username);
        await page.fill(passwordSelector, password);

        // Submit and wait for navigation or success indicator
        await Promise.all([
            page.waitForURL(successUrlPattern, { waitUntil: 'domcontentloaded', timeout: 15000 }).catch(() => { }),
            page.click(submitSelector),
        ]);

        // Wait for success indicator if provided
        if (successSelector) {
            await expect(page.locator(successSelector)).toBeVisible({ timeout: 15000 });
        }

        console.log('Logged in, current URL:', page.url());

        // Save authentication state (cookies, localStorage, sessionStorage)
        ensureAuthDir();
        await page.context().storageState({ path: authFile });

        console.log('Authentication state saved to:', authFile);
    } catch (error) {
        console.error('Authentication failed:', error);
        console.log('Falling back to unauthenticated state.');
        writeEmptyState();
    }
});

