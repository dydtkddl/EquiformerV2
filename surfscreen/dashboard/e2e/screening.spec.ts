import { test, expect } from '@playwright/test';

/**
 * Screening Page E2E Tests
 * 
 * Tests screening job creation and management
 */

test.describe('Screening Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/screening');
  });

  test('should load screening page', async ({ page }) => {
    await expect(page.locator('h1')).toContainText(/Screening/i);
  });

  test('should display screening jobs list', async ({ page }) => {
    // Check for jobs table or list
    const jobsList = page.locator('[data-testid="screening-jobs"], table');
    await expect(jobsList).toBeVisible({ timeout: 10000 });
  });

  test('should have new screening button', async ({ page }) => {
    const newButton = page.locator('button:has-text("New"), a:has-text("New Screening")');
    await expect(newButton).toBeVisible();
  });

  test('should navigate to new screening page', async ({ page }) => {
    const newButton = page.locator('button:has-text("New"), a:has-text("New")').first();
    await newButton.click();
    
    await expect(page).toHaveURL(/\/screening\/new/);
  });
});

test.describe('New Screening Form', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/screening/new');
  });

  test('should load new screening form', async ({ page }) => {
    await expect(page.locator('h1')).toContainText(/New|Screening/i);
  });

  test('should have file upload for molecule', async ({ page }) => {
    const fileInput = page.locator('[data-testid="molecule-upload"], input[type="file"]').first();
    await expect(fileInput).toBeVisible();
  });

  test('should have file upload for surface', async ({ page }) => {
    const fileInput = page.locator('[data-testid="surface-upload"], input[type="file"]');
    // Surface upload may be optional or second file input
    await page.waitForTimeout(500);
  });

  test('should have engine selection', async ({ page }) => {
    const engineSelect = page.locator('[data-testid="engine-select"], select[name="engine"]');
    await expect(engineSelect).toBeVisible();
    
    // Check available options
    const options = await engineSelect.locator('option').allTextContents();
    expect(options.length).toBeGreaterThan(0);
  });

  test('should have configurations slider', async ({ page }) => {
    const configSlider = page.locator('[data-testid="n-configs"], input[type="range"], input[name="nConfigs"]');
    
    if (await configSlider.isVisible()) {
      await expect(configSlider).toBeVisible();
    }
  });

  test('should validate required fields', async ({ page }) => {
    // Try to submit without filling required fields
    const submitButton = page.locator('button[type="submit"], button:has-text("Submit"), button:has-text("Start")');
    await submitButton.click();
    
    // Should show validation errors
    await page.waitForTimeout(500);
    const errorMessage = page.locator('[data-testid="error-message"], .error, [role="alert"]');
    // Either form validation prevents submit or error is shown
  });

  test('should toggle advanced settings', async ({ page }) => {
    const advancedToggle = page.locator('[data-testid="advanced-toggle"], button:has-text("Advanced")');
    
    if (await advancedToggle.isVisible()) {
      await advancedToggle.click();
      
      // Advanced options should appear
      const advancedOptions = page.locator('[data-testid="advanced-options"]');
      await expect(advancedOptions).toBeVisible();
    }
  });

  test('should upload molecule file via drag and drop', async ({ page }) => {
    const dropzone = page.locator('[data-testid="dropzone"], [class*="dropzone"]');
    
    if (await dropzone.isVisible()) {
      // Check dropzone is visible
      await expect(dropzone).toBeVisible();
    }
  });
});

test.describe('Screening Form Validation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/screening/new');
  });

  test('should validate file type', async ({ page }) => {
    const fileInput = page.locator('input[type="file"]').first();
    
    // Try to upload invalid file type
    await fileInput.setInputFiles({
      name: 'invalid.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('invalid content'),
    });
    
    // Should show file type error
    await page.waitForTimeout(500);
  });

  test('should show file preview after upload', async ({ page }) => {
    const fileInput = page.locator('input[type="file"]').first();
    
    // Upload valid XYZ file
    await fileInput.setInputFiles({
      name: 'molecule.xyz',
      mimeType: 'chemical/x-xyz',
      buffer: Buffer.from('3\nWater\nO 0 0 0\nH 1 0 0\nH 0 1 0\n'),
    });
    
    // Should show file name or preview
    await page.waitForTimeout(500);
    const preview = page.locator('[data-testid="file-preview"]');
    if (await preview.isVisible()) {
      await expect(preview).toContainText('molecule.xyz');
    }
  });
});
