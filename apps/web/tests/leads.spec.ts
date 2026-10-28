import { expect, test } from "@playwright/test";

test("register, persist leads, edit, archive, restore and isolate workspaces", async ({
  page,
}, testInfo) => {
  const suffix = `${Date.now()}-${testInfo.workerIndex}`;
  const workspace = `Demo operations ${suffix}`;
  const email = `buyer-${suffix}@example.com`;
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/login");
  await page
    .getByRole("button", { name: "Create an account", exact: true })
    .click();
  await page.getByLabel("Full name", { exact: true }).fill("Demo Operator");
  await page
    .getByLabel("Work email", { exact: true })
    .fill(`operator-${suffix}@example.com`);
  await page
    .getByLabel("Password", { exact: true })
    .fill("Fictional-Browser-Passphrase-42");
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await page.getByLabel("Workspace name", { exact: true }).fill(workspace);
  await page
    .getByRole("button", { name: "Create workspace", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Welcome back, Demo." }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Leads", exact: true }).click();
  await page.getByRole("button", { name: "Add lead", exact: true }).click();
  await page.getByLabel("Full name *", { exact: true }).fill("Demo Buyer");
  await page.getByLabel("Work email *", { exact: true }).fill(email);
  await page.getByLabel("Company", { exact: true }).fill("Example Company");
  await page.getByRole("button", { name: "Save lead", exact: true }).click();
  await expect(page.getByRole("status")).toHaveText("Lead added.");
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Demo Buyer", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Edit Demo Buyer", exact: true })
    .click();
  await page.getByLabel("Company", { exact: true }).fill("Updated Company");
  await page.getByRole("button", { name: "Save lead", exact: true }).click();
  await expect(
    page.getByText("Updated Company", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Add lead", exact: true }).click();
  await page.getByLabel("Full name *", { exact: true }).fill("Duplicate Buyer");
  await page.getByLabel("Work email *", { exact: true }).fill(email);
  await page.getByRole("button", { name: "Save lead", exact: true }).click();
  await expect(page.getByRole("dialog").getByRole("alert")).toContainText(
    "email already exists",
  );
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  page.once("dialog", (dialog) => dialog.accept());
  await page
    .getByRole("button", { name: "Archive Demo Buyer", exact: true })
    .click();
  await expect(page.getByRole("status")).toHaveText("Lead archived.");
  await page.getByLabel("Filter by status").selectOption("archived");
  await page
    .getByRole("button", { name: "Edit Demo Buyer", exact: true })
    .click();
  await page.getByLabel("Status", { exact: true }).selectOption("new");
  await page.getByRole("button", { name: "Save lead", exact: true }).click();
  await page.getByLabel("Filter by status").selectOption("");
  await expect(
    page.getByRole("button", { name: "Demo Buyer", exact: true }),
  ).toBeVisible();
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.screenshot({
    path: testInfo.outputPath("leads-desktop.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  const mobileLayout = await page.evaluate(() => ({
    width: window.innerWidth,
    scroll: document.documentElement.scrollWidth,
    wide: Array.from(document.querySelectorAll("body *"))
      .filter((element) => {
        if (element.getBoundingClientRect().right <= window.innerWidth)
          return false;
        let parent = element.parentElement;
        while (parent && parent !== document.body) {
          if (
            ["auto", "hidden", "scroll"].includes(
              getComputedStyle(parent).overflowX,
            )
          )
            return false;
          parent = parent.parentElement;
        }
        return true;
      })
      .map((element) => ({
        tag: element.tagName,
        classes: element.className,
        right: element.getBoundingClientRect().right,
      }))
      .slice(0, 15),
  }));
  console.log("Mobile layout", JSON.stringify(mobileLayout));
  expect(mobileLayout.scroll).toBeLessThanOrEqual(mobileLayout.width);

  await page.screenshot({
    path: testInfo.outputPath("leads-mobile.png"),
    fullPage: true,
  });
  await page
    .getByRole("link", { name: "Team & workspace", exact: true })
    .click();
  await page
    .getByLabel("Workspace name", { exact: true })
    .fill(`Separate ${suffix}`);
  await page
    .getByRole("button", { name: "Create workspace", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("Workspace created");
  await page
    .getByLabel("Workspace", { exact: true })
    .selectOption({ label: `Separate ${suffix}` });
  await page.getByRole("link", { name: "Leads", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Meet your next opportunity." }),
  ).toBeVisible();
  await page
    .getByLabel("Workspace", { exact: true })
    .selectOption({ label: workspace });
  await expect(
    page.getByRole("button", { name: "Demo Buyer", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Welcome back", exact: true }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});
