"use client";

import {
  Briefcase,
  Building2,
  Calendar,
  ClipboardSignature,
  Euro,
  FileCheck,
  FileText,
  Globe,
  Mail,
  MapPin,
  Phone,
  Send,
  ShieldAlert,
  Users,
  Warehouse,
  Wrench,
} from "lucide-react";

import { DescriptionEditor } from "@/components/ai/description-editor";
import {
  EmptyState,
  Eyebrow,
  InfoRow,
  Panel,
  PanelHeader,
  StatTile,
  StatusPill,
} from "@/components/aziende/tabs/_shared";
import { formatScadenza, SCADENZA_TONE_CLASS } from "@/lib/ui/scadenza";
import { surveyStatusMeta } from "@/lib/ui/status-map";
import type {
  Ambiente,
  Attrezzatura,
  Azienda,
  DocumentoGenerato,
  Persona,
  ValutazioneRischio,
} from "@/types";

interface PanoramicaTabProps {
  azienda: Azienda;
  persone: Persona[];
  ambienti: Ambiente[];
  attrezzature: Attrezzatura[];
  rischi: ValutazioneRischio[];
  documenti: DocumentoGenerato[];
  onDescriptionChange: (text: string) => Promise<void>;
}

const dateFmt = new Intl.DateTimeFormat("it-IT", {
  day: "2-digit",
  month: "long",
  year: "numeric",
});

const dateShort = new Intl.DateTimeFormat("it-IT", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
});

const eurFmt = new Intl.NumberFormat("it-IT", {
  style: "currency",
  currency: "EUR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function formatItalianDate(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return dateFmt.format(d);
}

function formatItalianDateShort(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return dateShort.format(d);
}

function sameSede(a: Azienda): boolean {
  return (
    !!a.sede_legale_via &&
    a.sede_legale_via === a.sede_operativa_via &&
    a.sede_legale_citta === a.sede_operativa_citta &&
    a.cap_legale === a.cap_operativa &&
    a.provincia_legale === a.provincia_operativa
  );
}

function fullAddress(
  via: string | null,
  cap: string | null,
  citta: string | null,
  provincia: string | null,
): { street: string; locality: string } {
  const street = via || "-";
  const localityParts = [
    cap,
    citta,
    provincia ? `(${provincia})` : null,
  ].filter(Boolean);
  return { street, locality: localityParts.join(" ") || "-" };
}

export default function PanoramicaTab({
  azienda,
  persone,
  ambienti,
  attrezzature,
  rischi,
  documenti,
  onDescriptionChange,
}: PanoramicaTabProps) {
  const personeCount = persone.length;
  const ambientiCount = ambienti.length;
  const attrezzatureCount = attrezzature.length;
  const rischiApplicabili = rischi.filter((r) => r.applicabile);
  const rischiCount = rischiApplicabili.length;
  const rischiCritici = rischiApplicabili.filter(
    (r) =>
      r.livello_rischio === "GRAVE" || r.livello_rischio === "GRAVISSIMO",
  ).length;
  const criticiPercent =
    rischiCount > 0 ? Math.round((rischiCritici / rischiCount) * 100) : 0;
  const docCount = documenti.length;

  const statusMeta = surveyStatusMeta(azienda.survey_status);
  const scadenzaInfo = formatScadenza(azienda.data_scadenza_dvr);
  const firmaDate = formatItalianDate(azienda.firma_signed_at ?? null);
  const visuraDate = formatItalianDateShort(azienda.visura_uploaded_at ?? null);

  const hasContatti =
    !!azienda.pec ||
    !!azienda.email ||
    !!azienda.telefono ||
    !!azienda.sito_web;

  const sedeLegale = fullAddress(
    azienda.sede_legale_via,
    azienda.cap_legale,
    azienda.sede_legale_citta,
    azienda.provincia_legale,
  );
  const sedeOperativa = fullAddress(
    azienda.sede_operativa_via,
    azienda.cap_operativa,
    azienda.sede_operativa_citta,
    azienda.provincia_operativa,
  );
  const sediCoincidono = sameSede(azienda);

  const sitoHref = (() => {
    if (!azienda.sito_web) return null;
    return /^https?:\/\//i.test(azienda.sito_web)
      ? azienda.sito_web
      : `https://${azienda.sito_web}`;
  })();

  return (
    <div className="grid gap-5 md:grid-cols-2">
      {/* Snapshot KPI strip */}
      <div className="md:col-span-2 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <StatTile label="Persone" value={personeCount} tone="navy" />
        <StatTile label="Ambienti" value={ambientiCount} tone="navy" />
        <StatTile label="Attrezzature" value={attrezzatureCount} tone="navy" />
        <StatTile
          label="Rischi applicabili"
          value={rischiCount}
          sublabel={
            rischi.length > 0 ? `su ${rischi.length} valutati` : undefined
          }
        />
        <StatTile
          label="Documenti generati"
          value={docCount}
          tone={docCount > 0 ? "ok" : "default"}
        />
        <StatTile
          label="Rischi critici"
          value={`${criticiPercent}%`}
          sublabel={
            rischiCritici > 0
              ? `${rischiCritici} GRAVE/GRAVISSIMO`
              : "Nessun rischio elevato"
          }
          tone={rischiCritici > 0 ? "warn" : "ok"}
        />
      </div>

      {/* Stato del DVR */}
      <Panel accent="navy">
        <PanelHeader
          icon={ClipboardSignature}
          title="Stato del DVR"
          accent="navy"
          action={<StatusPill className={statusMeta.badge}>{statusMeta.label}</StatusPill>}
        />
        <div className="grid gap-5 p-6 sm:grid-cols-2">
          <div className="flex flex-col gap-1">
            <Eyebrow>Firma</Eyebrow>
            {firmaDate ? (
              <div className="flex items-start gap-2">
                <FileCheck
                  className="mt-0.5 h-4 w-4 shrink-0 text-[#108c3d]"
                  strokeWidth={1.75}
                />
                <span className="text-[14px] leading-[1.4] text-[#061b31]">
                  Firmato da{" "}
                  <span className="font-medium">
                    {azienda.firma_signed_by_name || "operatore"}
                  </span>
                  <span className="block text-[12px] text-[#64748d] tnum">
                    {firmaDate}
                  </span>
                </span>
              </div>
            ) : (
              <span className="text-[14px] leading-[1.4] text-[#64748d]">
                Non firmato
              </span>
            )}
          </div>

          <div className="flex flex-col gap-1">
            <Eyebrow>Visura camerale</Eyebrow>
            {visuraDate ? (
              <span className="text-[14px] leading-[1.4] text-[#061b31]">
                Caricata
                <span className="block text-[12px] text-[#64748d] tnum">
                  il {visuraDate}
                </span>
              </span>
            ) : (
              <span className="text-[14px] leading-[1.4] text-[#64748d]">
                Non caricata
              </span>
            )}
          </div>

          <div className="flex flex-col gap-1 sm:col-span-2">
            <Eyebrow>Scadenza DVR</Eyebrow>
            {scadenzaInfo ? (
              <div className="flex items-baseline gap-2">
                <Calendar
                  className={
                    "h-4 w-4 shrink-0 " + SCADENZA_TONE_CLASS[scadenzaInfo.tone]
                  }
                  strokeWidth={1.75}
                />
                <span
                  className={
                    "tnum text-[14px] font-medium leading-[1.4] " +
                    SCADENZA_TONE_CLASS[scadenzaInfo.tone]
                  }
                >
                  {scadenzaInfo.label}
                </span>
                <span className="text-[12px] text-[#64748d] tnum">
                  {scadenzaInfo.diffDays < 0
                    ? `${Math.abs(scadenzaInfo.diffDays)} giorni fa`
                    : scadenzaInfo.diffDays === 0
                      ? "oggi"
                      : `tra ${scadenzaInfo.diffDays} giorni`}
                </span>
              </div>
            ) : (
              <span className="text-[14px] leading-[1.4] text-[#64748d]">
                Nessuna scadenza impostata
              </span>
            )}
          </div>
        </div>
      </Panel>

      {/* Dati Azienda */}
      <Panel accent="violet">
        <PanelHeader icon={Building2} title="Dati Azienda" accent="violet" />
        <div className="grid gap-5 p-6 sm:grid-cols-2">
          <InfoRow label="Ragione Sociale" value={azienda.ragione_sociale} />
          <InfoRow label="Forma giuridica" value={azienda.forma_giuridica} />
          <InfoRow label="Partita IVA" value={azienda.partita_iva} tnum />
          <InfoRow
            label="Codice Fiscale"
            value={azienda.codice_fiscale}
            tnum
          />
          <InfoRow label="Codice ATECO" value={azienda.codice_ateco} tnum />
          <InfoRow label="REA" value={azienda.rea} tnum />
          <InfoRow
            label="Data costituzione"
            value={formatItalianDate(azienda.data_costituzione)}
            tnum
          />
          <InfoRow
            label="Capitale sociale"
            value={
              azienda.capitale_sociale != null
                ? eurFmt.format(azienda.capitale_sociale)
                : null
            }
            tnum
          />
          <InfoRow
            label="Dipendenti dichiarati"
            value={
              azienda.numero_dipendenti_dichiarati != null
                ? String(azienda.numero_dipendenti_dichiarati)
                : null
            }
            tnum
          />
          <InfoRow label="Attivita'" value={azienda.attivita} />
          <InfoRow label="Orario di lavoro" value={azienda.orario_lavoro} />
          <InfoRow
            label="Metratura totale"
            value={
              azienda.metratura_totale != null
                ? `${azienda.metratura_totale} mq`
                : null
            }
            tnum
          />
          <InfoRow
            label="Zona sismica"
            value={
              azienda.zona_sismica != null
                ? `Zona ${azienda.zona_sismica}`
                : null
            }
          />
        </div>
      </Panel>

      {/* Contatti */}
      <Panel accent="sky">
        <PanelHeader icon={Send} title="Contatti" accent="sky" />
        {hasContatti ? (
          <div className="grid gap-4 p-6 sm:grid-cols-2">
            {azienda.pec && (
              <a
                href={`mailto:${azienda.pec}`}
                className="group flex items-start gap-2.5 rounded-md border border-[#e5edf5] bg-white px-3 py-2.5 transition hover:border-[#0ea5e9]/50 hover:bg-[#f6f9fc]"
              >
                <Send
                  className="mt-0.5 h-4 w-4 shrink-0 text-[#0ea5e9]"
                  strokeWidth={1.75}
                />
                <div className="min-w-0">
                  <span className="type-eyebrow">PEC</span>
                  <p className="truncate text-[14px] text-[#061b31] group-hover:text-[#003d74]">
                    {azienda.pec}
                  </p>
                </div>
              </a>
            )}
            {azienda.email && (
              <a
                href={`mailto:${azienda.email}`}
                className="group flex items-start gap-2.5 rounded-md border border-[#e5edf5] bg-white px-3 py-2.5 transition hover:border-[#0ea5e9]/50 hover:bg-[#f6f9fc]"
              >
                <Mail
                  className="mt-0.5 h-4 w-4 shrink-0 text-[#0ea5e9]"
                  strokeWidth={1.75}
                />
                <div className="min-w-0">
                  <span className="type-eyebrow">Email</span>
                  <p className="truncate text-[14px] text-[#061b31] group-hover:text-[#003d74]">
                    {azienda.email}
                  </p>
                </div>
              </a>
            )}
            {azienda.telefono && (
              <a
                href={`tel:${azienda.telefono.replace(/\s+/g, "")}`}
                className="group flex items-start gap-2.5 rounded-md border border-[#e5edf5] bg-white px-3 py-2.5 transition hover:border-[#0ea5e9]/50 hover:bg-[#f6f9fc]"
              >
                <Phone
                  className="mt-0.5 h-4 w-4 shrink-0 text-[#0ea5e9]"
                  strokeWidth={1.75}
                />
                <div className="min-w-0">
                  <span className="type-eyebrow">Telefono</span>
                  <p className="truncate tnum text-[14px] text-[#061b31] group-hover:text-[#003d74]">
                    {azienda.telefono}
                  </p>
                </div>
              </a>
            )}
            {azienda.sito_web && sitoHref && (
              <a
                href={sitoHref}
                target="_blank"
                rel="noopener noreferrer"
                className="group flex items-start gap-2.5 rounded-md border border-[#e5edf5] bg-white px-3 py-2.5 transition hover:border-[#0ea5e9]/50 hover:bg-[#f6f9fc]"
              >
                <Globe
                  className="mt-0.5 h-4 w-4 shrink-0 text-[#0ea5e9]"
                  strokeWidth={1.75}
                />
                <div className="min-w-0">
                  <span className="type-eyebrow">Sito web</span>
                  <p className="truncate text-[14px] text-[#061b31] group-hover:text-[#003d74]">
                    {azienda.sito_web}
                  </p>
                </div>
              </a>
            )}
          </div>
        ) : (
          <EmptyState
            icon={Mail}
            title="Nessun contatto"
            body="Aggiungi PEC, email, telefono o sito web modificando l'anagrafica dell'azienda."
          />
        )}
      </Panel>

      {/* Sedi */}
      <Panel accent="emerald">
        <PanelHeader icon={MapPin} title="Sedi" accent="emerald" />
        <div className="space-y-5 p-6">
          <div>
            <Eyebrow>Sede legale</Eyebrow>
            <p className="mt-1 text-[14px] leading-[1.4] text-[#061b31]">
              {sedeLegale.street}
            </p>
            <p className="text-[13px] text-[#64748d] tnum">
              {sedeLegale.locality}
            </p>
          </div>
          <div className="h-px bg-[#e5edf5]" />
          <div>
            <Eyebrow>Sede operativa</Eyebrow>
            {sediCoincidono ? (
              <p className="mt-1 text-[13px] italic text-[#64748d]">
                Coincide con sede legale
              </p>
            ) : (
              <>
                <p className="mt-1 text-[14px] leading-[1.4] text-[#061b31]">
                  {sedeOperativa.street}
                </p>
                <p className="text-[13px] text-[#64748d] tnum">
                  {sedeOperativa.locality}
                </p>
              </>
            )}
          </div>
        </div>
      </Panel>

      {/* Composizione operativa — quick at-a-glance counts of ambienti/attrezzature
          alongside the contact card to balance the grid visually. */}
      <Panel accent="amber">
        <PanelHeader icon={Briefcase} title="Composizione operativa" accent="amber" />
        <div className="grid gap-4 p-6 sm:grid-cols-3">
          <div className="flex items-start gap-2.5">
            <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-[rgba(0,61,116,0.08)]">
              <Users className="h-4 w-4 text-[#003d74]" strokeWidth={1.75} />
            </span>
            <div>
              <span className="type-eyebrow">Persone</span>
              <p className="tnum text-[16px] font-medium text-[#061b31]">
                {personeCount}
              </p>
              <p className="text-[12px] text-[#64748d]">
                {azienda.numero_dipendenti_dichiarati != null
                  ? `${azienda.numero_dipendenti_dichiarati} dichiarati`
                  : "in organico"}
              </p>
            </div>
          </div>
          <div className="flex items-start gap-2.5">
            <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-[rgba(5,150,105,0.1)]">
              <Warehouse
                className="h-4 w-4 text-[#059669]"
                strokeWidth={1.75}
              />
            </span>
            <div>
              <span className="type-eyebrow">Ambienti</span>
              <p className="tnum text-[16px] font-medium text-[#061b31]">
                {ambientiCount}
              </p>
              <p className="text-[12px] text-[#64748d]">
                {azienda.metratura_totale != null
                  ? `${azienda.metratura_totale} mq totali`
                  : "spazi censiti"}
              </p>
            </div>
          </div>
          <div className="flex items-start gap-2.5">
            <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-[rgba(217,119,6,0.1)]">
              <Wrench className="h-4 w-4 text-[#d97706]" strokeWidth={1.75} />
            </span>
            <div>
              <span className="type-eyebrow">Attrezzature</span>
              <p className="tnum text-[16px] font-medium text-[#061b31]">
                {attrezzatureCount}
              </p>
              <p className="text-[12px] text-[#64748d]">
                in dotazione
              </p>
            </div>
          </div>
          <div className="flex items-start gap-2.5 sm:col-span-3">
            <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-[rgba(234,34,97,0.08)]">
              <ShieldAlert
                className="h-4 w-4 text-[#b51648]"
                strokeWidth={1.75}
              />
            </span>
            <div className="flex-1">
              <span className="type-eyebrow">Rischi valutati</span>
              <p className="tnum text-[16px] font-medium text-[#061b31]">
                {rischiCount}
                {rischi.length > rischiCount && (
                  <span className="ml-2 text-[13px] font-normal text-[#64748d]">
                    su {rischi.length} totali
                  </span>
                )}
              </p>
              <p className="text-[12px] text-[#64748d]">
                {rischiCritici > 0
                  ? `${rischiCritici} richiedono attenzione (GRAVE / GRAVISSIMO)`
                  : "Nessun rischio critico al momento"}
              </p>
            </div>
          </div>
          <div className="flex items-start gap-2.5 sm:col-span-3">
            <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-[rgba(124,58,237,0.1)]">
              <FileText
                className="h-4 w-4 text-[#7c3aed]"
                strokeWidth={1.75}
              />
            </span>
            <div className="flex-1">
              <span className="type-eyebrow">Documenti generati</span>
              <p className="tnum text-[16px] font-medium text-[#061b31]">
                {docCount}
              </p>
              <p className="text-[12px] text-[#64748d]">
                {docCount > 0
                  ? "Disponibili nella sezione Documenti"
                  : "Nessun documento ancora generato"}
              </p>
            </div>
          </div>
          {azienda.capitale_sociale != null && (
            <div className="flex items-start gap-2.5 sm:col-span-3">
              <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-[rgba(0,61,116,0.08)]">
                <Euro className="h-4 w-4 text-[#003d74]" strokeWidth={1.75} />
              </span>
              <div>
                <span className="type-eyebrow">Capitale sociale</span>
                <p className="tnum text-[16px] font-medium text-[#061b31]">
                  {eurFmt.format(azienda.capitale_sociale)}
                </p>
              </div>
            </div>
          )}
        </div>
      </Panel>

      {/* Descrizione */}
      <div id="descrizione-attivita" className="scroll-mt-24 md:col-span-2">
        <Panel accent="violet">
          <PanelHeader icon={FileText} title="Descrizione" accent="violet" />
          <div className="space-y-6 p-6">
            <DescriptionEditor
              aziendaId={azienda.id}
              value={azienda.descrizione_attivita ?? ""}
              initialProvenance={
                azienda.descrizione_attivita ? "edited" : "none"
              }
              visuraUploadedAt={azienda.visura_uploaded_at ?? null}
              onChange={onDescriptionChange}
            />
            {azienda.contesto_territoriale && (
              <div>
                <Eyebrow>Contesto territoriale</Eyebrow>
                <p className="mt-2 text-[14px] leading-relaxed text-[#273951]">
                  {azienda.contesto_territoriale}
                </p>
              </div>
            )}
          </div>
        </Panel>
      </div>
    </div>
  );
}
