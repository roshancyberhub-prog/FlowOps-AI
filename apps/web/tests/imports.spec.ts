import { expect, test } from "@playwright/test";

test("import a mapped CSV outside the request and inspect every record result", async ({
  page,
}, testInfo) => {
  test.setTimeout(90000);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
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
  await page.getByRole("link", { name: "CSV imports", exact: true }).click();
  const csv =
    "Full Name,Email,Company\nBuyer One,buyer-one@example.com,Example Co\nBuyer Two,buyer-two@example.com,Example Tools\nInvalid,not-an-email,Example Co\nDuplicate,BUYER-ONE@example.com,Example Co\n";
  await page
    .getByLabel("CSV file", { exact: true })
    .setInputFiles({
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
  await page.screenshot({
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
  await page.screenshot({
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
  expect(errors).toEqual([]);
});
