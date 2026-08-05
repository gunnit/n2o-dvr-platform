export interface IncendioServerAreaFields {
  ambiente_id: string | null;
  nome_area: string | null;
  inf: number;
  si: number;
  pi: number;
  note: string | null;
  misure_prevenzione: string | null;
  estintori_presenti: number;
  idranti_presenti: number;
  uscite_emergenza: number;
}

export interface IncendioEditableAreaFields {
  ambiente_id: string | null;
  nome: string;
  inf: number;
  si: number;
  pi: number;
  note: string;
  misure_prevenzione: string | null;
  estintori_presenti: number;
  idranti_presenti: number;
  uscite_emergenza: number;
}

export interface IncendioRequestAreaFields {
  ambiente_id: string | null;
  nome_area: string | null;
  inf: number;
  si: number;
  pi: number;
  note: string | null;
  misure_prevenzione: string | null;
  estintori_presenti: number;
  idranti_presenti: number;
  uscite_emergenza: number;
}

function editableText(value: string | null): string {
  return value ?? "";
}

function persistedText(value: string): string | null {
  return value.trim() === "" ? null : value;
}

export function incendioAreaFromServer(
  area: IncendioServerAreaFields,
  linkedAmbienteName?: string,
): IncendioEditableAreaFields {
  return {
    ambiente_id: area.ambiente_id,
    nome:
      area.ambiente_id && linkedAmbienteName
        ? linkedAmbienteName
        : editableText(area.nome_area),
    inf: area.inf,
    si: area.si,
    pi: area.pi,
    note: editableText(area.note),
    misure_prevenzione: area.misure_prevenzione,
    estintori_presenti: area.estintori_presenti,
    idranti_presenti: area.idranti_presenti,
    uscite_emergenza: area.uscite_emergenza,
  };
}

export function incendioAreaToRequest(
  area: IncendioEditableAreaFields,
): IncendioRequestAreaFields {
  return {
    ambiente_id: area.ambiente_id || null,
    nome_area: persistedText(area.nome),
    inf: area.inf,
    si: area.si,
    pi: area.pi,
    note: persistedText(area.note),
    // Preserve the distinction between null (recommendations not configured)
    // and an explicit empty string (operator selected no recommendations).
    misure_prevenzione: area.misure_prevenzione,
    estintori_presenti: area.estintori_presenti,
    idranti_presenti: area.idranti_presenti,
    uscite_emergenza: area.uscite_emergenza,
  };
}

export function incendioAreaNameIsReadOnly(
  ambienteId: string | null,
  availableAmbienteIds: string[],
): boolean {
  return Boolean(ambienteId && availableAmbienteIds.includes(ambienteId));
}

export function incendioSaveAllowed({
  allScoresComplete,
  formIsValid,
}: {
  allScoresComplete: boolean;
  formIsValid: boolean;
}): boolean {
  return allScoresComplete && formIsValid;
}
