/**
 * Field, label and button classes shared by /login and /register.
 *
 * The two pages are one funnel — /prezzi sends a visitor to /register, and
 * /register hands off to /login — so they have to be the same instrument.
 * They used to disagree on every measurement: 46px fields with a 4px radius
 * and a 3px focus ring on login, 40px fields with a 6px radius and a 2px ring
 * on register, because register reached for the shadcn `Input`/`Button` built
 * for the dense application shell behind the paywall. These are the login
 * measurements, kept in one place so they cannot drift again.
 */

export const FIELD =
  "h-[46px] rounded-sm border border-[#e5edf5] bg-white px-3.5 text-[15px] text-[#061b31] outline-none transition-[border-color,box-shadow] duration-150 placeholder:text-[#8a96ab] focus:border-primary focus:shadow-[0_0_0_3px_rgba(0,61,116,0.13)] aria-invalid:border-[#c72a3a] aria-invalid:shadow-[0_0_0_3px_rgba(199,42,58,0.12)]";

export const FIELD_LABEL =
  "text-[11.5px] font-medium tracking-[0.09em] text-[#273951] uppercase";

// The lifted hover shadow is spelled out rather than reusing .shadow-stripe-deep:
// that is a plain class in globals.css, not a Tailwind utility, so hover:/
// not-disabled: variants cannot be stacked onto it. The `shadow:` type hint is
// required — without it Tailwind reads a value starting with rgba() as a shadow
// *colour* and emits --tw-shadow-color instead of box-shadow.
export const SUBMIT =
  "shadow-stripe-ambient mt-1.5 flex h-[46px] w-full items-center justify-center gap-2.5 rounded-sm bg-primary text-[15px] font-medium tracking-[0.01em] text-white transition-[background-color,transform,box-shadow] duration-150 hover:not-disabled:-translate-y-px hover:not-disabled:bg-[#1b5594] hover:not-disabled:shadow-[shadow:rgba(50,50,93,0.25)_0px_10px_20px_-12px,rgba(0,0,0,0.1)_0px_6px_12px_-8px] disabled:opacity-90";

/** Outlined companion to SUBMIT — the "other account state" route out. */
export const SECONDARY =
  "flex h-[46px] items-center justify-center gap-2 rounded-sm border border-[#cfe0f2] text-[14.5px] font-medium text-primary transition-[background-color,border-color] duration-150 hover:border-[#a5c8ff] hover:bg-primary/4";
