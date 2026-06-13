import os
import sys
import argparse
import tempfile
import urllib.request
import http.cookiejar
from pathlib import Path
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, Date
from sqlalchemy.engine import URL
import unicodedata
import re


# =========================
# CONFIGURAÇÕES DO USUÁRIO
# =========================
ARQUIVOS_E_TABELAS = {
    # Arquivos locais fixos (opcional). Pares URL/tabela vêm do config.env.
}

# Pares (URL, TABELA, ABA) lidos do config.env. Cada entrada define a variável
# de ambiente que contém a URL do xlsx, a variável com o nome da tabela destino
# e, opcionalmente, o nome da aba (sheet) a ser lida. sheet=None lê a 1ª aba.
# Uma mesma URL pode alimentar várias tabelas (uma por aba); o download é cacheado.
URLS_E_TABELAS_ENV = [
    ("URL_PBI_CAIXA_OGU", "TAB_BANCO_OGU", None),
    ("URL_PBI_CAIXA_OGU", "TAB_BANCO_OGU_SUSP_APRE", "Suspensiva Doc Apre"),
    ("URL_PBI_CAIXA_OGU", "TAB_BANCO_OGU_SUSP_NAO_APRE", "Suspensiva Doc Não Apre"),
    ("URL_PBI_CAIXA_FIN", "TAB_BANCO_FIN", None),
]

SCHEMA_PADRAO = "se_cgpac"

# Usuários que receberão GRANT nas tabelas carregadas.
# Configurável via DB_USUARIOS_PERMISSAO no config.env (lista separada por vírgula).
# Vazio = nenhum GRANT.

COLUNAS_FORCAR_STRING = [
    "proposta_nu",
    "convenio_co",
    "operacao_nu",
]


# =========================
# Configurações e Helpers
# =========================
def slugify(value):
    """
    Normaliza string para ser usada como nome de tabela/coluna.
    Remove acentos, caracteres especiais e espaços.
    """
    if not isinstance(value, str):
        value = str(value)
    value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    )
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    return re.sub(r"[-\s]+", "_", value)


def qident(name: str) -> str:
    """Quote seguro para identificadores SQL (schema/tabela/coluna)."""
    if name is None:
        raise ValueError("Identificador None não é permitido.")
    return '"' + name.replace('"', '""') + '"'


def load_db_config(env_path="config.env"):
    """Carrega variáveis de ambiente e valida."""
    if not os.path.exists(env_path):
        env_path = Path(__file__).parent / "config.env"

    load_dotenv(env_path)

    config = {
        "host": os.getenv("DB_HOST"),
        "database": os.getenv("DB_DATABASE") or os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "port": os.getenv("DB_PORT") or "5432",
    }

    if not all([config["host"], config["database"], config["user"]]):
        print("[ERRO] Variáveis de ambiente incompletas no arquivo .env.")
        print(f"       DB_HOST={config['host']}")
        print(f"       DB_DATABASE={config['database']}")
        print(f"       DB_USER={config['user']}")
        if not config["password"]:
            print("       DB_PASSWORD=(vazio)")
        sys.exit(1)

    return config


def criar_engine_db(config):
    url = URL.create(
        drivername="postgresql+psycopg2",
        username=config["user"],
        password=config["password"],
        host=config["host"],
        port=int(config["port"]),
        database=config["database"],
    )
    return create_engine(url)


# =========================
# Download de arquivos remotos
# =========================
def baixar_arquivo(url: str, destino_dir: Path) -> Path:
    """
    Baixa um arquivo a partir de uma URL para o diretório de destino.
    Retorna o Path do arquivo baixado.
    """
    nome = url.rstrip("/").split("/")[-1] or "arquivo_baixado"
    destino = destino_dir / nome
    print(f"[INFO] Baixando {url} -> {destino}")

    # Opener com CookieJar: o site da Caixa faz 302 setando cookie de sessão,
    # e sem persistir o cookie entre redirects o urllib entra em loop.
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cookie_jar),
        urllib.request.HTTPRedirectHandler(),
    )
    opener.addheaders = [
        (
            "User-Agent",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36",
        ),
        ("Accept", "*/*"),
        ("Accept-Language", "pt-BR,pt;q=0.9,en;q=0.8"),
    ]

    with opener.open(url, timeout=120) as resp, open(destino, "wb") as f:
        while True:
            chunk = resp.read(1024 * 64)
            if not chunk:
                break
            f.write(chunk)

    print(f"[INFO] Download concluído ({destino.stat().st_size} bytes).")
    return destino


def resolver_pares_env() -> list:
    """
    Lê os trios URL/TABELA/ABA declarados em URLS_E_TABELAS_ENV a partir das
    variáveis de ambiente carregadas pelo config.env.
    Retorna lista de tuplas (url, tabela, sheet).
    """
    pares = []
    for url_key, tab_key, sheet_name in URLS_E_TABELAS_ENV:
        url = os.getenv(url_key)
        tabela = os.getenv(tab_key)
        if not url or not tabela:
            print(
                f"[WARN] Ignorando par ({url_key}, {tab_key}): "
                f"url={'ok' if url else 'faltando'}, tabela={'ok' if tabela else 'faltando'}"
            )
            continue
        url = url.strip().strip('"').strip("'")
        tabela = tabela.strip().strip('"').strip("'")
        pares.append((url, tabela, sheet_name))
    return pares


# =========================
# Lógica de Leitura e Tratamento
# =========================
def infer_and_convert_types(df):
    """
    Tenta converter colunas object/string para numérico ou data.
    """
    print("Iniciando inferência de tipos...")

    cols_to_skip = set()
    if COLUNAS_FORCAR_STRING:
        cols_to_skip = {slugify(c) for c in COLUNAS_FORCAR_STRING}
        if cols_to_skip:
            print(f"[CONFIG] Ignorando inferência para colunas: {cols_to_skip}")

    for col in df.columns:
        if col in cols_to_skip:
            continue

        if df[col].dtype == "object":
            try:
                sample = df[col].dropna().astype(str).head(100)
                if sample.empty:
                    continue

                if sample.str.contains(r"^\d+,\d+$").any():
                    df[col] = (
                        df[col]
                        .astype(str)
                        .str.replace(".", "", regex=False)
                        .str.replace(",", ".", regex=False)
                    )
                    df[col] = pd.to_numeric(df[col], errors="raise")
                    print(
                        f"  - Coluna '{col}' convertida para NUMERIC (vírgula decimal)"
                    )
                    continue

                df[col] = pd.to_numeric(df[col], errors="raise")
                print(f"  - Coluna '{col}' convertida para NUMERIC")
                continue
            except Exception:
                pass

            # Só tenta parse de data se a amostra realmente parecer data —
            # evita que pandas caia no dateutil linha-a-linha em colunas
            # não-data (warning "Could not infer format").
            if sample.str.match(
                r"^\s*\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}"
                r"(?:[ T]\d{1,2}:\d{2}(?::\d{2})?)?\s*$"
            ).any():
                try:
                    df[col] = pd.to_datetime(
                        df[col], dayfirst=True, format="mixed", errors="raise"
                    )
                    print(f"  - Coluna '{col}' convertida para DATETIME")
                    continue
                except Exception:
                    pass

    return df


def ler_arquivo(caminho_arquivo, sheet_name=None):
    path = Path(caminho_arquivo)
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho_arquivo}")

    ext = path.suffix.lower()
    # sheet_name=None no pandas significaria "todas as abas"; para a 1ª aba usamos 0.
    sheet = 0 if sheet_name is None else sheet_name
    print(
        f"[INFO] Lendo arquivo '{path.name}' como {ext}"
        + (f" (aba '{sheet_name}')" if sheet_name else "")
        + "..."
    )

    dtype_dict = None
    if COLUNAS_FORCAR_STRING and ext in [".xlsx", ".csv"]:
        try:
            if ext == ".xlsx":
                cols_present = pd.read_excel(caminho_arquivo, sheet_name=sheet, nrows=0).columns
            else:
                try:
                    cols_present = pd.read_csv(
                        caminho_arquivo,
                        sep=None,
                        engine="python",
                        encoding="utf-8",
                        nrows=0,
                    ).columns
                except UnicodeDecodeError:
                    cols_present = pd.read_csv(
                        caminho_arquivo,
                        sep=None,
                        engine="python",
                        encoding="latin1",
                        nrows=0,
                    ).columns

            dtype_dict = {}
            for config_col in COLUNAS_FORCAR_STRING:
                slug_config = slugify(config_col)
                for file_col in cols_present:
                    if slugify(file_col) == slug_config:
                        dtype_dict[file_col] = str
                        print(
                            f"[INFO] Forçando leitura como string para: '{file_col}' (match com '{config_col}')"
                        )
        except Exception as e:
            print(
                f"[WARN] Não foi possível pré-ler colunas para aplicar filtro de tipos: {e}"
            )

    try:
        if ext == ".xlsx":
            df = pd.read_excel(caminho_arquivo, sheet_name=sheet, dtype=dtype_dict)

        elif ext == ".csv":
            try:
                df = pd.read_csv(
                    caminho_arquivo,
                    sep=None,
                    engine="python",
                    encoding="utf-8",
                    dtype=dtype_dict,
                )
            except UnicodeDecodeError:
                df = pd.read_csv(
                    caminho_arquivo,
                    sep=None,
                    engine="python",
                    encoding="latin1",
                    dtype=dtype_dict,
                )

        elif ext == ".parquet":
            df = pd.read_parquet(caminho_arquivo)

        else:
            raise ValueError(
                f"Extensão '{ext}' não suportada. Use .xlsx, .csv ou .parquet."
            )

        print(
            f"[INFO] Arquivo lido com sucesso. Linhas: {len(df)}, Colunas: {len(df.columns)}"
        )
        return df

    except Exception as e:
        raise RuntimeError(f"Falha ao ler arquivo: {e}") from e


def preparar_dataframe(df):
    df.columns = [slugify(c) for c in df.columns]
    df = infer_and_convert_types(df)

    if "dte_carga" not in df.columns:
        df["dte_carga"] = datetime.now()

    return df


# =========================
# Lógica de Banco
# =========================
def schema_existe(connection, schema: str) -> bool:
    sql = text("SELECT 1 FROM information_schema.schemata WHERE schema_name = :schema")
    return connection.execute(sql, {"schema": schema}).scalar() is not None


def garantir_schema(connection, schema: str):
    if not schema_existe(connection, schema):
        try:
            connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {qident(schema)}"))
            print(f"[INFO] Schema '{schema}' criado.")
        except Exception as e:
            print(f"[WARN] Não foi possível criar schema '{schema}': {e}")


def tabela_existe(connection, schema: str, tabela: str) -> bool:
    sql = text("""
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = :schema
          AND table_name = :tabela
    """)
    return (
        connection.execute(sql, {"schema": schema, "tabela": tabela}).scalar()
        is not None
    )


def truncar_tabela(connection, schema: str, tabela: str):
    sql = text(f"TRUNCATE TABLE {qident(schema)}.{qident(tabela)}")
    connection.execute(sql)
    print(f"[INFO] Tabela {schema}.{tabela} truncada com sucesso.")


def conceder_permissoes(connection, schema, tabela, usuarios):
    if not usuarios:
        return

    usuarios_str = ", ".join(qident(u) for u in usuarios)
    sql = text(f"""
        GRANT INSERT, TRUNCATE, SELECT, UPDATE, REFERENCES, DELETE, TRIGGER
        ON TABLE {qident(schema)}.{qident(tabela)}
        TO {usuarios_str};
    """)
    try:
        connection.execute(sql)
        print(f"[INFO] Permissões concedidas a: {', '.join(usuarios)}")
    except Exception as e:
        print(f"[WARN] Falha ao conceder permissões: {e}")


# =========================
# Lógica de Upload
# =========================
def processar_upload(
    engine,
    file_path: Path,
    table_name: str,
    schema: str,
    modo_carga: str,
    usuarios: list,
    sheet_name=None,
):
    print("=" * 60)
    print(f"Processando Arquivo: {file_path}")
    if sheet_name:
        print(f"Aba: {sheet_name}")
    print(f"Destino: {schema}.{table_name}")
    print(f"Modo: {modo_carga.upper()}")
    print("=" * 60)

    try:
        df = ler_arquivo(file_path, sheet_name=sheet_name)
    except Exception as e:
        print(f"[ERRO] Pulo arquivo {file_path} devido a erro de leitura: {e}")
        return

    try:
        df = preparar_dataframe(df)
    except Exception as e:
        print(f"[ERRO] Falha no tratamento do dataframe: {e}")
        return

    print("\nTipos finais do DataFrame:")
    print(df.dtypes)
    print("-" * 30)

    try:
        with engine.begin() as conn:
            garantir_schema(conn, schema)
            print(f"[INFO] Iniciando envio para o banco ({modo_carga})...")

            dtype_mapping = {
                col: Date for col in df.select_dtypes(include=["datetime"]).columns
            }

            existe = tabela_existe(conn, schema, table_name)

            if modo_carga == "append":
                df.to_sql(
                    table_name,
                    conn,
                    schema=schema,
                    if_exists="append",
                    index=False,
                    chunksize=5000,
                    method="multi",
                    dtype=dtype_mapping,
                )

            elif modo_carga == "replace":
                if existe:
                    print("[INFO] Tabela já existe. Executando TRUNCATE + APPEND.")
                    truncar_tabela(conn, schema, table_name)

                    df.to_sql(
                        table_name,
                        conn,
                        schema=schema,
                        if_exists="append",
                        index=False,
                        chunksize=5000,
                        method="multi",
                        dtype=dtype_mapping,
                    )
                else:
                    print("[INFO] Tabela não existe. Criando nova tabela.")
                    df.to_sql(
                        table_name,
                        conn,
                        schema=schema,
                        if_exists="fail",
                        index=False,
                        chunksize=5000,
                        method="multi",
                        dtype=dtype_mapping,
                    )
            else:
                raise ValueError(f"Modo de carga inválido: {modo_carga}")

            print(f"[SUCESSO] {len(df)} registros enviados para {schema}.{table_name}.")
            conceder_permissoes(conn, schema, table_name, usuarios)

    except Exception as e:
        print(f"\n[ERRO CRÍTICO] Falha no upload de {file_path}: {e}")


# =========================
# Main
# =========================
def main():
    parser = argparse.ArgumentParser(
        description="Upload genérico de arquivos (xlsx, csv, parquet) para PostgreSQL."
    )
    parser.add_argument(
        "arquivo",
        nargs="?",
        help="Caminho do arquivo a ser enviado (opcional se ARQUIVOS_E_TABELAS estiver preenchido).",
    )
    parser.add_argument(
        "--tabela",
        "-t",
        help="Nome da tabela de destino (opcional).",
    )
    parser.add_argument(
        "--schema",
        "-s",
        default=SCHEMA_PADRAO,
        help=f"Schema do banco (default: {SCHEMA_PADRAO}).",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Se ativado, adiciona os dados à tabela existente. Sem essa flag, substitui o conteúdo da tabela sem derrubá-la.",
    )

    args = parser.parse_args()

    try:
        db_config = load_db_config()
        engine = criar_engine_db(db_config)
    except Exception as e:
        print(f"[ERRO] Falha na conexão com banco: {e}")
        sys.exit(1)

    lista_execucao = []
    tmp_dir_ctx = None

    if args.arquivo:
        fpath = Path(args.arquivo)
        tname = args.tabela if args.tabela else slugify(fpath.stem)
        lista_execucao.append((fpath, tname, None))

    else:
        for caminho, tabela in ARQUIVOS_E_TABELAS.items():
            if not caminho:
                continue
            fpath = Path(caminho)
            tname = tabela if tabela else slugify(fpath.stem)
            lista_execucao.append((fpath, tname, None))

        pares_env = resolver_pares_env()
        if pares_env:
            tmp_dir_ctx = tempfile.TemporaryDirectory(prefix="upload_generico_")
            tmp_dir = Path(tmp_dir_ctx.name)
            print(f"[INFO] Diretório temporário para downloads: {tmp_dir}")
            # Cache de downloads por URL: a mesma URL pode alimentar várias
            # tabelas (uma por aba) e só deve ser baixada uma vez.
            downloads_por_url = {}
            for url, tabela, sheet in pares_env:
                fpath = downloads_por_url.get(url)
                if fpath is None:
                    try:
                        fpath = baixar_arquivo(url, tmp_dir)
                    except Exception as e:
                        print(f"[ERRO] Falha ao baixar {url}: {e}")
                        downloads_por_url[url] = False
                        continue
                    downloads_por_url[url] = fpath
                elif fpath is False:
                    continue  # download dessa URL já falhou antes
                lista_execucao.append((fpath, tabela, sheet))

        if not lista_execucao:
            parser.error(
                "Nenhum arquivo para processar: sem argumentos, ARQUIVOS_E_TABELAS vazio "
                "e nenhum par URL/TABELA válido no config.env."
            )

    modo_carga = "append" if args.append else "replace"

    usuarios_permissao = [
        u.strip()
        for u in (os.getenv("DB_USUARIOS_PERMISSAO") or "").split(",")
        if u.strip()
    ]
    if usuarios_permissao:
        print(f"[INFO] Usuários para GRANT: {usuarios_permissao}")

    print(f"Iniciando processamento de {len(lista_execucao)} arquivos...")

    try:
        for fpath, tname, sheet in lista_execucao:
            processar_upload(
                engine=engine,
                file_path=fpath,
                table_name=tname,
                schema=args.schema,
                modo_carga=modo_carga,
                usuarios=usuarios_permissao,
                sheet_name=sheet,
            )
    finally:
        if tmp_dir_ctx is not None:
            tmp_dir_ctx.cleanup()
            print("[INFO] Diretório temporário de downloads removido.")


if __name__ == "__main__":
    main()