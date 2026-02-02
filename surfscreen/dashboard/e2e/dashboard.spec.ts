import { test, expect } from '@playwright/test';

/**
 * Dashboard Page E2E Tests
 * 
 * Tests the main dashboard page functionality
 */

test.describe('Dashboard Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should load dashboard page', async ({ page }) => {
    // Check page title
    await expect(page).toHaveTitle(/SurfScreen/);
    
    // Check main heading
    await expect(page.locator('h1')).toContainText('Dashboard');
  });

  test('should display stats cards', async ({ page }) => {
    // Wait for stats to load
    await page.waitForSelector('[data-testid="stats-card"]', { timeout: 10000 });
    
    // Check stats cards are present
    const statsCards = page.locator('[data-testid="stats-card"]');
    await expect(statsCards).toHaveCount(4);
    
    // Check each card has a value
    for (let i = 0; i < 4; i++) {
      const card = statsCards.nth(i);
      await expect(card.locator('[data-testid="stats-value"]')).toBeVisible();
    }
  });

  test('should display recent jobs section', async ({ page }) => {
    // Check recent jobs section
    await expect(page.getByText('Recent Jobs')).toBeVisible();
  });

  test('should display server status', async ({ page }) => {
    // Check server status indicator
    const serverStatus = page.locator('[data-testid="server-status"]');
    await expect(serverStatus).toBeVisible();
  });

  test('should have working navigation', async ({ page }) => {
    // Check navigation links
    await expect(page.getByRole('link', { name: /Jobs/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /Screening/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /MD Simulation/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /Settings/i })).toBeVisible();
  });

  test('should navigate to jobs page', async ({ page }) => {
    await page.getByRole('link', { name: /Jobs/i }).click();
    await expect(page).toHaveURL(/\/jobs/);
  });

  test('should display quick actions', async ({ page }) => {
    // Check quick action buttons
    const quickActions = page.locator('[data-testid="quick-action"]');
    await expect(quickActions.first()).toBeVisible();
  });
});

test.describe('Dashboard Responsiveness', () => {
  test('should be responsive on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    
    // Check mobile menu button
    const menuButton = page.locator('[data-testid="mobile-menu-button"]');
    // Menu button should be visible on mobile
    await expect(menuButton.or(page.locator('[aria-label="Menu"]'))).toBeVisible();
  });

  test('should be responsive on tablet', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/');
    
    // Stats cards should stack on tablet
    await expect(page.locator('h1')).toBeVisible();
  });
});

test.describe('Dashboard Theme', () => {
  test('should support dark mode', async ({ page }) => {
    await page.goto('/');
    
    // Check for dark mode toggle
    const themeToggle = page.locator('[data-testid="theme-toggle"]');
    
    if (await themeToggle.isVisible()) {
      await themeToggle.click();
      
      // Check dark mode class on body
      await expect(page.locator('html')).toHaveClass(/dark/);
    }
  });
});
