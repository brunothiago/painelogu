---
title: Painel DMP-OGU-Novo PAC
toc: false
---

```js
import * as Plot from "@observablehq/plot";
import {html} from "htl";
import {dsvFormat} from "d3-dsv";
import {renderBaseDataTable} from "./components/base-data-table.js";
import {metricGrid} from "./components/cards.js";
import {cascadeChart, matchesCascadeSelection} from "./components/cascade-chart.js";
import {parseDate, addCalendarDays, formatNumber, formatCurrencyCompact, formatPercent, formatDate} from "./lib/formatters.js";
import {PALETTE, SITUACAO_CORES, SUSPENSIVA_CORES, SITUACAO_ORDER, SUSPENSIVA_ORDER, LICITACAO_CORES, INICIO_OBRA_CORES, REGIAO_ORDER, getRegiaoColor, getUfColor, getMunicipioColor} from "./lib/theme.js";
import {hexToRgba} from "./lib/dom-helpers.js";

const rawText = await FileAttachment("data/base_pc_32.csv").text();
const previousRawText = await FileAttachment("data/base_pc_32_previous.csv").text();
const baseDiffLatest = await FileAttachment("data/base_diff_latest.json").json();
const fluxoPc32ImageUrl = await FileAttachment("assets/fluxo-pc32.png").url();
const dsv = dsvFormat(";");

function pickField(row, ...names) {
  for (const name of names) {
    if (row[name] != null && row[name] !== "") return row[name];
  }
  return "";
}

// Detalhamento por documento da suspensiva (abas PBI Caixa). Rótulos legíveis e
// regra de "documento pendente" por origem (a validar com a área):
//   - Documentos apresentados  -> pendente quando o valor é "Não Apresentado"
//   - Documentos não apresentados -> pendente quando o valor é "NÃO"
const DOC_SUSPENSIVA_LABELS = {
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
};

function docSuspensivaPendente(tipo, valor) {
  if (!valor) return false;
  if (tipo === "Documentos apresentados") return valor === "Não Apresentado";
  if (tipo === "Documentos não apresentados") return valor === "NÃO";
  return false;
}

function docsSuspensivaPendentes(d) {
  const tipo = pickField(d, "tipo_doc_suspensiva");
  if (!tipo) return [];
  return Object.keys(DOC_SUSPENSIVA_LABELS)
    .filter((k) => docSuspensivaPendente(tipo, pickField(d, k)))
    .map((k) => DOC_SUSPENSIVA_LABELS[k]);
}

const LICITACAO_PC72_CORTE = Date.UTC(2025, 9, 21);

function parseBaseRow(d) {
  const dt_assinatura = parseDate(pickField(d, "dte_assinatura_contrato_saci", "dte_assinatura_contrato_tci", "dte_assinatura_contrato"));
  const dt_lae = parseDate(pickField(d, "dte_primeira_data_lae_tdb", "dte_primeira_data_lae"));
  const dt_lae_mais_60 =
    parseDate(pickField(d, "prazo_lae_mais_60_calc")) ?? (dt_lae ? addCalendarDays(dt_lae, 120) : null);
  const dt_lae_mais_60_mais_120 =
    parseDate(pickField(d, "prazo_lae_mais_60_mais_120_calc")) ??
    (dt_lae_mais_60 ? addCalendarDays(addCalendarDays(dt_lae_mais_60, 120), 60) : null);

  const row = {
  cod_tci: pickField(d, "cod_tci_saci", "cod_tci_tci", "cod_saci", "cod_tci"),
  num_convenio: pickField(d, "num_convenio_saci", "num_convenio_tci", "num_convenio"),
  uf: pickField(d, "txt_uf_saci", "txt_uf_tci", "txt_uf"),
  regiao: pickField(d, "txt_regiao_saci", "txt_regiao_tci", "txt_regiao"),
  cod_ibge: pickField(d, "cod_ibge_7dig_saci", "cod_ibge_7dig_tci", "cod_ibge_7dig"),
  municipio: pickField(d, "txt_municipio_saci", "txt_municipio_tci", "txt_municipio"),
  proponente: pickField(d, "txt_tomador_saci", "txt_tomador_tci", "txt_tomador"),
  objeto: pickField(d, "dsc_objeto_instrumento_saci", "dsc_objeto_instrumento_tci", "dsc_objeto_instrumento"),
  secretaria: pickField(d, "txt_sigla_secretaria_saci", "txt_sigla_secretaria_tci", "txt_sigla_secretaria"),
  fase: pickField(d, "dsc_fase_pac_saci", "dsc_fase_pac_tci", "dsc_fase_pac"),
  modalidade: pickField(d, "txt_modalidade_saci", "txt_modalidade_tci", "txt_modalidade"),
  situacao_contrato_tci: pickField(d, "dsc_situacao_contrato_mcid_saci", "dsc_situacao_contrato_mcid_tci", "dsc_situacao_contrato_mcid"),
  situacao: pickField(d, "dsc_situacao_contrato_mcid_saci", "dsc_situacao_contrato_mcid_tci", "dsc_situacao_contrato_mcid"),
  dt_assinatura,
  pos_72: dt_assinatura instanceof Date && !isNaN(dt_assinatura)
    ? (dt_assinatura.getTime() >= LICITACAO_PC72_CORTE ? "Nova PC 32" : "Antiga PC 32")
    : null,
  situacao_suspensiva: pickField(d, "situacao_da_analise_suspensiva_pbi", "situacao_da_analise_suspensiva"),
  situacao_suspensiva_pbi: pickField(d, "situacao_da_analise_suspensiva_pbi", "situacao_da_analise_suspensiva"),
  perspectiva_de_retirada_da_suspensiva: pickField(d, "perspectiva_de_retirada_da_suspensiva", "pespectiva_de_retirada_da_suspensiva"),
  motivo_suspensiva_retirada_dmp: pickField(d, "motivo_suspensiva_retirada_dmp", "motivo_suspensiva_retirada_cgpac"),
  dt_vencimento_suspensiva: parseDate(pickField(d, "vencimento_da_suspensiva_pbi", "vencimento_da_suspensiva")),
  mes_ano_vencimento_suspensiva: parseDate(pickField(d, "vencimento_da_suspensiva_pbi", "vencimento_da_suspensiva")),
  dt_retirada_suspensiva: parseDate(pickField(d, "dte_retirada_suspensiva_tgov", "dte_retirada_suspensiva")),
  dt_lae,
  dt_lae_mais_60,
  dt_lae_mais_60_mais_120,
  dt_pub_licitacao: parseDate(pickField(d, "dte_publicacao_licitacao_tgov", "dte_publicacao_licitacao")),
  dt_homolog_licitacao: parseDate(pickField(d, "dte_homologacao_licitacao_tgov", "dte_homologacao_licitacao")),
  dt_vrpl: parseDate(pickField(d, "dte_vrpl_tdb", "dte_vrpl")),
  dt_aio: parseDate(pickField(d, "dte_aio_tdb", "dte_aio")),
  dt_inicio_obra: parseDate(pickField(d, "dte_inicio_obra_mcid_saci", "dte_inicio_obra_mcid_tci", "dte_inicio_obra_mcid")),
  vlr_repasse: +pickField(d, "vlr_repasse_saci", "vlr_repasse_tci", "vlr_repasse") || 0,
  status_suspensiva: pickField(d, "status_suspensiva_calc", "status_suspensiva"),
  flag_publicacao_licitacao: pickField(d, "flag_publicacao_licitacao_calc", "flag_publicacao_licitacao"),
  flag_homologacao_licitacao: pickField(d, "flag_homologacao_licitacao_calc", "flag_homologacao_licitacao"),
  ultima_data_relevante: parseDate(pickField(d, "ultima_data_relevante_calc", "ultima_data_relevante")),
  fase_atual: pickField(d, "fase_atual_calc", "fase_atual"),
  dias_ate_publicacao: pickField(d, "dias_ate_publicacao_calc", "dias_ate_publicacao") === "" ? null : +pickField(d, "dias_ate_publicacao_calc", "dias_ate_publicacao"),
  dias_publicacao_ate_homologacao: pickField(d, "dias_publicacao_ate_homologacao_calc", "dias_publicacao_ate_homologacao") === "" ? null : +pickField(d, "dias_publicacao_ate_homologacao_calc", "dias_publicacao_ate_homologacao"),
  dias_homologacao_ate_vrpl: pickField(d, "dias_homologacao_ate_vrpl_calc", "dias_homologacao_ate_vrpl") === "" ? null : +pickField(d, "dias_homologacao_ate_vrpl_calc", "dias_homologacao_ate_vrpl"),
  dias_vrpl_ate_aio: pickField(d, "dias_vrpl_ate_aio_calc", "dias_vrpl_ate_aio") === "" ? null : +pickField(d, "dias_vrpl_ate_aio_calc", "dias_vrpl_ate_aio"),
  dias_aio_ate_inicio_obra: pickField(d, "dias_aio_ate_inicio_obra_calc", "dias_aio_ate_inicio_obra") === "" ? null : +pickField(d, "dias_aio_ate_inicio_obra_calc", "dias_aio_ate_inicio_obra"),
  faixa_repasse: pickField(d, "faixa_repasse_calc", "faixa_repasse"),
  prazo_pub_licitacao: parseDate(pickField(d, "prazo_pub_licitacao_calc", "prazo_pub_licitacao")),
  status_pub_licitacao: pickField(d, "status_pub_licitacao_calc", "status_pub_licitacao"),
  prazo_homolog_licitacao: parseDate(pickField(d, "prazo_homolog_licitacao_calc", "prazo_homolog_licitacao")),
  status_homolog_licitacao: pickField(d, "status_homolog_licitacao_calc", "status_homolog_licitacao"),
  prazo_inicio_obra: parseDate(pickField(d, "prazo_inicio_obra_calc", "prazo_inicio_obra")),
  status_inicio_obra: pickField(d, "status_inicio_obra_calc", "status_inicio_obra"),
  data_limite_licitacao_casa_civil: parseDate(pickField(d, "data_limite_licitacao_casa_civil_const", "data_limite_licitacao_casa_civil")),
  status_regra_casa_civil: pickField(d, "status_regra_casa_civil_calc", "status_regra_casa_civil"),
  urgencia_suspensiva: pickField(d, "urgencia_suspensiva_calc", "urgencia_suspensiva"),
  tipo_doc_suspensiva: pickField(d, "tipo_doc_suspensiva"),
  doc_titularidade: pickField(d, "doc_titularidade"),
  doc_viabilidade_terreno: pickField(d, "doc_viabilidade_terreno"),
  doc_sondagem: pickField(d, "doc_sondagem"),
  doc_orcamento: pickField(d, "doc_orcamento"),
  doc_projetos_implantacao: pickField(d, "doc_projetos_implantacao"),
  doc_projetos_complementares: pickField(d, "doc_projetos_complementares"),
  doc_ambiental: pickField(d, "doc_ambiental"),
  doc_vigilancia_sanitaria: pickField(d, "doc_vigilancia_sanitaria"),
  doc_bombeiros: pickField(d, "doc_bombeiros"),
  doc_trabalho_social: pickField(d, "doc_trabalho_social"),
  };
  const docsPendentes = docsSuspensivaPendentes(d);
  row.docs_suspensiva_pendentes = docsPendentes;
  row.docs_suspensiva_resumo = docsPendentes.length ? docsPendentes.join(", ") : "";
  row.docs_suspensiva_qtd = docsPendentes.length;
  return row;
}

const rawDataParsed = dsv.parse(rawText, parseBaseRow);
const previousRawData = dsv.parse(previousRawText, parseBaseRow);

// ── Diff: detectar alterações entre snapshots
const diffFields = [
  "situacao", "situacao_suspensiva", "status_suspensiva", "fase_atual",
  "dt_retirada_suspensiva", "dt_lae", "dt_pub_licitacao", "dt_homolog_licitacao",
  "dt_vrpl", "dt_aio", "dt_inicio_obra", "vlr_repasse",
  "status_pub_licitacao", "status_homolog_licitacao", "status_inicio_obra",
  "status_regra_casa_civil", "urgencia_suspensiva",
];

function rowKey(d) {
  return (d.num_convenio || d.cod_tci || "").trim();
}

function valStr(v) {
  if (v == null) return "";
  if (v instanceof Date) return v.toISOString();
  return String(v).trim();
}

function diffLabel(value) {
  if (value === "novo") return "Novo";
  if (value === "alterado") return "Alterado";
  return "Sem alteração";
}

function isSuspensivaRetirada(d) {
  return d.situacao_suspensiva === "Suspensiva retirada";
}

function isComSuspensivaAtiva(d) {
  return d.situacao === "Contratado - Suspensiva" && !isSuspensivaRetirada(d);
}

function isSemSuspensivaDmp(d) {
  return d.situacao === "Contratado - Normal" || isSuspensivaRetirada(d);
}

function isContratoNormal(d) {
  return d.situacao === "Contratado - Normal";
}

function isSemPrazoPc72(d) {
  return d.dt_assinatura instanceof Date && !isNaN(d.dt_assinatura) && d.dt_assinatura.getTime() < LICITACAO_PC72_CORTE;
}

function getStatusPubLicitacaoDisplay(d) {
  if (!d.dt_pub_licitacao && isSemPrazoPc72(d)) return "Sem prazo (PC 72)";
  if (!d.dt_pub_licitacao && !d.status_pub_licitacao) return "Sem prazo calculado";
  return d.status_pub_licitacao;
}

function getStatusHomologLicitacaoDisplay(d) {
  if (!d.dt_homolog_licitacao && isSemPrazoPc72(d)) return "Sem prazo (PC 72)";
  if (!d.dt_homolog_licitacao && !d.status_homolog_licitacao) return "Sem prazo calculado";
  return d.status_homolog_licitacao;
}

const previousByKey = new Map(previousRawData.map(d => [rowKey(d), d]));

const rawData = rawDataParsed.map(d => {
  const key = rowKey(d);
  const prev = previousByKey.get(key);
  if (!prev) return {...d, _diff: "novo", _diff_label: diffLabel("novo"), _diffCampos: []};
  const campos = diffFields.filter(f => valStr(d[f]) !== valStr(prev[f]));
  if (campos.length === 0) return {...d, _diff: null, _diff_label: diffLabel(null), _diffCampos: []};
  return {...d, _diff: "alterado", _diff_label: diffLabel("alterado"), _diffCampos: campos};
});

const secretarias = [...new Set(rawData.map(d => d.secretaria).filter(Boolean))].sort();

function maxSnapshotDateLabel(snapshotMeta) {
  const snapshotAtual = parseDate(snapshotMeta?.snapshot_atual);
  if (snapshotAtual instanceof Date && !isNaN(snapshotAtual)) {
    return formatDate(snapshotAtual);
  }

  const candidates = [
    snapshotMeta?.snapshot_anterior,
    snapshotMeta?.snapshot_primeiro,
  ]
    .map(parseDate)
    .filter((date) => date instanceof Date && !isNaN(date));

  if (candidates.length === 0) return "—";

  const maxDate = candidates.reduce((latest, current) =>
    current.getTime() > latest.getTime() ? current : latest
  );

  return formatDate(maxDate);
}

const updatedAt = maxSnapshotDateLabel(baseDiffLatest);

function formatMetricDelta(value) {
  if (value == null || value === 0) {
    return {label: null, tone: "neutral"};
  }
  return {
    label: `${value > 0 ? "+" : ""}${formatNumber(value)}`,
    tone: value > 0 ? "positive" : "negative",
  };
}

function formatCurrencyDelta(value) {
  if (value == null || value === 0) {
    return {label: null, tone: "neutral"};
  }
  return {
    label: `${value > 0 ? "+" : "-"}${formatCurrencyCompact(Math.abs(value))}`,
    tone: value > 0 ? "positive" : "negative",
  };
}

function buildMetricDelta(currentValue, previousValue, formatter = formatMetricDelta) {
  if (!baseDiffLatest?.snapshot_anterior) {
    return {
      ...formatter(null),
      title: "Sem snapshot anterior para comparação",
    };
  }

  return {
    ...formatter(currentValue - previousValue),
    title: `Variação em relação a ${formatDate(baseDiffLatest.snapshot_anterior)}`,
  };
}

function createReferenceImageButton({label, title, imageUrl, caption, linkLabel = "Abrir imagem em nova aba"}) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "context-link-btn";
  button.innerHTML = `<span class="context-link-btn__label">${label}</span>`;

  button.addEventListener("click", () => {
    window.__pc32RuleTooltipInit?.closeAllRuleTooltips?.();

    const previousOverflow = document.body.style.overflow;
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const titleId = `pc32-reference-modal-title-${Math.random().toString(36).slice(2, 9)}`;
    const captionId = `pc32-reference-modal-caption-${Math.random().toString(36).slice(2, 9)}`;

    const overlay = document.createElement("div");
    overlay.className = "reference-modal";
    overlay.innerHTML = `
      <div class="reference-modal__backdrop"></div>
      <div class="reference-modal__dialog" role="dialog" aria-modal="true" aria-labelledby="${titleId}" aria-describedby="${captionId}">
        <div class="reference-modal__header">
          <div class="reference-modal__titles">
            <h3 id="${titleId}">${title}</h3>
            <p id="${captionId}">${caption}</p>
          </div>
          <button type="button" class="reference-modal__close" aria-label="Fechar fluxo">Fechar</button>
        </div>
        <div class="reference-modal__body">
          <img src="${imageUrl}" alt="${title}" class="reference-modal__image">
        </div>
        <div class="reference-modal__footer">
          <a class="reference-modal__link" href="${imageUrl}" target="_blank" rel="noreferrer">${linkLabel}</a>
        </div>
      </div>
    `;

    const closeButton = overlay.querySelector(".reference-modal__close");
    const close = () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", onKeydown);
      overlay.remove();
      previousFocus?.focus?.();
    };
    const onKeydown = (event) => {
      if (event.key === "Escape") close();
    };

    overlay.addEventListener("click", (event) => {
      if (event.target === overlay || event.target.closest(".reference-modal__backdrop")) {
        close();
      }
    });
    closeButton?.addEventListener("click", close);
    document.addEventListener("keydown", onKeydown);
    document.body.append(overlay);
    document.body.style.overflow = "hidden";
    closeButton?.focus();
  });

  return button;
}
```

```js
if (!window.__pc32RuleTooltipInit) {
  const closeAllRuleTooltips = () => {
    document.querySelectorAll(".rule-tooltip.is-open").forEach((tooltip) => {
      tooltip.classList.remove("is-open");
      const trigger = tooltip.querySelector(".rule-tooltip__trigger");
      if (trigger) trigger.setAttribute("aria-expanded", "false");
    });
  };

  const syncRuleTooltips = () => {
    document.querySelectorAll(".rule-tooltip").forEach((tooltip, index) => {
      const trigger = tooltip.querySelector(".rule-tooltip__trigger");
      const content = tooltip.querySelector(".rule-tooltip__content");
      if (!trigger || !content) return;

      const tooltipId = content.id || `rule-tooltip-content-${index + 1}`;
      content.id = tooltipId;
      trigger.type = "button";
      trigger.setAttribute("aria-expanded", tooltip.classList.contains("is-open") ? "true" : "false");
      trigger.setAttribute("aria-controls", tooltipId);
      trigger.setAttribute("aria-haspopup", "dialog");
      content.setAttribute("role", "dialog");
    });
  };

  document.addEventListener("click", (event) => {
    const trigger = event.target.closest(".rule-tooltip__trigger");
    if (trigger) {
      const tooltip = trigger.closest(".rule-tooltip");
      const willOpen = !tooltip.classList.contains("is-open");
      closeAllRuleTooltips();
      if (willOpen) {
        tooltip.classList.add("is-open");
        trigger.setAttribute("aria-expanded", "true");
      }
      event.preventDefault();
      return;
    }

    if (!event.target.closest(".rule-tooltip")) {
      closeAllRuleTooltips();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeAllRuleTooltips();
  });

  window.addEventListener("resize", closeAllRuleTooltips);
  window.addEventListener("scroll", closeAllRuleTooltips, true);

  syncRuleTooltips();
  window.__pc32RuleTooltipInit = { closeAllRuleTooltips, syncRuleTooltips };
} else {
  window.__pc32RuleTooltipInit.syncRuleTooltips();
}
```

```js
const pageTitleBar = document.createElement("div");
pageTitleBar.className = "page-titlebar dashboard-toolbar";
pageTitleBar.innerHTML = `
  <div class="page-titlebar__heading dashboard-toolbar__title">
    <h1>Painel OGU - NOVO PAC - Novas Seleções - DMP/SE</h1>
  </div>
  <div class="page-titlebar__meta dashboard-toolbar__side" aria-label="Data de atualização">
    <div class="dashboard-toolbar__meta">
      <span class="page-titlebar__meta-label">Atualizado em</span>
      <strong class="page-titlebar__meta-value">${updatedAt}</strong>
    </div>
  </div>
`;
display(pageTitleBar);
```

<div class="filters-bar">

```js
const fConvenioInput = Inputs.search(rawData, {
  placeholder: "Buscar por num. convênio ou SACI…",
  columns: ["num_convenio", "cod_tci", "proponente"],
  label: "Convênio / SACI / Proponente",
});

function localizeSearchResults(input) {
  const output = input.querySelector("output");
  const searchField = input.querySelector("input[type='search']");
  const countFormatter = new Intl.NumberFormat("pt-BR");
  const sync = () => {
    if (output) {
      const match = output.textContent.match(/^([\d.,]+)\s+results?$/i);
      if (match) {
        const rawCount = match[1];
        const count = Number(rawCount.replace(/[.,]/g, ""));
        const formattedCount = Number.isFinite(count) ? countFormatter.format(count) : rawCount;
        output.textContent = `${formattedCount} ${count === 1 ? "resultado" : "resultados"}`;
      }
    }

    input.querySelectorAll("td").forEach((cell) => {
      if (cell.textContent?.trim() === "No results.") {
        cell.textContent = "Nenhum resultado.";
      }
    });
  };

  sync();
  input.addEventListener("input", sync);
  new MutationObserver(sync).observe(input, {childList: true, characterData: true, subtree: true});

  // Observable Inputs.search updates its internal result list while typing,
  // but it does not emit an input event on the form wrapper by default.
  // Forward the field events so downstream reactive cells see the filtered rows.
  if (searchField) {
    const notify = () => input.dispatchEvent(new Event("input", {bubbles: true}));
    searchField.addEventListener("input", notify);
    searchField.addEventListener("change", notify);
    searchField.addEventListener("search", notify);
  }
}

localizeSearchResults(fConvenioInput);

const fConvenio = view(fConvenioInput);
```

```js
function makeMultiPicker(labelText, options, selectedValues = [], allLabel = "Todas", selectedLabel = "selecionadas") {
  const selected = new Set(selectedValues.filter(value => options.includes(value)));
  const ac = new AbortController();
  const wrap = Object.assign(document.createElement("div"), { value: [...selected] });
  wrap.className = "multi-picker";

  const label = document.createElement("label");
  label.className = "multi-picker__label";
  label.textContent = labelText;

  const toggle = document.createElement("button");
  toggle.type = "button";
  toggle.className = "multi-picker__toggle";

  const panel = document.createElement("div");
  panel.className = "multi-picker__panel";
  panel.hidden = true;

  const actions = document.createElement("div");
  actions.className = "multi-picker__actions";

  const selectAll = document.createElement("button");
  selectAll.type = "button";
  selectAll.className = "multi-picker__action-btn";
  selectAll.textContent = "Selecionar todas";

  const clearAll = document.createElement("button");
  clearAll.type = "button";
  clearAll.className = "multi-picker__action-btn";
  clearAll.textContent = "Limpar";

  const grid = document.createElement("div");
  grid.className = "multi-picker__grid";

  const updateToggleText = () => {
    if (selected.size === 0 || selected.size === options.length) toggle.textContent = allLabel;
    else if (selected.size === 1) toggle.textContent = [...selected][0];
    else toggle.textContent = `${selected.size} ${selectedLabel}`;
  };

  const emit = () => {
    wrap.value = selected.size === options.length ? [] : options.filter(option => selected.has(option));
    updateToggleText();
    wrap.dispatchEvent(new Event("input", { bubbles: true }));
  };

  const chips = options.map(option => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "multi-picker__chip";
    chip.textContent = option;
    if (selected.has(option)) chip.classList.add("is-active");
    chip.addEventListener("click", () => {
      if (selected.has(option)) {
        selected.delete(option);
        chip.classList.remove("is-active");
      } else {
        selected.add(option);
        chip.classList.add("is-active");
      }
      emit();
    });
    return chip;
  });

  selectAll.addEventListener("click", () => {
    options.forEach(option => selected.add(option));
    chips.forEach(chip => chip.classList.add("is-active"));
    emit();
  });

  clearAll.addEventListener("click", () => {
    selected.clear();
    chips.forEach(chip => chip.classList.remove("is-active"));
    emit();
  });

  const closePanel = () => {
    panel.hidden = true;
    toggle.classList.remove("is-open");
    toggle.setAttribute("aria-expanded", "false");
  };

  toggle.addEventListener("click", () => {
    const willOpen = panel.hidden;
    panel.hidden = !panel.hidden;
    toggle.classList.toggle("is-open", willOpen);
    toggle.setAttribute("aria-expanded", willOpen ? "true" : "false");
  });

  document.addEventListener("click", (event) => {
    if (!wrap.contains(event.target)) closePanel();
  }, {signal: ac.signal});

  wrap.destroy = () => ac.abort();

  actions.append(selectAll, clearAll);
  grid.append(...chips);
  panel.append(actions, grid);
  label.append(toggle, panel);
  wrap.append(label);

  toggle.setAttribute("aria-haspopup", "dialog");
  toggle.setAttribute("aria-expanded", "false");
  updateToggleText();
  wrap.value = options.filter(option => selected.has(option));
  return wrap;
}

function getAno(d) {
  return d.dt_assinatura ? String(d.dt_assinatura.getUTCFullYear()) : null;
}

function filterBySelection(value, selectedValues) {
  return selectedValues.length === 0 || selectedValues.includes(value);
}

function computeCascadeOptions(data, state) {
  const secretaria = [...new Set(
    data
      .filter(d => filterBySelection(d.modalidade, state.modalidade))
      .filter(d => filterBySelection(getAno(d), state.ano))
      .map(d => d.secretaria)
      .filter(Boolean)
  )].sort();

  const modalidade = [...new Set(
    data
      .filter(d => filterBySelection(d.secretaria, state.secretaria))
      .filter(d => filterBySelection(getAno(d), state.ano))
      .map(d => d.modalidade)
      .filter(Boolean)
  )].sort();

  const ano = [...new Set(
    data
      .filter(d => filterBySelection(d.secretaria, state.secretaria))
      .filter(d => filterBySelection(d.modalidade, state.modalidade))
      .map(getAno)
      .filter(Boolean)
  )].sort();

  return {secretaria, modalidade, ano};
}

function sanitizeCascadeState(data, state) {
  const options = computeCascadeOptions(data, state);
  const secretaria = state.secretaria.filter(value => options.secretaria.includes(value));
  const modalidade = state.modalidade.filter(value => options.modalidade.includes(value));
  const ano = state.ano.filter(value => options.ano.includes(value));
  return {
    secretaria: secretaria.length === options.secretaria.length ? [] : secretaria,
    modalidade: modalidade.length === options.modalidade.length ? [] : modalidade,
    ano: ano.length === options.ano.length ? [] : ano
  };
}

function makeCascadeFilters(data) {
  let state = {secretaria: [], modalidade: [], ano: []};
  const wrap = Object.assign(document.createElement("div"), {value: state});
  wrap.className = "filters-cascade";

  function emit() {
    wrap.value = state;
    wrap.dispatchEvent(new Event("input", {bubbles: true}));
  }

  function render() {
    const options = computeCascadeOptions(data, state);
    wrap.querySelectorAll(".multi-picker").forEach(p => p.destroy?.());
    wrap.replaceChildren();

    const configs = [
      {key: "secretaria", label: "Secretaria", values: options.secretaria, allLabel: "Todas", selectedLabel: "selecionadas"},
      {key: "modalidade", label: "Modalidade", values: options.modalidade, allLabel: "Todas", selectedLabel: "selecionadas"},
      {key: "ano", label: "Ano de seleção", values: options.ano, allLabel: "Todos", selectedLabel: "anos"}
    ];

    configs.forEach((config) => {
      const slot = document.createElement("div");
      slot.className = "filters-cascade__item";
      const picker = makeMultiPicker(
        config.label,
        config.values,
        state[config.key],
        config.allLabel,
        config.selectedLabel
      );
      picker.addEventListener("input", () => {
        wrap.setState({...state, [config.key]: Array.isArray(picker.value) ? picker.value : []});
      });
      slot.append(picker);
      wrap.append(slot);
    });
  }

  wrap.setState = (nextState) => {
    state = sanitizeCascadeState(data, {
      secretaria: Array.isArray(nextState.secretaria) ? nextState.secretaria : [],
      modalidade: Array.isArray(nextState.modalidade) ? nextState.modalidade : [],
      ano: Array.isArray(nextState.ano) ? nextState.ano : []
    });
    render();
    emit();
  };

  wrap.reset = () => {
    wrap.setState({secretaria: [], modalidade: [], ano: []});
  };

  render();
  emit();
  return wrap;
}

const filtrosInput = makeCascadeFilters(rawData);
const filtros = view(filtrosInput);
```

```js
const clearFiltersButton = html`<button type="button" class="filters-reset">Limpar filtros do topo</button>`;

clearFiltersButton.addEventListener("click", () => {
  const searchInput = fConvenioInput.querySelector("input[type='search']");
  if (searchInput) {
    searchInput.value = "";
    searchInput.dispatchEvent(new Event("input", {bubbles: true}));
    searchInput.dispatchEvent(new Event("change", {bubbles: true}));
  }
  filtrosInput.reset();
});

display(clearFiltersButton);
```

</div>

```js
const filtrosAtivos = [
  (filtros?.secretaria?.length > 0) ? {key: "secretaria", text: summarizeFilter("Secretaria", filtros.secretaria)} : null,
  (filtros?.modalidade?.length > 0) ? {key: "modalidade", text: summarizeFilter("Modalidade", filtros.modalidade)} : null,
  (filtros?.ano?.length > 0) ? {key: "ano", text: summarizeFilter("Ano", filtros.ano, "anos")} : null
].filter(Boolean);

const filtersSummary = html`<div class="filters-summary" style="${filtrosAtivos.length === 0 ? 'display:none' : ''}">
  <span class="filters-summary__count">${filtrosAtivos.length} filtro${filtrosAtivos.length === 1 ? "" : "s"} ativo${filtrosAtivos.length === 1 ? "" : "s"}</span>
</div>`;

filtrosAtivos.forEach((item) => {
  const chip = html`<button type="button" class="filters-summary__chip">${item.text}<span aria-hidden="true">×</span></button>`;
  chip.addEventListener("click", () => {
    filtrosInput.setState({...filtrosInput.value, [item.key]: []});
  });
  filtersSummary.append(chip);
});

display(filtersSummary);
```

```js
const secretariaSelecionada = Array.isArray(filtros?.secretaria) ? filtros.secretaria : [];
const modalidadeSelecionada = Array.isArray(filtros?.modalidade) ? filtros.modalidade : [];
const anoSelecionado = Array.isArray(filtros?.ano) ? filtros.ano : [];

function matchesModalidadeFilter(d) {
  return modalidadeSelecionada.length === 0 || modalidadeSelecionada.includes(d.modalidade);
}

function matchesAnoFilter(d) {
  return anoSelecionado.length === 0 || (getAno(d) && anoSelecionado.includes(getAno(d)));
}

function matchesSecretariaFilter(d) {
  return secretariaSelecionada.length === 0 || secretariaSelecionada.includes(d.secretaria);
}

function summarizeFilter(label, values, pluralLabel = "selecionadas") {
  if (values.length === 0) return null;
  if (values.length <= 2) return `${label}: ${values.join(", ")}`;
  return `${label}: ${values.length} ${pluralLabel}`;
}

// ── baseData: filtros de topo
const baseData = fConvenio.filter(d =>
  matchesSecretariaFilter(d) &&
  matchesModalidadeFilter(d) &&
  matchesAnoFilter(d)
);

// ── helper: gráfico clicável como input reativo
function makeClickableChart(plotEl, items, keyField, initialValue = null) {
  const wrapper = document.createElement("div");
  wrapper.style.position = "relative";
  const input = Object.assign(wrapper, { value: initialValue });

  const badge = document.createElement("div");
  badge.style.cssText = `
    display:none; position:absolute; top:0; right:0;
    background:#fff7ed; border:1px solid #fdba74; border-radius:999px;
    padding:0.2rem 0.65rem; font-size:0.75rem; font-weight:600;
    color:#9a3412; cursor:pointer; align-items:center;
  `;

  const rects = Array.from(plotEl.querySelectorAll("g[aria-label='bar'] rect"));

  function sync(sel) {
    rects.forEach(r => {
      r.style.opacity = sel == null || r.dataset.key === sel ? "1" : "0.2";
    });
    badge.style.display = sel != null ? "inline-flex" : "none";
    if (sel != null) badge.textContent = `${sel}  ×`;
  }

  function setVal(val) {
    input.value = val;
    sync(val);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  }

  rects.forEach((r, i) => {
    if (i < items.length) {
      r.dataset.key = items[i][keyField];
      r.style.cursor = "pointer";
      r.addEventListener("click", e => {
        const key = r.dataset.key;
        setVal(input.value === key ? null : key);
        e.stopPropagation();
      });
    }
  });

  badge.addEventListener("click", e => { setVal(null); e.stopPropagation(); });
  plotEl.addEventListener("click", () => { if (input.value != null) setVal(null); });

  sync(initialValue);
  wrapper.append(plotEl, badge);
  return input;
}

function makeCrossFilteredCharts(data, previousBaseData, drillField, drillLabel, drillMarginLeft) {
  let sitSel = null;
  let suspSel = null;
  let drillSel = null;
  const wrap = Object.assign(document.createElement("div"), {
    value: {situacao: null, suspensiva: null, drill: null}
  });

  function applyFilter(d, field, value) {
    if (value == null) return true;
    return d[field] === value;
  }

  function computeChartData() {
    // Cross-filter: each chart sees data filtered by OTHER selections only
    const forSituacao = data.filter(d =>
      applyFilter(d, "situacao_suspensiva", suspSel) &&
      applyFilter(d, drillField, drillSel)
    );
    const bySituacao = SITUACAO_ORDER
      .map(s => ({situacao: s, qtd: forSituacao.filter(d => d.situacao === s).length}))
      .filter(d => d.qtd > 0);

    const forSuspensiva = data.filter(d =>
      applyFilter(d, "situacao", sitSel) &&
      applyFilter(d, drillField, drillSel)
    );
    const suspCounts = new Map();
    for (const d of forSuspensiva) {
      const s = d.situacao_suspensiva;
      if (s && s.trim() !== "") suspCounts.set(s, (suspCounts.get(s) ?? 0) + 1);
    }
    const bySuspensiva = SUSPENSIVA_ORDER
      .map(s => ({situacao_suspensiva: s, qtd: suspCounts.get(s) ?? 0}))
      .filter(d => d.qtd > 0);

    const forDrill = data.filter(d =>
      applyFilter(d, "situacao", sitSel) &&
      applyFilter(d, "situacao_suspensiva", suspSel)
    );
    const byDrill = [...new Set(forDrill.map(d => d[drillField]).filter(Boolean))]
      .map(group => {
        const groupRows = forDrill.filter(d => d[drillField] === group);
        return {
          group,
          contratos: groupRows.length,
          vlr_repasse: groupRows.reduce((sum, d) => sum + d.vlr_repasse, 0),
        };
      })
      .filter(d => d.contratos > 0)
      .sort((a, b) => b.contratos - a.contratos || b.vlr_repasse - a.vlr_repasse);

    return {bySituacao, bySuspensiva, byDrill};
  }

  function emit() {
    wrap.value = {situacao: sitSel, suspensiva: suspSel, drill: drillSel};
    wrap.dispatchEvent(new Event("input", {bubbles: true}));
  }

  function render() {
    wrap.innerHTML = "";
    const {bySituacao, bySuspensiva, byDrill} = computeChartData();

    // ── Row: Situação + Suspensiva
    const sitSuspRow = document.createElement("div");
    sitSuspRow.className = "grid-two";

    // ── Card Situação
    const sitCard = document.createElement("div");
    sitCard.className = "card";
    sitCard.innerHTML = `
      <h2>Situação do Contrato (SACI) <span class="rule-tooltip"><button class="rule-tooltip__trigger" aria-label="Regra">?</button><span class="rule-tooltip__content">Classificação da situação contratual conforme a origem (SACI/MCID).<ul><li><strong>Em Contratação</strong> — instrumento ainda não formalizado</li><li><strong>Contratado - Suspensiva</strong> — contrato assinado com condição suspensiva pendente</li><li><strong>Contratado - Normal</strong> — contrato ativo sem restrições</li><li><strong>Cancelado ou Distratado</strong> — contrato encerrado</li><li><strong>Contratado - Em Prestação de Contas</strong> — contrato em fase de prestação de contas</li></ul></span></span></h2>
      <p>Clique em uma barra para filtrar</p>
    `;
    const sitChart = makeClickableChart(
      Plot.plot({
        marginLeft: 220, marginRight: 50,
        height: Math.max(180, bySituacao.length * 44 + 40),
        style: {fontFamily: "var(--font-sans, IBM Plex Sans, sans-serif)", fontSize: 13},
        x: {label: null, grid: false, axis: null},
        y: {label: null, domain: bySituacao.map(d => d.situacao)},
        marks: [
          Plot.barX(bySituacao, {
            x: "qtd", y: "situacao",
            fill: d => SITUACAO_CORES[d.situacao] ?? "#8a94a3", rx: 6,
          }),
          Plot.text(bySituacao, {
            x: "qtd", y: "situacao",
            text: d => formatNumber(d.qtd),
            dx: 6, textAnchor: "start", fontSize: 12, fill: "#5b6470",
          }),
        ],
      }),
      bySituacao, "situacao", sitSel
    );
    sitChart.addEventListener("input", () => {
      sitSel = sitChart.value;
      render();
      emit();
    });
    sitCard.append(sitChart);

    // ── Card Suspensiva
    const suspCard = document.createElement("div");
    suspCard.className = "card";
    suspCard.innerHTML = `
      <h2>Situação da Análise Suspensiva (PBI) <span class="rule-tooltip"><button class="rule-tooltip__trigger" aria-label="Regra">?</button><span class="rule-tooltip__content">Situação da condição suspensiva conforme o PBI.<ul><li><strong>Doc. não enviada p/ análise</strong> — documentação ainda não submetida</li><li><strong>Análise não iniciada / iniciada</strong> — etapas de tramitação interna</li><li><strong>Analisada e aceita</strong> — condição aceita, aguardando retirada</li><li><strong>Suspensiva retirada</strong> — condição satisfeita, contrato liberado</li></ul></span></span></h2>
      <p>Clique em uma barra para filtrar</p>
    `;
    const suspChart = makeClickableChart(
      Plot.plot({
        marginLeft: 230, marginRight: 50,
        height: Math.max(180, bySuspensiva.length * 44 + 40),
        style: {fontFamily: "var(--font-sans, IBM Plex Sans, sans-serif)", fontSize: 13},
        x: {label: null, grid: false, axis: null},
        y: {label: null, domain: bySuspensiva.map(d => d.situacao_suspensiva)},
        marks: [
          Plot.barX(bySuspensiva, {
            x: "qtd", y: "situacao_suspensiva",
            fill: d => SUSPENSIVA_CORES[d.situacao_suspensiva] ?? "#8a94a3", rx: 6,
          }),
          Plot.text(bySuspensiva, {
            x: "qtd", y: "situacao_suspensiva",
            text: d => formatNumber(d.qtd),
            dx: 6, textAnchor: "start", fontSize: 12, fill: "#5b6470",
          }),
        ],
      }),
      bySuspensiva, "situacao_suspensiva", suspSel
    );
    suspChart.addEventListener("input", () => {
      suspSel = suspChart.value;
      render();
      emit();
    });
    suspCard.append(suspChart);

    sitSuspRow.append(sitCard, suspCard);

    // ── Row: Drill (Contratos + Repasse por Secretaria/Modalidade)
    const drillRow = document.createElement("div");
    drillRow.className = "grid-two";

    function makeDrillCard(title, subtitle, chartNode) {
      const card = document.createElement("div");
      card.className = "card";
      const h2 = document.createElement("h2");
      h2.textContent = title;
      const p = document.createElement("p");
      p.textContent = subtitle;
      card.append(h2, p, chartNode);
      return card;
    }

    const contratosChart = makeClickableChart(
      Plot.plot({
        marginLeft: drillMarginLeft,
        marginRight: 90,
        height: Math.max(180, byDrill.length * 52 + 40),
        style: {fontFamily: "var(--font-sans, IBM Plex Sans, sans-serif)", fontSize: 13},
        x: {label: null, grid: false, axis: null},
        y: {label: null, domain: byDrill.map(d => d.group)},
        marks: [
          Plot.barX(byDrill, {
            x: "contratos",
            y: "group",
            fill: "#356c8c",
            rx: 6,
          }),
          Plot.text(byDrill, {
            x: "contratos",
            y: "group",
            text: d => formatNumber(d.contratos),
            dx: 6,
            textAnchor: "start",
            fontSize: 12,
            fill: "#5b6470",
          }),
        ],
      }),
      byDrill, "group", drillSel
    );
    contratosChart.addEventListener("input", () => {
      drillSel = contratosChart.value;
      render();
      emit();
    });

    const repasseChart = makeClickableChart(
      Plot.plot({
        marginLeft: drillMarginLeft,
        marginRight: 110,
        height: Math.max(180, byDrill.length * 52 + 40),
        style: {fontFamily: "var(--font-sans, IBM Plex Sans, sans-serif)", fontSize: 13},
        x: {label: null, grid: false, axis: null},
        y: {label: null, domain: byDrill.map(d => d.group)},
        marks: [
          Plot.barX(byDrill, {
            x: "vlr_repasse",
            y: "group",
            fill: "#0f766e",
            rx: 6,
          }),
          Plot.text(byDrill, {
            x: "vlr_repasse",
            y: "group",
            text: d => formatCurrencyCompact(d.vlr_repasse),
            dx: 6,
            textAnchor: "start",
            fontSize: 12,
            fill: "#5b6470",
          }),
        ],
      }),
      byDrill, "group", drillSel
    );
    repasseChart.addEventListener("input", () => {
      drillSel = repasseChart.value;
      render();
      emit();
    });

    drillRow.append(
      makeDrillCard(`Contratos por ${drillLabel}`, "Distribuição da quantidade de contratos na seleção atual", contratosChart),
      makeDrillCard(`Repasse por ${drillLabel}`, "Distribuição do valor total de repasse na seleção atual", repasseChart)
    );

    // ── Cards (entre gráficos de situação e drill)
    const fullyFiltered = data.filter(d =>
      applyFilter(d, "situacao", sitSel) &&
      applyFilter(d, "situacao_suspensiva", suspSel) &&
      applyFilter(d, drillField, drillSel)
    );
    const prevFiltered = previousBaseData.filter(d =>
      applyFilter(d, "situacao", sitSel) &&
      applyFilter(d, "situacao_suspensiva", suspSel) &&
      applyFilter(d, drillField, drillSel)
    );
    const isComSuspensiva = (d) => isComSuspensivaAtiva(d);

    const isSemSuspensiva = (d) => isSemSuspensivaDmp(d);

    const isContratoRestante = (d) =>
      d.situacao === "Em Contratação" ||
      d.situacao === "Cancelado ou Distratado" ||
      d.situacao === "Contratado - Em Prestação de Contas";

    const _total = fullyFiltered.length;
    const _vlrTotal = fullyFiltered.reduce((sum, d) => sum + d.vlr_repasse, 0);
    const _semSusp = fullyFiltered.filter(isSemSuspensiva).length;
    const _vlrSemSusp = fullyFiltered.filter(isSemSuspensiva).reduce((sum, d) => sum + d.vlr_repasse, 0);
    const _comSusp = fullyFiltered.filter(isComSuspensiva).length;
    const _vlrComSusp = fullyFiltered.filter(isComSuspensiva).reduce((sum, d) => sum + d.vlr_repasse, 0);
    const _restantes = fullyFiltered.filter(isContratoRestante).length;
    const _vlrRestantes = fullyFiltered.filter(isContratoRestante).reduce((sum, d) => sum + d.vlr_repasse, 0);
    const _pTotal = prevFiltered.length;
    const _pSemSusp = prevFiltered.filter(isSemSuspensiva).length;
    const _pComSusp = prevFiltered.filter(isComSuspensiva).length;
    const _pRestantes = prevFiltered.filter(isContratoRestante).length;
    const _pctSusp = _total > 0 ? _comSusp / _total : 0;
    const _pctSem = _total > 0 ? _semSusp / _total : 0;
    const _pctRestantes = _total > 0 ? _restantes / _total : 0;
    const _drillDetail = drillSel == null
      ? "do recorte principal"
      : `do recorte de ${drillLabel.toLowerCase()} ${drillSel}`;

    const cardsRow = metricGrid([
      { label: "Total selecionadas", value: formatNumber(_total), topRight: formatCurrencyCompact(_vlrTotal), delta: buildMetricDelta(_total, _pTotal), detail: _drillDetail, tone: "default" },
      { label: "Com suspensiva", value: formatNumber(_comSusp), topRight: formatCurrencyCompact(_vlrComSusp), detail: `${formatPercent(_pctSusp)} ${_drillDetail}`, delta: buildMetricDelta(_comSusp, _pComSusp), tone: "gold" },
      { label: "Sem suspensiva", value: formatNumber(_semSusp), topRight: formatCurrencyCompact(_vlrSemSusp), detail: `${formatPercent(_pctSem)} ${_drillDetail}`, delta: buildMetricDelta(_semSusp, _pSemSusp), tone: "green" },
      { label: "Contratos inativos", value: formatNumber(_restantes), topRight: formatCurrencyCompact(_vlrRestantes), detail: `${formatPercent(_pctRestantes)} ${_drillDetail}`, delta: buildMetricDelta(_restantes, _pRestantes), tone: "blue" },
    ]);

    wrap.append(cardsRow, drillRow, sitSuspRow);

    if (window.__pc32RuleTooltipInit) {
      window.__pc32RuleTooltipInit.syncRuleTooltips();
    }
  }

  render();
  emit();
  return wrap;
}

const GEO_EMPTY_LABEL = "Não informado";

function normalizeGeoLabel(value) {
  const normalized = typeof value === "string" ? value.trim() : "";
  return normalized || GEO_EMPTY_LABEL;
}

function resolveGeoColor(field, label, sampleRow) {
  if (field === "regiao") return getRegiaoColor(label);
  if (field === "uf") return getUfColor(label, normalizeGeoLabel(sampleRow?.regiao));
  if (field === "municipio") {
    return getMunicipioColor(
      label,
      normalizeGeoLabel(sampleRow?.uf),
      normalizeGeoLabel(sampleRow?.regiao)
    );
  }
  return PALETTE.blue;
}

function buildGeoBreakdown(rows, field, order) {
  const counts = new Map();
  const samples = new Map();
  for (const row of rows) {
    const label = normalizeGeoLabel(row[field]);
    counts.set(label, (counts.get(label) ?? 0) + 1);
    if (!samples.has(label)) samples.set(label, row);
  }
  const items = [...counts.entries()]
    .map(([label, qtd]) => ({
      label,
      qtd,
      color: resolveGeoColor(field, label, samples.get(label)),
    }));
  if (order) {
    const idx = new Map(order.map((v, i) => [v, i]));
    return items.sort((a, b) => (idx.get(a.label) ?? 999) - (idx.get(b.label) ?? 999));
  }
  return items.sort((a, b) => b.qtd - a.qtd || a.label.localeCompare(b.label, "pt-BR"));
}

function matchesGeoSelection(d, selection = {}) {
  return (
    (selection?.regiao == null || normalizeGeoLabel(d.regiao) === selection.regiao) &&
    (selection?.uf == null || normalizeGeoLabel(d.uf) === selection.uf) &&
    (selection?.municipio == null || normalizeGeoLabel(d.municipio) === selection.municipio)
  );
}

const GEO_MUNICIPIO_LIMIT = 15;
const GEO_OUTROS_MUNICIPIOS_LABEL = "Outros municípios";

function makeGeoCascade(rows) {
  const wrap = Object.assign(document.createElement("div"), {
    value: {regiao: null, uf: null, municipio: null}
  });
  wrap.className = "casc-chart";

  function render() {
    wrap.innerHTML = "";
    const clear = makeFlowElement("button", "casc-clear", "Limpar seleção");
    clear.hidden = !Object.values(wrap.value).some(Boolean);
    clear.addEventListener("click", () => {
      wrap.value = {regiao: null, uf: null, municipio: null};
      render();
      wrap.dispatchEvent(new Event("input", {bubbles: true}));
    });
    wrap.append(clear);
    const active = makeCascadeActiveChips(
      wrap.value,
      {regiao: "Região", uf: "UF", municipio: "Município"},
      {
        regiao: (label) => getRegiaoColor(label),
        uf: (label) => getUfColor(label, wrap.value.regiao),
        municipio: (label) => getMunicipioColor(label, wrap.value.uf, wrap.value.regiao),
      },
      (key) => {
        if (key === "regiao") wrap.value = {regiao: null, uf: null, municipio: null};
        else if (key === "uf") wrap.value = {...wrap.value, uf: null, municipio: null};
        else wrap.value = {...wrap.value, [key]: null};
        render();
        wrap.dispatchEvent(new Event("input", {bubbles: true}));
      }
    );
    if (active) wrap.append(active);

    const regiaoData = buildGeoBreakdown(rows, "regiao", REGIAO_ORDER);
    const total = rows.length;

    wrap.append(
      makeFlowLevel(
        `${formatNumber(total)} contratos no recorte atual`,
        "por região",
        regiaoData,
        total,
        {
          filterKey: "regiao",
          selectedValue: wrap.value.regiao,
          onSelect: (_key, label) => {
            const nextRegiao = wrap.value.regiao === label ? null : label;
            wrap.value = {regiao: nextRegiao, uf: null, municipio: null};
            render();
            wrap.dispatchEvent(new Event("input", {bubbles: true}));
          }
        }
      )
    );

    if (wrap.value.regiao != null) {
      const ufBase = rows.filter(d => normalizeGeoLabel(d.regiao) === wrap.value.regiao);
      const ufData = buildGeoBreakdown(ufBase, "uf");

      if (ufData.length > 0) {
        if (!ufData.some(d => d.label === wrap.value.uf)) wrap.value = {...wrap.value, uf: null, municipio: null};
        wrap.append(makeFlowConnector(`estados da região ${wrap.value.regiao}`));
        wrap.append(
          makeFlowLevel(
            `${formatNumber(ufBase.length)} contratos na região ${wrap.value.regiao}`,
            "por UF",
            ufData,
            ufBase.length,
            {
              filterKey: "uf",
              selectedValue: wrap.value.uf,
              onSelect: (_key, label) => {
                wrap.value = {
                  ...wrap.value,
                  uf: wrap.value.uf === label ? null : label,
                  municipio: null
                };
                render();
                wrap.dispatchEvent(new Event("input", {bubbles: true}));
              }
            }
          )
        );
      }
    }

    if (wrap.value.regiao != null && wrap.value.uf != null) {
      const municipioBase = rows.filter(d =>
        normalizeGeoLabel(d.regiao) === wrap.value.regiao &&
        normalizeGeoLabel(d.uf) === wrap.value.uf
      );
      const municipioFullData = buildGeoBreakdown(municipioBase, "municipio");
      const municipioTopData = municipioFullData.slice(0, GEO_MUNICIPIO_LIMIT);
      const municipioRestante = municipioFullData
        .slice(GEO_MUNICIPIO_LIMIT)
        .reduce((sum, item) => sum + item.qtd, 0);
      const municipioData = municipioRestante > 0
        ? [
            ...municipioTopData,
            {
              label: GEO_OUTROS_MUNICIPIOS_LABEL,
              qtd: municipioRestante,
              color: "#94a3b8"
            }
          ]
        : municipioTopData;

      if (municipioData.length > 0) {
        if (
          wrap.value.municipio === GEO_OUTROS_MUNICIPIOS_LABEL ||
          !municipioData.some(d => d.label === wrap.value.municipio)
        ) {
          wrap.value = {...wrap.value, municipio: null};
        }
        wrap.append(makeFlowConnector(`municípios da UF ${wrap.value.uf}`));
        wrap.append(
          makeFlowLevel(
            `${formatNumber(municipioBase.length)} contratos na UF ${wrap.value.uf}`,
            municipioBase.length > GEO_MUNICIPIO_LIMIT
              ? `top ${GEO_MUNICIPIO_LIMIT} municípios por quantidade de contratos`
              : "por município",
            municipioData,
            municipioBase.length,
            {
              filterKey: "municipio",
              selectedValue: wrap.value.municipio,
              onSelect: (_key, label) => {
                wrap.value = {
                  ...wrap.value,
                  municipio: wrap.value.municipio === label ? null : label
                };
                render();
                wrap.dispatchEvent(new Event("input", {bubbles: true}));
              }
            }
          )
        );
      }
    }
  }

  render();
  return wrap;
}

const LICITACAO_PRAZO_ORDER = ["Vencida", "Próximos 30 dias", "No prazo", "Sem prazo (PC 72)", "Sem prazo calculado"];

function makeFlowElement(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function applyActiveChipColor(chip, color) {
  chip.style.setProperty("--chip-border", hexToRgba(color, 0.28));
  chip.style.setProperty("--chip-bg", hexToRgba(color, 0.12));
  chip.style.setProperty("--chip-bg-hover", hexToRgba(color, 0.18));
  chip.style.setProperty("--chip-fg", color);
}

function makeCascadeActiveChips(values, labels, colorByKey, onClear) {
  const entries = Object.entries(values).filter(([, value]) => value != null);
  if (entries.length === 0) return null;
  const wrap = makeFlowElement("div", "casc-active");
  for (const [key, value] of entries) {
    const chip = makeFlowElement("button", "casc-active__chip", `${labels[key] ?? key}: ${value} ×`);
    chip.type = "button";
    applyActiveChipColor(chip, colorByKey[key]?.(value) ?? PALETTE.blue);
    chip.addEventListener("click", () => onClear(key));
    wrap.append(chip);
  }
  return wrap;
}

function makeFlowLevel(title, subtitle, items, total, options = {}) {
  const {filterKey, selectedValue, onSelect} = options;
  const wrap = makeFlowElement("div", "casc-level");
  const header = makeFlowElement("div", "casc-level__header");
  header.append(
    makeFlowElement("strong", "casc-level__title", title),
    makeFlowElement("span", "casc-level__subtitle", subtitle)
  );

  const filteredItems = items.filter(item => item.qtd > 0);
  const bar = makeFlowElement("div", "casc-bar");
  for (const item of filteredItems) {
    const pct = total > 0 ? (item.qtd / total) * 100 : 0;
    const seg = makeFlowElement("div", "casc-bar__seg");
    seg.style.cssText = `width:${pct}%;background:${item.color};`;
    seg.title = `${item.label}: ${item.qtd.toLocaleString("pt-BR")} (${pct.toFixed(1)}%)`;
    if (filterKey) {
      seg.classList.add("is-clickable");
      if (selectedValue === item.label) seg.classList.add("is-selected");
      seg.setAttribute("role", "button");
      seg.tabIndex = 0;
      seg.addEventListener("click", (event) => {
        event.stopPropagation();
        onSelect(filterKey, item.label);
      });
      seg.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onSelect(filterKey, item.label);
        }
      });
    }
    if (pct > 4) seg.append(makeFlowElement("span", "casc-bar__seg-num", item.qtd.toLocaleString("pt-BR")));
    bar.append(seg);
  }

  const legend = makeFlowElement("div", "casc-legend");
  for (const item of filteredItems) {
    const pct = total > 0 ? (item.qtd / total) * 100 : 0;
    const row = makeFlowElement("div", "casc-legend__item");
    if (filterKey) {
      row.classList.add("is-clickable");
      if (selectedValue === item.label) row.classList.add("is-selected");
      row.setAttribute("role", "button");
      row.tabIndex = 0;
      row.addEventListener("click", () => onSelect(filterKey, item.label));
      row.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onSelect(filterKey, item.label);
        }
      });
    }
    const dot = makeFlowElement("span", "casc-legend__dot");
    dot.style.background = item.color;
    const txt = makeFlowElement("span", "casc-legend__text");
    txt.innerHTML = `<strong>${item.label}</strong> <span>${item.qtd.toLocaleString("pt-BR")}</span>`;
    const pctEl = makeFlowElement("span", "casc-legend__pct", `${pct.toFixed(1)}%`);
    pctEl.style.color = item.color;
    txt.append(pctEl);
    row.append(dot, txt);
    legend.append(row);
  }

  wrap.append(header, bar, legend);
  return wrap;
}

function makeFlowConnector(label) {
  const wrap = makeFlowElement("div", "casc-connector");
  wrap.append(
    makeFlowElement("div", "casc-connector__line"),
    makeFlowElement("span", "casc-connector__label", label)
  );
  return wrap;
}

function matchesLicitacaoSelection(d, selection = {}) {
  return (
    (selection.pub_etapa == null ||
      (selection.pub_etapa === "Aguardando publicação" ? !d.dt_pub_licitacao : !!d.dt_pub_licitacao)) &&
    (selection.pub_prazo == null ||
      (!d.dt_pub_licitacao && getStatusPubLicitacaoDisplay(d) === selection.pub_prazo)) &&
    (selection.homolog_etapa == null ||
      (selection.homolog_etapa === "Homologação pendente" ? !!d.dt_pub_licitacao && !d.dt_homolog_licitacao : !!d.dt_homolog_licitacao)) &&
    (selection.homolog_prazo == null ||
      (!!d.dt_pub_licitacao && !d.dt_homolog_licitacao && getStatusHomologLicitacaoDisplay(d) === selection.homolog_prazo))
  );
}

function renderLicitacaoExplorer(data, previousData) {
  const initialFlow = {pub_etapa: null, pub_prazo: null, homolog_etapa: null, homolog_prazo: null};
  const container = Object.assign(makeFlowElement("div", "licitacao-explorer"), {
    value: {flow: initialFlow, casaCivil: null}
  });

  const clear = makeFlowElement("button", "casc-clear", "Limpar seleção");
  clear.type = "button";
  clear.hidden = true;
  clear.addEventListener("click", () => {
    container.value = {flow: {...initialFlow}, casaCivil: null};
    render();
    container.dispatchEvent(new Event("input", {bubbles: true}));
  });

  function setFlow(key, label) {
    container.value = {
      ...container.value,
      flow: {
        ...container.value.flow,
        [key]: container.value.flow[key] === label ? null : label
      }
    };
    render();
    container.dispatchEvent(new Event("input", {bubbles: true}));
  }

  function setCasaCivil(value) {
    container.value = {
      ...container.value,
      casaCivil: container.value.casaCivil === value ? null : value
    };
    render();
    container.dispatchEvent(new Event("input", {bubbles: true}));
  }

  function render() {
    container.innerHTML = "";
    clear.hidden = !Object.values(container.value.flow).some(Boolean) && container.value.casaCivil == null;
    container.append(clear);
    const active = makeCascadeActiveChips(
      {...container.value.flow, casaCivil: container.value.casaCivil},
      {
        pub_etapa: "Publicação",
        pub_prazo: "Prazo publicação",
        homolog_etapa: "Homologação",
        homolog_prazo: "Prazo homologação",
        casaCivil: "Casa Civil",
      },
      {
        pub_etapa: (value) => LICITACAO_CORES[value] ?? PALETTE.green,
        pub_prazo: (value) => LICITACAO_CORES[value] ?? PALETTE.green,
        homolog_etapa: (value) => LICITACAO_CORES[value] ?? PALETTE.green,
        homolog_prazo: (value) => LICITACAO_CORES[value] ?? PALETTE.green,
        casaCivil: (value) => LICITACAO_CORES[value] ?? PALETTE.green,
      },
      (key) => {
        if (key === "casaCivil") {
          container.value = {...container.value, casaCivil: null};
        } else {
          container.value = {
            ...container.value,
            flow: {...container.value.flow, [key]: null}
          };
        }
        render();
        container.dispatchEvent(new Event("input", {bubbles: true}));
      }
    );
    if (active) container.append(active);

    const eligible = data.filter(d => isContratoNormal(d));
    const previousEligible = previousData.filter(d => isContratoNormal(d));
    const flowSource = eligible.filter(d => matchesCasaCivilSelection(d, container.value.casaCivil));
    const cascadeBase = flowSource.filter(d => matchesLicitacaoSelection(d, container.value.flow));
    const casaCivilSource = eligible.filter(d => matchesLicitacaoSelection(d, container.value.flow));
    const previousSelecionada = previousEligible
      .filter(d => matchesLicitacaoSelection(d, container.value.flow))
      .filter(d => matchesCasaCivilSelection(d, container.value.casaCivil));

    const vlr = arr => arr.reduce((s, d) => s + d.vlr_repasse, 0);
    const valorSelecionado = vlr(cascadeBase);
    const aguardandoPublicacaoSelecionada = cascadeBase.filter(d => !d.dt_pub_licitacao);
    const previousAguardandoPublicacaoSelecionada = previousSelecionada.filter(d => !d.dt_pub_licitacao);
    const pubSemPrazoArr = aguardandoPublicacaoSelecionada.filter(d => getStatusPubLicitacaoDisplay(d) === "Sem prazo (PC 72)");
    const previousPublicacaoSemPrazoSelecionada = previousAguardandoPublicacaoSelecionada.filter(d => getStatusPubLicitacaoDisplay(d) === "Sem prazo (PC 72)").length;
    const pubVencidaArr = aguardandoPublicacaoSelecionada.filter(d => getStatusPubLicitacaoDisplay(d) === "Vencida");
    const previousPublicacaoVencidaSelecionada = previousAguardandoPublicacaoSelecionada.filter(d => getStatusPubLicitacaoDisplay(d) === "Vencida").length;
    const pubProx30Arr = aguardandoPublicacaoSelecionada.filter(d => getStatusPubLicitacaoDisplay(d) === "Próximos 30 dias");
    const previousPublicacaoProx30Selecionada = previousAguardandoPublicacaoSelecionada.filter(d => getStatusPubLicitacaoDisplay(d) === "Próximos 30 dias").length;
    const publicadasSelecionada = cascadeBase.filter(d => d.dt_pub_licitacao);
    const previousPublicadasSelecionada = previousSelecionada.filter(d => d.dt_pub_licitacao);
    const homologacaoPendenteSelecionada = publicadasSelecionada.filter(d => !d.dt_homolog_licitacao);
    const previousHomologacaoPendenteSelecionada = previousPublicadasSelecionada.filter(d => !d.dt_homolog_licitacao);
    const homologVencidaArr = homologacaoPendenteSelecionada.filter(d => getStatusHomologLicitacaoDisplay(d) === "Vencida");
    const previousHomologacaoVencidaSelecionada = previousHomologacaoPendenteSelecionada.filter(d => getStatusHomologLicitacaoDisplay(d) === "Vencida").length;
    const homologProx30Arr = homologacaoPendenteSelecionada.filter(d => getStatusHomologLicitacaoDisplay(d) === "Próximos 30 dias");
    const previousHomologacaoProx30Selecionada = previousHomologacaoPendenteSelecionada.filter(d => getStatusHomologLicitacaoDisplay(d) === "Próximos 30 dias").length;
    const publicacaoSemPrazoSelecionada = pubSemPrazoArr.length;
    const publicacaoVencidaSelecionada = pubVencidaArr.length;
    const publicacaoProx30Selecionada = pubProx30Arr.length;
    const homologacaoVencidaSelecionada = homologVencidaArr.length;
    const homologacaoProx30Selecionada = homologProx30Arr.length;

    const homologAte0106Arr = homologacaoPendenteSelecionada.filter(d =>
      d.prazo_homolog_licitacao instanceof Date && !isNaN(d.prazo_homolog_licitacao)
      && d.data_limite_licitacao_casa_civil instanceof Date && !isNaN(d.data_limite_licitacao_casa_civil)
      && d.prazo_homolog_licitacao.getTime() <= d.data_limite_licitacao_casa_civil.getTime()
    );
    const previousHomologAte0106 = previousHomologacaoPendenteSelecionada.filter(d =>
      d.prazo_homolog_licitacao instanceof Date && !isNaN(d.prazo_homolog_licitacao)
      && d.data_limite_licitacao_casa_civil instanceof Date && !isNaN(d.data_limite_licitacao_casa_civil)
      && d.prazo_homolog_licitacao.getTime() <= d.data_limite_licitacao_casa_civil.getTime()
    ).length;

    const cumprimentoCasaCivil = [
      { status: "Cumpriu o prazo", qtd: casaCivilSource.filter(d => d.status_regra_casa_civil === "Cumpriu o prazo").length, color: LICITACAO_CORES["Cumpriu o prazo"] },
      { status: "Pendente", qtd: casaCivilSource.filter(d => d.status_regra_casa_civil === "Pendente").length, color: LICITACAO_CORES["Pendente"] },
      { status: "Fora do escopo", qtd: casaCivilSource.filter(d => d.status_regra_casa_civil === "Fora do escopo").length, color: LICITACAO_CORES["Fora do escopo"] },
    ].filter(d => d.qtd > 0);

    container.append(metricGrid([
      { label: "Contratado - Normal", value: formatNumber(cascadeBase.length), topRight: formatCurrencyCompact(valorSelecionado), detail: "no recorte atual da licitação", delta: buildMetricDelta(cascadeBase.length, previousSelecionada.length), tone: "default" },
      { label: "Aguardando publicação", value: formatNumber(aguardandoPublicacaoSelecionada.length), topRight: formatCurrencyCompact(vlr(aguardandoPublicacaoSelecionada)), detail: formatPercent(cascadeBase.length > 0 ? aguardandoPublicacaoSelecionada.length / cascadeBase.length : 0) + " dos contratos em Contratado - Normal", delta: buildMetricDelta(aguardandoPublicacaoSelecionada.length, previousAguardandoPublicacaoSelecionada.length), tone: "gold" },
      { label: "Sem prazo (PC 72)", value: formatNumber(publicacaoSemPrazoSelecionada), topRight: formatCurrencyCompact(vlr(pubSemPrazoArr)), detail: "assinados antes de 21/10/2025", delta: buildMetricDelta(publicacaoSemPrazoSelecionada, previousPublicacaoSemPrazoSelecionada), tone: "default" },
      { label: "Publicação vencida", value: formatNumber(publicacaoVencidaSelecionada), topRight: formatCurrencyCompact(vlr(pubVencidaArr)), detail: "prazo de 60 dias após LAE", delta: buildMetricDelta(publicacaoVencidaSelecionada, previousPublicacaoVencidaSelecionada), tone: "red" },
      { label: "Publicação nos próximos 30 dias", value: formatNumber(publicacaoProx30Selecionada), topRight: formatCurrencyCompact(vlr(pubProx30Arr)), detail: "prazo de 60 dias após LAE", delta: buildMetricDelta(publicacaoProx30Selecionada, previousPublicacaoProx30Selecionada), tone: "gold" },
      { label: "Homologação vencida", value: formatNumber(homologacaoVencidaSelecionada), topRight: formatCurrencyCompact(vlr(homologVencidaArr)), detail: "prazo de 120 dias após publicação", delta: buildMetricDelta(homologacaoVencidaSelecionada, previousHomologacaoVencidaSelecionada), tone: "red" },
      { label: "Homologação nos próximos 30 dias", value: formatNumber(homologacaoProx30Selecionada), topRight: formatCurrencyCompact(vlr(homologProx30Arr)), detail: "prazo de 120 dias após publicação", delta: buildMetricDelta(homologacaoProx30Selecionada, previousHomologacaoProx30Selecionada), tone: "gold" },
      { label: "Homologação até 01/06/2026", value: formatNumber(homologAte0106Arr.length), topRight: formatCurrencyCompact(vlr(homologAte0106Arr)), detail: "prazo limite Casa Civil", delta: buildMetricDelta(homologAte0106Arr.length, previousHomologAte0106), tone: "blue" },
    ]));

    if (publicacaoVencidaSelecionada > 0 || publicacaoProx30Selecionada > 0 || homologacaoVencidaSelecionada > 0 || homologacaoProx30Selecionada > 0) {
      const alertEl = document.createElement("div");
      alertEl.className = "urgency-alert";
      alertEl.innerHTML = `
        <div class="urgency-alert__icon">⚠️</div>
        <div class="urgency-alert__body">
          <div class="urgency-alert__title">Atenção: licitações com prazo crítico</div>
          <div class="urgency-alert__text">
            ${publicacaoVencidaSelecionada > 0 ? `<strong>${formatNumber(publicacaoVencidaSelecionada)}</strong> contrato${publicacaoVencidaSelecionada > 1 ? "s" : ""} com <strong>publicação vencida</strong>. ` : ""}
            ${publicacaoProx30Selecionada > 0 ? `<strong>${formatNumber(publicacaoProx30Selecionada)}</strong> contrato${publicacaoProx30Selecionada > 1 ? "s" : ""} com publicação nos <strong>próximos 30 dias</strong>. ` : ""}
            ${homologacaoVencidaSelecionada > 0 ? `<strong>${formatNumber(homologacaoVencidaSelecionada)}</strong> contrato${homologacaoVencidaSelecionada > 1 ? "s" : ""} com <strong>homologação vencida</strong>. ` : ""}
            ${homologacaoProx30Selecionada > 0 ? `<strong>${formatNumber(homologacaoProx30Selecionada)}</strong> contrato${homologacaoProx30Selecionada > 1 ? "s" : ""} com homologação nos <strong>próximos 30 dias</strong>.` : ""}
          </div>
        </div>
      `;
      container.append(alertEl);
    }

    if (cumprimentoCasaCivil.length > 0) {
      const casaCivilChart = makeClickableChart(
        Plot.plot({
          marginLeft: 140,
          marginRight: 50,
          height: Math.max(160, cumprimentoCasaCivil.length * 44 + 36),
          style: { fontFamily: "var(--font-sans, IBM Plex Sans, sans-serif)", fontSize: 13 },
          x: { label: null, grid: false, axis: null },
          y: { label: null, domain: cumprimentoCasaCivil.map(d => d.status) },
          marks: [
            Plot.barX(cumprimentoCasaCivil, { x: "qtd", y: "status", fill: "color", rx: 6 }),
            Plot.text(cumprimentoCasaCivil, {
              x: "qtd",
              y: "status",
              text: d => formatNumber(d.qtd),
              dx: 6,
              textAnchor: "start",
              fontSize: 12,
              fill: "#5b6470",
            }),
          ],
        }),
        cumprimentoCasaCivil,
        "status",
        container.value.casaCivil
      );
      casaCivilChart.addEventListener("input", () => setCasaCivil(casaCivilChart.value));
      container.append(casaCivilChart);
    }

    if (cascadeBase.length === 0) {
      container.append(makeFlowElement("p", "casc-empty", "Nenhum contrato corresponde à seleção atual na análise de licitação."));
      return;
    }

    const aguardandoPublicacao = cascadeBase.filter(d => !d.dt_pub_licitacao);
    const publicadas = cascadeBase.filter(d => d.dt_pub_licitacao);
    container.append(
      makeFlowLevel(
        `${cascadeBase.length.toLocaleString("pt-BR")} contratos em Contratado - Normal`,
        "por etapa da publicação da licitação",
        [
          { label: "Aguardando publicação", qtd: aguardandoPublicacao.length, color: LICITACAO_CORES["Aguardando publicação"] },
          { label: "Publicada", qtd: publicadas.length, color: LICITACAO_CORES["Publicada"] },
        ],
        cascadeBase.length,
        { filterKey: "pub_etapa", selectedValue: container.value.flow.pub_etapa, onSelect: setFlow }
      )
    );

    if (aguardandoPublicacao.length > 0) {
      container.append(makeFlowConnector("publicação até 120 dias para contratos em Contratado - Normal"));
      container.append(
        makeFlowLevel(
          `${aguardandoPublicacao.length.toLocaleString("pt-BR")} contratos aguardando publicação`,
          "por urgência do prazo de publicação",
          LICITACAO_PRAZO_ORDER.map(label => ({
            label,
            qtd: aguardandoPublicacao.filter(d => getStatusPubLicitacaoDisplay(d) === label).length,
            color: LICITACAO_CORES[label],
          })),
          aguardandoPublicacao.length,
          { filterKey: "pub_prazo", selectedValue: container.value.flow.pub_prazo, onSelect: setFlow }
        )
      );
    }

    if (publicadas.length > 0) {
      const homologacaoPendente = publicadas.filter(d => !d.dt_homolog_licitacao);
      const homologadas = publicadas.filter(d => d.dt_homolog_licitacao);

      container.append(makeFlowConnector("homologação até 120 dias após a publicação"));
      container.append(
        makeFlowLevel(
          `${publicadas.length.toLocaleString("pt-BR")} contratos com licitação publicada`,
          "por etapa da homologação",
          [
            { label: "Homologação pendente", qtd: homologacaoPendente.length, color: LICITACAO_CORES["Homologação pendente"] },
            { label: "Homologada", qtd: homologadas.length, color: LICITACAO_CORES["Homologada"] },
          ],
          publicadas.length,
          { filterKey: "homolog_etapa", selectedValue: container.value.flow.homolog_etapa, onSelect: setFlow }
        )
      );

      if (homologacaoPendente.length > 0) {
        container.append(makeFlowConnector("homologação pendente por urgência do prazo"));
        container.append(
          makeFlowLevel(
            `${homologacaoPendente.length.toLocaleString("pt-BR")} contratos aguardando homologação`,
            "por urgência do prazo de homologação",
            LICITACAO_PRAZO_ORDER.map(label => ({
              label,
              qtd: homologacaoPendente.filter(d => getStatusHomologLicitacaoDisplay(d) === label).length,
              color: LICITACAO_CORES[label],
            })),
            homologacaoPendente.length,
            { filterKey: "homolog_prazo", selectedValue: container.value.flow.homolog_prazo, onSelect: setFlow }
          )
        );
      }
    }
  }

  render();
  return container;
}

function matchesCasaCivilSelection(d, selection = null) {
  return selection == null || d.status_regra_casa_civil === selection;
}

function matchesInicioObraSelection(d, selection = null) {
  return selection == null || d.status_inicio_obra === selection;
}

function normalizeDrillSelection(selection) {
  if (selection == null) return null;
  if (typeof selection === "string") return selection;
  if (Array.isArray(selection)) return selection.length === 1 ? selection[0] : null;
  if (typeof selection === "object") {
    if (typeof selection.value === "string") return selection.value;
    if (typeof selection.group === "string") return selection.group;
  }
  return null;
}
```

```js
// ── Drill field config (depende apenas dos filtros cascade, sem circular dependency)
const secretariaDrillField = secretariaSelecionada.length === 1 ? "modalidade" : "secretaria";
const secretariaDrillLabel = secretariaDrillField === "secretaria" ? "Secretaria" : "Modalidade";
const secretariaDrillMarginLeft = secretariaDrillField === "secretaria" ? 90 : 240;
```

```js
// ── previousBaseData (depende apenas dos filtros cascade, sem dependência de selectedCharts)
const previousBaseData = previousRawData.filter(d =>
  fConvenio.some(row => row.num_convenio === d.num_convenio && row.cod_tci === d.cod_tci) &&
  matchesSecretariaFilter(d) &&
  matchesModalidadeFilter(d) &&
  matchesAnoFilter(d)
);
```

```js
const selectedCharts = view(makeCrossFilteredCharts(
  baseData,
  previousBaseData,
  secretariaDrillField,
  secretariaDrillLabel,
  secretariaDrillMarginLeft
));
```

```js
// ── data final: baseData + seleção dos gráficos (cross-filtered)
const selectedSituacao = selectedCharts?.situacao ?? null;
const selectedSuspensiva = selectedCharts?.suspensiva ?? null;
const secretariaDrillSelection = normalizeDrillSelection(selectedCharts?.drill ?? null);

const preGeoData = baseData.filter(d =>
  (selectedSituacao == null || d.situacao === selectedSituacao) &&
  (selectedSuspensiva == null || d.situacao_suspensiva === selectedSuspensiva) &&
  (secretariaDrillSelection == null || d[secretariaDrillField] === secretariaDrillSelection)
);

const previousData = previousBaseData.filter(d =>
  (selectedSituacao == null || d.situacao === selectedSituacao) &&
  (selectedSuspensiva == null || d.situacao_suspensiva === selectedSuspensiva) &&
  (secretariaDrillSelection == null || d[secretariaDrillField] === secretariaDrillSelection)
);
```

<section class="section-block section-block--geo">
<header class="section-block__header">
<span class="section-block__eyebrow">Recorte territorial</span>
<h2>Distribuição Territorial <span class="rule-tooltip"><button class="rule-tooltip__trigger" aria-label="Regra">?</button><span class="rule-tooltip__content">Recorte territorial de todos os contratos atualmente visíveis no painel.<ul><li><strong>Região</strong> — considera todos os contratos após os filtros do topo e dos gráficos gerais</li><li><strong>UF</strong> — abre quando uma região é selecionada</li><li>As seleções passam a valer para os blocos analíticos seguintes</li></ul></span></span></h2>
<p>Clique em uma região para abrir os estados; esse recorte passa a valer para os blocos abaixo.</p>
</header>

<div class="section-block__body">
<div class="card card--chapter card--chapter-geo">

```js
const selectedGeo = view(makeGeoCascade(preGeoData));
```

</div>
</div>
</section>

```js
const geoScopedData = preGeoData.filter(d => matchesGeoSelection(d, selectedGeo));
const geoScopedPreviousData = previousData.filter(d => matchesGeoSelection(d, selectedGeo));
```

<section class="section-block section-block--suspensiva">
<header class="section-block__header">
<span class="section-block__eyebrow">Análise de contratos</span>
<h2>Análise de Suspensivas <span class="rule-tooltip"><button class="rule-tooltip__trigger" aria-label="Regra">?</button><span class="rule-tooltip__content">Cascata dos contratos com suspensiva ativa, classificados por urgência do vencimento.<ul><li><strong>Vencida</strong> — data de vencimento da suspensiva já passou</li><li><strong>Próximos 30 dias</strong> — vence em até 30 dias corridos</li><li><strong>31–90 dias</strong> — vence entre 31 e 90 dias</li><li><strong>Mais de 90 dias</strong> — vence após 90 dias</li><li><strong>Sem data</strong> — sem data de vencimento registrada</li></ul></span></span></h2>
<p>Quebra por etapas com foco na urgência de vencimento das suspensivas ativas.</p>
</header>

<div class="section-block__body">
<div class="card card--chapter card--chapter-suspensiva card--suspensiva-analysis">

```js
const comSuspData = geoScopedData.filter(d => d.situacao === "Contratado - Suspensiva");
const pendentes = comSuspData.filter(d => !d.dt_retirada_suspensiva);
const vencida = pendentes.filter(d => d.urgencia_suspensiva === "Vencida").length;
const prox30  = pendentes.filter(d => d.urgencia_suspensiva === "Próximos 30 dias").length;

if (vencida > 0 || prox30 > 0) {
  const alertEl = document.createElement("div");
  alertEl.className = "urgency-alert";
  alertEl.innerHTML = `
    <div class="urgency-alert__icon">⚠️</div>
    <div class="urgency-alert__body">
      <div class="urgency-alert__title">Atenção: suspensivas com prazo crítico</div>
      <div class="urgency-alert__text">
        ${vencida > 0 ? `<strong>${formatNumber(vencida)}</strong> contrato${vencida > 1 ? "s" : ""} com suspensiva <strong>já vencida</strong>.` : ""}
        ${prox30 > 0 ? ` <strong>${formatNumber(prox30)}</strong> contrato${prox30 > 1 ? "s" : ""} vencem nos <strong>próximos 30 dias</strong>.` : ""}
      </div>
    </div>
  `;
display(alertEl);
}

const tableRowsForCharts = Object.assign(document.createElement("div"), {value: null});

const selectedCascade = view(cascadeChart(geoScopedData, tableRowsForCharts));
```

</div>

<div class="card card--chapter card--chapter-suspensiva">
<h2>Documentos da suspensiva com pendência <span class="rule-tooltip"><button class="rule-tooltip__trigger" aria-label="Regra">?</button><span class="rule-tooltip__content">Contagem de contratos com cada documento pendente, a partir do detalhamento por documento do PBI Caixa.<ul><li><strong>Documentos apresentados</strong> — pendente quando o item está como "Não Apresentado"</li><li><strong>Documentos não apresentados</strong> — pendente quando o item está como "NÃO"</li></ul>Cobre apenas contratos com detalhamento de documentos no recorte atual.</span></span></h2>
<p>Clique em uma barra para filtrar a Base de Dados pelos contratos com aquele documento pendente.</p>

```js
const docScope = geoScopedData.filter(d => d.tipo_doc_suspensiva);
const docPendChart = Object.values(DOC_SUSPENSIVA_LABELS)
  .map(label => ({ doc: label, qtd: docScope.filter(d => d.docs_suspensiva_pendentes.includes(label)).length }))
  .filter(d => d.qtd > 0)
  .sort((a, b) => b.qtd - a.qtd);

const docPendInput = docPendChart.length
  ? makeClickableChart(
      Plot.plot({
        marginLeft: 210, marginRight: 50,
        height: Math.max(140, docPendChart.length * 34 + 36),
        style: { fontFamily: "var(--font-sans, IBM Plex Sans, sans-serif)", fontSize: 13 },
        x: { label: null, grid: false, axis: null },
        y: { label: null, domain: docPendChart.map(d => d.doc) },
        marks: [
          Plot.barX(docPendChart, { x: "qtd", y: "doc", fill: "#e07b39", rx: 6 }),
          Plot.text(docPendChart, { x: "qtd", y: "doc", text: d => formatNumber(d.qtd), dx: 6, textAnchor: "start", fontSize: 12, fill: "#5b6470" }),
        ],
      }),
      docPendChart, "doc"
    )
  : Object.assign(html`<p class="casc-empty">Sem detalhamento de documentos no recorte atual.</p>`, { value: null });

const selectedDocSuspensiva = view(docPendInput);
```

</div>
</div>
</section>

<section class="section-block section-block--licitacao">
<header class="section-block__header">
<span class="section-block__eyebrow">Marco licitatório</span>
<h2>Análise de Licitação <span class="rule-tooltip"><button class="rule-tooltip__trigger" aria-label="Regra">?</button><span class="rule-tooltip__content">Monitoramento dos prazos de licitação para contratos com situação de contrato (SACI) igual a <strong>Contratado - Normal</strong>.<ul><li><strong>Base do bloco</strong> — considera apenas contratos em <strong>Contratado - Normal</strong></li><li><strong>Exceção PC 72</strong> — contratos assinados antes de <strong>21/10/2025</strong> aparecem como <strong>Sem prazo (PC 72)</strong> na publicação</li><li><strong>Sem prazo calculado</strong> — contratos sem publicação e sem classificação de prazo calculada na base</li><li><strong>Prazo de publicação</strong> — até 120 dias corridos conforme a regra calculada da base, exceto os casos da PC 72</li><li><strong>Prazo de homologação</strong> — até 120 dias corridos após a publicação da licitação</li><li><strong>Regra Casa Civil</strong> — publicação, homologação e ordem de serviço devem ocorrer até 01/06/2026</li></ul>Classificação de prazo:<ul><li><strong>Vencida</strong> — prazo já expirou</li><li><strong>Próximos 30 dias</strong> — vence em até 30 dias</li><li><strong>No prazo</strong> — mais de 30 dias restantes</li><li><strong>Sem prazo (PC 72)</strong> — assinatura anterior a 21/10/2025</li><li><strong>Sem prazo calculado</strong> — sem status calculado na base</li></ul></span></span></h2>
<p>Prazos de publicação e homologação para contratos em <strong>Contratado - Normal</strong>, incluindo a exceção da PC 72.</p>
</header>

<div class="section-block__body">
<div class="card card--chapter card--chapter-licitacao card--licitacao-analysis">

<div class="context-action-row">

```js
display(createReferenceImageButton({
  label: "Ver fluxo PC 32",
  title: "Fluxo de prazos — Portaria Conjunta 32/2024",
  imageUrl: fluxoPc32ImageUrl,
  caption: "Referência visual do fluxo de prazos do termo de compromisso do Novo PAC, da condição suspensiva até a prestação de contas.",
}));
```

</div>

```js
const selectedLicitacaoState = view(renderLicitacaoExplorer(geoScopedData, geoScopedPreviousData));
```

</div>
</div>
</section>

<section class="section-block section-block--obra">
<header class="section-block__header">
<span class="section-block__eyebrow">Execução física</span>
<h2>Análise de Início da Obra <span class="rule-tooltip"><button class="rule-tooltip__trigger" aria-label="Regra">?</button><span class="rule-tooltip__content">Monitoramento do prazo para início da obra após a emissão da AIO (Autorização de Início de Obra).<ul><li><strong>Prazo</strong> — 10 dias úteis após a data de AIO</li><li><strong>Iniciada no prazo</strong> — obra iniciada dentro do prazo</li><li><strong>Iniciada em atraso</strong> — obra iniciada após o prazo</li><li><strong>Próximos 10 dias úteis</strong> — prazo vence em até 10 dias úteis</li><li><strong>Prazo vencido</strong> — prazo expirou sem início da obra</li><li><strong>No prazo</strong> — mais de 10 dias úteis restantes</li></ul></span></span></h2>
<p>Prazo após AIO, com destaque para obras iniciadas em atraso e contratos em janela crítica.</p>
</header>

<div class="section-block__body">
<div class="card card--chapter card--chapter-obra card--inicio-obra-analysis">

```js
const inicioObraBase = geoScopedData.filter(d => d.dt_aio && d.situacao !== "Cancelado ou Distratado");
const inicioPrazoVencido = inicioObraBase.filter(d => d.status_inicio_obra === "Prazo vencido").length;
const inicioProx10 = inicioObraBase.filter(d => d.status_inicio_obra === "Próximos 10 dias úteis").length;
const inicioNoPrazo = inicioObraBase.filter(d => d.status_inicio_obra === "No prazo").length;
const iniciadaNoPrazo = inicioObraBase.filter(d => d.status_inicio_obra === "Iniciada no prazo").length;
const iniciadaEmAtraso = inicioObraBase.filter(d => d.status_inicio_obra === "Iniciada em atraso").length;
const previousInicioObraBase = geoScopedPreviousData.filter(d => d.dt_aio && d.situacao !== "Cancelado ou Distratado");
const previousInicioPrazoVencido = previousInicioObraBase.filter(d => d.status_inicio_obra === "Prazo vencido").length;
const previousInicioProx10 = previousInicioObraBase.filter(d => d.status_inicio_obra === "Próximos 10 dias úteis").length;
const previousInicioNoPrazo = previousInicioObraBase.filter(d => d.status_inicio_obra === "No prazo").length;
const previousIniciadaNoPrazo = previousInicioObraBase.filter(d => d.status_inicio_obra === "Iniciada no prazo").length;
const previousIniciadaEmAtraso = previousInicioObraBase.filter(d => d.status_inicio_obra === "Iniciada em atraso").length;
const inicioObraChart = [
  { status: "Iniciada no prazo", qtd: iniciadaNoPrazo, color: INICIO_OBRA_CORES["Iniciada no prazo"] },
  { status: "Iniciada em atraso", qtd: iniciadaEmAtraso, color: INICIO_OBRA_CORES["Iniciada em atraso"] },
  { status: "No prazo", qtd: inicioNoPrazo, color: INICIO_OBRA_CORES["No prazo"] },
  { status: "Próximos 10 dias úteis", qtd: inicioProx10, color: INICIO_OBRA_CORES["Próximos 10 dias úteis"] },
  { status: "Prazo vencido", qtd: inicioPrazoVencido, color: INICIO_OBRA_CORES["Prazo vencido"] },
].filter(d => d.qtd > 0);
```

```js
const selectedInicioObra = view(makeClickableChart(
  Plot.plot({
    marginLeft: 160,
    marginRight: 50,
    height: Math.max(170, inicioObraChart.length * 44 + 36),
    style: { fontFamily: "var(--font-sans, IBM Plex Sans, sans-serif)", fontSize: 13 },
    x: { label: null, grid: false, axis: null },
    y: { label: null, domain: inicioObraChart.map(d => d.status) },
    marks: [
      Plot.barX(inicioObraChart, {
        x: "qtd",
        y: "status",
        fill: "color",
        rx: 6,
      }),
      Plot.text(inicioObraChart, {
        x: "qtd",
        y: "status",
        text: d => formatNumber(d.qtd),
        dx: 6,
        textAnchor: "start",
        fontSize: 12,
        fill: "#5b6470",
      }),
    ],
  }),
  inicioObraChart, "status"
));
```

```js
const vlrObra = arr => arr.reduce((s, d) => s + d.vlr_repasse, 0);
const filterObraStatus = (rows, status) => rows.filter(d => d.status_inicio_obra === status);
const inicioObraSelecionada = inicioObraBase.filter(d => matchesInicioObraSelection(d, selectedInicioObra));
const previousInicioObraSelecionada = previousInicioObraBase.filter(d => matchesInicioObraSelection(d, selectedInicioObra));
const iniciadaNoPrazoArr = filterObraStatus(inicioObraSelecionada, "Iniciada no prazo");
const previousIniciadaNoPrazoArr = filterObraStatus(previousInicioObraSelecionada, "Iniciada no prazo");
const iniciadaEmAtrasoArr = filterObraStatus(inicioObraSelecionada, "Iniciada em atraso");
const previousIniciadaEmAtrasoArr = filterObraStatus(previousInicioObraSelecionada, "Iniciada em atraso");
const prazoVencidoArr = filterObraStatus(inicioObraSelecionada, "Prazo vencido");
const previousPrazoVencidoArr = filterObraStatus(previousInicioObraSelecionada, "Prazo vencido");
const prox10Arr = filterObraStatus(inicioObraSelecionada, "Próximos 10 dias úteis");
const previousProx10Arr = filterObraStatus(previousInicioObraSelecionada, "Próximos 10 dias úteis");
const noPrazoArr = filterObraStatus(inicioObraSelecionada, "No prazo");
const previousNoPrazoArr = filterObraStatus(previousInicioObraSelecionada, "No prazo");

display(metricGrid([
  { label: "Com AIO", value: formatNumber(inicioObraSelecionada.length), topRight: formatCurrencyCompact(vlrObra(inicioObraSelecionada)), delta: buildMetricDelta(inicioObraSelecionada.length, previousInicioObraSelecionada.length), tone: "default" },
  { label: "Iniciada no prazo", value: formatNumber(iniciadaNoPrazoArr.length), topRight: formatCurrencyCompact(vlrObra(iniciadaNoPrazoArr)), delta: buildMetricDelta(iniciadaNoPrazoArr.length, previousIniciadaNoPrazoArr.length), tone: "green" },
  { label: "Iniciada em atraso", value: formatNumber(iniciadaEmAtrasoArr.length), topRight: formatCurrencyCompact(vlrObra(iniciadaEmAtrasoArr)), delta: buildMetricDelta(iniciadaEmAtrasoArr.length, previousIniciadaEmAtrasoArr.length), tone: "red" },
  { label: "Prazo vencido", value: formatNumber(prazoVencidoArr.length), topRight: formatCurrencyCompact(vlrObra(prazoVencidoArr)), delta: buildMetricDelta(prazoVencidoArr.length, previousPrazoVencidoArr.length), tone: "red" },
  { label: "Próximos 10 dias úteis", value: formatNumber(prox10Arr.length), topRight: formatCurrencyCompact(vlrObra(prox10Arr)), delta: buildMetricDelta(prox10Arr.length, previousProx10Arr.length), tone: "gold" },
  { label: "No prazo", value: formatNumber(noPrazoArr.length), topRight: formatCurrencyCompact(vlrObra(noPrazoArr)), delta: buildMetricDelta(noPrazoArr.length, previousNoPrazoArr.length), tone: "blue" },
]));
```

```js
if (prazoVencidoArr.length > 0 || prox10Arr.length > 0) {
  const alertEl = document.createElement("div");
  alertEl.className = "urgency-alert";
  alertEl.innerHTML = `
    <div class="urgency-alert__icon">⚠️</div>
    <div class="urgency-alert__body">
      <div class="urgency-alert__title">Atenção: início de obra com prazo crítico</div>
      <div class="urgency-alert__text">
        ${prazoVencidoArr.length > 0 ? `<strong>${formatNumber(prazoVencidoArr.length)}</strong> contrato${prazoVencidoArr.length > 1 ? "s" : ""} com <strong>prazo vencido</strong> para início da obra. ` : ""}
        ${prox10Arr.length > 0 ? `<strong>${formatNumber(prox10Arr.length)}</strong> contrato${prox10Arr.length > 1 ? "s" : ""} nos <strong>próximos 10 dias úteis</strong> para início da obra.` : ""}
      </div>
    </div>
  `;
  display(alertEl);
}
```

</div>
</div>
</section>

<section class="section-block section-block--dados">
<header class="section-block__header">
<span class="section-block__eyebrow">Exploração detalhada</span>
<h2>Base de Dados</h2>
<p>Camada final de consulta e exportação, já respeitando todos os filtros e seleções aplicados nos blocos anteriores.</p>
</header>

<div class="section-block__body">
<div class="table-shell table-shell--terminal">

```js
const hasCascadeSelection = Object.values(selectedCascade ?? {})
  .some(v => Array.isArray(v) ? v.length > 0 : Boolean(v));
const selectedLicitacao = selectedLicitacaoState?.flow ?? {};
const selectedCasaCivil = selectedLicitacaoState?.casaCivil ?? null;
const hasLicitacaoSelection = Object.values(selectedLicitacao).some(Boolean) || selectedCasaCivil != null;
const tableData = geoScopedData.filter(d =>
  (!hasCascadeSelection || matchesCascadeSelection(d, selectedCascade)) &&
  (!hasLicitacaoSelection || isContratoNormal(d)) &&
  (!hasLicitacaoSelection || matchesLicitacaoSelection(d, selectedLicitacao)) &&
  (!hasLicitacaoSelection || matchesCasaCivilSelection(d, selectedCasaCivil)) &&
  (!selectedDocSuspensiva || (d.docs_suspensiva_pendentes && d.docs_suspensiva_pendentes.includes(selectedDocSuspensiva))) &&
  matchesInicioObraSelection(d, selectedInicioObra)
);

const exportColumns = [
  "_diff_label", "num_convenio", "cod_tci", "secretaria", "regiao", "uf", "municipio", "proponente", "fase", "modalidade",
  "situacao_contrato_tci", "situacao_suspensiva_pbi", "dt_assinatura", "pos_72", "dt_vencimento_suspensiva", "mes_ano_vencimento_suspensiva",
  "dt_retirada_suspensiva", "perspectiva_de_retirada_da_suspensiva", "dt_lae", "dt_lae_mais_60", "dt_lae_mais_60_mais_120", "data_limite_licitacao_casa_civil", "status_regra_casa_civil", "prazo_pub_licitacao", "status_pub_licitacao",
  "dt_pub_licitacao", "prazo_homolog_licitacao", "status_homolog_licitacao", "dt_homolog_licitacao",
  "dt_vrpl", "dt_aio", "prazo_inicio_obra", "status_inicio_obra", "dt_inicio_obra", "vlr_repasse",
  "tipo_doc_suspensiva", "docs_suspensiva_resumo",
  "doc_titularidade", "doc_viabilidade_terreno", "doc_sondagem", "doc_orcamento", "doc_projetos_implantacao",
  "doc_projetos_complementares", "doc_ambiental", "doc_vigilancia_sanitaria", "doc_bombeiros", "doc_trabalho_social",
];
const exportHeaders = {
  _diff_label: "Alteração",
  num_convenio: "Convênio",
  cod_tci: "SACI",
  secretaria: "Secretaria",
  regiao: "Região",
  uf: "UF",
  municipio: "Município",
  proponente: "Proponente (SACI)",
  fase: "Fase",
  modalidade: "Modalidade",
  situacao_contrato_tci: "Situação Contrato (SACI)",
  situacao_suspensiva_pbi: "Situação Suspensiva (PBI)",
  dt_vencimento_suspensiva: "Venc. Suspensiva (PBI)",
  mes_ano_vencimento_suspensiva: "Mês/Ano Venc. Suspensiva",
  dt_retirada_suspensiva: "Retirada Suspensiva (TGOV)",
  perspectiva_de_retirada_da_suspensiva: "Perspectiva de Retirada da Suspensiva",
  dt_assinatura: "Assinatura (SACI)",
  pos_72: "Pos-72",
  dt_lae: "LAE (TDB)",
  dt_lae_mais_60: "Publ. Licit. = LAE + 60d +60d (CALC)",
  dt_lae_mais_60_mais_120: "Fim Licit. = (LAE + 60d +60d)+ 120 + 60 (CALC)",
  data_limite_licitacao_casa_civil: "Data Limite Licitação (CONST)",
  status_regra_casa_civil: "Cumprimento Regra Casa Civil (CALC)",
  prazo_pub_licitacao: "Prazo Publicação (CALC)",
  status_pub_licitacao: "Status Publicação (CALC)",
  dt_pub_licitacao: "Pub. Licitação (TGOV)",
  prazo_homolog_licitacao: "Prazo Homolog. (CALC)",
  status_homolog_licitacao: "Status Homolog. (CALC)",
  dt_homolog_licitacao: "Homolog. Licitação (TGOV)",
  dt_vrpl: "VRPL (TDB)",
  dt_aio: "AIO (TDB)",
  prazo_inicio_obra: "Prazo Início Obra (CALC)",
  status_inicio_obra: "Status Início Obra (CALC)",
  dt_inicio_obra: "Início Obra (SACI)",
  vlr_repasse: "Repasse (SACI)",
  tipo_doc_suspensiva: "Tipo Doc. Suspensiva",
  docs_suspensiva_resumo: "Documentos Pendentes (Suspensiva)",
  doc_titularidade: "Doc.: Titularidade",
  doc_viabilidade_terreno: "Doc.: Viabilidade do Terreno",
  doc_sondagem: "Doc.: Estudos de Sondagem",
  doc_orcamento: "Doc.: Orçamento",
  doc_projetos_implantacao: "Doc.: Projetos de Implantação",
  doc_projetos_complementares: "Doc.: Projetos Complementares",
  doc_ambiental: "Doc.: Órgão Ambiental",
  doc_vigilancia_sanitaria: "Doc.: Vigilância Sanitária",
  doc_bombeiros: "Doc.: Bombeiros",
  doc_trabalho_social: "Doc.: Trabalho Social",
};

const defaultSelectedColumns = [
  "num_convenio",
  "cod_tci",
  "secretaria",
  "uf",
  "municipio",
  "proponente",
  "modalidade",
  "situacao_contrato_tci",
  "situacao_suspensiva_pbi",
  "dt_assinatura",
  "pos_72",
  "dt_vencimento_suspensiva",
  "mes_ano_vencimento_suspensiva",
  "dt_retirada_suspensiva",
  "perspectiva_de_retirada_da_suspensiva",
  "dt_lae",
  "dt_lae_mais_60",
  "dt_lae_mais_60_mais_120",
  "data_limite_licitacao_casa_civil",
  "status_regra_casa_civil",
  "status_pub_licitacao",
  "dt_pub_licitacao",
  "status_homolog_licitacao",
  "dt_homolog_licitacao",
  "dt_vrpl",
  "dt_aio",
  "status_inicio_obra",
  "dt_inicio_obra",
  "vlr_repasse",
];

function makeColumnPicker(columns, headers) {
  const defaultColumns = columns.filter((col) => defaultSelectedColumns.includes(col));
  const selected = new Set(defaultColumns);
  const wrap = Object.assign(document.createElement("div"), { value: [...defaultColumns] });
  wrap.className = "col-picker";

  const toggle = document.createElement("button");
  toggle.type = "button";
  toggle.className = "col-picker__toggle";
  toggle.textContent = "Personalizar colunas";

  const panel = document.createElement("div");
  panel.className = "col-picker__panel";
  panel.hidden = true;

  const actions = document.createElement("div");
  actions.className = "col-picker__actions";
  const selectAll = document.createElement("button");
  selectAll.type = "button";
  selectAll.className = "col-picker__action-btn";
  selectAll.textContent = "Selecionar todas";
  const clearAll = document.createElement("button");
  clearAll.type = "button";
  clearAll.className = "col-picker__action-btn";
  clearAll.textContent = "Limpar todas";
  actions.append(selectAll, clearAll);

  const grid = document.createElement("div");
  grid.className = "col-picker__grid";

  const chips = columns.map(col => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = selected.has(col) ? "col-picker__chip is-active" : "col-picker__chip";
    chip.textContent = headers[col] ?? col;
    chip.dataset.col = col;
    chip.addEventListener("click", () => {
      if (selected.has(col)) { selected.delete(col); chip.classList.remove("is-active"); }
      else { selected.add(col); chip.classList.add("is-active"); }
      emit();
    });
    return chip;
  });
  grid.append(...chips);

  selectAll.addEventListener("click", () => {
    columns.forEach(col => selected.add(col));
    chips.forEach(c => c.classList.add("is-active"));
    emit();
  });
  clearAll.addEventListener("click", () => {
    selected.clear();
    chips.forEach(c => c.classList.remove("is-active"));
    emit();
  });

  toggle.addEventListener("click", () => {
    panel.hidden = !panel.hidden;
    toggle.classList.toggle("is-open");
  });

function emit() {
  wrap.value = columns.filter(c => selected.has(c));
    wrap.dispatchEvent(new Event("input", { bubbles: true }));
  }

  panel.append(actions, grid);
  wrap.append(toggle, panel);
  return wrap;
}

const selectedColumns = view(makeColumnPicker(exportColumns, exportHeaders));
```

```js
const activeColumns = selectedColumns;
```

```js
const dateCol = d => d ? formatDate(d) : "—";
const tciLinkCol = d => d
  ? html`<a href=${`https://saci.cidades.gov.br/contratos/${d}`} target="_blank" rel="noopener noreferrer">${d}</a>`
  : "—";

const diffFieldLabels = {
  situacao: "Situação", situacao_contrato_tci: "Sit. Contrato SACI", situacao_suspensiva_pbi: "Sit. Suspensiva PBI", status_suspensiva: "Status Suspensiva",
  fase_atual: "Fase Atual", dt_retirada_suspensiva: "Ret. Suspensiva", dt_lae: "LAE",
  dt_pub_licitacao: "Pub. Licitação", dt_homolog_licitacao: "Homolog.", dt_vrpl: "VRPL",
  dt_aio: "AIO", dt_inicio_obra: "Início Obra", vlr_repasse: "Repasse",
  status_pub_licitacao: "Status Pub.", status_homolog_licitacao: "Status Homolog.",
  status_inicio_obra: "Status Início Obra", status_regra_casa_civil: "Regra Casa Civil",
  urgencia_suspensiva: "Urgência Susp.",
};

function diffCol(value) {
  if (!value || value === "Sem alteração") return "—";
  const cls = value === "Novo" ? "diff-pill--novo" : "diff-pill--alterado";
  const label = diffFieldLabels[value] || value;
  const el = html`<span class="diff-pill ${cls}">${label}</span>`;
  return el;
}
display(renderBaseDataTable({
  rows: tableData,
  columns: activeColumns,
  headers: {
    _diff_label: "Alteração", num_convenio: "Convênio", cod_tci: "SACI", secretaria: "Secretaria",
    regiao: "Região", uf: "UF", municipio: "Município", proponente: "Proponente (SACI)",
    fase: "Fase", modalidade: "Modalidade", situacao_contrato_tci: "Situação Contrato (SACI)",
    situacao_suspensiva_pbi: "Situação Suspensiva (PBI)",
    dt_vencimento_suspensiva: "Venc. Suspensiva (PBI)", mes_ano_vencimento_suspensiva: "Mês/Ano Venc. Susp.", dt_retirada_suspensiva: "Retirada Suspensiva (TGOV)",
    perspectiva_de_retirada_da_suspensiva: "Perspectiva de Retirada da Suspensiva",
    dt_assinatura: "Assinatura (SACI)", pos_72: "Pos-72", dt_lae: "LAE (TDB)", dt_lae_mais_60: "Publ. Licit. = LAE + 60d +60d (CALC)", dt_lae_mais_60_mais_120: "Fim Licit. = (LAE + 60d +60d)+ 120 + 60 (CALC)", data_limite_licitacao_casa_civil: "Data Limite Licitação (CONST)", status_regra_casa_civil: "Cumprimento Regra Casa Civil (CALC)", prazo_pub_licitacao: "Prazo Publicação (CALC)",
    status_pub_licitacao: "Status Publicação (CALC)", dt_pub_licitacao: "Pub. Licitação (TGOV)",
    prazo_homolog_licitacao: "Prazo Homolog. (CALC)", status_homolog_licitacao: "Status Homolog. (CALC)",
    dt_homolog_licitacao: "Homolog. Licitação (TGOV)", dt_vrpl: "VRPL (TDB)", dt_aio: "AIO (TDB)", prazo_inicio_obra: "Prazo Início Obra (CALC)", status_inicio_obra: "Status Início Obra (CALC)",
    dt_inicio_obra: "Início Obra (SACI)", vlr_repasse: "Repasse (SACI)",
    tipo_doc_suspensiva: "Tipo Doc. Suspensiva", docs_suspensiva_resumo: "Documentos Pendentes (Suspensiva)",
    doc_titularidade: "Doc.: Titularidade", doc_viabilidade_terreno: "Doc.: Viabilidade do Terreno",
    doc_sondagem: "Doc.: Estudos de Sondagem", doc_orcamento: "Doc.: Orçamento",
    doc_projetos_implantacao: "Doc.: Projetos de Implantação", doc_projetos_complementares: "Doc.: Projetos Complementares",
    doc_ambiental: "Doc.: Órgão Ambiental", doc_vigilancia_sanitaria: "Doc.: Vigilância Sanitária",
    doc_bombeiros: "Doc.: Bombeiros", doc_trabalho_social: "Doc.: Trabalho Social",
  },
  formatters: {
    _diff_label: diffCol,
    cod_tci: tciLinkCol,
    vlr_repasse: d => d.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }),
    dt_assinatura: dateCol, dt_lae: dateCol, dt_lae_mais_60: dateCol, dt_lae_mais_60_mais_120: dateCol, data_limite_licitacao_casa_civil: dateCol, prazo_pub_licitacao: dateCol, dt_pub_licitacao: dateCol,
    prazo_homolog_licitacao: dateCol, prazo_inicio_obra: dateCol,
    dt_homolog_licitacao: dateCol, dt_vrpl: dateCol, dt_aio: dateCol,
    dt_inicio_obra: dateCol, dt_vencimento_suspensiva: dateCol, dt_retirada_suspensiva: dateCol,
    mes_ano_vencimento_suspensiva: d => d instanceof Date && !isNaN(d)
      ? `${String(d.getMonth() + 1).padStart(2, "0")}/${d.getFullYear()}`
      : "—",
  },
  invalidation,
  exportFilePrefix: "pc32-tabela-filtrada",
  onFilteredRowsChange(rows) {
    tableRowsForCharts.value = rows;
    tableRowsForCharts.dispatchEvent(new Event("input", {bubbles: true}));
  },
}));
```

</div>
</div>
</section>
