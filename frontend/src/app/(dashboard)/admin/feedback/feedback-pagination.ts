const FEEDBACK_PAGE_SIZE = 500;

export async function fetchAllFeedback<T extends { id: string }>(
  apiFetch: (path: string) => Promise<T[]>,
): Promise<T[]> {
  const rowsById = new Map<string, T>();
  let offset = 0;

  while (true) {
    const page = await apiFetch(
      `/api/v1/feedback?limit=${FEEDBACK_PAGE_SIZE}&offset=${offset}`,
    );
    for (const row of page) {
      if (!rowsById.has(row.id)) rowsById.set(row.id, row);
    }
    if (page.length < FEEDBACK_PAGE_SIZE) break;
    offset += page.length;
  }

  return [...rowsById.values()];
}
