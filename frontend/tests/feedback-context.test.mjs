import assert from "node:assert/strict";
import test from "node:test";

import {
  PAGE_URL_MAX,
  ROUTE_MAX,
  USER_AGENT_MAX,
  buildFeedbackContext,
} from "../src/components/feedback/feedback-context.ts";

test("auto-captured context is clamped to what the API stores", () => {
  const context = buildFeedbackContext({
    pageUrl: "https://dvr-sicurezza.it/survey?q=" + "x".repeat(3000),
    route: "/survey/" + "y".repeat(900),
    userAgent: "Mozilla/5.0 " + "z".repeat(900),
  });

  // The operator typed none of these — an over-long one must never be the
  // reason their report comes back as a 422.
  assert.equal(context.page_url.length, PAGE_URL_MAX);
  assert.equal(context.route.length, ROUTE_MAX);
  assert.equal(context.user_agent.length, USER_AGENT_MAX);
  assert.ok(context.page_url.startsWith("https://dvr-sicurezza.it/survey?q="));
});

test("context that already fits is passed through untouched", () => {
  const context = buildFeedbackContext({
    pageUrl: "https://dvr-sicurezza.it/survey/abc",
    route: "/survey/abc",
    userAgent: "Mozilla/5.0",
  });

  assert.deepEqual(context, {
    page_url: "https://dvr-sicurezza.it/survey/abc",
    route: "/survey/abc",
    user_agent: "Mozilla/5.0",
  });
});

test("missing context is sent as null, not as an empty string", () => {
  assert.deepEqual(buildFeedbackContext({}), {
    page_url: null,
    route: null,
    user_agent: null,
  });
  assert.deepEqual(
    buildFeedbackContext({ pageUrl: "", route: null, userAgent: undefined }),
    { page_url: null, route: null, user_agent: null },
  );
});
