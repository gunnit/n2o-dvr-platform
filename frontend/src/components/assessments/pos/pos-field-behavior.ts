export type CsvDraftAction =
  | { type: "edit"; value: string }
  | { type: "sync"; values: string[] };

export function csvDraftReducer(
  current: string,
  action: CsvDraftAction,
): string {
  return action.type === "edit" ? action.value : action.values.join(", ");
}

export function parseCsvDraft(draft: string): string[] {
  return draft
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
}

export function draftCsvValues(draft: string): string[] {
  return draft.split(",");
}

export function normalizeCsvValues(values: string[]): string[] {
  return parseCsvDraft(values.join(","));
}

type ResizableTextarea = Pick<HTMLTextAreaElement, "scrollHeight" | "style">;

export function expandTextareaToContent(textarea: ResizableTextarea): void {
  textarea.style.height = "auto";
  textarea.style.height = `${textarea.scrollHeight}px`;
}
