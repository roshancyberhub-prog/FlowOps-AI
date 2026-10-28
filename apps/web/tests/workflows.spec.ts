import { expect, test } from "@playwright/test";

test("edit a visual workflow, validate, publish and inspect an immutable version", async ({
  page,
}, testInfo) => {
  const suffix = Date.now();
  await page.goto("/login");
  await page
    .getByRole("button", { name: "Create an account", exact: true })
    .click();
  await page.getByLabel("Full name", { exact: true }).fill("Workflow Operator");
  await page
    .getByLabel("Work email", { exact: true })
    .fill(`workflow-${suffix}@example.com`);
  await page
    .getByLabel("Password", { exact: true })
    .fill("Fictional-Workflow-Passphrase-42");
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await page
    .getByLabel("Workspace name", { exact: true })
    .fill(`Workflow workspace ${suffix}`);
  await page
    .getByRole("button", { name: "Create workspace", exact: true })
    .click();
  await page.getByRole("link", { name: "Workflows", exact: true }).click();
  await page.getByRole("button", { name: "New workflow", exact: true }).click();
  await page.getByLabel("Workflow name", { exact: true }).fill("Demo workflow");
  await page
    .getByRole("button", { name: "Create workflow", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Workflow builder" }),
  ).toBeVisible();
  await page
    .getByTestId("workflow-node")
    .filter({ hasText: "Record result" })
    .click();
  await page
    .getByLabel("Node label", { exact: true })
    .fill("Record verified result");
  await page.getByRole("button", { name: "Save draft", exact: true }).click();
  await expect(page.getByRole("status")).toHaveText("Draft saved.");
  await page.getByRole("button", { name: "Validate", exact: true }).click();
  await expect(
    page.getByText("Workflow is valid.", { exact: false }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Publish version", exact: true })
    .click();
  await expect(page.getByRole("status")).toHaveText("Version 1 published.");
  await page
    .getByTestId("workflow-node")
    .filter({ hasText: "Record verified result" })
    .click();
  await page
    .getByLabel("Node label", { exact: true })
    .fill("A different draft label");
  await page.getByRole("button", { name: "Save draft", exact: true }).click();
  await expect(page.getByRole("status")).toHaveText("Draft saved.");
  await page
    .getByLabel("Definition", { exact: true })
    .selectOption({ label: "Published version 1" });
  await expect(
    page
      .getByTestId("workflow-node")
      .filter({ hasText: "Record verified result" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Publish version", exact: true }),
  ).toHaveCount(0);
  await page.setViewportSize({ width: 1440, height: 1100 });
  await page.screenshot({
    path: testInfo.outputPath("workflow-builder.png"),
    fullPage: true,
  });
  await page.reload();
  await expect(
    page
      .getByTestId("workflow-node")
      .filter({ hasText: "A different draft label" }),
  ).toBeVisible();
});
