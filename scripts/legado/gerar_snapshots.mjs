// Gera snapshots datados da base de legado e os artefatos de "Alterações":
//   - data/historico/base_legado_<data>.csv   (snapshot completo)
//   - src/data/base_alteracoes.csv             (mudanças acumuladas entre snapshots)
//   - src/data/base_diff_latest.json           (resumo do snapshot atual vs anterior)
//
// A "data" do snapshot vem da coluna dt_atualizacao da planilha (fallback: hoje).
// Reexecuções no mesmo dia sobrescrevem o snapshot do dia (idempotente).

import {mkdirSync, readdirSync, readFileSync, writeFileSync} from "node:fs";
import {fileURLToPath} from "node:url";
import {dsvFormat} from "d3-dsv";
import {extractLegadoRows, FIELDS, KEY_FIELD} from "./legado-extract.mjs";

const dsv = dsvFormat(";");
const HISTORICO_DIR = fileURLToPath(new URL("../../data/legado/historico/", import.meta.url));
const DATA_DIR = fileURLToPath(new URL("../../src/legado/data/", import.meta.url));

// Campos cuja mudança é registrada na página de Alterações.
const TRACKED_FIELDS = [
  "ativo",
  "situacao_obra",
  "pct_fisico",
  "vlr_repasse",
  "vlr_contrapartida",
  "vlr_desembolsado",
  "mes_ultimo_desbloqueio",
  "situacao_contrato",
  "situacao_compl",
  "dias_sem_bm",
  "motivo_paralisacao",
  "detalhamento_motivo",
  "principal_entrave",
  "plano_acao",
  "previsao_retomada",
];

const ALTERACOES_FIELDS = [
  "data", "tipo", "natureza", "operacao", "uf", "municipio", "recebedor", "modalidade",
  "campo", "valor_anterior", "valor_atual",
];

function todayISO() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function snapshotDateFromRows(rows) {
  const datas = rows.map((r) => r.dt_atualizacao).filter(Boolean).sort();
  return datas.length ? datas[datas.length - 1] : todayISO();
}

function mapByKey(rows) {
  const m = new Map();
  for (const r of rows) {
    const key = (r[KEY_FIELD] || "").trim();
    if (key) m.set(key, r);
  }
  return m;
}

function norm(v) {
  return v == null ? "" : String(v).trim();
}

function main() {
  mkdirSync(HISTORICO_DIR, {recursive: true});
  mkdirSync(DATA_DIR, {recursive: true});

  const rows = extractLegadoRows();
  const snapshotDate = snapshotDateFromRows(rows);

  // 1) grava/atualiza o snapshot do dia
  writeFileSync(`${HISTORICO_DIR}base_legado_${snapshotDate}.csv`, dsv.format(rows, FIELDS));

  // 2) carrega todos os snapshots, ordenados por data
  const snapshots = readdirSync(HISTORICO_DIR)
    .map((name) => {
      const m = /^base_legado_(\d{4}-\d{2}-\d{2})\.csv$/.exec(name);
      return m ? {date: m[1], name} : null;
    })
    .filter(Boolean)
    .sort((a, b) => a.date.localeCompare(b.date));

  const parsed = snapshots.map((s) => ({
    date: s.date,
    rows: dsv.parse(readFileSync(`${HISTORICO_DIR}${s.name}`, "utf8")),
  }));

  // 3) acumula alterações entre snapshots consecutivos
  const alteracoes = [];
  let ultimoResumo = {entered: 0, exited: 0, changed_records: 0};

  for (let i = 1; i < parsed.length; i++) {
    const prev = mapByKey(parsed[i - 1].rows);
    const cur = mapByKey(parsed[i].rows);
    const data = parsed[i].date;
    const resumo = {entered: 0, exited: 0, changed_records: 0};

    for (const [key, row] of cur) {
      const ident = {
        operacao: key,
        uf: norm(row.uf),
        municipio: norm(row.municipio),
        recebedor: norm(row.recebedor),
        modalidade: norm(row.modalidade),
      };

      if (!prev.has(key)) {
        resumo.entered += 1;
        alteracoes.push({data, tipo: "Novo", natureza: "novo_registro", ...ident, campo: "", valor_anterior: "", valor_atual: ""});
        continue;
      }

      const before = prev.get(key);
      let changed = false;
      for (const campo of TRACKED_FIELDS) {
        const a = norm(before[campo]);
        const b = norm(row[campo]);
        if (a !== b) {
          changed = true;
          alteracoes.push({data, tipo: "Alterado", natureza: "dados_origem", ...ident, campo, valor_anterior: a, valor_atual: b});
        }
      }
      if (changed) resumo.changed_records += 1;
    }

    for (const [key, row] of prev) {
      if (!cur.has(key)) {
        resumo.exited += 1;
        alteracoes.push({
          data, tipo: "Removido", natureza: "registro_removido",
          operacao: key, uf: norm(row.uf), municipio: norm(row.municipio),
          recebedor: norm(row.recebedor), modalidade: norm(row.modalidade),
          campo: "", valor_anterior: "", valor_atual: "",
        });
      }
    }

    ultimoResumo = resumo;
  }

  // 4) grava base_alteracoes.csv
  writeFileSync(`${DATA_DIR}base_alteracoes.csv`, dsv.format(alteracoes, ALTERACOES_FIELDS));

  // 5) grava base_diff_latest.json
  const atual = parsed[parsed.length - 1] ?? null;
  const anterior = parsed.length >= 2 ? parsed[parsed.length - 2] : null;
  const primeiro = parsed[0] ?? null;
  const diff = {
    snapshot_atual: atual?.date ?? snapshotDate,
    snapshot_anterior: anterior?.date ?? null,
    snapshot_primeiro: primeiro?.date ?? snapshotDate,
    total_atual: atual?.rows.length ?? rows.length,
    total_anterior: anterior?.rows.length ?? null,
    delta_total: anterior ? (atual.rows.length - anterior.rows.length) : 0,
    resumo: ultimoResumo,
  };
  writeFileSync(`${DATA_DIR}base_diff_latest.json`, JSON.stringify(diff, null, 2) + "\n");

  // 6) atualiza a data de atualização das fontes (rodapé)
  const freshnessPath = `${DATA_DIR}source_freshness.json`;
  try {
    const freshness = JSON.parse(readFileSync(freshnessPath, "utf8"));
    if (Array.isArray(freshness.sources) && freshness.sources.length) {
      freshness.sources = freshness.sources.map((s) => ({...s, updated_at: snapshotDate}));
      writeFileSync(freshnessPath, JSON.stringify(freshness, null, 2) + "\n");
    }
  } catch {
    // mantém o arquivo existente se não puder atualizar
  }

  console.log(
    `Snapshot ${snapshotDate}: ${rows.length} registros · ` +
    `${snapshots.length} snapshot(s) no histórico · ${alteracoes.length} alteração(ões) acumulada(s).`
  );
}

main();
