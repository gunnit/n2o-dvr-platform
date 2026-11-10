"use client";

import {
  memo,
  useCallback,
  useEffect,
  useRef,
  useState,
  type ClipboardEvent,
  type KeyboardEvent,
  type ReactNode,
} from "react";
import { RotateCcw } from "lucide-react";

import {
  effectiveRunStyle,
  replacementRunStyle,
  type ParagraphLook,
} from "@/components/documents/editor/doc-typography";
import { cn } from "@/lib/utils";
import type { PreviewParagraph, PreviewRun } from "@/types";

// Run colours, sizes and weights come straight from the .docx and are
// exempt from the DESIGN.md chrome palette — they reproduce the document.
// The paragraph box (DocParagraph) carries the paragraph's own look.
function RunSpan({ run, look }: { run: PreviewRun; look: ParagraphLook }) {
  return <span style={effectiveRunStyle(run, look)}>{run.text}</span>;
}

interface EditSession {
  initialText: string;
  initialOverride: string | null;
  committed: boolean;
}

export interface EditableParagraphProps {
  paragraph: PreviewParagraph;
  /**
   * The paragraph's resolved look (doc-typography). Its box — size,
   * colour, alignment, spacing — is drawn by the caller; runs, overrides
   * and the live edit add their own formatting on top.
   */
  look: ParagraphLook;
  /** Saved/pending override for this paragraph, if any. */
  override: string | undefined;
  /**
   * Single mutation channel: text commits pass the new text, "Ripristina"
   * passes null, Escape-revert passes the pre-edit override (or null).
   */
  onOverrideChange: (addr: string, value: string | null) => void;
  /**
   * Extra static content (inline images). Paragraphs carrying images are
   * always editable=false per the API contract, so this never coexists
   * with an edit session.
   */
  trailing?: ReactNode;
}

export const EditableParagraph = memo(function EditableParagraph({
  paragraph,
  look,
  override,
  onOverrideChange,
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

  // One line high even when empty: an empty paragraph keeps its height,
  // as on paper.
  const baseClassName = "min-h-[1lh] break-words whitespace-pre-wrap";

  // An override replaces the runs with plain text in the first run's
  // formatting — mirroring what the backend does to the .docx (one run,
  // first run's formatting, "\n" = line break).
  const replacementStyle = replacementRunStyle(paragraph, look);
  const staticContent = (
    <>
      {hasOverride ? (
        <span style={replacementStyle}>{override}</span>
      ) : (
        paragraph.runs.map((run, i) => <RunSpan key={i} run={run} look={look} />)
      )}
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
        // App chrome inside the sheet: back to the app's own type.
        <div className="invisible absolute -top-3 right-0 z-10 flex items-center gap-1 font-body leading-normal not-italic group-focus-within:visible group-hover:visible">
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
            className="inline-flex items-center gap-1 rounded-sm border border-[#e5edf5] bg-white px-1.5 py-0.5 text-[10px] font-medium text-[#273951] normal-case shadow-stripe-ambient transition-colors hover:bg-[#f6f9fc]"
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
          // The text is typed in the look it will print with (the first
          // run's), over the cell fill or art. Never in display capitals:
          // innerText would hand them back as the typed text.
          style={{ ...replacementStyle, textTransform: "none" }}
          className={cn(baseClassName, "rounded-sm ring-2 ring-primary outline-none")}
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
