---
title: DocSuspensivas — Painel OGU
toc: false
---

```js
import {dsvFormat} from "d3-dsv";
import {html} from "htl";
import {metricGrid} from "./components/cards.js";
import {renderBaseDataTable} from "./components/base-data-table.js";
import {formatNumber} from "./lib/formatters.js";

const docRawText = await FileAttachment("data/doc_suspensivas.csv").text();
const dsv = dsvFormat(";");
const docRows = dsv.parse(docRawText, (d) => ({...d}));
```

```js
const pageTitleBar = document.createElement("div");
pageTitleBar.className = "page-titlebar dashboard-toolbar";
pageTitleBar.innerHTML = `
  <div class="page-titlebar__heading dashboard-toolbar__title">
    <h1>Documentos da Suspensiva</h1>
  </div>
`;
display(pageTitleBar);
```

<p class="metric-detail">Detalhamento por documento da condição suspensiva (abas "Suspensiva Doc Apre" e "Suspensiva Doc Não Apre" do PBI Caixa), com <strong>todos</strong> os instrumentos da fonte — inclusive os que não constam na Base Ativa do Painel. A coluna <strong>Consta na base ativa</strong> indica quais também aparecem no painel principal.</p>

```js
const totalInstrumentos = docRows.length;
const docApresentados = docRows.filter((d) => d.tipo_doc_suspensiva === "Documentos apresentados").length;
const docNaoApresentados = docRows.filter((d) => d.tipo_doc_suspensiva === "Documentos não apresentados").length;
const constamNaBase = docRows.filter((d) => d.consta_base_pc32 === "SIM").length;

display(metricGrid([
  { label: "Instrumentos", value: formatNumber(totalInstrumentos), tone: "default" },
  { label: "Documentos apresentados", value: formatNumber(docApresentados), tone: "gold" },
  { label: "Documentos não apresentados", value: formatNumber(docNaoApresentados), tone: "blue" },
  { label: "Constam na base ativa", value: formatNumber(constamNaBase), tone: "green" },
]));
```

<div class="table-shell">

```js
const docColumns = [
  "tipo_doc_suspensiva", "consta_base_pc32", "instrumento", "recebedor", "uf", "municipio_beneficiado",
  "programa", "valor_repasse", "situacao_da_analise",
  "doc_titularidade", "doc_viabilidade_terreno", "doc_sondagem", "doc_orcamento",
  "doc_projetos_implantacao", "doc_projetos_complementares", "doc_ambiental",
  "doc_vigilancia_sanitaria", "doc_bombeiros", "doc_trabalho_social", "dt_atualizacao",
];

const docHeaders = {
  tipo_doc_suspensiva: "Tipo",
  consta_base_pc32: "Consta na base ativa",
  instrumento: "Instrumento",
  recebedor: "Recebedor",
  uf: "UF",
  municipio_beneficiado: "Município",
  programa: "Programa",
  valor_repasse: "Valor Repasse",
  situacao_da_analise: "Situação da Análise",
  doc_titularidade: "Titularidade",
  doc_viabilidade_terreno: "Viabilidade do Terreno",
  doc_sondagem: "Estudos de Sondagem",
  doc_orcamento: "Orçamento",
  doc_projetos_implantacao: "Projetos de Implantação",
  doc_projetos_complementares: "Projetos Complementares",
  doc_ambiental: "Órgão Ambiental",
  doc_vigilancia_sanitaria: "Vigilância Sanitária",
  doc_bombeiros: "Bombeiros",
  doc_trabalho_social: "Trabalho Social",
  dt_atualizacao: "Atualização",
};

const moneyCol = (v) => {
  const n = Number(v);
  return v === "" || v == null || Number.isNaN(n)
    ? "—"
    : n.toLocaleString("pt-BR", {minimumFractionDigits: 2, maximumFractionDigits: 2});
};

if (docRows.length > 0) {
  display(renderBaseDataTable({
    rows: docRows,
    columns: docColumns,
    headers: docHeaders,
    formatters: { valor_repasse: moneyCol },
    invalidation,
    exportFilePrefix: "doc-suspensivas",
  }));
} else {
  display(html`<p>Nenhum registro de documento da suspensiva encontrado.</p>`);
}
```

</div>
