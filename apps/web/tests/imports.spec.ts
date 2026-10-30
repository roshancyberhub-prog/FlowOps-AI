import { createHmac } from "node:crypto";
import { readFileSync } from "node:fs";
import { expect, test } from "@playwright/test";

test.use({
  video: { mode: "on", size: { width: 1440, height: 1100 } },
  viewport: { width: 1440, height: 1100 },
});

test("import, score, review and simulate protected outreach through separate workers", async ({
  page,
  browser,
}, testInfo) => {
  test.setTimeout(180000);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  // The deliberate hold makes the recorded real UI readable; assertions synchronize the app.
  const checkpoint = async (options: Parameters<typeof page.screenshot>[0]) => {
    await page.screenshot(options);
    await page.waitForTimeout(1200);
  };
  await page.setViewportSize({ width: 1440, height: 1100 });
  await page.goto("/login");
  await page
    .getByRole("button", { name: "Create an account", exact: true })
    .click();
  await page.getByLabel("Full name", { exact: true }).fill("Import Operator");
  await page
    .getByLabel("Work email", { exact: true })
    .fill(`import-${Date.now()}@example.com`);
  await page
    .getByLabel("Password", { exact: true })
    .fill("Fictional-Import-Passphrase-42");
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await page
    .getByLabel("Workspace name", { exact: true })
    .fill("CSV verification");
  await page
    .getByRole("button", { name: "Create workspace", exact: true })
    .click();
  await page.getByRole("link", { name: "Workflows", exact: true }).click();
  await page.getByRole("button", { name: "New workflow", exact: true }).click();
  await page
    .getByLabel("Workflow name", { exact: true })
    .fill("Reviewed lead outreach");
  await page
    .getByLabel("Starting template", { exact: true })
    .selectOption("outreach");
  await page
    .getByRole("button", { name: "Create workflow", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Publish version", exact: true })
    .click();
  await expect(
    page.getByRole("status", { name: "Workflow update" }),
  ).toHaveText("Version 1 published.");
  const outreachWorkflowId = page.url().split("/").at(-1)!;
  await page.getByRole("link", { name: "CSV imports", exact: true }).click();
  const csv =
    "Full Name,Email,Company,Job Title,Industry,Company Size,Website\n" +
    "Buyer One,buyer-one@example.com,Example Co,Founder,Software,11-50,https://example.com\n" +
    "Buyer Two,buyer-two@example.com,Example Tools,Director,Technology,51-200,https://example.org\n" +
    "Invalid,not-an-email,Example Co,Analyst,Software,11-50,\n" +
    "Duplicate,BUYER-ONE@example.com,Example Co,Founder,Software,11-50,https://example.com\n";
  await page.getByLabel("CSV file", { exact: true }).setInputFiles({
    name: "fictional-leads.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(csv),
  });
  await page
    .getByRole("button", { name: "Preview columns", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Map columns · 4 records", exact: true }),
  ).toBeVisible();
  await page
    .getByLabel("Full name *", { exact: true })
    .selectOption("Full Name");
  await page.getByLabel("Email *", { exact: true }).selectOption("Email");
  await page
    .getByRole("button", { name: "Start CSV import", exact: true })
    .click();
  await expect(page).toHaveURL(/\/imports\/[^/]+$/);
  await expect(page.getByTestId("import-status")).toHaveText("Succeeded", {
    timeout: 45000,
  });
  await expect(page.getByTestId("import-inserted")).toHaveText("2");
  await expect(page.getByTestId("import-invalid")).toHaveText("1");
  await expect(page.getByTestId("import-duplicates")).toHaveText("1");
  await expect(page.locator("tbody tr")).toHaveCount(4);
  await checkpoint({
    path: testInfo.outputPath("csv-import-report.png"),
    fullPage: true,
  });
  await page
    .getByLabel("Filter records", { exact: true })
    .selectOption("invalid");
  await expect(page.locator("tbody tr")).toHaveCount(1);
  await expect(page.getByText("not-an-email", { exact: true })).toBeVisible();
  await page
    .getByLabel("Filter records", { exact: true })
    .selectOption("duplicate");
  await expect(page.locator("tbody tr")).toHaveCount(1);
  await page.reload();
  await expect(page.getByTestId("import-status")).toHaveText("Succeeded");
  await page.setViewportSize({ width: 390, height: 844 });
  await expect
    .poll(() => page.evaluate(() => document.documentElement.scrollWidth))
    .toBeLessThanOrEqual(390);
  await checkpoint({
    path: testInfo.outputPath("csv-import-mobile.png"),
    fullPage: true,
  });
  await page.getByRole("link", { name: "Leads", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Buyer One", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Buyer Two", exact: true }),
  ).toBeVisible();
  await expect(page.locator("tbody tr")).toHaveCount(2);
  await page.setViewportSize({ width: 1440, height: 1100 });
  await page.getByRole("link", { name: "Approvals", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Review email draft", exact: true }),
  ).toHaveCount(2, { timeout: 60000 });
  await expect(
    page.getByText("Mock AI draft", { exact: false }).first(),
  ).toBeVisible();
  const org = await page.evaluate(() =>
    localStorage.getItem("flowops.workspace"),
  );
  expect(org).toBeTruthy();
  const headers = { "X-Organization-ID": org! };
  const pending = (
    await (
      await page.request.get("/api/v1/approvals?status=pending", { headers })
    ).json()
  ).items;
  const first = pending.find(
    (item: { payload: { draft: { recipient: string } } }) =>
      item.payload.draft.recipient === "buyer-one@example.com",
  );
  const second = pending.find(
    (item: { payload: { draft: { recipient: string } } }) =>
      item.payload.draft.recipient === "buyer-two@example.com",
  );
  expect(first).toBeTruthy();
  expect(second).toBeTruthy();
  await checkpoint({
    path: testInfo.outputPath("mock-outreach-approvals.png"),
    fullPage: true,
  });
  await page
    .getByRole("article")
    .filter({ hasText: "buyer-one@example.com" })
    .getByRole("link", { name: /View or edit draft/ })
    .click();
  await expect(
    page.getByRole("heading", { name: "Outreach draft", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Mock AI output", { exact: false }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Edit draft", exact: true }).click();
  await page
    .getByLabel("Subject", { exact: true })
    .fill("Reviewed follow-up for Example Co");
  await page
    .getByLabel("Message body", { exact: true })
    .fill(
      "Hi Buyer,\n\nThis fictional message was reviewed for the FlowOps AI demonstration.\n\nBest regards",
    );
  await page
    .getByRole("button", { name: "Save draft revision", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("Draft revision saved.");
  await checkpoint({
    path: testInfo.outputPath("reviewed-mock-draft.png"),
    fullPage: true,
  });
  const stale = await page.request.post(
    `/api/v1/approvals/${first.id}/approve`,
    {
      headers,
      data: { revision: first.revision, payload_hash: first.payload_hash },
    },
  );
  expect(stale.status()).toBe(409);
  await page
    .getByRole("link", { name: "Review approval", exact: true })
    .click();
  const firstCard = page
    .getByRole("article")
    .filter({ hasText: "buyer-one@example.com" });
  await expect(firstCard).toContainText("Reviewed follow-up for Example Co");
  await expect(firstCard).toContainText("Revision 2");
  await firstCard
    .getByRole("button", { name: "Approve and continue", exact: true })
    .click();
  await expect(firstCard).toHaveCount(0);
  await page
    .getByRole("article")
    .filter({ hasText: "buyer-two@example.com" })
    .getByRole("button", { name: "Reject", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "No approvals to review.", exact: true }),
  ).toBeVisible();
  await page.goto(`/executions/${first.execution_id}`);
  await expect(page.getByTestId("execution-status")).toHaveText("Succeeded", {
    timeout: 45000,
  });
  await expect(page.getByText("Succeeded", { exact: true })).toHaveCount(10);
  await expect(
    page.getByText("Mock receipt · No external email was sent.", {
      exact: true,
    }),
  ).toBeVisible();
  await page
    .getByText("Mock receipt · No external email was sent.", { exact: true })
    .scrollIntoViewIfNeeded();
  await checkpoint({
    path: testInfo.outputPath("mock-outreach-completed.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect
    .poll(() => page.evaluate(() => document.documentElement.scrollWidth))
    .toBeLessThanOrEqual(390);
  await checkpoint({
    path: testInfo.outputPath("mock-outreach-mobile.png"),
    fullPage: true,
  });
  await page.goto(`/executions/${second.execution_id}`);
  await expect(page.getByTestId("execution-status")).toHaveText("Cancelled");
  await expect(
    page.getByText("No delivery receipt has been recorded.", { exact: true }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Leads", exact: true }).click();
  await expect(
    page.getByRole("row").filter({ hasText: "buyer-one@example.com" }),
  ).toContainText("80/100");
  await page.setViewportSize({ width: 1440, height: 1100 });
  await page.getByRole("button", { name: "Buyer One", exact: true }).click();
  await page
    .getByRole("region", { name: "Lead score", exact: true })
    .scrollIntoViewIfNeeded();
  await expect(
    page.getByText("All configured required fields are present.", {
      exact: true,
    }),
  ).toBeVisible();
  await checkpoint({
    path: testInfo.outputPath("outreach-score-reasons.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Close", exact: true }).click();
  await page.getByRole("link", { name: "Integrations", exact: true }).click();
  await page.getByLabel("Name", { exact: true }).fill("Inbound verification");
  await page.getByLabel("Provider", { exact: true }).selectOption("webhook");
  await page
    .getByRole("button", { name: "Add integration", exact: true })
    .click();
  const connection = page.getByRole("region", {
    name: "Inbound verification",
    exact: true,
  });
  await expect(connection).toBeVisible();
  await connection
    .getByRole("button", { name: "Test connection", exact: true })
    .click();
  await expect(connection).toContainText("Connection: connected");
  await connection
    .getByRole("button", { name: "View events & deliveries", exact: true })
    .click();
  const endpoint = (await connection.locator("code").innerText()).trim();
  const identifier = endpoint.split("/").at(-1)!;
  const key = readFileSync("../../.env", "utf8")
    .split("\n")
    .find((line) => line.startsWith("WEBHOOK_SIGNING_KEY="))
    ?.slice("WEBHOOK_SIGNING_KEY=".length);
  expect(key).toBeTruthy();
  const body = Buffer.from(
    JSON.stringify({
      event_id: "browser:lead:001",
      lead: { name: "Existing buyer", email: "buyer-one@example.com" },
    }),
  );
  const timestamp = Math.floor(Date.now() / 1000);
  const derived = createHmac("sha256", key!).update(identifier).digest();
  const signed =
    "sha256=" +
    createHmac("sha256", derived)
      .update(Buffer.concat([Buffer.from(`${timestamp}.`), body]))
      .digest("hex");
  const signedHeaders = {
    "Content-Type": "application/json",
    "X-FlowOps-Timestamp": String(timestamp),
    "X-FlowOps-Signature": signed,
  };
  const incoming = await page.request.post(endpoint, {
    headers: signedHeaders,
    data: body,
  });
  expect(incoming.status()).toBe(200);
  const duplicate = await page.request.post(endpoint, {
    headers: signedHeaders,
    data: body,
  });
  expect((await duplicate.json()).duplicate).toBe(true);
  const rejected = await page.request.post(endpoint, {
    headers: {
      ...signedHeaders,
      "X-FlowOps-Signature": "sha256=" + "0".repeat(64),
    },
    data: body,
  });
  expect(rejected.status()).toBe(401);
  await expect(
    connection.getByText("browser:lead:001", { exact: true }),
  ).toBeVisible({ timeout: 10000 });
  await connection
    .getByText("browser:lead:001", { exact: true })
    .scrollIntoViewIfNeeded();
  await checkpoint({
    path: testInfo.outputPath("signed-webhook-history.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect
    .poll(() => page.evaluate(() => document.documentElement.scrollWidth))
    .toBeLessThanOrEqual(390);
  await page.setViewportSize({ width: 1440, height: 1100 });
  await page.getByRole("link", { name: "Overview", exact: true }).click();
  await expect(page.getByTestId("metric-leads")).toHaveText("2");
  await expect(page.getByTestId("metric-workflows")).toHaveText("1");
  await expect(page.getByTestId("metric-executions")).toHaveText("2");
  await expect(page.getByTestId("metric-approvals")).toHaveText("0");
  await expect(page.getByText("100%", { exact: true })).toBeVisible();
  await page.getByText("View exact daily values", { exact: true }).click();
  await expect(page.getByRole("table").locator("tbody tr")).toHaveCount(7);
  await checkpoint({
    path: testInfo.outputPath("analytics-overview.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect
    .poll(() => page.evaluate(() => document.documentElement.scrollWidth))
    .toBeLessThanOrEqual(390);
  await checkpoint({
    path: testInfo.outputPath("analytics-mobile.png"),
    fullPage: true,
  });
  const buyer = (
    await (
      await page.request.get("/api/v1/leads?search=buyer-one@example.com", {
        headers,
      })
    ).json()
  ).items[0];
  const retry = await page.request.post(
    `/api/v1/workflows/${outreachWorkflowId}/test-runs`,
    {
      headers: { ...headers, "Idempotency-Key": crypto.randomUUID() },
      data: { lead_id: buyer.id },
    },
  );
  expect(retry.status()).toBe(202);
  const retryRun = await retry.json();
  await page.setViewportSize({ width: 1440, height: 1100 });
  await page.goto(`/executions/${retryRun.id}`);
  await expect(page.getByTestId("execution-status")).toHaveText(
    "Waiting for approval",
    { timeout: 60000 },
  );
  const retrySteps = (
    await (
      await page.request.get(`/api/v1/executions/${retryRun.id}/steps`, {
        headers,
      })
    ).json()
  ).items.filter(
    (step: { node_type: string }) =>
      step.node_type === "action.generate_email_draft",
  );
  expect(retrySteps.map((step: { status: string }) => step.status)).toEqual([
    "failed",
    "succeeded",
  ]);
  expect(retrySteps[0].error_code).toBe("DEMO_TRANSIENT_FAILURE");
  await expect(page.getByText("Failed", { exact: true })).toHaveCount(1);
  await page.getByText("Failed", { exact: true }).scrollIntoViewIfNeeded();
  await checkpoint({
    path: testInfo.outputPath("mock-provider-retry-history.png"),
    fullPage: true,
  });
  const review = (
    await (
      await page.request.get("/api/v1/approvals?status=pending", { headers })
    ).json()
  ).items.find(
    (approval: { execution_id: string }) =>
      approval.execution_id === retryRun.id,
  );
  expect(review).toBeTruthy();
  const viewer = await browser.newContext();
  const viewerEmail = `viewer-${Date.now()}@example.com`;
  const password = "Fictional-Viewer-Passphrase-42";
  expect(
    (
      await viewer.request.post("http://localhost:3000/api/v1/auth/register", {
        data: { email: viewerEmail, password, display_name: "Demo Viewer" },
      })
    ).status(),
  ).toBe(201);
  expect(
    (
      await viewer.request.post(
        "http://localhost:3000/api/v1/auth/session/login",
        { form: { username: viewerEmail, password } },
      )
    ).status(),
  ).toBe(204);
  await page
    .getByRole("link", { name: "Team & workspace", exact: true })
    .click();
  await page.getByLabel("Member email", { exact: true }).fill(viewerEmail);
  await page.getByLabel("Access role", { exact: true }).selectOption("viewer");
  await page.getByRole("button", { name: "Add member", exact: true }).click();
  await expect(
    page.getByRole("row").filter({ hasText: viewerEmail }),
  ).toBeVisible();
  const denied = await viewer.request.post(
    `http://localhost:3000/api/v1/approvals/${review.id}/approve`,
    {
      headers,
      data: { revision: review.revision, payload_hash: review.payload_hash },
    },
  );
  expect(denied.status()).toBe(403);
  const separate = await viewer.request.post(
    "http://localhost:3000/api/v1/organizations",
    { data: { name: "Viewer separate workspace" } },
  );
  expect(separate.status()).toBe(201);
  expect(
    (
      await viewer.request.get(
        `http://localhost:3000/api/v1/executions/${retryRun.id}`,
        { headers: { "X-Organization-ID": (await separate.json()).id } },
      )
    ).status(),
  ).toBe(404);
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Welcome back", exact: true }),
  ).toBeVisible();
  // Use the independently authenticated viewer session to show actual read-only controls.
  await page.context().addCookies(await viewer.cookies());
  await page.goto("/approvals");
  await expect(
    page.getByRole("heading", { name: "Review email draft", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Approve and continue", exact: true }),
  ).toHaveCount(0);
  await checkpoint({
    path: testInfo.outputPath("viewer-cannot-approve.png"),
    fullPage: true,
  });
  await page
    .getByLabel("Workspace", { exact: true })
    .selectOption({ label: "Viewer separate workspace" });
  await page.goto(`/executions/${retryRun.id}`);
  await expect(page.getByRole("alert")).toContainText("Execution not found.");
  await checkpoint({
    path: testInfo.outputPath("cross-workspace-denied.png"),
    fullPage: true,
  });
  await viewer.close();
  expect(errors).toEqual([]);
});
