import { test, expect } from "@playwright/test";

const API_BASE = process.env.E2E_API_URL || "http://localhost:8000";

test("shopping agent shows the real Guard's fail-closed result and provenance", async ({ page }) => {
  const agentResponse = await page.request.post(`${API_BASE}/agents`, { data: {
    name: "Shopping UI test", max_transaction: 5000, daily_limit: 10000,
    allowed_categories: ["sports"], blocked_categories: [], requires_approval_above: 4900,
  } });
  expect(agentResponse.ok()).toBeTruthy();
  const agent = await agentResponse.json();
  await page.request.post(`${API_BASE}/dashboard/llm-toggle?disabled=true`);
  try {
    await page.goto("/dashboard");
    const box = page.getByRole("region", { name: "Shopping Agent" });
    await expect(box).toBeVisible();
    await box.getByLabel("Agent", { exact: true }).selectOption(agent.id);
    await box.getByLabel("Purchase intent").fill("Buy shoes or running shoes under 5000");
    await box.getByRole("button", { name: "Run", exact: true }).click();
    await expect(box.getByText("Review", { exact: true })).toBeVisible({ timeout: 30_000 });
    await expect(box.getByText(/Agent model: rules_only/)).toBeVisible();
    await expect(box.getByText(/Guard model: rules_only/)).toBeVisible();
    await expect(box.getByText(/Risk:.*Intent:/)).toBeVisible();
    await expect(box.getByRole("link", { name: /Audit trail/ })).toBeVisible();
  } finally {
    await page.request.post(`${API_BASE}/dashboard/llm-toggle?disabled=false`);
  }
});

test("shopping agent displays API errors without a decision badge", async ({ page }) => {
  await page.goto("/dashboard");
  const box = page.getByRole("region", { name: "Shopping Agent" });
  await expect(box.getByRole("button", { name: "Run", exact: true })).toBeEnabled();
  await box.getByLabel("Purchase intent").fill("Buy running shoes under 1");
  await box.getByRole("button", { name: "Run", exact: true }).click();
  await expect(box.getByRole("alert")).toContainText("No local catalog product fits");
  await expect(box.getByRole("link", { name: /Audit trail/ })).toHaveCount(0);
});
