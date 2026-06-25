// Baixa a planilha-fonte (Relatorios_Analiticos_PBI.xlsx) direto do site da Caixa
// e atualiza a cópia local em data/. Assim não é preciso fornecer o arquivo manualmente.
//
// É o mesmo arquivo usado pelo Painel OGU (painelogu/python/config.env → URL_PBI_CAIXA_OGU).
// O site da Caixa responde 302 setando um cookie de sessão; por isso seguimos o redirect
// manualmente, reenviando o cookie e um User-Agent de navegador.
//
// URL pode ser sobrescrita pela env LEGADO_XLSX_URL.

import {renameSync, writeFileSync} from "node:fs";
import * as XLSX from "xlsx";
import {XLSX_PATH, SHEET_NAME} from "./legado-extract.mjs";

const URL_PADRAO = "https://www.caixa.gov.br/Downloads/orgaos-publicos-novo-pac/Relatorios_Analiticos_PBI.xlsx";
const URL_FONTE = process.env.LEGADO_XLSX_URL || URL_PADRAO;

const HEADERS_BASE = {
  "User-Agent":
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 " +
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
  "Accept": "*/*",
  "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
};

// Faz o GET seguindo redirects manualmente e propagando o cookie de sessão.
async function baixarComCookie(url, maxHops = 5) {
  let alvo = url;
  let cookie = "";

  for (let hop = 0; hop <= maxHops; hop++) {
    const headers = {...HEADERS_BASE};
    if (cookie) headers["Cookie"] = cookie;

    const res = await fetch(alvo, {redirect: "manual", headers});

    if (res.status >= 300 && res.status < 400) {
      const setCookie = res.headers.getSetCookie?.() ?? [];
      if (setCookie.length) {
        const novos = setCookie.map((c) => c.split(";")[0]).join("; ");
        cookie = cookie ? `${cookie}; ${novos}` : novos;
      }
      const location = res.headers.get("location");
      if (!location) throw new Error(`Redirect ${res.status} sem header location`);
      alvo = new URL(location, alvo).toString();
      continue;
    }

    if (!res.ok) throw new Error(`HTTP ${res.status} ao baixar ${alvo}`);
    return Buffer.from(await res.arrayBuffer());
  }

  throw new Error(`Excesso de redirects (>${maxHops}) ao baixar ${url}`);
}

async function main() {
  console.log(`[INFO] Baixando ${URL_FONTE}`);
  const buffer = await baixarComCookie(URL_FONTE);
  console.log(`[INFO] Download concluído (${buffer.length.toLocaleString("pt-BR")} bytes).`);

  // Valida que é um xlsx com a aba esperada antes de sobrescrever a cópia local.
  const wb = XLSX.read(buffer, {type: "buffer"});
  const ws = wb.Sheets[SHEET_NAME];
  if (!ws) {
    throw new Error(
      `Aba "${SHEET_NAME}" não encontrada no arquivo baixado. Abas: ${wb.SheetNames.join(", ")}`
    );
  }
  const linhas = XLSX.utils.sheet_to_json(ws);
  const cabecalho = XLSX.utils.sheet_to_json(ws, {header: 1})[0] ?? [];
  const obrigatorias = ["OPERAÇÃO", "SITUAÇÃO DA OBRA CASA CIVIL"];
  const faltando = obrigatorias.filter((c) => !cabecalho.includes(c));
  if (faltando.length) {
    throw new Error(`Cabeçalho inesperado na aba "${SHEET_NAME}" — faltam colunas: ${faltando.join(", ")}`);
  }

  // Gravação atômica: escreve em .tmp e renomeia.
  const tmp = `${XLSX_PATH}.tmp`;
  writeFileSync(tmp, buffer);
  renameSync(tmp, XLSX_PATH);

  console.log(
    `[OK] Planilha atualizada: ${XLSX_PATH}\n` +
    `     Aba "${SHEET_NAME}" com ${linhas.length.toLocaleString("pt-BR")} linhas.`
  );
}

main().catch((err) => {
  console.error(`[ERRO] ${err.message}`);
  process.exit(1);
});
