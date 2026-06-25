---
title: Painel Legado OGU - Obras Migradas
toc: false
---

```js
import * as Plot from "@observablehq/plot";
import {html} from "htl";
import {dsvFormat} from "d3-dsv";
import {renderBaseDataTable} from "./components/base-data-table.js";
import {metricGrid} from "./components/cards.js";
import {parseDate, formatNumber, formatCurrencyCompact, formatPercent, formatDate} from "./lib/formatters.js";
import {
  PALETTE,
  SITUACAO_OBRA_CORES, SITUACAO_OBRA_ORDER,
  TIPO_OPERACAO_CORES, TIPO_OPERACAO_ORDER,
  FAIXA_FISICA_CORES, FAIXA_FISICA_ORDER,
  REGIAO_ORDER, getRegiaoColor, getUfColor, getMunicipioColor, regiaoDaUf,
} from "./lib/theme.js";
import {hexToRgba} from "./lib/dom-helpers.js";

const rawText = await FileAttachment("data/base_legado.csv").text();
const dsv = dsvFormat(";");

function faixaFisica(pct) {
  if (pct == null || Number.isNaN(pct)) return "Sem dado";
  if (pct <= 0) return "0%";
  if (pct < 26) return "1–25%";
  if (pct < 51) return "26–50%";
  if (pct < 76) return "51–75%";
  if (pct < 100) return "76–99%";
  return "100%";
}

function parseLegadoRow(d) {
  const uf = (d.uf || "").trim().toUpperCase();
  const pct = d.pct_fisico === "" || d.pct_fisico == null ? null : +d.pct_fisico;
  return {
    ativo: d.ativo || "",
    tipo_operacao: d.tipo_operacao || "Não informado",
    proposta: d.proposta || "",
    operacao: d.operacao || "",
    dv: d.dv || "",
    instrumento: d.instrumento || "",
    repassador: d.repassador || "Não informado",
    uf,
    regiao: regiaoDaUf(uf),
    recebedor: d.recebedor || "",
    ente: d.ente || "",
    municipio: d.municipio || "",
    objeto: d.objeto || "",
    modalidade: d.modalidade || "Não informado",
    modalidade_cc: d.modalidade_cc || "Não informado",
    situacao_obra: d.situacao_obra || "Não informado",
    pct_fisico: pct,
    faixa_fisica: faixaFisica(pct),
    dt_assinatura: parseDate(d.dt_assinatura),
    vlr_repasse: +d.vlr_repasse || 0,
    vlr_contrapartida: +d.vlr_contrapartida || 0,
    vlr_desembolsado: +d.vlr_desembolsado || 0,
    mes_ultimo_desbloqueio: d.mes_ultimo_desbloqueio || "",
    situacao_contrato: d.situacao_contrato || "",
    situacao_compl: d.situacao_compl || "",
    dias_sem_bm: d.dias_sem_bm === "" || d.dias_sem_bm == null ? null : +d.dias_sem_bm,
    motivo_paralisacao: d.motivo_paralisacao || "",
    detalhamento_motivo: d.detalhamento_motivo || "",
    descricao_motivo: d.descricao_motivo || "",
    principal_entrave: d.principal_entrave || "",
    plano_acao: d.plano_acao || "",
    previsao_retomada: parseDate(d.previsao_retomada),
    dt_atualizacao: d.dt_atualizacao || "",
  };
}

const rawData = dsv.parse(rawText, parseLegadoRow);

const updatedAt = formatDate(rawData.find(d => d.dt_atualizacao)?.dt_atualizacao ?? null);

function isParalisada(d) {
  return d.situacao_obra === "Obra Paralisada";
}
function isConcluida(d) {
  return d.situacao_obra === "Obra concluída";
}
function isAndamento(d) {
  return d.situacao_obra === "Obra em andamento";
}
```

```js
if (!window.__legadoRuleTooltipInit) {
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
  window.__legadoRuleTooltipInit = { closeAllRuleTooltips, syncRuleTooltips };
} else {
  window.__legadoRuleTooltipInit.syncRuleTooltips();
}
```

```js
const pageTitleBar = document.createElement("div");
pageTitleBar.className = "page-titlebar dashboard-toolbar";
pageTitleBar.innerHTML = `
  <div class="page-titlebar__heading dashboard-toolbar__title">
    <h1>Painel Legado OGU - Obras Migradas - DMP/SE</h1>
  </div>
  <div class="page-titlebar__meta dashboard-toolbar__side" aria-label="Data de atualização">
    <div class="dashboard-toolbar__meta">
      <span class="page-titlebar__meta-label">Atualizado em</span>
      <strong class="page-titlebar__meta-value">${updatedAt}</strong>
    </div>
    <a class="page-subnav-link" href="./alteracoes" style="display:inline-flex;align-items:center;font-size:0.8125rem;font-weight:600;text-decoration:none;padding:0.35rem 0.7rem;border:1px solid var(--theme-foreground-faintest,#d0d7de);border-radius:999px;white-space:nowrap;">Ver Alterações do Legado →</a>
  </div>
`;
display(pageTitleBar);
```

<div class="filters-bar">

```js
const fBuscaInput = Inputs.search(rawData, {
  placeholder: "Buscar por operação, recebedor ou município…",
  columns: ["operacao", "recebedor", "municipio", "ente"],
  label: "Operação / Recebedor / Município",
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

  if (searchField) {
    const notify = () => input.dispatchEvent(new Event("input", {bubbles: true}));
    searchField.addEventListener("input", notify);
    searchField.addEventListener("change", notify);
    searchField.addEventListener("search", notify);
  }
}

localizeSearchResults(fBuscaInput);

const fBusca = view(fBuscaInput);
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
  const tipo = [...new Set(
    data
      .filter(d => filterBySelection(d.modalidade_cc, state.modalidade_cc))
      .filter(d => filterBySelection(getAno(d), state.ano))
      .map(d => d.tipo_operacao)
      .filter(Boolean)
  )].sort();

  const modalidade_cc = [...new Set(
    data
      .filter(d => filterBySelection(d.tipo_operacao, state.tipo))
      .filter(d => filterBySelection(getAno(d), state.ano))
      .map(d => d.modalidade_cc)
      .filter(Boolean)
  )].sort();

  const ano = [...new Set(
    data
      .filter(d => filterBySelection(d.tipo_operacao, state.tipo))
      .filter(d => filterBySelection(d.modalidade_cc, state.modalidade_cc))
      .map(getAno)
      .filter(Boolean)
  )].sort();

  return {tipo, modalidade_cc, ano};
}

function sanitizeCascadeState(data, state) {
  const options = computeCascadeOptions(data, state);
  const tipo = state.tipo.filter(value => options.tipo.includes(value));
  const modalidade_cc = state.modalidade_cc.filter(value => options.modalidade_cc.includes(value));
  const ano = state.ano.filter(value => options.ano.includes(value));
  return {
    tipo: tipo.length === options.tipo.length ? [] : tipo,
    modalidade_cc: modalidade_cc.length === options.modalidade_cc.length ? [] : modalidade_cc,
    ano: ano.length === options.ano.length ? [] : ano
  };
}

function makeCascadeFilters(data) {
  let state = {tipo: [], modalidade_cc: [], ano: []};
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
      {key: "tipo", label: "Tipo de operação", values: options.tipo, allLabel: "Todos", selectedLabel: "selecionados"},
      {key: "modalidade_cc", label: "Modalidade (Casa Civil)", values: options.modalidade_cc, allLabel: "Todas", selectedLabel: "selecionadas"},
      {key: "ano", label: "Ano de assinatura", values: options.ano, allLabel: "Todos", selectedLabel: "anos"}
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
      tipo: Array.isArray(nextState.tipo) ? nextState.tipo : [],
      modalidade_cc: Array.isArray(nextState.modalidade_cc) ? nextState.modalidade_cc : [],
      ano: Array.isArray(nextState.ano) ? nextState.ano : []
    });
    render();
    emit();
  };

  wrap.reset = () => {
    wrap.setState({tipo: [], modalidade_cc: [], ano: []});
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
  const searchInput = fBuscaInput.querySelector("input[type='search']");
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
function summarizeFilter(label, values, pluralLabel = "selecionadas") {
  if (values.length === 0) return null;
  if (values.length <= 2) return `${label}: ${values.join(", ")}`;
  return `${label}: ${values.length} ${pluralLabel}`;
}

const filtrosAtivos = [
  (filtros?.tipo?.length > 0) ? {key: "tipo", text: summarizeFilter("Tipo", filtros.tipo, "selecionados")} : null,
  (filtros?.modalidade_cc?.length > 0) ? {key: "modalidade_cc", text: summarizeFilter("Modalidade", filtros.modalidade_cc)} : null,
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
const tipoSelecionado = Array.isArray(filtros?.tipo) ? filtros.tipo : [];
const modalidadeCcSelecionada = Array.isArray(filtros?.modalidade_cc) ? filtros.modalidade_cc : [];
const anoSelecionado = Array.isArray(filtros?.ano) ? filtros.ano : [];

function matchesTipoFilter(d) {
  return tipoSelecionado.length === 0 || tipoSelecionado.includes(d.tipo_operacao);
}
function matchesModalidadeCcFilter(d) {
  return modalidadeCcSelecionada.length === 0 || modalidadeCcSelecionada.includes(d.modalidade_cc);
}
function matchesAnoFilter(d) {
  return anoSelecionado.length === 0 || (getAno(d) && anoSelecionado.includes(getAno(d)));
}

// ── baseData: filtros de topo
const baseData = fBusca.filter(d =>
  matchesTipoFilter(d) &&
  matchesModalidadeCcFilter(d) &&
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

const DRILL_LIMIT = 12;

function makeObraCrossCharts(data, drillField, drillLabel, drillMarginLeft) {
  let obraSel = null;
  let tipoSel = null;
  let drillSel = null;
  const wrap = Object.assign(document.createElement("div"), {
    value: {situacao_obra: null, tipo_operacao: null, drill: null}
  });

  function applyFilter(d, field, value) {
    if (value == null) return true;
    return d[field] === value;
  }

  function computeChartData() {
    const forObra = data.filter(d =>
      applyFilter(d, "tipo_operacao", tipoSel) &&
      applyFilter(d, drillField, drillSel)
    );
    const byObra = SITUACAO_OBRA_ORDER
      .map(s => ({situacao_obra: s, qtd: forObra.filter(d => d.situacao_obra === s).length}))
      .filter(d => d.qtd > 0);

    const forTipo = data.filter(d =>
      applyFilter(d, "situacao_obra", obraSel) &&
      applyFilter(d, drillField, drillSel)
    );
    const byTipo = TIPO_OPERACAO_ORDER
      .map(s => ({tipo_operacao: s, qtd: forTipo.filter(d => d.tipo_operacao === s).length}))
      .filter(d => d.qtd > 0);

    const forDrill = data.filter(d =>
      applyFilter(d, "situacao_obra", obraSel) &&
      applyFilter(d, "tipo_operacao", tipoSel)
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
      .sort((a, b) => b.contratos - a.contratos || b.vlr_repasse - a.vlr_repasse)
      .slice(0, DRILL_LIMIT);

    return {byObra, byTipo, byDrill};
  }

  function emit() {
    wrap.value = {situacao_obra: obraSel, tipo_operacao: tipoSel, drill: drillSel};
    wrap.dispatchEvent(new Event("input", {bubbles: true}));
  }

  function render() {
    wrap.innerHTML = "";
    const {byObra, byTipo, byDrill} = computeChartData();

    const sitTipoRow = document.createElement("div");
    sitTipoRow.className = "grid-two";

    // ── Card Situação da Obra
    const sitCard = document.createElement("div");
    sitCard.className = "card";
    sitCard.innerHTML = `
      <h2>Situação da Obra (Casa Civil) <span class="rule-tooltip"><button class="rule-tooltip__trigger" aria-label="Regra">?</button><span class="rule-tooltip__content">Classificação da obra conforme acompanhamento da Casa Civil.<ul><li><strong>Obra em andamento</strong> — execução em curso</li><li><strong>Obra concluída</strong> — execução física finalizada</li><li><strong>Obra Paralisada</strong> — execução interrompida</li><li><strong>Não iniciada</strong> — obra ainda não iniciada</li><li><strong>Não executada - Contrato Encerrado</strong> — contrato encerrado sem execução</li></ul></span></span></h2>
      <p>Clique em uma barra para filtrar</p>
    `;
    const sitChart = makeClickableChart(
      Plot.plot({
        marginLeft: 220, marginRight: 50,
        height: Math.max(180, byObra.length * 44 + 40),
        style: {fontFamily: "var(--font-sans, IBM Plex Sans, sans-serif)", fontSize: 13},
        x: {label: null, grid: false, axis: null},
        y: {label: null, domain: byObra.map(d => d.situacao_obra)},
        marks: [
          Plot.barX(byObra, {
            x: "qtd", y: "situacao_obra",
            fill: d => SITUACAO_OBRA_CORES[d.situacao_obra] ?? "#8a94a3", rx: 6,
          }),
          Plot.text(byObra, {
            x: "qtd", y: "situacao_obra",
            text: d => formatNumber(d.qtd),
            dx: 6, textAnchor: "start", fontSize: 12, fill: "#5b6470",
          }),
        ],
      }),
      byObra, "situacao_obra", obraSel
    );
    sitChart.addEventListener("input", () => {
      obraSel = sitChart.value;
      render();
      emit();
    });
    sitCard.append(sitChart);

    // ── Card Tipo de Operação
    const tipoCard = document.createElement("div");
    tipoCard.className = "card";
    tipoCard.innerHTML = `
      <h2>Tipo de Operação <span class="rule-tooltip"><button class="rule-tooltip__trigger" aria-label="Regra">?</button><span class="rule-tooltip__content">Natureza do instrumento de financiamento da obra.<ul><li><strong>Repasse</strong> — recursos de repasse da União (OGU)</li><li><strong>Financiamento</strong> — operação de crédito/empréstimo</li></ul></span></span></h2>
      <p>Clique em uma barra para filtrar</p>
    `;
    const tipoChart = makeClickableChart(
      Plot.plot({
        marginLeft: 160, marginRight: 50,
        height: Math.max(180, byTipo.length * 44 + 40),
        style: {fontFamily: "var(--font-sans, IBM Plex Sans, sans-serif)", fontSize: 13},
        x: {label: null, grid: false, axis: null},
        y: {label: null, domain: byTipo.map(d => d.tipo_operacao)},
        marks: [
          Plot.barX(byTipo, {
            x: "qtd", y: "tipo_operacao",
            fill: d => TIPO_OPERACAO_CORES[d.tipo_operacao] ?? "#8a94a3", rx: 6,
          }),
          Plot.text(byTipo, {
            x: "qtd", y: "tipo_operacao",
            text: d => formatNumber(d.qtd),
            dx: 6, textAnchor: "start", fontSize: 12, fill: "#5b6470",
          }),
        ],
      }),
      byTipo, "tipo_operacao", tipoSel
    );
    tipoChart.addEventListener("input", () => {
      tipoSel = tipoChart.value;
      render();
      emit();
    });
    tipoCard.append(tipoChart);

    sitTipoRow.append(sitCard, tipoCard);

    // ── Drill (Contratos + Repasse por Modalidade)
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
        marginLeft: drillMarginLeft, marginRight: 90,
        height: Math.max(180, byDrill.length * 40 + 40),
        style: {fontFamily: "var(--font-sans, IBM Plex Sans, sans-serif)", fontSize: 12},
        x: {label: null, grid: false, axis: null},
        y: {label: null, domain: byDrill.map(d => d.group)},
        marks: [
          Plot.barX(byDrill, {x: "contratos", y: "group", fill: "#356c8c", rx: 6}),
          Plot.text(byDrill, {
            x: "contratos", y: "group",
            text: d => formatNumber(d.contratos),
            dx: 6, textAnchor: "start", fontSize: 12, fill: "#5b6470",
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
        marginLeft: drillMarginLeft, marginRight: 110,
        height: Math.max(180, byDrill.length * 40 + 40),
        style: {fontFamily: "var(--font-sans, IBM Plex Sans, sans-serif)", fontSize: 12},
        x: {label: null, grid: false, axis: null},
        y: {label: null, domain: byDrill.map(d => d.group)},
        marks: [
          Plot.barX(byDrill, {x: "vlr_repasse", y: "group", fill: "#0f766e", rx: 6}),
          Plot.text(byDrill, {
            x: "vlr_repasse", y: "group",
            text: d => formatCurrencyCompact(d.vlr_repasse),
            dx: 6, textAnchor: "start", fontSize: 12, fill: "#5b6470",
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
      makeDrillCard(`Contratos por ${drillLabel}`, `Top ${DRILL_LIMIT} por quantidade na seleção atual`, contratosChart),
      makeDrillCard(`Repasse por ${drillLabel}`, `Top ${DRILL_LIMIT} por quantidade na seleção atual`, repasseChart)
    );

    // ── Cards
    const fullyFiltered = data.filter(d =>
      applyFilter(d, "situacao_obra", obraSel) &&
      applyFilter(d, "tipo_operacao", tipoSel) &&
      applyFilter(d, drillField, drillSel)
    );
    const vlr = arr => arr.reduce((s, d) => s + d.vlr_repasse, 0);
    const _total = fullyFiltered.length;
    const _vlrTotal = vlr(fullyFiltered);
    const _conc = fullyFiltered.filter(isConcluida);
    const _and = fullyFiltered.filter(isAndamento);
    const _par = fullyFiltered.filter(isParalisada);
    const pct = arr => _total > 0 ? arr.length / _total : 0;

    const cardsRow = metricGrid([
      { label: "Obras selecionadas", value: formatNumber(_total), topRight: formatCurrencyCompact(_vlrTotal), detail: "no recorte atual", tone: "default" },
      { label: "Concluídas", value: formatNumber(_conc.length), topRight: formatCurrencyCompact(vlr(_conc)), detail: formatPercent(pct(_conc)) + " do recorte", tone: "green" },
      { label: "Em andamento", value: formatNumber(_and.length), topRight: formatCurrencyCompact(vlr(_and)), detail: formatPercent(pct(_and)) + " do recorte", tone: "blue" },
      { label: "Paralisadas", value: formatNumber(_par.length), topRight: formatCurrencyCompact(vlr(_par)), detail: formatPercent(pct(_par)) + " do recorte", tone: "red" },
    ]);

    wrap.append(cardsRow, drillRow, sitTipoRow);

    if (window.__legadoRuleTooltipInit) {
      window.__legadoRuleTooltipInit.syncRuleTooltips();
    }
  }

  render();
  emit();
  return wrap;
}

// ── Geo cascade (Região → UF → Município)
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
        `${formatNumber(total)} obras no recorte atual`,
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
            `${formatNumber(ufBase.length)} obras na região ${wrap.value.regiao}`,
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
        ? [...municipioTopData, {label: GEO_OUTROS_MUNICIPIOS_LABEL, qtd: municipioRestante, color: "#94a3b8"}]
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
            `${formatNumber(municipioBase.length)} obras na UF ${wrap.value.uf}`,
            municipioBase.length > GEO_MUNICIPIO_LIMIT
              ? `top ${GEO_MUNICIPIO_LIMIT} municípios por quantidade de obras`
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

function normalizeDrillSelection(selection) {
  if (selection == null) return null;
  if (typeof selection === "string") return selection;
  if (Array.isArray(selection)) return selection.length === 1 ? selection[0] : null;
  return null;
}
```

<section class="section-block section-block--geral">
<header class="section-block__header">
<span class="section-block__eyebrow">Visão geral</span>
<h2>Panorama das Obras <span class="rule-tooltip"><button class="rule-tooltip__trigger" aria-label="Regra">?</button><span class="rule-tooltip__content">Cruzamento entre situação da obra, tipo de operação e modalidade. Clique nas barras para filtrar — as seleções valem para os blocos abaixo.</span></span></h2>
<p>Clique nas barras para cruzar situação da obra, tipo de operação e modalidade.</p>
</header>

<div class="section-block__body">

```js
const obraDrillField = "modalidade";
const obraDrillLabel = "Modalidade";
const obraDrillMarginLeft = 260;
```

```js
const selectedCharts = view(makeObraCrossCharts(
  baseData,
  obraDrillField,
  obraDrillLabel,
  obraDrillMarginLeft
));
```

</div>
</section>

```js
const selectedObra = selectedCharts?.situacao_obra ?? null;
const selectedTipo = selectedCharts?.tipo_operacao ?? null;
const drillSelection = normalizeDrillSelection(selectedCharts?.drill ?? null);

const preGeoData = baseData.filter(d =>
  (selectedObra == null || d.situacao_obra === selectedObra) &&
  (selectedTipo == null || d.tipo_operacao === selectedTipo) &&
  (drillSelection == null || d[obraDrillField] === drillSelection)
);
```

<section class="section-block section-block--geo">
<header class="section-block__header">
<span class="section-block__eyebrow">Recorte territorial</span>
<h2>Distribuição Territorial <span class="rule-tooltip"><button class="rule-tooltip__trigger" aria-label="Regra">?</button><span class="rule-tooltip__content">Recorte territorial das obras visíveis no painel.<ul><li><strong>Região</strong> — considera todas as obras após os filtros do topo e do panorama</li><li><strong>UF</strong> — abre quando uma região é selecionada</li><li>As seleções passam a valer para os blocos seguintes</li></ul></span></span></h2>
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
```

<section class="section-block section-block--fisico">
<header class="section-block__header">
<span class="section-block__eyebrow">Execução</span>
<h2>Execução Física e Financeira <span class="rule-tooltip"><button class="rule-tooltip__trigger" aria-label="Regra">?</button><span class="rule-tooltip__content">Distribuição das obras por faixa de execução física e indicadores financeiros do recorte atual.<ul><li><strong>% físico médio</strong> — média simples do percentual físico realizado</li><li><strong>Desembolsado</strong> — valor desbloqueado/desembolsado acumulado</li><li><strong>% desembolsado</strong> — desembolsado sobre o repasse/empréstimo</li></ul></span></span></h2>
<p>Clique em uma faixa de execução para refletir na Base de Dados.</p>
</header>

<div class="section-block__body">

```js
const fisicoComDado = geoScopedData.filter(d => d.pct_fisico != null);
const pctMedio = fisicoComDado.length
  ? fisicoComDado.reduce((s, d) => s + d.pct_fisico, 0) / fisicoComDado.length / 100
  : 0;
const vlrRepasseTotal = geoScopedData.reduce((s, d) => s + d.vlr_repasse, 0);
const vlrDesembTotal = geoScopedData.reduce((s, d) => s + d.vlr_desembolsado, 0);
const vlrContrapTotal = geoScopedData.reduce((s, d) => s + d.vlr_contrapartida, 0);
const pctDesemb = vlrRepasseTotal > 0 ? vlrDesembTotal / vlrRepasseTotal : 0;

display(metricGrid([
  { label: "Obras no recorte", value: formatNumber(geoScopedData.length), topRight: formatCurrencyCompact(vlrRepasseTotal), detail: "repasse/empréstimo total", tone: "default" },
  { label: "% físico médio", value: formatPercent(pctMedio), detail: `${formatNumber(fisicoComDado.length)} obras com dado físico`, tone: "blue" },
  { label: "Desembolsado", value: formatCurrencyCompact(vlrDesembTotal), detail: `${formatPercent(pctDesemb)} do repasse`, tone: "green" },
  { label: "Contrapartida", value: formatCurrencyCompact(vlrContrapTotal), detail: "valor de contrapartida atual", tone: "gold" },
]));
```

<div class="card">

```js
const faixaCounts = FAIXA_FISICA_ORDER
  .map(f => ({faixa: f, qtd: geoScopedData.filter(d => d.faixa_fisica === f).length}))
  .filter(d => d.qtd > 0);
const semDadoFaixa = geoScopedData.filter(d => d.faixa_fisica === "Sem dado").length;
const faixaItems = semDadoFaixa > 0
  ? [...faixaCounts, {faixa: "Sem dado", qtd: semDadoFaixa}]
  : faixaCounts;

const faixaChart = makeClickableChart(
  Plot.plot({
    marginLeft: 90, marginRight: 60,
    height: Math.max(180, faixaItems.length * 40 + 40),
    style: {fontFamily: "var(--font-sans, IBM Plex Sans, sans-serif)", fontSize: 13},
    x: {label: null, grid: false, axis: null},
    y: {label: null, domain: faixaItems.map(d => d.faixa)},
    marks: [
      Plot.barX(faixaItems, {
        x: "qtd", y: "faixa",
        fill: d => FAIXA_FISICA_CORES[d.faixa] ?? "#94a3b8", rx: 6,
      }),
      Plot.text(faixaItems, {
        x: "qtd", y: "faixa",
        text: d => formatNumber(d.qtd),
        dx: 6, textAnchor: "start", fontSize: 12, fill: "#5b6470",
      }),
    ],
  }),
  faixaItems, "faixa", null
);
const selectedFaixa = view(faixaChart);
```

</div>
</div>
</section>

```js
const fisicoScopedData = geoScopedData.filter(d => selectedFaixa == null || d.faixa_fisica === selectedFaixa);
```

<section class="section-block section-block--paralisacao">
<header class="section-block__header">
<span class="section-block__eyebrow">Atenção</span>
<h2>Análise de Paralisações <span class="rule-tooltip"><button class="rule-tooltip__trigger" aria-label="Regra">?</button><span class="rule-tooltip__content">Recorte das obras com situação <strong>Obra Paralisada</strong> no escopo atual, detalhando o principal motivo de paralisação. Clique em um motivo para filtrar a Base de Dados.</span></span></h2>
<p>Obras paralisadas por principal motivo. Clique em um motivo para refletir na Base de Dados.</p>
</header>

<div class="section-block__body">

```js
const paralisadas = fisicoScopedData.filter(isParalisada);
const diasComBm = paralisadas.filter(d => d.dias_sem_bm != null);
const diasMedioBm = diasComBm.length
  ? Math.round(diasComBm.reduce((s, d) => s + d.dias_sem_bm, 0) / diasComBm.length)
  : null;
const comPlano = paralisadas.filter(d => d.plano_acao && d.plano_acao.trim() !== "").length;
const comPrevisao = paralisadas.filter(d => d.previsao_retomada).length;

display(metricGrid([
  { label: "Obras paralisadas", value: formatNumber(paralisadas.length), topRight: formatCurrencyCompact(paralisadas.reduce((s, d) => s + d.vlr_repasse, 0)), detail: "no recorte atual", tone: "red" },
  { label: "Dias médios sem BM", value: diasMedioBm == null ? "—" : formatNumber(diasMedioBm), detail: `${formatNumber(diasComBm.length)} obras com dado`, tone: "gold" },
  { label: "Com plano de ação", value: formatNumber(comPlano), detail: paralisadas.length ? formatPercent(comPlano / paralisadas.length) + " das paralisadas" : "—", tone: "blue" },
  { label: "Com previsão de retomada", value: formatNumber(comPrevisao), detail: paralisadas.length ? formatPercent(comPrevisao / paralisadas.length) + " das paralisadas" : "—", tone: "green" },
]));
```

<div class="card">

```js
const motivoCounts = [...new Set(paralisadas.map(d => d.motivo_paralisacao).filter(Boolean))]
  .map(m => ({motivo: m, qtd: paralisadas.filter(d => d.motivo_paralisacao === m).length}))
  .sort((a, b) => b.qtd - a.qtd)
  .slice(0, 12);

if (motivoCounts.length === 0) {
  display(html`<p class="casc-empty">Nenhuma obra paralisada com motivo registrado no recorte atual.</p>`);
}

const motivoChart = motivoCounts.length
  ? makeClickableChart(
      Plot.plot({
        marginLeft: 320, marginRight: 60,
        height: Math.max(160, motivoCounts.length * 38 + 36),
        style: {fontFamily: "var(--font-sans, IBM Plex Sans, sans-serif)", fontSize: 12},
        x: {label: null, grid: false, axis: null},
        y: {label: null, domain: motivoCounts.map(d => d.motivo)},
        marks: [
          Plot.barX(motivoCounts, {x: "qtd", y: "motivo", fill: "#b42318", rx: 6}),
          Plot.text(motivoCounts, {
            x: "qtd", y: "motivo",
            text: d => formatNumber(d.qtd),
            dx: 6, textAnchor: "start", fontSize: 12, fill: "#5b6470",
          }),
        ],
      }),
      motivoCounts, "motivo", null
    )
  : Object.assign(document.createElement("div"), {value: null});
const selectedMotivo = view(motivoChart);
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
const tableData = fisicoScopedData.filter(d =>
  selectedMotivo == null || (isParalisada(d) && d.motivo_paralisacao === selectedMotivo)
);

const exportColumns = [
  "ativo", "tipo_operacao", "operacao", "repassador", "regiao", "uf", "municipio", "recebedor", "ente",
  "objeto", "modalidade", "modalidade_cc", "situacao_obra", "pct_fisico", "dt_assinatura",
  "vlr_repasse", "vlr_contrapartida", "vlr_desembolsado", "mes_ultimo_desbloqueio",
  "situacao_contrato", "situacao_compl", "dias_sem_bm",
  "motivo_paralisacao", "detalhamento_motivo", "descricao_motivo", "principal_entrave", "plano_acao", "previsao_retomada",
];
const exportHeaders = {
  ativo: "Ativo/Inativo",
  tipo_operacao: "Tipo de Operação",
  operacao: "Operação",
  repassador: "Repassador",
  regiao: "Região",
  uf: "UF",
  municipio: "Município",
  recebedor: "Recebedor",
  ente: "Ente de Vinculação",
  objeto: "Objeto",
  modalidade: "Modalidade",
  modalidade_cc: "Modalidade (Casa Civil)",
  situacao_obra: "Situação da Obra (Casa Civil)",
  pct_fisico: "% Físico Realizado",
  dt_assinatura: "Data da Assinatura",
  vlr_repasse: "Repasse/Empréstimo",
  vlr_contrapartida: "Contrapartida Atual",
  vlr_desembolsado: "Desembolsado",
  mes_ultimo_desbloqueio: "Mês Últ. Desbloqueio",
  situacao_contrato: "Situação do Contrato",
  situacao_compl: "Sit. Contrato Complemento",
  dias_sem_bm: "Dias sem BM",
  motivo_paralisacao: "Principal Motivo de Paralisação",
  detalhamento_motivo: "Detalhamento do Motivo",
  descricao_motivo: "Descrição do Motivo",
  principal_entrave: "Principal Entrave",
  plano_acao: "Plano de Ação",
  previsao_retomada: "Previsão de Retomada",
};

const defaultSelectedColumns = [
  "tipo_operacao", "operacao", "uf", "municipio", "recebedor", "modalidade",
  "situacao_obra", "pct_fisico", "dt_assinatura", "vlr_repasse", "vlr_desembolsado",
  "situacao_contrato", "motivo_paralisacao", "previsao_retomada",
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
const dateCol = d => d ? formatDate(d) : "—";
const moneyCol = d => (d ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const pctCol = d => d == null ? "—" : `${formatNumber(d)}%`;
const mesCol = d => {
  const m = /^(\d{4})(\d{2})$/.exec(String(d ?? ""));
  return m ? `${m[2]}/${m[1]}` : (d || "—");
};

display(renderBaseDataTable({
  rows: tableData,
  columns: selectedColumns,
  headers: exportHeaders,
  formatters: {
    vlr_repasse: moneyCol,
    vlr_contrapartida: moneyCol,
    vlr_desembolsado: moneyCol,
    pct_fisico: pctCol,
    dt_assinatura: dateCol,
    previsao_retomada: dateCol,
    mes_ultimo_desbloqueio: mesCol,
  },
  invalidation,
  exportFilePrefix: "legadoogu-tabela-filtrada",
}));
```

</div>
</div>
</section>
