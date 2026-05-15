"""
Gera a base PC 32 consultando o PostgreSQL e salva os CSVs do painel.

Uso:
  1. Preencha o arquivo config.env com as credenciais do banco
  2. uv run 2_gerar_base_pc32.py
"""

import csv
import json
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

from comparar_snapshots_base import generate_daily_snapshot_diff

load_dotenv(os.path.join(os.path.dirname(__file__), "config.env"))

DATABASE_URL = URL.create(
    drivername="postgresql+psycopg2",
    username=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT", "5432")),
    database=os.getenv("DB_NAME"),
)

CSV_OUTPUT = os.path.join(os.path.dirname(__file__), "..", "src", "data", "base_pc_32.csv")
HISTORY_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "historico")
DIFF_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "diff")
LATEST_DIFF_JSON = os.path.join(os.path.dirname(__file__), "..", "src", "data", "base_diff_latest.json")
SOURCE_FRESHNESS_OUTPUT = os.path.join(os.path.dirname(__file__), "..", "src", "data", "source_freshness.json")
PREVIOUS_CSV_OUTPUT = os.path.join(os.path.dirname(__file__), "..", "src", "data", "base_pc_32_previous.csv")
FIRST_CSV_OUTPUT = os.path.join(os.path.dirname(__file__), "..", "src", "data", "base_pc_32_first.csv")
CUMULATIVE_DIFF_OUTPUT = os.path.join(os.path.dirname(__file__), "..", "src", "data", "base_alteracoes.csv")

QUERY = text("""
WITH publicacao_licitacao AS (
    SELECT tl.num_convenio,
           min(tl.dte_publicacao_licitacao) AS dte_publicacao_licitacao
    FROM mcid_transferegov.tab_licitacao tl
    GROUP BY tl.num_convenio
),
homologacao_licitacao AS (
    SELECT tl.num_convenio,
           min(tl.dte_homologacao_licitacao) AS dte_homologacao_licitacao
    FROM mcid_transferegov.tab_licitacao tl
    GROUP BY tl.num_convenio
),
constantes AS (
    SELECT '2025-10-21'::date AS data_publicacao_pc72,
           '2026-06-01'::date AS data_limite_licitacao_casa_civil
),
base AS (
    SELECT
        tci.cod_tci AS cod_tci_tci,
        tci.cod_tci AS cod_tci,
        tci.num_convenio AS num_convenio_tci,
        tci.txt_uf AS txt_uf_tci,
        tci.txt_regiao AS txt_regiao_tci,
        tci.cod_ibge_7dig AS cod_ibge_7dig_tci,
        tci.txt_municipio AS txt_municipio_tci,
        tci.txt_tomador AS txt_tomador_tci,
        tci.dsc_objeto_instrumento AS dsc_objeto_instrumento_tci,
        tci.txt_sigla_secretaria AS txt_sigla_secretaria_tci,
        tci.dsc_fase_pac AS dsc_fase_pac_tci,
        tci.txt_modalidade AS txt_modalidade_tci,
        tci.dsc_situacao_contrato_mcid AS dsc_situacao_contrato_mcid_tci,
        tci.dte_assinatura_contrato AS dte_assinatura_contrato_tci,
        pbi.situacao_da_analise_suspensiva AS situacao_da_analise_suspensiva_pbi,
        pbi.vencimento_da_suspensiva AS vencimento_da_suspensiva_pbi,
        tcon.dte_retirada_suspensiva AS dte_retirada_suspensiva_tgov,
        tdb.dte_primeira_data_lae AS dte_primeira_data_lae_tdb,
        pl.dte_publicacao_licitacao AS dte_publicacao_licitacao_tgov,
        hl.dte_homologacao_licitacao AS dte_homologacao_licitacao_tgov,
        tdb.dte_vrpl AS dte_vrpl_tdb,
        tdb.dte_aio AS dte_aio_tdb,
        tci.dte_inicio_obra_mcid AS dte_inicio_obra_mcid_tci,
        tci.vlr_repasse AS vlr_repasse_tci,
        -- perspectiva de retirada da suspensiva | fonte: se_cgpac."Suspensiva29_04"
        s29.pespectiva_de_retirada_da_suspensiva AS perspectiva_de_retirada_da_suspensiva,

        -- status_suspensiva | fonte: derivada de pbi + tcon
        CASE
            WHEN pbi.vencimento_da_suspensiva IS NOT NULL
             AND tcon.dte_retirada_suspensiva IS NULL
            THEN 'PENDENTE'
            WHEN tcon.dte_retirada_suspensiva IS NOT NULL
            THEN 'RETIRADA'
            ELSE 'SEM SUSPENSIVA'
        END AS status_suspensiva_calc,

        -- flags | fonte: derivadas de pl + hl
        CASE WHEN pl.dte_publicacao_licitacao IS NOT NULL THEN 'SIM' ELSE 'NAO' END AS flag_publicacao_licitacao_calc,
        CASE WHEN hl.dte_homologacao_licitacao IS NOT NULL THEN 'SIM' ELSE 'NAO' END AS flag_homologacao_licitacao_calc,

        -- ultima_data_relevante | fonte: derivada de tci + tdb + hl + pl
        greatest(
            tci.dte_inicio_obra_mcid, tdb.dte_aio, tdb.dte_vrpl,
            hl.dte_homologacao_licitacao, pl.dte_publicacao_licitacao,
            tdb.dte_primeira_data_lae
        ) AS ultima_data_relevante_calc,

        -- fase_atual | fonte: derivada de tci + tdb + hl + pl + tcon + pbi
        CASE
            WHEN tci.dte_inicio_obra_mcid IS NOT NULL THEN 'OBRA INICIADA'
            WHEN tdb.dte_aio IS NOT NULL THEN 'AIO'
            WHEN tdb.dte_vrpl IS NOT NULL THEN 'VRPL'
            WHEN hl.dte_homologacao_licitacao IS NOT NULL THEN 'HOMOLOGACAO'
            WHEN pl.dte_publicacao_licitacao IS NOT NULL THEN 'PUBLICACAO LICITACAO'
            WHEN tdb.dte_primeira_data_lae IS NOT NULL THEN 'LAE'
            WHEN tcon.dte_retirada_suspensiva IS NOT NULL THEN 'SUSPENSIVA RETIRADA'
            WHEN pbi.vencimento_da_suspensiva IS NOT NULL THEN 'SUSPENSIVA'
            ELSE 'SEM ANDAMENTO'
        END AS fase_atual_calc,

        -- intervalos em dias | fonte: derivados de pl + tdb + hl + tci
        (pl.dte_publicacao_licitacao - tdb.dte_primeira_data_lae) AS dias_ate_publicacao_calc,
        (hl.dte_homologacao_licitacao - pl.dte_publicacao_licitacao) AS dias_publicacao_ate_homologacao_calc,
        (tdb.dte_vrpl - hl.dte_homologacao_licitacao) AS dias_homologacao_ate_vrpl_calc,
        (tdb.dte_aio - tdb.dte_vrpl) AS dias_vrpl_ate_aio_calc,
        (tci.dte_inicio_obra_mcid - tdb.dte_aio) AS dias_aio_ate_inicio_obra_calc,

        -- faixa_repasse | fonte: derivada de tci.vlr_repasse
        CASE
            WHEN tci.vlr_repasse < 1000000 THEN 'ATE 1 MI'
            WHEN tci.vlr_repasse < 5000000 THEN '1 A 5 MI'
            WHEN tci.vlr_repasse < 10000000 THEN '5 A 10 MI'
            ELSE 'ACIMA DE 10 MI'
        END AS faixa_repasse_calc,

        -- prazos calculados | fonte: derivados de tcon + pl + tdb (contratos PC 72 — assinados antes de 21/10/2025 — não contam prazo)
        CASE WHEN tci.dte_assinatura_contrato < c.data_publicacao_pc72 THEN NULL
             WHEN tdb.dte_primeira_data_lae IS NOT NULL
             THEN tdb.dte_primeira_data_lae + 60
        END AS prazo_pub_licitacao_calc,

        -- soma de datas a partir da LAE (sempre que houver LAE; independente da regra PC 72)
        CASE WHEN tdb.dte_primeira_data_lae IS NOT NULL
             THEN tdb.dte_primeira_data_lae + 60
        END AS prazo_lae_mais_60_calc,

        CASE WHEN tdb.dte_primeira_data_lae IS NOT NULL
             THEN tdb.dte_primeira_data_lae + 60 + 120 + 60
        END AS prazo_lae_mais_60_mais_120_calc,

        CASE WHEN tci.dte_assinatura_contrato < c.data_publicacao_pc72 THEN NULL
             WHEN pl.dte_publicacao_licitacao IS NOT NULL
             THEN pl.dte_publicacao_licitacao + 120
        END AS prazo_homolog_licitacao_120d,

        -- prazo_inicio_obra: 10 dias uteis apos AIO
        CASE WHEN tdb.dte_aio IS NOT NULL THEN
            (SELECT (array_agg(d::date ORDER BY d))[10]
             FROM generate_series(
                 tdb.dte_aio + interval '1 day',
                 tdb.dte_aio + interval '16 days',
                 interval '1 day'
             ) d
             WHERE EXTRACT(DOW FROM d) NOT IN (0, 6))
        END AS prazo_inicio_obra_calc

    FROM se_saci.view_mat_carteira_investimento tci
    CROSS JOIN constantes c
    LEFT JOIN se_cgpac.tab_thiago_pbi_caixa_ogu pbi
        ON tci.num_convenio::numeric = pbi.instrumento::numeric
    LEFT JOIN mcid_bd_gestores.tab_dados_basicos tdb
        ON tci.num_convenio = tdb.cod_convenio_siafi
    LEFT JOIN publicacao_licitacao pl
        ON tci.num_convenio::numeric = pl.num_convenio::numeric
    LEFT JOIN homologacao_licitacao hl
        ON tci.num_convenio::numeric = hl.num_convenio::numeric
    LEFT JOIN mcid_transferegov.tab_convenios tcon
        ON tci.num_convenio::numeric = tcon.num_convenio::numeric
    LEFT JOIN se_cgpac."Suspensiva29_04" s29
        ON tci.num_convenio::text = s29.instrumento::text
    WHERE tci.txt_fonte = 'OGU'
      AND tci.dsc_fase_pac = 'NOVO PAC - Seleção'
      AND tci.txt_sigla_secretaria <> 'SNH'
),
resultado AS (
SELECT
    base.*,

    -- data limite casa civil | fonte: constante fixa
    c.data_limite_licitacao_casa_civil AS data_limite_licitacao_casa_civil_const,

    -- status regra casa civil | fonte: derivada de base.dsc_situacao_contrato_mcid + base.dte_publicacao_licitacao + base.dte_homologacao_licitacao + base.dte_inicio_obra_mcid
    CASE
        WHEN dsc_situacao_contrato_mcid_tci = 'Cancelado ou Distratado' THEN 'Fora do escopo'
        WHEN dte_publicacao_licitacao_tgov IS NOT NULL AND dte_publicacao_licitacao_tgov <= c.data_limite_licitacao_casa_civil
         AND dte_homologacao_licitacao_tgov IS NOT NULL AND dte_homologacao_licitacao_tgov <= c.data_limite_licitacao_casa_civil
         AND dte_inicio_obra_mcid_tci IS NOT NULL AND dte_inicio_obra_mcid_tci <= c.data_limite_licitacao_casa_civil
        THEN 'Cumpriu o prazo'
        ELSE 'Pendente'
    END AS status_regra_casa_civil_calc,

    -- prazo homologacao: o maior entre publicacao + 120 dias e a data limite casa civil
    GREATEST(prazo_homolog_licitacao_120d, c.data_limite_licitacao_casa_civil) AS prazo_homolog_licitacao_calc,

    -- status publicacao licitacao | fonte: derivada de base.dte_primeira_data_lae + base.dsc_situacao_contrato_mcid + base.dte_publicacao_licitacao + base.prazo_pub_licitacao
    CASE
        WHEN dte_assinatura_contrato_tci < c.data_publicacao_pc72 THEN NULL
        WHEN dte_primeira_data_lae_tdb IS NULL
          OR dsc_situacao_contrato_mcid_tci = 'Cancelado ou Distratado' THEN NULL
        WHEN dte_publicacao_licitacao_tgov IS NOT NULL
         AND dte_publicacao_licitacao_tgov <= prazo_pub_licitacao_calc THEN 'Concluída no prazo'
        WHEN dte_publicacao_licitacao_tgov IS NOT NULL THEN 'Concluída em atraso'
        WHEN CURRENT_DATE > prazo_pub_licitacao_calc THEN 'Vencida'
        WHEN (prazo_pub_licitacao_calc - CURRENT_DATE) <= 30 THEN 'Próximos 30 dias'
        ELSE 'No prazo'
    END AS status_pub_licitacao_calc,

    -- status homologacao licitacao | fonte: derivada de base.dte_homologacao_licitacao + base.dte_publicacao_licitacao + base.dsc_situacao_contrato_mcid + GREATEST(pub+120, data_limite_casa_civil)
    CASE
        WHEN dte_assinatura_contrato_tci < c.data_publicacao_pc72 THEN NULL
        WHEN dte_homologacao_licitacao_tgov IS NOT NULL
         AND dte_publicacao_licitacao_tgov IS NULL THEN 'Inconsistência de base'
        WHEN dte_publicacao_licitacao_tgov IS NULL
          OR dsc_situacao_contrato_mcid_tci = 'Cancelado ou Distratado' THEN NULL
        WHEN dte_homologacao_licitacao_tgov IS NOT NULL
         AND dte_homologacao_licitacao_tgov <= GREATEST(prazo_homolog_licitacao_120d, c.data_limite_licitacao_casa_civil) THEN 'Concluída no prazo'
        WHEN dte_homologacao_licitacao_tgov IS NOT NULL THEN 'Concluída em atraso'
        WHEN CURRENT_DATE > GREATEST(prazo_homolog_licitacao_120d, c.data_limite_licitacao_casa_civil) THEN 'Vencida'
        WHEN (GREATEST(prazo_homolog_licitacao_120d, c.data_limite_licitacao_casa_civil) - CURRENT_DATE) <= 30 THEN 'Próximos 30 dias'
        ELSE 'No prazo'
    END AS status_homolog_licitacao_calc,

    -- status inicio obra | fonte: derivada de base.dte_aio + base.dsc_situacao_contrato_mcid + base.dte_inicio_obra_mcid + base.prazo_inicio_obra
    CASE
        WHEN dte_aio_tdb IS NULL
          OR dsc_situacao_contrato_mcid_tci = 'Cancelado ou Distratado' THEN NULL
        WHEN dte_inicio_obra_mcid_tci IS NOT NULL
         AND dte_inicio_obra_mcid_tci <= prazo_inicio_obra_calc THEN 'Iniciada no prazo'
        WHEN dte_inicio_obra_mcid_tci IS NOT NULL THEN 'Iniciada em atraso'
        WHEN CURRENT_DATE > prazo_inicio_obra_calc THEN 'Prazo vencido'
        WHEN (SELECT COUNT(*)::int
              FROM generate_series(
                  CURRENT_DATE + interval '1 day',
                  prazo_inicio_obra_calc::timestamp,
                  interval '1 day'
              ) d
              WHERE EXTRACT(DOW FROM d) NOT IN (0, 6)) <= 10
        THEN 'Próximos 10 dias úteis'
        ELSE 'No prazo'
    END AS status_inicio_obra_calc,

    -- urgencia suspensiva (usado no cascade chart) | fonte: derivada de base.dte_retirada_suspensiva + base.dsc_situacao_contrato_mcid + base.vencimento_da_suspensiva
    CASE
        WHEN dte_retirada_suspensiva_tgov IS NOT NULL THEN NULL
        WHEN dsc_situacao_contrato_mcid_tci = 'Cancelado ou Distratado' THEN NULL
        WHEN vencimento_da_suspensiva_pbi IS NULL THEN 'Sem data'
        WHEN CURRENT_DATE > vencimento_da_suspensiva_pbi THEN 'Vencida'
        WHEN (vencimento_da_suspensiva_pbi - CURRENT_DATE) <= 30 THEN 'Próximos 30 dias'
        WHEN (vencimento_da_suspensiva_pbi - CURRENT_DATE) <= 90 THEN '31–90 dias'
        ELSE 'Mais de 90 dias'
    END AS urgencia_suspensiva_calc

FROM base
CROSS JOIN constantes c
)
SELECT
    resultado.*,

    CASE
        WHEN dsc_situacao_contrato_mcid_tci in('Em Contratação','Cancelado ou Distratado','Contratado - Em Prestação de Contas') THEN 'Não se aplica'
        WHEN situacao_da_analise_suspensiva_pbi = 'Suspensiva retirada' THEN 'Suspensiva retirada'
        --WHEN dte_retirada_suspensiva_tgov IS NOT NULL THEN 'Suspensiva retirada'
        --WHEN dte_primeira_data_lae_tdb IS NOT NULL THEN 'Suspensiva retirada'
        --WHEN dte_publicacao_licitacao_tgov IS NOT NULL THEN 'Suspensiva retirada'
        --WHEN status_homolog_licitacao_calc = 'Concluída no prazo' THEN 'Suspensiva retirada'
        --WHEN dte_homologacao_licitacao_tgov IS NOT NULL THEN 'Suspensiva retirada'
        --WHEN dte_vrpl_tdb IS NOT NULL THEN 'Suspensiva retirada'
        WHEN dte_aio_tdb IS NOT NULL THEN 'Suspensiva retirada'
        WHEN dte_inicio_obra_mcid_tci IS NOT NULL THEN 'Suspensiva retirada'
        ELSE situacao_da_analise_suspensiva_pbi
    END AS situacao_da_analise_suspensiva_dmp,

    CASE
        WHEN (
            CASE
                WHEN dsc_situacao_contrato_mcid_tci in('Em Contratação','Cancelado ou Distratado','Contratado - Em Prestação de Contas') THEN 'Não se aplica'
                WHEN situacao_da_analise_suspensiva_pbi = 'Suspensiva retirada' THEN 'Suspensiva retirada'
                --WHEN dte_retirada_suspensiva_tgov IS NOT NULL THEN 'Suspensiva retirada'
                --WHEN dte_primeira_data_lae_tdb IS NOT NULL THEN 'Suspensiva retirada'
                --WHEN dte_publicacao_licitacao_tgov IS NOT NULL THEN 'Suspensiva retirada'
                --WHEN status_homolog_licitacao_calc = 'Concluída no prazo' THEN 'Suspensiva retirada'
                --WHEN dte_homologacao_licitacao_tgov IS NOT NULL THEN 'Suspensiva retirada'
                --WHEN dte_vrpl_tdb IS NOT NULL THEN 'Suspensiva retirada'
                WHEN dte_aio_tdb IS NOT NULL THEN 'Suspensiva retirada'
                WHEN dte_inicio_obra_mcid_tci IS NOT NULL THEN 'Suspensiva retirada'
                ELSE situacao_da_analise_suspensiva_pbi
            END
        ) = 'Suspensiva retirada' THEN 'Contratado - Normal'
        ELSE dsc_situacao_contrato_mcid_tci
    END AS situacao_contrato_dmp,

    CASE
        WHEN dsc_situacao_contrato_mcid_tci in('Em Contratação','Cancelado ou Distratado','Contratado - Em Prestação de Contas') THEN 'Não se aplica'
        WHEN situacao_da_analise_suspensiva_pbi = 'Suspensiva retirada' THEN 'situacao_da_analise_suspensiva_pbi'
        --WHEN dte_retirada_suspensiva_tgov IS NOT NULL THEN 'dte_retirada_suspensiva_tgov'
        --WHEN dte_primeira_data_lae_tdb IS NOT NULL THEN 'dte_primeira_data_lae_tdb'
        --WHEN dte_publicacao_licitacao_tgov IS NOT NULL THEN 'dte_publicacao_licitacao_tgov'
        --WHEN status_homolog_licitacao_calc = 'Concluída no prazo' THEN 'status_homolog_licitacao_calc'
        --WHEN dte_homologacao_licitacao_tgov IS NOT NULL THEN 'dte_homologacao_licitacao_tgov'
        --WHEN dte_vrpl_tdb IS NOT NULL THEN 'dte_vrpl_tdb'
        WHEN dte_aio_tdb IS NOT NULL THEN 'dte_aio_tdb'
        WHEN dte_inicio_obra_mcid_tci IS NOT NULL THEN 'dte_inicio_obra_mcid_tci'
        ELSE NULL
    END AS motivo_suspensiva_retirada_dmp

FROM resultado;
""")

SOURCE_FRESHNESS_QUERY = text("""
WITH selected_convenios AS (
    SELECT DISTINCT tci.num_convenio
    FROM se_saci.view_mat_carteira_investimento tci
    WHERE tci.txt_fonte = 'OGU'
      AND tci.dsc_fase_pac = 'NOVO PAC - Seleção'
      AND tci.txt_sigla_secretaria <> 'SNH'
)
SELECT 'tci_mcid' AS key,
       'SACI/ Ministério das Cidades' AS label,
       'TCI/MCID' AS sigla,
       max(tci.dte_carga)::date AS updated_at,
       'max(dte_carga)' AS method
FROM se_saci.view_mat_carteira_investimento tci
WHERE tci.txt_fonte = 'OGU'
  AND tci.dsc_fase_pac = 'NOVO PAC - Seleção'
  AND tci.txt_sigla_secretaria <> 'SNH'

UNION ALL

SELECT 'transferegov' AS key,
       'Transferegov' AS label,
       'TGOV' AS sigla,
       greatest(max(tc.dte_carga), max(tl.dte_carga))::date AS updated_at,
       'greatest(max(tab_convenios.dte_carga), max(tab_licitacao.dte_carga))' AS method
FROM selected_convenios sc
LEFT JOIN mcid_transferegov.tab_convenios tc
       ON sc.num_convenio::numeric = tc.num_convenio::numeric
LEFT JOIN mcid_transferegov.tab_licitacao tl
       ON sc.num_convenio::numeric = tl.num_convenio::numeric

UNION ALL

SELECT 'bdgestores' AS key,
       'BDGestores' AS label,
       'TDB' AS sigla,
       max(tdb.dte_posicao)::date AS updated_at,
       'max(dte_posicao)' AS method
FROM selected_convenios sc
LEFT JOIN mcid_bd_gestores.tab_dados_basicos tdb
       ON sc.num_convenio = tdb.cod_convenio_siafi

UNION ALL

SELECT 'power_bi_caixa' AS key,
       'Power BI Caixa' AS label,
       'PBI' AS sigla,
       max(pbi.data_atualizacao)::date AS updated_at,
       'max(data_atualizacao)' AS method
FROM selected_convenios sc
LEFT JOIN se_cgpac.tab_thiago_pbi_caixa_ogu pbi
       ON sc.num_convenio::numeric = pbi.instrumento::numeric
""")


def serialize_date(value):
    return value.isoformat() if value is not None else None


def fetch_source_freshness(conn):
    rows = conn.execute(SOURCE_FRESHNESS_QUERY).mappings().all()
    return [
        {
            "key": row["key"],
            "label": row["label"],
            "sigla": row["sigla"],
            "updated_at": serialize_date(row["updated_at"]),
            "method": row["method"],
            "fallback": False,
        }
        for row in rows
    ]


def write_source_freshness(path, snapshot_atual, sources):
    payload = {
        "snapshot_atual": snapshot_atual,
        "sources": sources + [
            {
                "key": "dmp",
                "label": "Diretoria de Monitoramento de Projetos",
                "sigla": "DMP",
                "updated_at": snapshot_atual,
                "method": "snapshot_atual",
                "fallback": True,
                "note": "Fallback: nenhuma tabela/coluna de carga dedicada da DMP foi identificada no pipeline atual.",
            }
        ],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")

def main():
    print(f"Conectando em {DATABASE_URL.host}:{DATABASE_URL.port}/{DATABASE_URL.database}...")
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        print(f"Executando: {QUERY}")
        result = conn.execute(QUERY)
        source_freshness = fetch_source_freshness(conn)

        colunas = list(result.keys())
        linhas = result.fetchall()

        with open(CSV_OUTPUT, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=";", quoting=csv.QUOTE_ALL)
            writer.writerow(colunas)
            writer.writerows(linhas)

        print(f"CSV salvo em {CSV_OUTPUT} ({len(linhas)} linhas)")

    artifacts = generate_daily_snapshot_diff(
        current_csv=CSV_OUTPUT,
        history_dir=HISTORY_DIR,
        diff_dir=DIFF_DIR,
        latest_json_path=LATEST_DIFF_JSON,
        previous_csv_path=PREVIOUS_CSV_OUTPUT,
        first_csv_path=FIRST_CSV_OUTPUT,
        cumulative_csv_path=CUMULATIVE_DIFF_OUTPUT,
    )

    print(f"Snapshot salvo em {artifacts.snapshot_path}")
    if artifacts.latest_json_path:
        print(f"Resumo consumível pelo painel salvo em {artifacts.latest_json_path}")
        with open(artifacts.latest_json_path, encoding="utf-8") as f:
            latest_json = json.load(f)
        write_source_freshness(
            SOURCE_FRESHNESS_OUTPUT,
            latest_json.get("snapshot_atual"),
            source_freshness,
        )
        print(f"Atualização por fonte salva em {SOURCE_FRESHNESS_OUTPUT}")
    if artifacts.previous_csv_path:
        print(f"Snapshot anterior consumível pelo painel salvo em {artifacts.previous_csv_path}")
    if artifacts.first_csv_path:
        print(f"Primeiro snapshot consumível pelo painel salvo em {artifacts.first_csv_path}")
    if artifacts.cumulative_csv_path:
        print(f"Histórico cumulativo consumível pelo painel salvo em {artifacts.cumulative_csv_path}")
    if artifacts.summary_md_path and artifacts.detail_csv_path:
        print(f"Relatório salvo em {artifacts.summary_md_path}")
        print(f"Detalhe salvo em {artifacts.detail_csv_path}")
    else:
        print("Nenhum snapshot anterior encontrado. Apenas o snapshot de hoje foi salvo.")


if __name__ == "__main__":
    main()
