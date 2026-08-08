interface RiskMasterEquipmentSource {
  id: string;
  ambiente_id: string;
  descrizione: string;
}

interface RiskMasterEnvironmentSource {
  id: string;
  nome: string;
}

export interface RiskMasterEquipmentRow {
  id: string;
  description: string;
  environment: string;
}

type ApiFetch = <T>(path: string) => Promise<T>;

const UNKNOWN_ENVIRONMENT = "Ambiente non disponibile";

function compareText(first: string, second: string): number {
  if (first < second) return -1;
  if (first > second) return 1;
  return 0;
}

export async function loadRiskMasterEquipment(
  aziendaId: string,
  apiFetch: ApiFetch
): Promise<RiskMasterEquipmentRow[]> {
  const [equipment, environments] = await Promise.all([
    apiFetch<RiskMasterEquipmentSource[]>(
      `/api/v1/aziende/${aziendaId}/attrezzature`
    ),
    apiFetch<RiskMasterEnvironmentSource[]>(
      `/api/v1/aziende/${aziendaId}/ambienti`
    ),
  ]);
  const environmentNames = new Map(
    environments.map((environment) => [
      environment.id,
      environment.nome.trim() || UNKNOWN_ENVIRONMENT,
    ])
  );

  return equipment
    .map((item) => ({
      id: item.id,
      description: item.descrizione.trim(),
      environment:
        environmentNames.get(item.ambiente_id) ?? UNKNOWN_ENVIRONMENT,
    }))
    .filter((item) => item.description.length > 0)
    .sort(
      (first, second) =>
        compareText(first.environment, second.environment) ||
        compareText(first.description, second.description) ||
        compareText(first.id, second.id)
    );
}
