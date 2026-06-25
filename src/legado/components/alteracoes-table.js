import {html} from "htl";
import * as XLSX from "xlsx";
import DataTable from "datatables.net-responsive-dt";

const tableColumns = [
  {key: "data_fmt", label: "Data", filter: "text", className: "col-data"},
  {key: "operacao", label: "Operação", filter: "text", className: "col-tci"},
  {key: "uf", label: "UF", filter: "select", className: "col-uf"},
  {key: "municipio", label: "Município", filter: "text", className: "col-anterior"},
  {key: "modalidade", label: "Modalidade", filter: "select", className: "col-campo"},
  {key: "tipo", label: "Tipo", filter: "select", className: "col-tipo"},
  {key: "natureza", label: "Natureza", filter: "select", className: "col-natureza"},
  {key: "campo", label: "Campo", filter: "select", className: "col-campo"},
  {key: "anterior", label: "Valor Anterior", filter: "text", className: "col-anterior"},
  {key: "atual", label: "Valor Atual", filter: "text", className: "col-atual"},
];

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

function exportAlteracoesRows(rows) {
  const exportRows = rows.map((row) => ({
    Data: row.data_fmt ?? "",
    Operação: row.operacao ?? "",
    UF: row.uf ?? "",
    Município: row.municipio ?? "",
    Modalidade: row.modalidade ?? "",
    Tipo: row.tipo ?? "",
    Natureza: row.natureza ?? "",
    Campo: row.campo ?? "",
    "Valor Anterior": row.anterior ?? "",
    "Valor Atual": row.atual ?? "",
  }));

  const worksheet = XLSX.utils.json_to_sheet(exportRows, {cellDates: true});
  applyNumericCellFormat(worksheet);
  applyColumnWidths(worksheet, exportRows.map(Object.values), Object.keys(exportRows[0] ?? {}));
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, "Alterações");
  const stamp = new Date().toISOString().slice(0, 10);
  XLSX.writeFileXLSX(workbook, `legadoogu-alteracoes-${stamp}.xlsx`);
}

function columnOptions(rows, key) {
  return [...new Set(rows.map((row) => row[key]).filter((value) => value && value !== "—"))]
    .sort((a, b) => String(a).localeCompare(String(b), "pt-BR"));
}

export function renderAlteracoesDataTable(rows, invalidation) {
  const headerRow = html`<tr>${tableColumns.map((column) => html`<th>${column.label}</th>`)}</tr>`;
  const filterRow = html`<tr class="datatable-filters-row">${tableColumns.map(() => html`<th></th>`)}</tr>`;
  const table = html`<table class="display nowrap alteracoes-datatable" style="width:100%">
    <thead>${headerRow}${filterRow}</thead>
  </table>`;
  const tableScroll = html`<div class="datatable-scroll"></div>`;
  tableScroll.append(table);

  const summary = html`<p class="metric-detail datatable-summary"></p>`;
  const exportBtn = html`<button class="export-btn" type="button"></button>`;
  const controls = html`<div class="table-controls table-controls--top"></div>`;
  controls.append(summary, exportBtn);
  const dtTopBar = html`<div class="datatable-toolbar datatable-toolbar--top"></div>`;
  const dtBottomBar = html`<div class="datatable-toolbar datatable-toolbar--bottom"></div>`;

  const root = html`<div class="datatable-block"></div>`;
  root.append(controls, dtTopBar, tableScroll, dtBottomBar);

  const dataTable = new DataTable(table, {
    data: rows,
    autoWidth: false,
    orderCellsTop: true,
    pageLength: 25,
    lengthMenu: [10, 25, 50, 100],
    order: [[0, "desc"]],
    responsive: true,
    columns: [
      {
        data: "data_fmt",
        title: "Data",
        className: "col-data",
        width: "88px",
        render: (data, type, row) => {
          if (type === "sort" || type === "type") return row.data instanceof Date ? row.data.getTime() : 0;
          return data;
        },
      },
      {data: "operacao", title: "Operação", className: "col-tci", width: "100px"},
      {data: "uf", title: "UF", className: "col-uf", width: "48px"},
      {data: "municipio", title: "Município", className: "col-anterior", width: "160px"},
      {data: "modalidade", title: "Modalidade", className: "col-campo", width: "176px"},
      {data: "tipo", title: "Tipo", className: "col-tipo", width: "80px"},
      {data: "natureza", title: "Natureza", className: "col-natureza", width: "144px"},
      {data: "campo", title: "Campo", className: "col-campo", width: "160px"},
      {data: "anterior", title: "Valor Anterior", className: "col-anterior", width: "176px"},
      {data: "atual", title: "Valor Atual", className: "col-atual", width: "176px"},
    ],
    columnDefs: [
      {targets: [3, 4, 8, 9], className: "dt-body-wrap"},
    ],
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

      tableColumns.forEach((column, index) => {
        const cell = filterRow.cells[index];
        const label = column.label;

        if (column.filter === "select") {
          const select = document.createElement("select");
          select.className = `datatable-filter ${column.className || ""}`.trim();
          select.setAttribute("aria-label", `Filtrar coluna ${label}`);
          select.innerHTML = `<option value="">Todos</option>`;

          for (const value of columnOptions(rows, column.key)) {
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
          return;
        }

        const input = document.createElement("input");
        input.className = `datatable-filter ${column.className || ""}`.trim();
        input.type = "search";
        input.placeholder = label;
        input.setAttribute("aria-label", `Filtrar coluna ${label}`);
        input.addEventListener("input", () => {
          api.column(index).search(input.value).draw();
        });

        cell.replaceChildren(input);
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

  function updateControls() {
    const visibleRows = dataTable.rows({search: "applied"}).data().toArray();
    summary.textContent = `${visibleRows.length.toLocaleString("pt-BR")} registro${visibleRows.length === 1 ? "" : "s"} encontrado${visibleRows.length === 1 ? "" : "s"} na tabela`;
    exportBtn.textContent = `Exportar tabela (${visibleRows.length.toLocaleString("pt-BR")})`;
    exportBtn.disabled = visibleRows.length === 0;
  }

  exportBtn.addEventListener("click", () => {
    const visibleRows = dataTable.rows({search: "applied"}).data().toArray();
    exportAlteracoesRows(visibleRows);
  });

  dataTable.on("draw", updateControls);
  updateControls();

  invalidation.then(() => {
    dataTable.off("draw", updateControls);
    dataTable.destroy();
  });

  return root;
}
