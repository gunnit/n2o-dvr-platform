import { AuthSplit } from "@/components/auth/auth-split";
import { RegisterForm } from "./register-form";

/**
 * Server component on purpose: reading `?piano=` here instead of with
 * `useSearchParams()` in the form is what lets the signup form exist in the
 * served HTML. The route is dynamic rather than static as a result, which is
 * correct — what it renders genuinely depends on the query string.
 *
 * `metadata` stays in the sibling layout, which already owns it.
 */
export default async function RegisterPage({
  searchParams,
}: {
  searchParams: Promise<{ piano?: string | string[] }>;
}) {
  const { piano } = await searchParams;
  // A repeated ?piano= gives an array; take the first rather than rendering
  // "B_BASE,B_PLUS" as a plan code.
  const planCode = Array.isArray(piano) ? (piano[0] ?? null) : (piano ?? null);

  return (
    <AuthSplit
      panelWidth="440px"
      backdrop={{
        eyebrow: "Il tuo ambiente di lavoro",
        title: <>Il primo fascicolo parte da qui.</>,
        body: "Attivi l'organizzazione, carichi la prima azienda e il sopralluogo comincia. I documenti si compongono da sé.",
      }}
    >
      <RegisterForm piano={planCode} />
    </AuthSplit>
  );
}
