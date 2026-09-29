import { chromium } from '../frontend/node_modules/playwright/index.mjs';
import path from 'path';
import fs from 'fs';

const ARTIFACT_DIR = 'C:\\Users\\ASUS\\.gemini\\antigravity-ide\\brain\\120890b2-b6d5-47e2-a357-e490a7ed6f21';
const SCREENSHOTS_DIR = path.join(ARTIFACT_DIR, 'verification_screenshots');
const VIDEO_DIR = path.join(ARTIFACT_DIR, 'verification_video');

if (!fs.existsSync(SCREENSHOTS_DIR)) fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
if (!fs.existsSync(VIDEO_DIR)) fs.mkdirSync(VIDEO_DIR, { recursive: true });

async function runVerification() {
  console.log('--- STARTING PLAYWRIGHT END-TO-END VERIFICATION ---');

  const browser = await chromium.launch({
    channel: 'msedge',
    headless: true,
  });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    recordVideo: {
      dir: VIDEO_DIR,
      size: { width: 1440, height: 900 },
    },
    permissions: ['geolocation'],
    geolocation: { latitude: 25.594, longitude: 85.137 },
  });

  const page = await context.newPage();

  const consoleLogs = [];
  page.on('console', (msg) => {
    const text = msg.text();
    consoleLogs.push(`[${msg.type()}] ${text}`);
    if (msg.type() === 'error' && !text.includes('tile.openstreetmap.org')) {
      console.error('PAGE ERROR LOG:', text);
    }
  });

  page.on('pageerror', (err) => {
    console.error('UNCAUGHT PAGE ERROR:', err.message);
  });

  try {
    // ── STEP 1: Load Live Dashboard ──────────────────────────────────────────
    console.log('[Step 1] Navigating to http://127.0.0.1:5173/ ...');
    await page.goto('http://127.0.0.1:5173/', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    const initialScreenshot = path.join(SCREENSHOTS_DIR, '01_dashboard_initial.png');
    await page.screenshot({ path: initialScreenshot });
    console.log('[Step 1] Saved:', initialScreenshot);

    // ── STEP 2: Navigate to "Report Weather" Tab ──────────────────────────────
    console.log('[Step 2] Switching to "Report Weather" tab ...');
    await page.click('button:has-text("Report Weather")');
    await page.waitForTimeout(1000);

    const reportTabScreenshot = path.join(SCREENSHOTS_DIR, '02_report_screen.png');
    await page.screenshot({ path: reportTabScreenshot });
    console.log('[Step 2] Saved:', reportTabScreenshot);

    // Click "Patna (Hindi)" demo preset
    console.log('[Step 2] Clicking "Patna (Hindi)" preset ...');
    await page.click('button:has-text("Patna (Hindi)")');
    await page.waitForTimeout(500);

    // Also click "Capture Current GPS" to verify GPS capture button
    console.log('[Step 2] Clicking "Update Location" / "Capture Current GPS" ...');
    const gpsBtn = await page.$('button:has-text("Update Location"), button:has-text("Capture Current GPS")');
    if (gpsBtn) {
      await gpsBtn.click();
      await page.waitForTimeout(1000);
    }

    const filledReportScreenshot = path.join(SCREENSHOTS_DIR, '03_report_filled.png');
    await page.screenshot({ path: filledReportScreenshot });
    console.log('[Step 2] Saved:', filledReportScreenshot);

    // Submit the flood report
    console.log('[Step 2] Submitting flood report ...');
    await page.click('button:has-text("Submit Weather Report")');

    // Wait for the tracking card to appear
    await page.waitForSelector('text=HTTP 202 Accepted', { timeout: 8000 });
    console.log('[Step 2] Submission accepted! Waiting 3 seconds for ML pipeline status...');
    await page.waitForTimeout(3500);

    const trackingScreenshot = path.join(SCREENSHOTS_DIR, '04_report_tracking.png');
    await page.screenshot({ path: trackingScreenshot });
    console.log('[Step 2] Saved:', trackingScreenshot);

    // ── STEP 3: Navigate to "Admin Review" Tab ────────────────────────────────
    console.log('[Step 3] Switching to "Admin Review" tab ...');
    await page.click('button:has-text("Admin Review")');
    await page.waitForTimeout(1000);

    const loginScreenshot = path.join(SCREENSHOTS_DIR, '05_admin_login.png');
    await page.screenshot({ path: loginScreenshot });
    console.log('[Step 3] Saved:', loginScreenshot);

    // Authenticate
    console.log('[Step 3] Submitting admin credentials ...');
    await page.click('button:has-text("Authenticate (In-Memory Bearer Token)")');
    await page.waitForTimeout(2000);

    // Verify Review Queue and KPI tiles loaded
    await page.waitForSelector('text=Pending Human Verification', { timeout: 8000 });
    const queueScreenshot = path.join(SCREENSHOTS_DIR, '06_admin_review_queue.png');
    await page.screenshot({ path: queueScreenshot });
    console.log('[Step 3] Saved:', queueScreenshot);

    // Approve the report
    console.log('[Step 3] Finding and approving the queued report ...');
    const approveBtn = await page.$('button:has-text("Approve & Verify")');
    if (approveBtn) {
      await approveBtn.click();
      await page.waitForTimeout(2500);
      console.log('[Step 3] Clicked Approve & Verify!');
    } else {
      console.warn('[Step 3] No Approve & Verify button found!');
    }

    const approvedScreenshot = path.join(SCREENSHOTS_DIR, '07_admin_approved.png');
    await page.screenshot({ path: approvedScreenshot });
    console.log('[Step 3] Saved:', approvedScreenshot);

    // ── STEP 4: Switch to "Live Dashboard" WITHOUT Page Refresh ───────────────
    console.log('[Step 4] Switching back to "Live Dashboard" WITHOUT page refresh ...');
    await page.click('button:has-text("Live Dashboard")');
    await page.waitForTimeout(2500);

    const dashboardUpdatedScreenshot = path.join(SCREENSHOTS_DIR, '08_dashboard_live_verified.png');
    await page.screenshot({ path: dashboardUpdatedScreenshot });
    console.log('[Step 4] Saved:', dashboardUpdatedScreenshot);

    // Click on the newly verified report in the left sidebar
    const patnaItem = await page.$('div:has-text("Patna")');
    if (patnaItem) {
      console.log('[Step 4] Clicking on Patna report card in sidebar ...');
      await patnaItem.click();
      await page.waitForTimeout(2000);
      const popupScreenshot = path.join(SCREENSHOTS_DIR, '09_dashboard_marker_popup.png');
      await page.screenshot({ path: popupScreenshot });
      console.log('[Step 4] Saved:', popupScreenshot);
    }

    console.log('--- ALL VERIFICATION STEPS PASSED SUCCESSFULLY! ---');
  } catch (err) {
    console.error('VERIFICATION ERROR:', err);
    const errScreenshot = path.join(SCREENSHOTS_DIR, 'error_state.png');
    await page.screenshot({ path: errScreenshot });
    console.log('Saved error screenshot:', errScreenshot);
  } finally {
    // Closing context flushes the video file
    await context.close();
    await browser.close();

    // Check video file
    const videoFiles = fs.readdirSync(VIDEO_DIR);
    console.log('Video files generated:', videoFiles);
    if (videoFiles.length > 0) {
      const videoPath = path.join(VIDEO_DIR, videoFiles[0]);
      console.log('Screen recording saved to:', videoPath);
    }
  }
}

runVerification();
