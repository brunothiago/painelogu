import {html} from "htl";
import * as XLSX from "xlsx";
import DataTable from "datatables.net-responsive-dt";

function toPlainText(value) {
  if (value == null) return "";
  if (value instanceof Node) return value.textContent?.replace(/\s+/g, " ").trim() ?? "";
  return String(value).replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
}

function escapeRegex(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function applyNumericCellFormat(worksheet) {
  for (const [cellRef, cell] of Object.entries(worksheet)) {
    if (cellRef.startsWith("!")) continue;
    if (cell?.t === "d") {
      cell.z = "dd/mm/yyyy";
      continue;
    }
    if (cell?.t === "n") cell.z = "#,##0.00";
  }
}

function applyColumnWidths(worksheet, rows, headers) {
  worksheet["!cols"] = headers.map((header, index) => {
    const values = rows.map((row) => row[index]);
    const nonEmptyValues = values.filter((value) => value != null && value !== "");
    const sample = nonEmptyValues[0];

    if (sample instanceof Date) return {wch: 12};
    if (typeof sample === "number") return {wch: 14};

    const lengths = nonEmptyValues
      .map((value) => String(value).length)
      .sort((a, b) => a - b);
    const percentileLength = lengths.length
      ? lengths[Math.min(lengths.length - 1, Math.floor(lengths.length * 0.9))]
      : 0;
    const targetLength = Math.max(String(header).length, percentileLength);
    return {wch: Math.min(Math.max(targetLength + 2, 8), 24)};
  });
}

function exportRowsToXlsx(rows, columns, headers, filePrefix) {
  const exportRows = rows.map((row) => {
    const record = {};
    for (const column of columns) record[headers[column] ?? column] = row[column] ?? "";
    return record;
  });

  const worksheet = XLSX.utils.json_to_sheet(exportRows, {cellDates: true});
  applyNumericCellFormat(worksheet);
  applyColumnWidths(worksheet, exportRows.map(Object.values), Object.keys(exportRows[0] ?? {}));
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, "Tabela");
  const stamp = new Date().toISOString().slice(0, 10);
  XLSX.writeFileXLSX(workbook, `${filePrefix}-${stamp}.xlsx`);
}

function chooseFilterType(rows, column) {
  if (
    column === "fase" ||
    column === "modalidade" ||
    column === "situacao" ||
    column === "situacao_suspensiva" ||
    column === "situacao_contrato_tci" ||
    column === "situacao_contrato_dmp" ||
    column === "situacao_suspensiva_pbi" ||
    column === "situacao_suspensiva_dmp" ||
    column === "mes_ano_vencimento_suspensiva"
  ) {
    return "select";
  }
  const values = [...new Set(rows.map((row) => toPlainText(row[column])).filter(Boolean))];
  if (values.length > 1 && values.length <= 30 && values.every((value) => String(value).length <= 24)) {
    return "select";
  }
  return "text";
}

function getColumnClassName(column) {
  if (column === "_diff_label") return "col-diff";
  if (column === "num_convenio") return "col-convenio";
  if (column === "cod_tci") return "col-tci";
  if (column === "secretaria") return "col-secretaria";
  if (column.startsWith("dt_") || column.startsWith("prazo_") || column === "mes_ano_vencimento_suspensiva") return "col-date";
  if (column.startsWith("status_")) return "col-status";
  if (column === "vlr_repasse") return "col-money";
  if (column === "fase" || column === "modalidade") return "col-medium";
  if (
    column === "situacao" ||
    column === "situacao_suspensiva" ||
    column === "situacao_contrato_tci" ||
    column === "situacao_contrato_dmp" ||
    column === "situacao_suspensiva_pbi" ||
    column === "situacao_suspensiva_dmp" ||
    column === "data_limite_licitacao_casa_civil" ||
    column === "proponente"
  ) return "col-long";
  return "col-default";
}

function getColumnWidth(column) {
  if (column === "_diff_label") return "86px";
  if (column === "num_convenio") return "92px";
  if (column === "cod_tci") return "96px";
  if (column === "secretaria") return "68px";
  if (column === "uf") return "48px";
  if (column.startsWith("dt_") || column.startsWith("prazo_") || column === "mes_ano_vencimento_suspensiva") return "104px";
  if (column.startsWith("status_")) return "160px";
  if (column === "vlr_repasse") return "124px";
  if (column === "fase" || column === "modalidade") return "120px";
  if (
    column === "situacao" ||
    column === "situacao_suspensiva" ||
    column === "situacao_contrato_tci" ||
    column === "situacao_contrato_dmp" ||
    column === "situacao_suspensiva_pbi" ||
    column === "situacao_suspensiva_dmp"
  ) return "176px";
  if (column === "proponente") return "200px";
  if (column === "data_limite_licitacao_casa_civil") return "168px";
  return "132px";
}

export function renderBaseDataTable({
  rows,
  columns,
  headers,
  formatters = {},
  invalidation,
  exportFilePrefix = "tabela-filtrada",
  onFilteredRowsChange,
}) {
  const processedRows = rows.map((row) => {
    const processed = {__source: row};
    for (const column of columns) {
      const formatter = formatters[column];
      const value = row[column];
      processed[`${column}__raw`] = value;
      processed[column] = formatter ? formatter(value, row) : (value ?? "—");
      processed[`${column}__text`] = toPlainText(processed[column]);
    }
    return processed;
  });

  const columnMeta = columns.map((column) => ({
    key: column,
    label: headers[column] ?? column,
    filter: chooseFilterType(processedRows, column),
    className: getColumnClassName(column),
    width: getColumnWidth(column),
  }));

  const headerRow = html`<tr>${columnMeta.map((column) => html`<th>${column.label}</th>`)}</tr>`;
  const filterRow = html`<tr class="datatable-filters-row">${columnMeta.map(() => html`<th></th>`)}</tr>`;
  const table = html`<table class="display nowrap base-datatable">
    <thead>${headerRow}${filterRow}</thead>
  </table>`;
  const tableScroll = html`<div class="datatable-scroll"></div>`;
  tableScroll.append(table);

  const summary = html`<p class="metric-detail datatable-summary"></p>`;
  const clearFiltersBtn = html`<button class="clear-filters-btn" type="button" style="display:none;">Limpar filtros</button>`;
  const exportBtn = html`<button class="export-btn" type="button"></button>`;
  const controls = html`<div class="table-controls table-controls--top"></div>`;
  controls.append(summary, clearFiltersBtn, exportBtn);
  const dtTopBar = html`<div class="datatable-toolbar datatable-toolbar--top"></div>`;
  const dtBottomBar = html`<div class="datatable-toolbar datatable-toolbar--bottom"></div>`;

  const root = html`<div class="datatable-block base-datatable-block"></div>`;
  root.append(controls, dtTopBar, tableScroll, dtBottomBar);

  const dtColumns = columnMeta.map((column) => ({
    data: column.key,
    title: column.label,
    className: column.className,
    width: column.width,
    render(data, type, row) {
      if (type === "display") return data ?? "—";
      const raw = row[`${column.key}__raw`];
      // Só usar timestamp na ordenação; busca/filtro da coluna precisa bater com o texto exibido (ex.: Mês/Ano).
      if (type === "sort" && raw instanceof Date && !isNaN(raw)) return raw.getTime();
      return toPlainText(data);
    },
  }));

  const dataTable = new DataTable(table, {
    data: processedRows,
    autoWidth: false,
    orderCellsTop: true,
    pageLength: 25,
    lengthMenu: [10, 25, 50, 100],
    responsive: true,
    columns: dtColumns,
    language: {
      search: "Buscar na tabela:",
      searchPlaceholder: "Digite para buscar",
      lengthMenu: "Mostrar _MENU_ registros",
      info: "Mostrando _START_ a _END_ de _TOTAL_ registros",
      infoEmpty: "Nenhum registro encontrado",
      infoFiltered: "(filtrado de _MAX_ registros)",
      zeroRecords: "Nenhum registro corresponde à busca",
      emptyTable: "Nenhum registro disponível",
      paginate: {
        first: "Primeira",
        last: "Última",
        next: "Próxima",
        previous: "Anterior",
      },
    },
    initComplete() {
      const api = this.api();

      columnMeta.forEach((column, index) => {
        const cell = filterRow.cells[index];
        if (column.filter === "select") {
          const valueMap = new Map();
          for (const row of processedRows) {
            const text = toPlainText(row[column.key]);
            if (text && !valueMap.has(text)) valueMap.set(text, row[`${column.key}__raw`]);
          }
          const values = [...valueMap.entries()]
            .sort((a, b) => {
              const rawA = a[1], rawB = b[1];
              if (rawA instanceof Date && rawB instanceof Date) return rawA - rawB;
              return String(a[0]).localeCompare(String(b[0]), "pt-BR");
            })
            .map(([text]) => text);
          const select = document.createElement("select");
          select.className = `datatable-filter ${column.className}`.trim();
          select.setAttribute("aria-label", `Filtrar coluna ${column.label}`);
          select.innerHTML = `<option value="">Todos</option>`;
          for (const value of values) {
            const option = document.createElement("option");
            option.value = value;
            option.textContent = value;
            select.append(option);
          }
          select.addEventListener("change", () => {
            const value = select.value;
            api.column(index).search(value ? `^${escapeRegex(value)}$` : "", true, false).draw();
          });
          cell.replaceChildren(select);
        } else {
          const input = document.createElement("input");
          input.className = `datatable-filter ${column.className}`.trim();
          input.type = "search";
          input.placeholder = column.label;
          input.setAttribute("aria-label", `Filtrar coluna ${column.label}`);
          input.addEventListener("input", () => {
            api.column(index).search(input.value).draw();
          });
          cell.replaceChildren(input);
        }
      });
    },
  });

  const dtWrapper = dataTable.table().container();
  const dtLength = dtWrapper?.querySelector(".dt-length, .dataTables_length");
  const dtFilter = dtWrapper?.querySelector(".dt-search, .dataTables_filter");
  const dtInfo = dtWrapper?.querySelector(".dt-info, .dataTables_info");
  const dtPaginate = dtWrapper?.querySelector(".dt-paging, .dataTables_paginate");
  if (dtLength) dtTopBar.append(dtLength);
  if (dtFilter) dtTopBar.append(dtFilter);
  if (dtInfo) dtBottomBar.append(dtInfo);
  if (dtPaginate) dtBottomBar.append(dtPaginate);

  function hasActiveFilters() {
    const globalSearch = dataTable.search();
    if (globalSearch) return true;
    let hasColumn = false;
    dataTable.columns().every(function () {
      if (this.search()) hasColumn = true;
    });
    return hasColumn;
  }

  function updateControls() {
    const visibleRows = dataTable.rows({search: "applied"}).data().toArray();
    const visibleSourceRows = visibleRows.map((row) => row.__source);
    summary.textContent = `${visibleRows.length.toLocaleString("pt-BR")} registro${visibleRows.length === 1 ? "" : "s"} encontrado${visibleRows.length === 1 ? "" : "s"} na tabela`;
    exportBtn.textContent = `Exportar tabela (${visibleRows.length.toLocaleString("pt-BR")})`;
    exportBtn.disabled = visibleRows.length === 0;
    clearFiltersBtn.style.display = hasActiveFilters() ? "" : "none";
    onFilteredRowsChange?.(visibleSourceRows);
  }

  clearFiltersBtn.addEventListener("click", () => {
    dataTable.search("");
    dataTable.columns().search("");
    filterRow.querySelectorAll("select").forEach((s) => (s.value = ""));
    filterRow.querySelectorAll("input").forEach((i) => (i.value = ""));
    const globalInput = dtWrapper?.querySelector(".dt-search input, .dataTables_filter input");
    if (globalInput) globalInput.value = "";
    dataTable.draw();
  });

  exportBtn.addEventListener("click", () => {
    const visibleRows = dataTable.rows({search: "applied"}).data().toArray().map((row) => row.__source);
    exportRowsToXlsx(visibleRows, columns, headers, exportFilePrefix);
  });

  dataTable.on("draw", updateControls);
  updateControls();

  invalidation.then(() => {
    dataTable.off("draw", updateControls);
    dataTable.destroy();
  });

  return root;
}
