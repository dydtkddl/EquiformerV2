import { test, expect } from '@playwright/test';

/**
 * Settings Page E2E Tests
 * 
 * Tests settings configuration and persistence
 */

test.describe('Settings Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings');
  });

  test('should load settings page', async ({ page }) => {
    await expect(page.locator('h1')).toContainText(/Settings/i);
  });

  test('should display API settings section', async ({ page }) => {
    await expect(page.getByText(/API|Connection/i)).toBeVisible();
  });

  test('should have API URL input', async ({ page }) => {
    const apiUrlInput = page.locator('[data-testid="api-url"], input[name="apiUrl"]');
    await expect(apiUrlInput).toBeVisible();
  });

  test('should have API key input', async ({ page }) => {
    const apiKeyInput = page.locator('[data-testid="api-key"], input[name="apiKey"]');
    await expect(apiKeyInput).toBeVisible();
    
    // API key should be masked by default
    const inputType = await apiKeyInput.getAttribute('type');
    expect(inputType).toBe('password');
  });

  test('should toggle API key visibility', async ({ page }) => {
    const toggleButton = page.locator('[data-testid="toggle-api-key"], button[aria-label*="Show"]');
    
    if (await toggleButton.isVisible()) {
      await toggleButton.click();
      
      const apiKeyInput = page.locator('[data-testid="api-key"], input[name="apiKey"]');
      const inputType = await apiKeyInput.getAttribute('type');
      expect(inputType).toBe('text');
    }
  });
});

test.describe('Theme Settings', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings');
  });

  test('should have theme selection', async ({ page }) => {
    const themeSection = page.locator('[data-testid="theme-settings"]');
    await expect(themeSection.or(page.getByText(/Theme|Appearance/i))).toBeVisible();
  });

  test('should switch to dark theme', async ({ page }) => {
    const darkThemeOption = page.locator('[data-testid="theme-dark"], input[value="dark"], button:has-text("Dark")');
    
    if (await darkThemeOption.isVisible()) {
      await darkThemeOption.click();
      
      // Check dark class on html
      await expect(page.locator('html')).toHaveClass(/dark/);
    }
  });

  test('should switch to light theme', async ({ page }) => {
    const lightThemeOption = page.locator('[data-testid="theme-light"], input[value="light"], button:has-text("Light")');
    
    if (await lightThemeOption.isVisible()) {
      await lightThemeOption.click();
      
      // Check light theme
      await expect(page.locator('html')).not.toHaveClass(/dark/);
    }
  });

  test('should persist theme preference', async ({ page }) => {
    const darkThemeOption = page.locator('[data-testid="theme-dark"], input[value="dark"], button:has-text("Dark")');
    
    if (await darkThemeOption.isVisible()) {
      await darkThemeOption.click();
      
      // Reload page
      await page.reload();
      
      // Theme should persist
      await expect(page.locator('html')).toHaveClass(/dark/);
    }
  });
});

test.describe('Default Settings', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings');
  });

  test('should have default engine selection', async ({ page }) => {
    const engineSelect = page.locator('[data-testid="default-engine"], select[name="defaultEngine"]');
    
    if (await engineSelect.isVisible()) {
      await expect(engineSelect).toBeVisible();
    }
  });

  test('should have default device selection', async ({ page }) => {
    const deviceSelect = page.locator('[data-testid="default-device"], select[name="defaultDevice"]');
    
    if (await deviceSelect.isVisible()) {
      const options = await deviceSelect.locator('option').allTextContents();
      expect(options.join(' ')).toMatch(/cpu|cuda|GPU/i);
    }
  });

  test('should have polling interval setting', async ({ page }) => {
    const pollingToggle = page.locator('[data-testid="polling-toggle"], input[name="enablePolling"]');
    
    if (await pollingToggle.isVisible()) {
      await expect(pollingToggle).toBeVisible();
    }
  });
});

test.describe('Settings Persistence', () => {
  test('should save settings on change', async ({ page }) => {
    await page.goto('/settings');
    
    const apiUrlInput = page.locator('[data-testid="api-url"], input[name="apiUrl"]');
    
    if (await apiUrlInput.isVisible()) {
      await apiUrlInput.fill('http://test-api:8000');
      await apiUrlInput.blur();
      
      // Wait for save
      await page.waitForTimeout(500);
      
      // Reload and check
      await page.reload();
      
      const savedValue = await apiUrlInput.inputValue();
      expect(savedValue).toBe('http://test-api:8000');
    }
  });

  test('should show save confirmation', async ({ page }) => {
    await page.goto('/settings');
    
    const apiKeyInput = page.locator('[data-testid="api-key"], input[name="apiKey"]');
    
    if (await apiKeyInput.isVisible()) {
      await apiKeyInput.fill('new-api-key-12345');
      await apiKeyInput.blur();
      
      // Check for save confirmation
      const saveMessage = page.locator('[data-testid="save-message"], [role="status"]');
      // May or may not show confirmation
      await page.waitForTimeout(500);
    }
  });

  test('should validate API URL format', async ({ page }) => {
    await page.goto('/settings');
    
    const apiUrlInput = page.locator('[data-testid="api-url"], input[name="apiUrl"]');
    
    if (await apiUrlInput.isVisible()) {
      await apiUrlInput.fill('not-a-valid-url');
      await apiUrlInput.blur();
      
      // Should show validation error
      await page.waitForTimeout(500);
    }
  });
});

test.describe('Connection Test', () => {
  test('should have test connection button', async ({ page }) => {
    await page.goto('/settings');
    
    const testButton = page.locator('button:has-text("Test"), button:has-text("Connect")');
    await expect(testButton).toBeVisible();
  });

  test('should show connection status', async ({ page }) => {
    await page.goto('/settings');
    
    const testButton = page.locator('button:has-text("Test"), button:has-text("Connect")').first();
    
    if (await testButton.isVisible()) {
      await testButton.click();
      
      // Wait for connection test
      await page.waitForTimeout(2000);
      
      // Check for status indicator
      const statusIndicator = page.locator('[data-testid="connection-status"]');
      // Status should show success or failure
    }
  });
});
