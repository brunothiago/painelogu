import * as Plot from "@observablehq/plot";
import {SITUACAO_CORES, SUSPENSIVA_CORES, SITUACAO_ORDER, SUSPENSIVA_ORDER, URGENCIA_CORES, PALETTE} from "../lib/theme.js";
import {hexToRgba} from "../lib/dom-helpers.js";

const URGENCIA_ORDER = ["Vencida", "Próximos 30 dias", "31–90 dias", "Mais de 90 dias", "Sem data"];
const MS_PER_DAY = 86400000;

function isSuspensivaPendente(d) {
  return !d.dt_retirada_suspensiva && d.situacao_suspensiva !== "Suspensiva retirada";
}

export {isSuspensivaPendente};

function monthYearKey(date) {
  if (!(date instanceof Date) || isNaN(date)) return null;
  return date.getUTCFullYear() * 100 + (date.getUTCMonth() + 1);
}

function monthYearLabel(sortKey) {
  if (sortKey == null) return "Sem data";
  const month = sortKey % 100;
  const year = Math.floor(sortKey / 100);
  return `${String(month).padStart(2, "0")}/${year}`;
}

function urgencyColorForMonth(sortKey) {
  if (sortKey == null) return URGENCIA_CORES["Sem data"];
  const year = Math.floor(sortKey / 100);
  const month = sortKey % 100;
  const ref = new Date(Date.UTC(year, month - 1, 15));
  const today = new Date();
  const todayUtc = Date.UTC(today.getFullYear(), today.getMonth(), today.getDate());
  const diffDays = Math.floor((ref.getTime() - todayUtc) / MS_PER_DAY);
  if (diffDays < 0) return URGENCIA_CORES["Vencida"];
  if (diffDays <= 30) return URGENCIA_CORES["Próximos 30 dias"];
  if (diffDays <= 90) return URGENCIA_CORES["31–90 dias"];
  return URGENCIA_CORES["Mais de 90 dias"];
}

function buildVencimentoMonthChart(rows, options = {}) {
  const {fromTable = false} = options;
  const counts = new Map();
  let semData = 0;
  for (const row of rows) {
    const key = monthYearKey(row.dt_vencimento_suspensiva);
    if (key == null) {
      semData += 1;
      continue;
    }
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }

  const byMonth = [...counts.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([sortKey, qtd]) => ({
      sortKey,
      label: monthYearLabel(sortKey),
      qtd,
      color: urgencyColorForMonth(sortKey),
    }));

  if (semData > 0) {
    byMonth.push({
      sortKey: null,
      label: "Sem data",
      qtd: semData,
      color: URGENCIA_CORES["Sem data"],
    });
  }

  const wrap = el("div", "casc-month-chart");
  const header = el("div", "casc-level__header");
  const title = el("strong", "casc-level__title");
  title.textContent = `${rows.length.toLocaleString("pt-BR")} contratos com suspensiva pendente`;
  const subtitle = el("span", "casc-level__subtitle");
  subtitle.textContent = fromTable
    ? "por mês de vencimento (PBI) · recorte da Base de Dados"
    : "por mês de vencimento (PBI)";
  header.append(title, subtitle);
  wrap.append(header);

  if (byMonth.length === 0) {
    const empty = el("p", "casc-empty");
    empty.textContent = "Nenhum contrato com suspensiva pendente no recorte atual.";
    wrap.append(empty);
    return wrap;
  }

  const scroll = el("div", "casc-month-chart__scroll");
  scroll.append(
    Plot.plot({
      width: Math.max(420, byMonth.length * 52 + 48),
      height: 260,
      marginLeft: 48,
      marginRight: 16,
      marginBottom: 56,
      marginTop: 12,
      style: {fontFamily: "var(--font-sans, IBM Plex Sans, sans-serif)", fontSize: 12},
      x: {
        label: null,
        domain: byMonth.map((d) => d.label),
        tickRotate: -40,
      },
      y: {label: "Contratos", grid: true, nice: true},
      marks: [
        Plot.barY(byMonth, {x: "label", y: "qtd", fill: "color", rx: 4}),
        Plot.text(byMonth, {
          x: "label",
          y: "qtd",
          text: (d) => (d.qtd > 0 ? d.qtd.toLocaleString("pt-BR") : ""),
          dy: -6,
          fontSize: 11,
          fill: "#5b6470",
        }),
      ],
    })
  );
  wrap.append(scroll);
  return wrap;
}

function el(tag, cls) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  return node;
}

function proportionalBar(items, total, options = {}) {
  const {filterKey, selectedValue, onSelect} = options;
  const wrap = el("div", "casc-bar");
  for (const {label, qtd, color} of items) {
    if (!qtd) continue;
    const pct = (qtd / total) * 100;
    const seg = el("div", "casc-bar__seg");
    seg.style.cssText = `width:${pct}%;background:${color};`;
    seg.title = `${label}: ${qtd.toLocaleString("pt-BR")} (${pct.toFixed(1)}%)`;
    if (filterKey) {
      seg.classList.add("is-clickable");
      if (selectedValue === label) seg.classList.add("is-selected");
      seg.dataset.filterKey = filterKey;
      seg.dataset.filterLabel = label;
      seg.setAttribute("role", "button");
      seg.tabIndex = 0;
      seg.addEventListener("click", (event) => {
        event.stopPropagation();
        onSelect(filterKey, label);
      });
      seg.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onSelect(filterKey, label);
        }
      });
    }
    if (pct > 4) {
      const lbl = el("span", "casc-bar__seg-num");
      lbl.textContent = qtd.toLocaleString("pt-BR");
      seg.append(lbl);
    }
    wrap.append(seg);
  }
  return wrap;
}

function legend(items, options = {}) {
  const {filterKey, selectedValue, onSelect} = options;
  const wrap = el("div", "casc-legend");
  for (const {label, qtd, color, pct} of items) {
    if (!qtd) continue;
    const item = el("div", "casc-legend__item");
    if (filterKey) {
      item.classList.add("is-clickable");
      if (selectedValue === label) item.classList.add("is-selected");
      item.dataset.filterKey = filterKey;
      item.dataset.filterLabel = label;
      item.setAttribute("role", "button");
      item.tabIndex = 0;
      item.addEventListener("click", () => onSelect(filterKey, label));
      item.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onSelect(filterKey, label);
        }
      });
    }
    const dot = el("span", "casc-legend__dot");
    dot.style.background = color;
    const txt = el("span", "casc-legend__text");
    txt.innerHTML = `<strong>${label}</strong> <span>${qtd.toLocaleString("pt-BR")}</span>`;
    if (pct !== undefined) {
      const badge = el("span", "casc-legend__pct");
      badge.textContent = `${pct.toFixed(1)}%`;
      badge.style.color = color;
      txt.append(badge);
    }
    item.append(dot, txt);
    wrap.append(item);
  }
  return wrap;
}

function level(title, subtitle, items, total, options = {}) {
  const wrap = el("div", "casc-level");
  const header = el("div", "casc-level__header");
  const h = el("strong", "casc-level__title");
  h.textContent = title;
  const sub = el("span", "casc-level__subtitle");
  sub.textContent = subtitle;
  header.append(h, sub);

  const itemsWithPct = items.map(i => ({...i, pct: (i.qtd / total) * 100}));
  wrap.append(
    header,
    proportionalBar(itemsWithPct, total, options),
    legend(itemsWithPct, options)
  );
  return wrap;
}

function connector(label) {
  const wrap = el("div", "casc-connector");
  const line = el("div", "casc-connector__line");
  const lbl = el("span", "casc-connector__label");
  lbl.textContent = label;
  wrap.append(line, lbl);
  return wrap;
}

function styleActiveChip(chip, color) {
  chip.style.setProperty("--chip-border", hexToRgba(color, 0.28));
  chip.style.setProperty("--chip-bg", hexToRgba(color, 0.12));
  chip.style.setProperty("--chip-bg-hover", hexToRgba(color, 0.18));
  chip.style.setProperty("--chip-fg", color);
}

function activeSelection(values, colorByKey, onClear) {
  const entries = Object.entries(values).filter(([, value]) => value != null);
  if (entries.length === 0) return null;

  const labels = {
    suspensiva: "Situação",
    urgencia: "Urgência",
  };

  const wrap = el("div", "casc-active");
  for (const [key, value] of entries) {
    const chip = el("button", "casc-active__chip");
    chip.type = "button";
    chip.textContent = `${labels[key] ?? key}: ${value} ×`;
    styleActiveChip(chip, colorByKey[key]?.(value) ?? PALETTE.blue);
    chip.addEventListener("click", () => onClear(key));
    wrap.append(chip);
  }
  return wrap;
}

export function matchesCascadeSelection(d, selection = {}) {
  return (
    d.situacao === "Contratado - Suspensiva" &&
    (selection.suspensiva == null || d.situacao_suspensiva === selection.suspensiva) &&
    (
      selection.urgencia == null ||
      (
        !d.dt_retirada_suspensiva &&
        d.urgencia_suspensiva === selection.urgencia
      )
    )
  );
}

/**
 * @param {Array} data - dados filtrados
 * @param {HTMLElement} [tableRowsRef] - linhas visíveis na Base de Dados (atualiza o gráfico mensal)
 */
export function cascadeChart(data, tableRowsRef = null) {
  const container = Object.assign(el("div", "casc-chart"), {
    value: {suspensiva: null, urgencia: null}
  });

  if (tableRowsRef) {
    tableRowsRef.addEventListener("input", () => render());
  }

  function monthChartRows(pendentes) {
    const tableRows = tableRowsRef?.value;
    if (tableRows == null) return pendentes;
    const visible = new Set(tableRows);
    return pendentes.filter((d) => visible.has(d));
  }

  function setFilter(key, label) {
    const nextValue = container.value[key] === label ? null : label;
    container.value = {
      ...container.value,
      [key]: nextValue
    };
    render();
    container.dispatchEvent(new Event("input", {bubbles: true}));
  }

  const clear = el("button", "casc-clear");
  clear.type = "button";
  clear.textContent = "Limpar seleção";
  clear.hidden = true;
  clear.addEventListener("click", () => {
    container.value = {suspensiva: null, urgencia: null};
    render();
    container.dispatchEvent(new Event("input", {bubbles: true}));
  });

  function render() {
    container.innerHTML = "";
    clear.hidden = !Object.values(container.value).some(Boolean);
    container.append(clear);
    const active = activeSelection(
      container.value,
      {
        suspensiva: (value) => SUSPENSIVA_CORES[value] ?? PALETTE.orange,
        urgencia: (value) => URGENCIA_CORES[value] ?? PALETTE.gold,
      },
      (key) => {
        container.value = {...container.value, [key]: null};
        render();
        container.dispatchEvent(new Event("input", {bubbles: true}));
      }
    );
    if (active) container.append(active);

    const filteredData = data.filter((d) => matchesCascadeSelection(d, container.value));
    const totalN1 = filteredData.length;

    if (totalN1 === 0) {
      const msg = el("p", "casc-empty");
      msg.textContent = "Nenhum contrato corresponde à seleção atual na cascata.";
      container.append(msg);
      return;
    }

    const pendentes = filteredData.filter(isSuspensivaPendente);

    const byAnlise = SUSPENSIVA_ORDER
      .map(s => ({
        label: s,
        qtd: filteredData.filter(d => d.situacao_suspensiva === s).length,
        color: SUSPENSIVA_CORES[s] ?? PALETTE.gray,
      }))
      .filter(i => i.qtd > 0);

    container.append(
      level(
        `${totalN1.toLocaleString("pt-BR")} contratos em suspensiva`,
        "por situação da análise",
        byAnlise,
        totalN1,
        {
          filterKey: "suspensiva",
          selectedValue: container.value.suspensiva,
          onSelect: setFilter
        }
      )
    );

    container.append(connector("por prazo de vencimento da suspensiva"));
    const byUrgencia = URGENCIA_ORDER
      .map(u => ({
        label: u,
        qtd: pendentes.filter(d => d.urgencia_suspensiva === u).length,
        color: URGENCIA_CORES[u],
      }))
      .filter(i => i.qtd > 0);

    container.append(
      level(
        `${pendentes.length.toLocaleString("pt-BR")} contratos com suspensiva pendente`,
        "por urgência do vencimento",
        byUrgencia,
        pendentes.length,
        {
          filterKey: "urgencia",
          selectedValue: container.value.urgencia,
          onSelect: setFilter
        }
      )
    );

    if (pendentes.length > 0) {
      const monthRows = monthChartRows(pendentes);
      const tableFiltered = tableRowsRef?.value != null && monthRows.length !== pendentes.length;
      container.append(connector("calendário de vencimento da suspensiva (PBI)"));
      container.append(buildVencimentoMonthChart(monthRows, {fromTable: tableFiltered}));
    }
  }

  render();
  return container;
}
