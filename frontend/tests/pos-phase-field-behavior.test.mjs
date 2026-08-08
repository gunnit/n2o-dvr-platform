import assert from "node:assert/strict";
import test from "node:test";

import {
  csvDraftReducer,
  draftCsvValues,
  expandTextareaToContent,
  normalizeCsvValues,
  parseCsvDraft,
} from "../src/components/assessments/pos/pos-field-behavior.ts";

test("CSV editing preserves the operator's exact commas and trailing spaces", () => {
  const typed = "Caduta dall'alto, Rumore ";

  assert.equal(
    csvDraftReducer("Caduta dall'alto", { type: "edit", value: typed }),
    typed,
  );
});

test("CSV values are trimmed and parsed only when the edit is committed", () => {
  assert.deepEqual(
    parseCsvDraft("Caduta dall'alto,  Rumore con macchine , "),
    ["Caduta dall'alto", "Rumore con macchine"],
  );
});

test("CSV drafts mark the form dirty without discarding commas or spaces", () => {
  assert.deepEqual(draftCsvValues("Caduta dall'alto, Rumore, "), [
    "Caduta dall'alto",
    " Rumore",
    " ",
  ]);
});

test("submitted CSV arrays are normalized even when the input did not blur", () => {
  assert.deepEqual(
    normalizeCsvValues(["Caduta dall'alto", " Rumore", " "]),
    ["Caduta dall'alto", "Rumore"],
  );
});

test("description expansion resets height before applying the full content height", () => {
  const heightWrites = [];
  let height = "80px";
  const style = {};
  Object.defineProperty(style, "height", {
    get: () => height,
    set: (value) => {
      height = value;
      heightWrites.push(value);
    },
  });

  expandTextareaToContent({ scrollHeight: 176, style });

  assert.deepEqual(heightWrites, ["auto", "176px"]);
});

test("description expansion includes the border-box overflow at mobile widths", () => {
  const heightWrites = [];
  let height = "80px";
  const style = {};
  Object.defineProperty(style, "height", {
    get: () => height,
    set: (value) => {
      height = value;
      heightWrites.push(value);
    },
  });

  const textarea = {
    scrollHeight: 156,
    get clientHeight() {
      return height === "156px" ? 154 : 156;
    },
    style,
  };

  expandTextareaToContent(textarea);

  assert.deepEqual(heightWrites, ["auto", "156px", "158px"]);
});
