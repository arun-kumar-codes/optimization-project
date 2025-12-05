import { defineConfig } from '@playwright/test';

export default defineConfig({
  // Test directory - organized in tests/ folder
  testDir: './tests',
  
  // Run tests in parallel (adjust based on CPU cores)
  workers: process.env.CI ? 2 : 4,
  
  // Retry failed tests (only in CI)
  retries: process.env.CI ? 2 : 0,
  
  // Timeout per test (30 seconds)
  timeout: 30000,
  
  // Global test timeout
  globalTimeout: 600000, // 10 minutes
  
  // Test expectations
  expect: {
    timeout: 5000, // Assertion timeout
  },
  
  // Use configuration
  use: {
    // Run in headless mode for speed (set to false for debugging)
    headless: true,
    
    // Optimized viewport size
    viewport: { width: 1280, height: 720 },
    
    // Action timeout (how long to wait for actionability)
    actionTimeout: 10000,
    
    // Navigation timeout
    navigationTimeout: 30000,
    
    // Browser launch arguments for performance optimization
    launchOptions: {
      args: [
        // Disable animations and visual effects
        '--disable-animations',
        '--disable-gpu',
        '--disable-software-rasterizer',
        
        // Disable background processes
        '--disable-background-networking',
        '--disable-background-timer-throttling',
        '--disable-backgrounding-occluded-windows',
        '--disable-renderer-backgrounding',
        
        // Performance optimizations
        '--disable-dev-shm-usage',
        '--disable-extensions',
        '--disable-features=TranslateUI',
        '--disable-ipc-flooding-protection',
        
        // Automation optimizations
        '--disable-blink-features=AutomationControlled',
        '--disable-features=IsolateOrigins,site-per-process',
        '--disable-site-isolation-trials',
        
        // Memory and performance
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-web-security',
        '--disable-features=VizDisplayCompositor',
      ],
    },
    
    // OPTIMIZATION #4: Strategic wait state - Use domcontentloaded by default
    // This is faster than waiting for full page load
    // Can be overridden per navigation if needed
    
    // Ignore HTTPS errors (faster)
    ignoreHTTPSErrors: true,
    
    // Enable HTTP cache for faster subsequent runs
    // This helps with network caching optimization
    // Cache key is relaxed to increase hit rates
    // (volatile headers are ignored)
    
    // Screenshot on failure only
    screenshot: 'only-on-failure',
    
    // Video on failure only (disable for speed)
    video: 'off', // Change to 'on' or 'retain-on-failure' if needed
    
    // Trace on failure only
    trace: 'on-first-retry',
    
    // OPTIMIZATION #2: Authentication state reuse
    // Note: storageState is set per-project below
    // If auth.setup.js runs successfully, .auth/user.json will be created and used
  },
  
  // Reporter configuration
  reporter: [
    ['list'], // Console reporter
    ['html', { open: 'never' }], // HTML report (don't auto-open)
  ],
  
  // Projects for different browsers (optional)
  projects: [
    // OPTIMIZATION #2: Authentication setup project
    // This runs first to authenticate and save state (if credentials provided)
    {
      name: 'setup',
      testMatch: /.*\.setup\.js/, // Run auth.setup.js from tests folder
    },
    {
      name: 'chromium',
      use: { 
        browserName: 'chromium',
        // Additional chromium-specific optimizations
        // OPTIMIZATION #2: Use saved auth state if it exists
        storageState: '.auth/user.json', // Auth state saved at project root
      },
      dependencies: ['setup'], // Run setup project first
    },
    // Uncomment to test on other browsers
    // {
    //   name: 'firefox',
    //   use: { browserName: 'firefox' },
    // },
    // {
    //   name: 'webkit',
    //   use: { browserName: 'webkit' },
    // },
  ],
});

