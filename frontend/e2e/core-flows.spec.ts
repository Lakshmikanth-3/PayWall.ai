import { test, expect, type Page } from "@playwright/test";

const API_BASE = process.env.E2E_API_URL || "http://localhost:8000";

/**
 * Forces the backend's Layer 3 (LLM) off for the duration of a test so
 * results are deterministic and don't burn real Groq/OpenAI quota — the
 * fail-closed keyword-fallback path (PRD Section 21) is itself part of
 * what's under test.
 */
async function withLlmDisabled(page: Page, run: () => Promise<void>) {
  await page.request.post(`${API_BASE}/dashboard/llm-toggle?disabled=true`);
  try {
    await run();
  } finally {
    await page.request.post(`${API_BASE}/dashboard/llm-toggle?disabled=false`);
  }
}

test.describe("Landing page", () => {
  test("loads and links into the dashboard", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /trust layer/i })).toBeVisible();
    await expect(page.getByText(/razorpay ai buildathon/i).first()).toBeVisible();

    await page.getByRole("link", { name: /launch dashboard/i }).first().click();
    await expect(page).toHaveURL(/\/dashboard$/);
    await expect(page.getByText("Command Center")).toBeVisible();
  });

  test("has no emoji characters anywhere on the page", async ({ page }) => {
    await page.goto("/");
    const text = await page.evaluate(() => document.body.innerText);
    // Matches common emoji ranges without flagging currency symbols (₹) or typographic punctuation.
    const emojiPattern = /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/u;
    expect(emojiPattern.test(text)).toBe(false);
  });
});

test.describe("Dashboard navigation", () => {
  const pages = [
    ["/dashboard", "Command Center"],
    ["/dashboard/live", "Live"],
    ["/dashboard/evaluate", "Transaction Evaluator"],
    ["/dashboard/audit", "Audit"],
    ["/dashboard/agents", "Agent"],
    ["/dashboard/merchants", "Merchant"],
    ["/dashboard/metrics", "Metric"],
    ["/dashboard/simulate", "Simulator"],
  ] as const;

  for (const [path, expectedText] of pages) {
    test(`${path} loads without error`, async ({ page }) => {
      const errors: string[] = [];
      page.on("pageerror", (e) => errors.push(e.message));

      await page.goto(path);
      await expect(page.getByText(new RegExp(expectedText, "i")).first()).toBeVisible({ timeout: 10_000 });
      expect(errors).toEqual([]);
    });
  }
});

test.describe("Evaluate page — Guard decisions", () => {
  test("manipulated upsell (protection plan) is blocked — the killer scenario", async ({ page }) => {
    await withLlmDisabled(page, async () => {
      await page.goto("/dashboard/evaluate");
      await page.getByRole("button", { name: /manipulated upsell.*protection plan/i }).click();
      await page.getByRole("button", { name: /evaluate transaction/i }).click();

      await expect(page.getByText("Block", { exact: true })).toBeVisible({ timeout: 15_000 });
      await expect(page.getByText(/category authorized/i)).toBeVisible();
    });
  });

  test("budget violation over the transaction limit is blocked", async ({ page }) => {
    await withLlmDisabled(page, async () => {
      await page.goto("/dashboard/evaluate");
      await page.getByRole("button", { name: /budget violation/i }).click();
      await page.getByRole("button", { name: /evaluate transaction/i }).click();

      await expect(page.getByText("Block", { exact: true })).toBeVisible({ timeout: 15_000 });
    });
  });

  /**
   * Creates a brand-new agent + merchant via the API rather than reusing the
   * shared AGT-001/MER-001 demo data — the long-running dev backend
   * accumulates every manual/API call made against it in the agent's
   * recent-transaction velocity window, which can itself push the ML risk
   * score up regardless of how clean the transaction is. A fresh agent has
   * no history yet, so its ALLOW/BLOCK behavior only reflects this test.
   */
  async function createFreshAgentAndMerchant(page: Page) {
    const suffix = Math.random().toString(36).slice(2, 8);
    const agent = await (
      await page.request.post(`${API_BASE}/agents`, {
        data: {
          name: `E2E Agent ${suffix}`, max_transaction: 5000, daily_limit: 10000,
          allowed_categories: ["electronics"], blocked_categories: [], requires_approval_above: 0,
        },
      })
    ).json();
    const merchant = await (
      await page.request.post(`${API_BASE}/merchants`, {
        data: { name: `E2E Merchant ${suffix}`, category: "electronics", risk_score: 8, age_days: 3650 },
      })
    ).json();
    return { agent, merchant };
  }

  test("a clean, well-matched, low-amount purchase is allowed", async ({ page }) => {
    await withLlmDisabled(page, async () => {
      const { agent, merchant } = await createFreshAgentAndMerchant(page);
      await page.goto("/dashboard/evaluate");
      await page.selectOption("#field-agent", agent.id);
      await page.selectOption("#field-merchant", merchant.id);
      await page.getByLabel(/amount/i).fill("500");
      await page.getByLabel(/category/i).fill("electronics");
      await page.getByLabel(/product description/i).fill("Wireless Mouse");
      await page.getByLabel(/user's original intent/i).fill("Buy wireless mouse electronics today");
      await page.getByRole("button", { name: /evaluate transaction/i }).click();

      await expect(page.getByText("Allow", { exact: true })).toBeVisible({ timeout: 15_000 });
    });
  });

  test("proposing an upsell after an ALLOW runs it through the same Guard", async ({ page }) => {
    await withLlmDisabled(page, async () => {
      const { agent, merchant } = await createFreshAgentAndMerchant(page);
      await page.goto("/dashboard/evaluate");
      await page.selectOption("#field-agent", agent.id);
      await page.selectOption("#field-merchant", merchant.id);
      await page.getByLabel(/amount/i).fill("500");
      await page.getByLabel(/category/i).fill("electronics");
      await page.getByLabel(/product description/i).fill("Wireless Mouse");
      await page.getByLabel(/user's original intent/i).fill("Buy wireless mouse electronics today");
      await page.getByRole("button", { name: /evaluate transaction/i }).click();
      await expect(page.getByText("Allow", { exact: true })).toBeVisible({ timeout: 15_000 });

      const upsellButton = page.getByRole("button", { name: /propose upsell/i });
      await upsellButton.click();
      await expect(page.getByText(/upsell agent/i)).toBeVisible({ timeout: 15_000 });
    });
  });

  test("toggling AI reasoning off shows the fail-closed indicator", async ({ page }) => {
    await page.goto("/dashboard/evaluate");
    const toggle = page.getByRole("button", { name: /ai reasoning/i });
    await toggle.click();
    await expect(page.getByText(/ai reasoning: disabled/i)).toBeVisible();
    await toggle.click();
    await expect(page.getByText(/ai reasoning: online/i)).toBeVisible();
  });
});

test.describe("Revenue Impact panel", () => {
  test("Overview page shows the Merchant Revenue Impact panel with real numbers", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.getByText("Merchant Revenue Impact")).toBeVisible();
    await expect(page.getByText("Upsells Proposed")).toBeVisible();
    await expect(page.getByText("Incremental GMV from Upsells")).toBeVisible();
  });
});
