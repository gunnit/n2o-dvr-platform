import assert from "node:assert/strict";
import test from "node:test";

import { fetchAllFeedback } from "../src/app/(dashboard)/admin/feedback/feedback-pagination.ts";

test("admin feedback pagination loads every page and retains the newest duplicate", async () => {
  const firstPage = Array.from({ length: 500 }, (_, index) => ({
    id: `row-${index}`,
    value: index === 499 ? "newest-copy" : `value-${index}`,
  }));
  const paths = [];

  const rows = await fetchAllFeedback(async (path) => {
    paths.push(path);
    if (path === "/api/v1/feedback?limit=500&offset=0") return firstPage;
    if (path === "/api/v1/feedback?limit=500&offset=500") {
      return [
        { id: "row-499", value: "older-copy" },
        { id: "row-500", value: "value-500" },
      ];
    }
    throw new Error(`Unexpected path: ${path}`);
  });

  assert.deepEqual(paths, [
    "/api/v1/feedback?limit=500&offset=0",
    "/api/v1/feedback?limit=500&offset=500",
  ]);
  assert.equal(rows.length, 501);
  assert.equal(rows[499].value, "newest-copy");
  assert.equal(rows[500].id, "row-500");
});
