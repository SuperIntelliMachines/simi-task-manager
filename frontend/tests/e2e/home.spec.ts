import { expect, test } from "@playwright/test";

test("task workbench renders", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Tasks" }).click();
  await expect(page.getByText("Task Workbench")).toBeVisible();
  await expect(page.getByText("Renew Ravi policy bundle")).toBeVisible();
});
