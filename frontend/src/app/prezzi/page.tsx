import type { Metadata } from "next";
import Link from "next/link";
import { auth } from "@/lib/auth";
import { PricingTabs } from "@/components/landing/pricing-tabs";
import { SUPPORT_EMAIL } from "@/components/landing/pricing-data";
import { Reveal } from "@/components/landing/reveal";
import { SiteFooter } from "@/components/landing/site-footer";
import { SiteNav } from "@/components/landing/site-nav";

export const metadata: Metadata = {
  // Bare "Prezzi": the root layout's `%s | N2O DVR` template applies to child
  // segments, so spelling the suffix out here rendered "Prezzi | N2O DVR |
  // N2O DVR" in the tab and in search results.
  title: "Prezzi",
  description:
    "Piani annuali per consulenti della sicurezza e per aziende. Prezzi, limiti e add-on della piattaforma N2O DVR, IVA esclusa.",
};

const BILLING_FAQ: { question: string; answer: string }[] = [
  {
    question: "Quando viene addebitato",
    answer:
      "L'abbonamento è annuale e si attiva tramite PayPal. L'attivazione è confermata solo dopo la conferma di PayPal: se interrompi l'approvazione non viene addebitato nulla. I prezzi di listino sono al netto dell'IVA 22%.",
  },
  {
    question: "Se un pagamento non va a buon fine",
    answer:
      "PayPal riprova nei giorni successivi e nel frattempo mantieni l'accesso completo. Non interrompiamo un lavoro in corso per un insoluto tecnico: te lo segnaliamo in piattaforma.",
  },
  {
    question: "Cosa succede se disdici",
    answer:
      "Mantieni l'accesso fino alla fine del periodo già pagato. Dopo la scadenza puoi sempre consultare e scaricare tutti i documenti già generati — la conservazione richiesta dal D.Lgs. 81/2008 è garantita — ma non generarne di nuovi.",
  },
  {
    question: "Come si controllano i consumi",
    answer:
      "Nella schermata Abbonamento trovi piano, periodo corrente, crediti AI usati e aziende attive con barra di avanzamento. Gli avvisi arrivano al 75% e al 90%, prima del limite e non quando lo hai superato.",
  },
  {
    question: "Chi può cambiare piano",
    answer:
      "Solo un amministratore dell'organizzazione può passare a un altro piano o disdire. Il passaggio a un piano superiore è immediato; quello a un piano inferiore decorre dal rinnovo.",
  },
  {
    question: "Onboarding, add-on e sconti",
    answer:
      "I costi di onboarding una tantum e gli add-on sono fatturati separatamente dall'abbonamento. Il prepagato triennale è trattabile in fase di offerta: non vendiamo licenze perpetue, perché i contenuti seguono gli aggiornamenti del D.Lgs. 81/2008.",
  },
];

export default async function PrezziPage() {
  const session = await auth();

  return (
    <div className="bg-white">
      <SiteNav variant="solid" />

      <main>
        <PricingTabs signedIn={Boolean(session)} />

        {/* ================= Fatturazione ================= */}
        <section id="fatturazione" className="section-y scroll-mt-20 bg-white">
          <div className="mx-auto w-full max-w-[1160px] px-6 sm:px-7">
            <Reveal>
              <p className="mb-[18px] text-[12px] font-medium tracking-[0.16em] text-[#003d74] uppercase">
                Fatturazione
              </p>
              <h2 className="max-w-[22ch] font-heading text-[clamp(1.8rem,3vw,2.4rem)] leading-[1.12] font-light tracking-[-0.028em] text-balance text-[#061b31]">
                Come funziona il pagamento.
              </h2>
            </Reveal>

            <Reveal className="mt-11 grid gap-11 md:grid-cols-2 md:gap-x-18">
              {BILLING_FAQ.map((item) => (
                <div key={item.question}>
                  <h3 className="text-[15.5px] font-semibold text-[#061b31]">
                    {item.question}
                  </h3>
                  <p className="mt-2.5 text-[14.5px] leading-[1.65] text-[#64748d]">
                    {item.answer}
                  </p>
                </div>
              ))}
            </Reveal>

            <Reveal className="mt-13 rounded-[10px] border border-[#e5edf5] bg-[#f6f9fc] px-[30px] py-[26px]">
              <p className="max-w-[92ch] text-[14.5px] leading-[1.65] text-[#273951]">
                Un DVR privo di data certa espone a una sanzione compresa fra{" "}
                <strong className="tnum font-semibold">€1.228,50 e €2.457,02</strong>{" "}
                (Cass. 14579/2026), e il documento va aggiornato entro trenta
                giorni da ogni nuova attrezzatura, infortunio o modifica
                organizzativa (art. 29 c.3, D.Lgs. 81/2008). L&apos;abbonamento
                esiste perché l&apos;obbligo è ricorrente.
              </p>
            </Reveal>
          </div>
        </section>

        {/* ================= Chiusura ================= */}
        <section id="richiesta" className="dark-section section-y-loose scroll-mt-20 bg-[#18244e]">
          <div className="mx-auto grid w-full max-w-[1160px] items-center gap-16 px-6 sm:px-7 md:grid-cols-2">
            <div>
              <h2 className="font-heading text-[clamp(1.8rem,3vw,2.4rem)] leading-[1.12] font-light tracking-[-0.028em] text-balance text-white">
                Attiva il piano e comincia dal primo sopralluogo.
              </h2>
              <p className="mt-5 max-w-[52ch] text-[16px] leading-[1.64] font-light text-white/72">
                Carichi una vera azienda, fai un vero sopralluogo, generi un vero
                DVR. Se non sei sicuro di quale piano ti serve, scrivici: lo
                scegliamo insieme.
              </p>
              <div className="mt-8 flex flex-wrap gap-3.5">
                <Link
                  href={session ? "/billing" : "/register"}
                  className="inline-flex h-[46px] items-center rounded-[4px] bg-white px-[26px] text-[15px] font-medium text-[#061b31] transition-colors hover:bg-[#e5edf5]"
                >
                  {session ? "Vai all'abbonamento" : "Crea un account"}
                </Link>
                <a
                  href={`mailto:${SUPPORT_EMAIL}?subject=${encodeURIComponent("Richiesta preventivo — N2O DVR")}`}
                  className="inline-flex h-[46px] items-center rounded-[4px] border border-white/45 px-[26px] text-[15px] font-medium text-white transition-colors hover:border-white/70 hover:bg-white/10"
                >
                  Richiedi un preventivo
                </a>
              </div>
            </div>
            <div className="rounded-[10px] border border-white/14 bg-white/6 px-8 py-[30px]">
              <p className="text-[11.5px] font-semibold tracking-[0.1em] text-[#a5c8ff] uppercase">
                Studio di riferimento
              </p>
              <p className="mt-3.5 text-[15.5px] leading-[1.68] font-light text-white/82">
                N2O SRL usa la piattaforma sul proprio portafoglio clienti come
                founding partner. I template, i metodi di calcolo e la struttura
                dei documenti nascono dal suo lavoro quotidiano, non da un
                capitolato.
              </p>
              <p className="mt-5 border-t border-white/14 pt-[18px] text-[13.5px] leading-[1.6] text-white/55">
                Obiettivo di prodotto dichiarato: 60–70% di riduzione dei tempi
                di produzione documentale.
              </p>
            </div>
          </div>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}
