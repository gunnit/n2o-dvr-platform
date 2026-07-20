"use client";

import {
  memo,
  useCallback,
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type ClipboardEvent,
  type KeyboardEvent,
  type ReactNode,
} from "react";
import { RotateCcw } from "lucide-react";

import { cn } from "@/lib/utils";
import type { PreviewParagraph, PreviewRun } from "@/types";

/** pt -> px at 96dpi (1pt = 4/3 px). */
function ptToPx(pt: number): number {
  return Math.round(pt * (4 / 3) * 100) / 100;
}

const ALIGNMENT_CLASS: Record<string, string> = {
  left: "text-left",
  center: "text-center",
  right: "text-right",
  justify: "text-justify",
};

// Word "Heading N" styles mapped onto the sheet's type scale. Sizes
// approximate the DVR templates' hierarchy — faithful enough for a preview
// whose ground truth stays the .docx itself. Margins live here so body
// paragraphs can keep their own tighter rhythm.
const HEADING_CLASS: Record<number, string> = {
  1: "mt-6 mb-3 text-[23px] font-bold leading-[1.25]",
  2: "mt-5 mb-2.5 text-[19px] font-bold leading-[1.25]",
  3: "mt-4 mb-2 text-[16px] font-semibold leading-[1.3]",
  4: "mt-3 mb-1.5 text-[14.5px] font-semibold leading-[1.3]",
};

// Run colors/sizes come straight from the .docx and are exempt from the
// DESIGN.md chrome palette — they reproduce the document.
function RunSpan({ run }: { run: PreviewRun }) {
  const style: CSSProperties = {};
  if (run.color) style.color = `#${run.color}`;
  if (run.size !== null) style.fontSize = `${ptToPx(run.size)}px`;
  return (
    <span
      className={cn(
        run.bold && "font-bold",
        run.italic && "italic",
        run.underline && "underline",
      )}
      style={run.color || run.size !== null ? style : undefined}
    >
      {run.text}
    </span>
  );
}

interface EditSession {
  initialText: string;
  initialOverride: string | null;
  committed: boolean;
}

export interface EditableParagraphProps {
  paragraph: PreviewParagraph;
  /** Saved/pending override for this paragraph, if any. */
  override: string | undefined;
  /**
   * Single mutation channel: text commits pass the new text, "Ripristina"
   * passes null, Escape-revert passes the pre-edit override (or null).
   */
  onOverrideChange: (addr: string, value: string | null) => void;
  /** Rendered inside a table cell: tighter type and spacing. */
  inCell?: boolean;
  /**
   * Extra static content (inline images). Paragraphs carrying images are
   * always editable=false per the API contract, so this never coexists
   * with an edit session.
   */
  trailing?: ReactNode;
}

export const EditableParagraph = memo(function EditableParagraph({
  paragraph,
  override,
  onOverrideChange,
  inCell = false,
  trailing,
}: EditableParagraphProps) {
  const [editing, setEditing] = useState(false);
  const editRef = useRef<HTMLDivElement | null>(null);
  const sessionRef = useRef<EditSession | null>(null);
  const debounceRef = useRef<number | null>(null);
  // True while an IME composition (accented chars, dead keys) is open.
  const composingRef = useRef(false);
  // Text of the live edit session as of the last non-composing input, for
  // the unmount flush — the DOM node is already detached by the time a
  // passive cleanup runs.
  const liveValueRef = useRef<string | null>(null);

  const runText = paragraph.runs.map((r) => r.text).join("");
  const effectiveText = override ?? runText;
  const hasOverride = override !== undefined;

  // Latest effective text for the debounced commit closure. Updated in an
  // effect (not during render) to stay strict-mode clean; commits only run
  // from user events, which always fire after effects.
  const effectiveTextRef = useRef(effectiveText);
  useEffect(() => {
    effectiveTextRef.current = effectiveText;
  });

  const clearDebounce = useCallback(() => {
    if (debounceRef.current !== null) {
      window.clearTimeout(debounceRef.current);
      debounceRef.current = null;
    }
  }, []);

  // contentEditable keeps a trailing <br> after the last line; strip the
  // single newline it adds to innerText.
  const readValue = useCallback((): string => {
    const el = editRef.current;
    if (!el) return "";
    return el.innerText.replace(/\n$/, "");
  }, []);

  const commit = useCallback(() => {
    if (!sessionRef.current) return;
    const text = readValue();
    if (text !== effectiveTextRef.current) {
      onOverrideChange(paragraph.addr, text);
      sessionRef.current.committed = true;
    }
  }, [onOverrideChange, paragraph.addr, readValue]);

  const startEditing = useCallback(() => {
    if (!paragraph.editable || sessionRef.current) return;
    sessionRef.current = {
      initialText: effectiveTextRef.current,
      initialOverride: override ?? null,
      committed: false,
    };
    liveValueRef.current = effectiveTextRef.current;
    setEditing(true);
  }, [override, paragraph.editable]);

  // Populate + focus the contentEditable when an edit session starts. The
  // text is set imperatively (never as React children) so re-renders from
  // mid-session autosaves cannot clobber the caret.
  useEffect(() => {
    if (!editing) return;
    const el = editRef.current;
    if (!el || !sessionRef.current) return;
    el.textContent = sessionRef.current.initialText;
    el.focus();
    const range = document.createRange();
    range.selectNodeContents(el);
    range.collapse(false);
    const selection = window.getSelection();
    selection?.removeAllRanges();
    selection?.addRange(range);
  }, [editing]);

  // Flush — not cancel — a pending debounced commit on unmount, so the
  // last keystrokes of an edit session survive when the editor disappears
  // without a blur (e.g. route change while the paragraph is focused).
  // The contentEditable ref is already detached when this passive cleanup
  // runs, so commit from the mirrored live value: whenever a debounce is
  // pending, the last non-composing input has mirrored the exact DOM text.
  useEffect(() => {
    return () => {
      if (debounceRef.current === null) return;
      window.clearTimeout(debounceRef.current);
      debounceRef.current = null;
      if (!sessionRef.current) return;
      const text = liveValueRef.current;
      if (text !== null && text !== effectiveTextRef.current) {
        onOverrideChange(paragraph.addr, text);
        sessionRef.current.committed = true;
      }
    };
  }, [onOverrideChange, paragraph.addr]);

  const handleInput = useCallback(() => {
    // Mid-composition input is provisional: never mirror or schedule a
    // commit for it (the compositionend handler restarts the debounce).
    if (composingRef.current) return;
    liveValueRef.current = readValue();
    clearDebounce();
    debounceRef.current = window.setTimeout(() => {
      debounceRef.current = null;
      commit();
    }, 1000);
  }, [clearDebounce, commit, readValue]);

  const handleCompositionStart = useCallback(() => {
    composingRef.current = true;
    // A debounce firing mid-composition would persist half-composed text.
    clearDebounce();
  }, [clearDebounce]);

  const handleCompositionEnd = useCallback(() => {
    composingRef.current = false;
    // The composed text is final now: mirror it and restart the debounce.
    handleInput();
  }, [handleInput]);

  const handleBlur = useCallback(() => {
    clearDebounce();
    if (sessionRef.current) commit();
    sessionRef.current = null;
    setEditing(false);
  }, [clearDebounce, commit]);

  const handleEditKeyDown = useCallback(
    (event: KeyboardEvent<HTMLDivElement>) => {
      // Keys that control an open IME composition (confirm/cancel) belong
      // to the IME — hijacking Enter here would insert a spurious newline
      // on every composition confirm.
      if (event.nativeEvent.isComposing) return;
      if (event.key === "Escape") {
        event.preventDefault();
        clearDebounce();
        const session = sessionRef.current;
        sessionRef.current = null; // the blur handler must not commit
        if (session?.committed) {
          // A debounced autosave already fired mid-session: restore the
          // pre-edit state (previous override, or none at all).
          onOverrideChange(paragraph.addr, session.initialOverride);
        }
        setEditing(false);
        return;
      }
      if (event.key === "Enter") {
        // Newline within the paragraph (a <w:br/> in the .docx), never a
        // new block. execCommand keeps native undo history working.
        event.preventDefault();
        document.execCommand("insertText", false, "\n");
      }
    },
    [clearDebounce, onOverrideChange, paragraph.addr],
  );

  const handlePaste = useCallback((event: ClipboardEvent<HTMLDivElement>) => {
    event.preventDefault();
    const text = event.clipboardData.getData("text/plain");
    if (text) document.execCommand("insertText", false, text);
  }, []);

  const handleStaticKeyDown = useCallback(
    (event: KeyboardEvent<HTMLDivElement>) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        startEditing();
      }
    },
    [startEditing],
  );

  const baseClassName = cn(
    "min-h-[1.45em] break-words whitespace-pre-wrap",
    inCell ? "my-0.5 text-[12.5px] leading-[1.4]" : "text-[14px] leading-[1.55]",
    !inCell &&
      (paragraph.heading_level !== null
        ? HEADING_CLASS[paragraph.heading_level]
        : "my-1"),
    ALIGNMENT_CLASS[paragraph.alignment ?? "left"],
  );

  // An override replaces the runs with plain text in the paragraph's base
  // style — mirroring what the backend does to the .docx (one run, first
  // run's formatting, "\n" = line break).
  const staticContent = (
    <>
      {hasOverride
        ? override
        : paragraph.runs.map((run, i) => <RunSpan key={i} run={run} />)}
      {trailing}
    </>
  );

  if (!paragraph.editable) {
    return <div className={baseClassName}>{staticContent}</div>;
  }

  return (
    <div
      className={cn(
        "group relative",
        hasOverride && "-ml-[11px] border-l-2 border-l-primary pl-[9px]",
      )}
    >
      {hasOverride && !editing && (
        <div className="invisible absolute -top-3 right-0 z-10 flex items-center gap-1 group-focus-within:visible group-hover:visible">
          <span className="rounded-sm border border-[rgba(0,61,116,0.2)] bg-white px-1.5 py-0.5 text-[10px] font-semibold tracking-[0.04em] text-primary uppercase shadow-stripe-ambient">
            Modificato
          </span>
          <button
            type="button"
            onClick={(event) => {
              event.stopPropagation();
              onOverrideChange(paragraph.addr, null);
            }}
            title="Ripristina il testo originale"
            aria-label="Ripristina il testo originale"
            className="inline-flex items-center gap-1 rounded-sm border border-[#e5edf5] bg-white px-1.5 py-0.5 text-[10px] font-medium text-[#273951] shadow-stripe-ambient transition-colors hover:bg-[#f6f9fc]"
          >
            <RotateCcw className="h-2.5 w-2.5" strokeWidth={2} />
            Ripristina
          </button>
        </div>
      )}
      {editing ? (
        <div
          key="editor"
          ref={editRef}
          contentEditable
          suppressContentEditableWarning
          role="textbox"
          aria-multiline="true"
          aria-label="Modifica testo del paragrafo"
          spellCheck={false}
          onInput={handleInput}
          onBlur={handleBlur}
          onKeyDown={handleEditKeyDown}
          onPaste={handlePaste}
          onCompositionStart={handleCompositionStart}
          onCompositionEnd={handleCompositionEnd}
          className={cn(
            baseClassName,
            "rounded-sm bg-white ring-2 ring-primary outline-none",
          )}
        />
      ) : (
        <div
          key="static"
          role="button"
          tabIndex={0}
          title="Clicca per modificare"
          onClick={startEditing}
          onKeyDown={handleStaticKeyDown}
          className={cn(
            baseClassName,
            "cursor-edit rounded-sm transition-shadow hover:ring-1 hover:ring-[#a5c8ff] focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-primary",
          )}
        >
          {staticContent}
        </div>
      )}
    </div>
  );
});
