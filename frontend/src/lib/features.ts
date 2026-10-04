/**
 * Modules switched off on purpose, kept in the codebase for later.
 *
 * Protocollo sanitario: N2O asked to hide it "per ora non necessario"
 * (segnalazione 2026-10-02). The backend twin is PROTOCOLLO_SANITARIO_ATTIVO
 * in backend/app/services/protocollo_sanitario.py, which also keeps saved
 * protocols out of DVR §4.3; flip both to bring the module back.
 */
export const PROTOCOLLO_SANITARIO_ENABLED = false;
