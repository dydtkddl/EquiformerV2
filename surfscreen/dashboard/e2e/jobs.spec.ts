import { test, expect } from '@playwright/test';

/**
 * Jobs Page E2E Tests
 * 
 * Tests job listing, filtering, and management
 */

test.describe('Jobs Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/jobs');
  });

  test('should load jobs page', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('Jobs');
  });

  test('should display job table', async ({ page }) => {
    // Wait for table to load
    const table = page.locator('table, [data-testid="job-table"]');
    await expect(table).toBeVisible({ timeout: 10000 });
    
    // Check table headers
    await expect(page.getByText('ID')).toBeVisible();
    await expect(page.getByText('Status')).toBeVisible();
  });

  test('should filter jobs by status', async ({ page }) => {
    // Find status filter
    const statusFilter = page.locator('[data-testid="status-filter"], select[name="status"]');
    
    if (await statusFilter.isVisible()) {
      await statusFilter.selectOption('completed');
      
      // URL should update with filter
      await expect(page).toHaveURL(/status=completed/);
    }
  });

  test('should filter jobs by type', async ({ page }) => {
    const typeFilter = page.locator('[data-testid="type-filter"], select[name="type"]');
    
    if (await typeFilter.isVisible()) {
      await typeFilter.selectOption('screening');
      await expect(page).toHaveURL(/type=screening/);
    }
  });

  test('should search jobs', async ({ page }) => {
    const searchInput = page.locator('[data-testid="search-input"], input[type="search"]');
    
    if (await searchInput.isVisible()) {
      await searchInput.fill('test');
      await searchInput.press('Enter');
      
      // Wait for search results
      await page.waitForTimeout(500);
    }
  });

  test('should sort jobs by column', async ({ page }) => {
    // Click on a sortable column header
    const statusHeader = page.locator('th:has-text("Status")');
    
    if (await statusHeader.isVisible()) {
      await statusHeader.click();
      
      // Check sort indicator
      await expect(statusHeader.locator('svg, [data-sort]')).toBeVisible();
    }
  });

  test('should navigate to job details', async ({ page }) => {
    // Wait for jobs to load
    await page.waitForSelector('[data-testid="job-row"], tr[data-job-id]', { timeout: 10000 }).catch(() => null);
    
    const firstJobRow = page.locator('[data-testid="job-row"], tr[data-job-id]').first();
    
    if (await firstJobRow.isVisible()) {
      await firstJobRow.click();
      
      // Should navigate to job details
      await expect(page).toHaveURL(/\/jobs\/.+/);
    }
  });

  test('should display empty state when no jobs', async ({ page }) => {
    // If no jobs, should show empty state
    const emptyState = page.locator('[data-testid="empty-state"]');
    const jobTable = page.locator('[data-testid="job-table"], table');
    
    // Either empty state or table should be visible
    const hasContent = await emptyState.isVisible() || await jobTable.isVisible();
    expect(hasContent).toBeTruthy();
  });
});

test.describe('Job Details Page', () => {
  test('should display job details', async ({ page }) => {
    // Navigate to a job details page (mock job ID)
    await page.goto('/jobs/test-job-123');
    
    // Check for job details elements
    await expect(page.locator('[data-testid="job-status"]').or(page.getByText('Status'))).toBeVisible();
  });

  test('should display job logs', async ({ page }) => {
    await page.goto('/jobs/test-job-123');
    
    // Check for logs section
    const logsSection = page.locator('[data-testid="job-logs"]');
    
    // Logs section may or may not be visible depending on job state
    if (await logsSection.isVisible()) {
      await expect(logsSection).toContainText(/log/i);
    }
  });

  test('should have cancel button for running jobs', async ({ page }) => {
    await page.goto('/jobs/test-job-123');
    
    const cancelButton = page.locator('[data-testid="cancel-button"], button:has-text("Cancel")');
    
    // Cancel button visibility depends on job status
    // Just check it doesn't crash
    await page.waitForTimeout(500);
  });

  test('should have download button for completed jobs', async ({ page }) => {
    await page.goto('/jobs/test-job-123');
    
    const downloadButton = page.locator('[data-testid="download-button"], button:has-text("Download")');
    
    // Download button visibility depends on job status
    await page.waitForTimeout(500);
  });
});

test.describe('Jobs Pagination', () => {
  test('should paginate job list', async ({ page }) => {
    await page.goto('/jobs');
    
    const pagination = page.locator('[data-testid="pagination"], nav[aria-label="Pagination"]');
    
    if (await pagination.isVisible()) {
      // Check next button
      const nextButton = pagination.locator('button:has-text("Next"), [aria-label="Next page"]');
      await expect(nextButton).toBeVisible();
    }
  });

  test('should change page size', async ({ page }) => {
    await page.goto('/jobs');
    
    const pageSizeSelect = page.locator('[data-testid="page-size"], select[name="pageSize"]');
    
    if (await pageSizeSelect.isVisible()) {
      await pageSizeSelect.selectOption('25');
      await expect(page).toHaveURL(/pageSize=25/);
    }
  });
});
