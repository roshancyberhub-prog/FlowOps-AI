import { expect, test } from "@playwright/test";

test("sign-in page is accessible and validates empty fields", async ({
  page,
}) => {
  await page.goto("/login");
  await expect(
    page.getByRole("heading", { name: "Welcome back" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByLabel("Work email")).toBeFocused();
});
