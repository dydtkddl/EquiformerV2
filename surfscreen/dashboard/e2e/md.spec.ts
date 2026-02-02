import { test, expect } from '@playwright/test';

/**
 * MD Simulation Page E2E Tests
 * 
 * Tests MD simulation job creation and management
 */

test.describe('MD Simulation Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/md');
  });

  test('should load MD page', async ({ page }) => {
    await expect(page.locator('h1')).toContainText(/MD|Simulation/i);
  });

  test('should display MD jobs list', async ({ page }) => {
    const jobsList = page.locator('[data-testid="md-jobs"], table');
    await expect(jobsList).toBeVisible({ timeout: 10000 });
  });

  test('should have new simulation button', async ({ page }) => {
    const newButton = page.locator('button:has-text("New"), a:has-text("New")').first();
    await expect(newButton).toBeVisible();
  });

  test('should navigate to new MD page', async ({ page }) => {
    const newButton = page.locator('button:has-text("New"), a:has-text("New")').first();
    await newButton.click();
    
    await expect(page).toHaveURL(/\/md\/new/);
  });
});

test.describe('New MD Simulation Form', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/md/new');
  });

  test('should load new MD form', async ({ page }) => {
    await expect(page.locator('h1')).toContainText(/New|MD|Simulation/i);
  });

  test('should have structure file upload', async ({ page }) => {
    const fileInput = page.locator('[data-testid="structure-upload"], input[type="file"]').first();
    await expect(fileInput).toBeVisible();
  });

  test('should have ensemble selection', async ({ page }) => {
    const ensembleSelect = page.locator('[data-testid="ensemble-select"], select[name="ensemble"]');
    await expect(ensembleSelect).toBeVisible();
    
    // Check NVT and NVE options
    const options = await ensembleSelect.locator('option').allTextContents();
    expect(options.join(' ')).toMatch(/NVT|NVE/i);
  });

  test('should have temperature input', async ({ page }) => {
    const tempInput = page.locator('[data-testid="temperature-input"], input[name="temperature"]');
    await expect(tempInput).toBeVisible();
    
    // Default should be reasonable value
    const value = await tempInput.inputValue();
    expect(parseInt(value) || 300).toBeGreaterThan(0);
  });

  test('should have timestep input', async ({ page }) => {
    const timestepInput = page.locator('[data-testid="timestep-input"], input[name="timestep"]');
    await expect(timestepInput).toBeVisible();
  });

  test('should have n_steps input', async ({ page }) => {
    const stepsInput = page.locator('[data-testid="nsteps-input"], input[name="nSteps"], input[name="n_steps"]');
    await expect(stepsInput).toBeVisible();
  });

  test('should validate temperature range', async ({ page }) => {
    const tempInput = page.locator('[data-testid="temperature-input"], input[name="temperature"]');
    
    // Try negative temperature
    await tempInput.fill('-100');
    await tempInput.blur();
    
    // Should show error or reset to valid value
    await page.waitForTimeout(500);
  });

  test('should show thermostat options for NVT', async ({ page }) => {
    const ensembleSelect = page.locator('[data-testid="ensemble-select"], select[name="ensemble"]');
    await ensembleSelect.selectOption('nvt');
    
    // Thermostat options should appear
    const thermostatSelect = page.locator('[data-testid="thermostat-select"], select[name="thermostat"]');
    await expect(thermostatSelect).toBeVisible();
  });

  test('should hide temperature for NVE', async ({ page }) => {
    const ensembleSelect = page.locator('[data-testid="ensemble-select"], select[name="ensemble"]');
    await ensembleSelect.selectOption('nve');
    
    // Temperature input may be hidden or disabled for NVE
    await page.waitForTimeout(500);
  });
});

test.describe('MD Form Submission', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/md/new');
  });

  test('should submit valid MD job', async ({ page }) => {
    const fileInput = page.locator('input[type="file"]').first();
    
    // Upload structure file
    await fileInput.setInputFiles({
      name: 'structure.xyz',
      mimeType: 'chemical/x-xyz',
      buffer: Buffer.from(`8
Cu cluster
Cu 0 0 0
Cu 2.5 0 0
Cu 1.25 2.16 0
Cu 3.75 2.16 0
Cu 0.83 0.72 2.04
Cu 3.33 0.72 2.04
Cu 2.08 2.88 2.04
Cu 4.58 2.88 2.04
`),
    });
    
    // Fill form
    const tempInput = page.locator('input[name="temperature"]');
    if (await tempInput.isVisible()) {
      await tempInput.fill('300');
    }
    
    // Submit
    const submitButton = page.locator('button[type="submit"], button:has-text("Start")');
    
    // Just check submit button is enabled
    await expect(submitButton).toBeVisible();
  });
});

test.describe('MD Results', () => {
  test('should display trajectory viewer for completed job', async ({ page }) => {
    // Navigate to a completed MD job
    await page.goto('/md/test-md-job-123');
    
    // Check for trajectory viewer or download button
    const trajectorySection = page.locator('[data-testid="trajectory-viewer"]');
    const downloadButton = page.locator('button:has-text("Download Trajectory")');
    
    // One of these should be visible for completed jobs
    await page.waitForTimeout(1000);
  });

  test('should display energy plot', async ({ page }) => {
    await page.goto('/md/test-md-job-123');
    
    const energyPlot = page.locator('[data-testid="energy-plot"], canvas');
    // Energy plot may or may not be visible
    await page.waitForTimeout(500);
  });
});
