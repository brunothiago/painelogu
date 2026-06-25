import {readFileSync} from "node:fs";
import {fileURLToPath} from "node:url";
import * as XLSX from "xlsx";

// Caminho da planilha-fonte (relativo a este módulo). A 2ª aba "Legado Migradas"
// é a entrada do Painel Legado OGU.
export const XLSX_PATH = fileURLToPath(new URL("../../data/legado/Relatorios_Analiticos_PBI.xlsx", import.meta.url));
export const SHEET_NAME = "Legado Migradas";

// Mapeamento das colunas do XLSX para os campos (slugs) consumidos pelo painel.
const COLUMN_MAP = {
  "ATIVO_INATIVO": "ativo",
  "TIPO DE OPERAÇÃO": "tipo_operacao",
  "PROPOSTA": "proposta",
  "OPERAÇÃO": "operacao",
  "DV": "dv",
  "INSTRUMENTO": "instrumento",
  "REPASSADOR": "repassador",
  "UF": "uf",
  "RECEBEDOR": "recebedor",
  "ENTE DE VINCULAÇÃO": "ente",
  "MUNICÍPIO BENEFICIADO": "municipio",
  "OBJETO": "objeto",
  "Modalidade": "modalidade",
  "Modalidade - classificação Casa Civil": "modalidade_cc",
  "SITUAÇÃO DA OBRA CASA CIVIL": "situacao_obra",
  "% FÍSICO REALIZADO": "pct_fisico",
  "DATA DA ASSINATURA": "dt_assinatura",
  "VALOR DE REPASSE/EMPRÉSTIMO": "vlr_repasse",
  "VALOR DE CONTRAPARTIDA ATUAL": "vlr_contrapartida",
  "VALOR DESBLOQUEADO/DESEMBOLSADO": "vlr_desembolsado",
  "MES ÚLTIMO DESBLOQUEIO/DESEMBOLSO": "mes_ultimo_desbloqueio",
  "SITUAÇÃO DO CONTRATO": "situacao_contrato",
  "Situação Contrato Complemento": "situacao_compl",
  "Dias sem Apresentação de BM": "dias_sem_bm",
  "PRINCIPAL MOTIVO DE PARALISAÇÃO": "motivo_paralisacao",
  "DETALHAMENTO DO MOTIVO": "detalhamento_motivo",
  "DESCRIÇÃO DO MOTIVO": "descricao_motivo",
  "PRINCIPAL ENTRAVE": "principal_entrave",
  "PLANO DE AÇÃO": "plano_acao",
  "PREVISÃO DE RETOMADA": "previsao_retomada",
  "dt_atualizacao": "dt_atualizacao",
};

export const FIELDS = Object.values(COLUMN_MAP);

// Campo que identifica unicamente cada registro (567/567 preenchidos e únicos).
export const KEY_FIELD = "operacao";

const DATE_FIELDS = new Set(["dt_assinatura", "dt_atualizacao", "previsao_retomada"]);

function pad2(n) {
  return String(n).padStart(2, "0");
}

// Normaliza datas para YYYY-MM-DD (esperado por parseDate em lib/formatters.js).
export function normalizeDate(value) {
  if (value == null || value === "") return "";
  if (value instanceof Date && !Number.isNaN(value.getTime())) {
    return `${value.getUTCFullYear()}-${pad2(value.getUTCMonth() + 1)}-${pad2(value.getUTCDate())}`;
  }
  const text = String(value).trim();
  const br = /^(\d{1,2})\/(\d{1,2})\/(\d{2,4})$/.exec(text);
  if (br) {
    const year = br[3].length === 2 ? `20${br[3]}` : br[3];
    return `${year}-${pad2(br[2])}-${pad2(br[1])}`;
  }
  const iso = /^(\d{4})-(\d{1,2})-(\d{1,2})/.exec(text);
  if (iso) return `${iso[1]}-${pad2(iso[2])}-${pad2(iso[3])}`;
  return text;
}

function clean(value) {
  if (value == null) return "";
  return String(value).replace(/\s+/g, " ").trim();
}

export function extractLegadoRows() {
  const workbook = XLSX.read(readFileSync(XLSX_PATH), {type: "buffer", cellDates: true});
  const worksheet = workbook.Sheets[SHEET_NAME];
  if (!worksheet) {
    throw new Error(`Aba "${SHEET_NAME}" não encontrada em ${XLSX_PATH}`);
  }

  const rawRows = XLSX.utils.sheet_to_json(worksheet, {defval: "", raw: true});

  return rawRows.map((raw) => {
    const out = {};
    for (const [source, field] of Object.entries(COLUMN_MAP)) {
      const value = raw[source];
      if (DATE_FIELDS.has(field) || value instanceof Date) {
        out[field] = normalizeDate(value);
      } else {
        out[field] = clean(value);
      }
    }
    return out;
  });
}
