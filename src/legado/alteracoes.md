---
title: Alterações — Painel Legado OGU
toc: false
---

```js
import {dsvFormat} from "d3-dsv";
import {html} from "htl";
import {metricGrid} from "./components/cards.js";
import {renderAlteracoesDataTable} from "./components/alteracoes-table.js";
import {parseDate, formatNumber, formatDate} from "./lib/formatters.js";

const changesRawText = await FileAttachment("data/base_alteracoes.csv").text();
const baseDiffLatest = await FileAttachment("data/base_diff_latest.json").json();
const dsv = dsvFormat(";");

function parseChangeRow(d) {
  return {
    data: parseDate(d.data),
    natureza: d.natureza,
    tipo: d.tipo,
    operacao: d.operacao,
    uf: d.uf,
    municipio: d.municipio,
    recebedor: d.recebedor,
    modalidade: d.modalidade,
    campo: d.campo,
    anterior: d.valor_anterior,
    atual: d.valor_atual,
  };
}

const rawChanges = dsv.parse(changesRawText, parseChangeRow);

const diffFieldLabels = {
  ativo: "Ativo/Inativo",
  situacao_obra: "Situação da Obra (Casa Civil)",
  pct_fisico: "% Físico Realizado",
  vlr_repasse: "Repasse/Empréstimo",
  vlr_contrapartida: "Contrapartida Atual",
  vlr_desembolsado: "Desembolsado",
  mes_ultimo_desbloqueio: "Mês Últ. Desbloqueio",
  situacao_contrato: "Situação do Contrato",
  situacao_compl: "Sit. Contrato Complemento",
  dias_sem_bm: "Dias sem BM",
  motivo_paralisacao: "Principal Motivo de Paralisação",
  detalhamento_motivo: "Detalhamento do Motivo",
  principal_entrave: "Principal Entrave",
  plano_acao: "Plano de Ação",
  previsao_retomada: "Previsão de Retomada",
};

const natureLabels = {
  dados_origem: "Mudança de dado",
  novo_registro: "Novo registro",
  registro_removido: "Registro removido",
};

function fmt(v, campo) {
  if (v == null || v === "") return "(vazio)";
  if (v instanceof Date) return formatDate(v);
  const moneyFields = new Set(["vlr_repasse", "vlr_contrapartida", "vlr_desembolsado"]);
  if (moneyFields.has(campo) && !isNaN(v)) {
    return Number(v).toLocaleString("pt-BR", {minimumFractionDigits: 2, maximumFractionDigits: 2});
  }
  if (campo === "previsao_retomada") {
    const d = parseDate(v);
    if (d) return formatDate(d);
  }
  return String(v);
}

const alteracaoRows = rawChanges.map(d => ({
  data: d.data,
  data_fmt: fmt(d.data),
  natureza_raw: d.natureza || "dados_origem",
  natureza: natureLabels[d.natureza] || "Mudança de dado",
  operacao: d.operacao || "—",
  uf: d.uf || "—",
  municipio: d.municipio || "—",
  recebedor: d.recebedor || "—",
  modalidade: d.modalidade || "—",
  tipo: d.tipo || "—",
  campo_original: d.campo,
  campo: d.campo ? (diffFieldLabels[d.campo] || d.campo) : "—",
  anterior: fmt(d.anterior, d.campo),
  atual: fmt(d.atual, d.campo),
}));

alteracaoRows.sort((a, b) => {
  const da = a.data instanceof Date ? a.data.getTime() : 0;
  const db = b.data instanceof Date ? b.data.getTime() : 0;
  return db - da;
});

const obrasAlteradas = new Set(alteracaoRows.map(d => d.operacao));

const snapshotPrimeiroLabel = baseDiffLatest?.snapshot_primeiro
  ? formatDate(baseDiffLatest.snapshot_primeiro)
  : "primeiro registro";

const updatedAt = baseDiffLatest?.snapshot_atual ? formatDate(baseDiffLatest.snapshot_atual) : "—";
```

```js
const pageTitleBar = document.createElement("div");
pageTitleBar.className = "page-titlebar dashboard-toolbar";
pageTitleBar.innerHTML = `
  <div class="page-titlebar__heading dashboard-toolbar__title">
    <h1>Alterações desde ${snapshotPrimeiroLabel}</h1>
  </div>
  <div class="page-titlebar__meta dashboard-toolbar__side" aria-label="Data de atualização">
    <div class="dashboard-toolbar__meta">
      <span class="page-titlebar__meta-label">Atualizado em</span>
      <strong class="page-titlebar__meta-value">${updatedAt}</strong>
    </div>
    <a class="page-subnav-link" href="./" style="display:inline-flex;align-items:center;font-size:0.8125rem;font-weight:600;text-decoration:none;padding:0.35rem 0.7rem;border:1px solid var(--theme-foreground-faintest,#d0d7de);border-radius:999px;white-space:nowrap;">← Voltar ao Painel Legado</a>
  </div>
`;
display(pageTitleBar);
```

```js
const totalCamposAlterados = alteracaoRows.filter(d => d.tipo === "Alterado").length;
const totalObras = obrasAlteradas.size;
const novosRegistros = new Set(alteracaoRows.filter(d => d.tipo === "Novo").map(d => d.operacao)).size;
const registrosRemovidos = new Set(alteracaoRows.filter(d => d.tipo === "Removido").map(d => d.operacao)).size;

const alteracoesMetricGrid = metricGrid([
  { label: "Obras com alteração", value: formatNumber(totalObras), tone: "default" },
  { label: "Campos alterados", value: formatNumber(totalCamposAlterados), tone: "blue" },
  { label: "Obras novas", value: formatNumber(novosRegistros), tone: "green" },
  { label: "Obras removidas", value: formatNumber(registrosRemovidos), tone: "red" },
]);
alteracoesMetricGrid.classList.add("metrics-grid--alteracoes");
display(alteracoesMetricGrid);
```

<p class="metric-detail">Cada linha da tabela abaixo representa um campo alterado entre snapshots consecutivos da base de legado.</p>

<div class="table-shell">

```js
if (alteracaoRows.length > 0) {
  display(renderAlteracoesDataTable(alteracaoRows, invalidation));
} else {
  display(html`<p>Nenhuma alteração registrada ainda. As alterações aparecem quando há ao menos dois snapshots da base no histórico (gere novos com <code>npm run snapshot</code> após atualizar a planilha).</p>`);
}
```

</div>
