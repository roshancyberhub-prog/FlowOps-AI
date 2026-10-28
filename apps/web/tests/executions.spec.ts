import { expect, test } from "@playwright/test";

test("separate worker completes runs and resumes a reviewed checkpoint", async ({
  page,
}, testInfo) => {
  test.setTimeout(120000);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.setViewportSize({ width: 1440, height: 1050 });
  await page.goto("/login");
  await page
    .getByRole("button", { name: "Create an account", exact: true })
    .click();
  await page
    .getByLabel("Full name", { exact: true })
    .fill("Execution Operator");
  await page
    .getByLabel("Work email", { exact: true })
    .fill(`execution-${Date.now()}@example.com`);
  await page
    .getByLabel("Password", { exact: true })
    .fill("Fictional-Execution-Passphrase-42");
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await page
    .getByLabel("Workspace name", { exact: true })
    .fill("Execution verification");
  await page
    .getByRole("button", { name: "Create workspace", exact: true })
    .click();
  await page.getByRole("link", { name: "Workflows", exact: true }).click();
  await page.getByRole("button", { name: "New workflow", exact: true }).click();
  await page
    .getByLabel("Workflow name", { exact: true })
    .fill("Durable background run");
  await page
    .getByRole("button", { name: "Create workflow", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Publish version", exact: true })
    .click();
  await expect(
    page.getByRole("status", { name: "Workflow update" }),
  ).toHaveText("Version 1 published.");
  await page.getByRole("button", { name: "Run workflow", exact: true }).click();
  await page
    .getByRole("button", { name: "Start background run", exact: true })
    .click();
  await expect(page).toHaveURL(/\/executions\/[^/]+$/);
  await expect(
    page.getByText("Succeeded", { exact: true }).first(),
  ).toBeVisible({ timeout: 45000 });
  await expect(page.getByText("Record result", { exact: true })).toBeVisible();
  await expect(page.getByText("Attempt 1", { exact: false })).toHaveCount(2);
  await page.screenshot({
    path: testInfo.outputPath("execution-completed.png"),
    fullPage: true,
  });
  await page.reload();
  await expect(
    page.getByText("Succeeded", { exact: true }).first(),
  ).toBeVisible();

  const org = await page.evaluate(() =>
    localStorage.getItem("flowops.workspace"),
  );
  expect(org).toBeTruthy();
  const headers = { "X-Organization-ID": org! };
  const createdResponse = await page.request.post("/api/v1/workflows", {
    headers,
    data: { name: "Review before continuing" },
  });
  expect(createdResponse.status()).toBe(201);
  const created = await createdResponse.json();
  const types = [
    "trigger.manual",
    "action.request_approval",
    "action.record_result",
  ];
  const graph = {
    schema_version: 1,
    nodes: types.map((type, index) => ({
      id: `node_${index}`,
      type,
      config:
        index === 1
          ? {
              kind: "continue",
              message: "Review this fictional test checkpoint.",
            }
          : {},
      position: { x: index * 230, y: 160 },
    })),
    edges: [0, 1].map((index) => ({
      id: `edge_${index}`,
      source: `node_${index}`,
      target: `node_${index + 1}`,
    })),
  };
  const path = `/api/v1/workflows/${created.id}`;
  const saved = await page.request.patch(path, {
    headers,
    data: { expected_revision: created.revision, graph },
  });
  expect(saved.status()).toBe(200);
  const published = await page.request.post(path + "/publish", {
    headers,
    data: { expected_revision: (await saved.json()).revision },
  });
  expect(published.status()).toBe(200);
  await page.goto(`/workflows/${created.id}`);
  await page.getByRole("button", { name: "Run workflow", exact: true }).click();
  await page
    .getByRole("button", { name: "Start background run", exact: true })
    .click();
  await expect(
    page.getByRole("link", { name: "Review pending approval" }),
  ).toBeVisible({ timeout: 45000 });
  await page.getByRole("link", { name: "Review pending approval" }).click();
  await expect(
    page.getByText("Review this fictional test checkpoint."),
  ).toBeVisible();
  await page.screenshot({
    path: testInfo.outputPath("approval-checkpoint.png"),
    fullPage: true,
  });
  await page
    .getByLabel("Decision note (optional)")
    .fill("Reviewed the test checkpoint.");
  await page.getByRole("button", { name: "Approve and continue" }).click();
  await expect(
    page.getByRole("heading", { name: "No approvals to review." }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Executions", exact: true }).click();
  await page
    .getByRole("link", { name: "Review before continuing", exact: true })
    .click();
  await expect(
    page.getByText("Succeeded", { exact: true }).first(),
  ).toBeVisible({ timeout: 45000 });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect
    .poll(() => page.evaluate(() => document.documentElement.scrollWidth))
    .toBeLessThanOrEqual(390);
  await page.screenshot({
    path: testInfo.outputPath("execution-mobile.png"),
    fullPage: true,
  });
  expect(errors).toEqual([]);
});
