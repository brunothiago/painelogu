from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import shutil


KEY_FIELD = "num_convenio_tci"
FALLBACK_KEY_FIELD = "cod_tci_tci"

FIELD_ALIASES = {
    "cod_tci": "cod_tci_tci",
    "num_convenio": "num_convenio_tci",
    "txt_uf": "txt_uf_tci",
    "txt_regiao": "txt_regiao_tci",
    "cod_ibge_7dig": "cod_ibge_7dig_tci",
    "txt_municipio": "txt_municipio_tci",
    "txt_tomador": "txt_tomador_tci",
    "dsc_objeto_instrumento": "dsc_objeto_instrumento_tci",
    "txt_sigla_secretaria": "txt_sigla_secretaria_tci",
    "dsc_fase_pac": "dsc_fase_pac_tci",
    "txt_modalidade": "txt_modalidade_tci",
    "dsc_situacao_contrato_mcid": "dsc_situacao_contrato_mcid_tci",
    "dte_assinatura_contrato": "dte_assinatura_contrato_tci",
    "situacao_da_analise_suspensiva": "situacao_da_analise_suspensiva_pbi",
    "situacao_da_analise_suspensiva_cgpac": "situacao_da_analise_suspensiva_dmp",
    "motivo_suspensiva_retirada_cgpac": "motivo_suspensiva_retirada_dmp",
    "vencimento_da_suspensiva": "vencimento_da_suspensiva_pbi",
    "dte_retirada_suspensiva": "dte_retirada_suspensiva_tgov",
    "dte_primeira_data_lae": "dte_primeira_data_lae_tdb",
    "dte_publicacao_licitacao": "dte_publicacao_licitacao_tgov",
    "dte_homologacao_licitacao": "dte_homologacao_licitacao_tgov",
    "dte_vrpl": "dte_vrpl_tdb",
    "dte_aio": "dte_aio_tdb",
    "dte_inicio_obra_mcid": "dte_inicio_obra_mcid_tci",
    "vlr_repasse": "vlr_repasse_tci",
    "status_suspensiva": "status_suspensiva_calc",
    "flag_publicacao_licitacao": "flag_publicacao_licitacao_calc",
    "flag_homologacao_licitacao": "flag_homologacao_licitacao_calc",
    "ultima_data_relevante": "ultima_data_relevante_calc",
    "fase_atual": "fase_atual_calc",
    "dias_ate_publicacao": "dias_ate_publicacao_calc",
    "dias_publicacao_ate_homologacao": "dias_publicacao_ate_homologacao_calc",
    "dias_homologacao_ate_vrpl": "dias_homologacao_ate_vrpl_calc",
    "dias_vrpl_ate_aio": "dias_vrpl_ate_aio_calc",
    "dias_aio_ate_inicio_obra": "dias_aio_ate_inicio_obra_calc",
    "faixa_repasse": "faixa_repasse_calc",
    "prazo_pub_licitacao": "prazo_pub_licitacao_calc",
    "prazo_homolog_licitacao": "prazo_homolog_licitacao_calc",
    "prazo_inicio_obra": "prazo_inicio_obra_calc",
    "data_limite_licitacao_casa_civil": "data_limite_licitacao_casa_civil_const",
    "status_regra_casa_civil": "status_regra_casa_civil_calc",
    "status_pub_licitacao": "status_pub_licitacao_calc",
    "status_homolog_licitacao": "status_homolog_licitacao_calc",
    "status_inicio_obra": "status_inicio_obra_calc",
    "urgencia_suspensiva": "urgencia_suspensiva_calc",
}

SOURCE_FIELDS = {
    "cod_tci_tci",
    "num_convenio_tci",
    "txt_uf_tci",
    "txt_regiao_tci",
    "cod_ibge_7dig_tci",
    "txt_municipio_tci",
    "txt_tomador_tci",
    "dsc_objeto_instrumento_tci",
    "txt_sigla_secretaria_tci",
    "dsc_fase_pac_tci",
    "txt_modalidade_tci",
    "dsc_situacao_contrato_mcid_tci",
    "dte_assinatura_contrato_tci",
    "situacao_da_analise_suspensiva_pbi",
    "situacao_da_analise_suspensiva_dmp",
    "vencimento_da_suspensiva_pbi",
    "dte_retirada_suspensiva_tgov",
    "dte_primeira_data_lae_tdb",
    "dte_publicacao_licitacao_tgov",
    "dte_homologacao_licitacao_tgov",
    "dte_vrpl_tdb",
    "dte_aio_tdb",
    "dte_inicio_obra_mcid_tci",
    "vlr_repasse_tci",
    "motivo_suspensiva_retirada_dmp",
}

STATUS_FIELDS = {
    "status_suspensiva_calc",
    "status_pub_licitacao_calc",
    "status_homolog_licitacao_calc",
    "status_inicio_obra_calc",
    "status_regra_casa_civil_calc",
    "urgencia_suspensiva_calc",
    "fase_atual_calc",
}

TIME_DRIVEN_FIELDS = {
    "prazo_pub_licitacao_calc",
    "prazo_homolog_licitacao_120d",
    "prazo_homolog_licitacao_calc",
    "prazo_inicio_obra_calc",
    "status_pub_licitacao_calc",
    "status_homolog_licitacao_calc",
    "status_inicio_obra_calc",
    "urgencia_suspensiva_calc",
}

IGNORED_CHANGE_FIELDS = {
    "data_limite_licitacao_casa_civil_const",
    "status_regra_casa_civil_calc",
}

SUMMARY_STATUS_FIELDS = [
    "status_suspensiva_calc",
    "status_pub_licitacao_calc",
    "status_homolog_licitacao_calc",
    "status_inicio_obra_calc",
    "status_regra_casa_civil_calc",
    "urgencia_suspensiva_calc",
    "fase_atual_calc",
]


@dataclass
class DiffArtifacts:
    snapshot_path: Path
    detail_csv_path: Path | None
    summary_md_path: Path | None
    latest_json_path: Path | None
    previous_csv_path: Path | None
    first_csv_path: Path | None
    cumulative_csv_path: Path | None


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        rows = list(reader)
    if reader.fieldnames is None:
        raise ValueError(f"Arquivo CSV sem cabeçalho: {path}")
    return reader.fieldnames, rows


def _row_key(row: dict[str, str]) -> str:
    """Retorna num_convenio como chave; se vazio, usa cod_tci como fallback."""
    key = (row.get(KEY_FIELD) or "").strip()
    if not key:
        key = (row.get("num_convenio") or "").strip()
    if not key:
        key = (row.get(FALLBACK_KEY_FIELD) or "").strip()
    if not key:
        key = (row.get("cod_tci") or "").strip()
    return key


def _index_rows(rows: list[dict[str, str]], label: str) -> dict[str, dict[str, str]]:
    indexed: dict[str, dict[str, str]] = {}
    duplicates: list[str] = []
    missing: int = 0

    for row in rows:
        key = _row_key(row)
        if not key:
            missing += 1
            continue
        if key in indexed:
            duplicates.append(key)
            continue
        indexed[key] = row

    if missing:
        raise ValueError(f"{label}: {missing} linhas sem chave '{KEY_FIELD}' nem '{FALLBACK_KEY_FIELD}'.")
    if duplicates:
        examples = ", ".join(sorted(set(duplicates))[:5])
        raise ValueError(f"{label}: chaves duplicadas: {examples}")
    return indexed


def _normalize(value: str | None) -> str:
    return (value or "").strip()


def _canonical_field_name(field: str) -> str:
    return FIELD_ALIASES.get(field, field)


def _canonicalize_header(header: list[str]) -> list[str]:
    canonical: list[str] = []
    seen: set[str] = set()
    for field in header:
        normalized = _canonical_field_name(field)
        if normalized in seen:
            continue
        seen.add(normalized)
        canonical.append(normalized)
    return canonical


def _canonicalize_row(row: dict[str, str]) -> dict[str, str]:
    canonical: dict[str, str] = {}
    for field, value in row.items():
        canonical[_canonical_field_name(field)] = value
    return canonical


def _canonicalize_indexed_rows(indexed_rows: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    return {key: _canonicalize_row(row) for key, row in indexed_rows.items()}


def _comparable_fields(current_header: list[str], previous_header: list[str]) -> list[str]:
    previous_fields = set(previous_header)
    return [
        field
        for field in current_header
        if field in previous_fields and field not in (KEY_FIELD, FALLBACK_KEY_FIELD)
    ]


def _field_nature(field: str, change_type: str) -> str:
    if change_type == "entrou":
        return "novo_registro"
    if change_type == "saiu":
        return "registro_removido"
    if field in SOURCE_FIELDS:
        return "dados_origem"
    if field in TIME_DRIVEN_FIELDS:
        return "derivado_tempo"
    return "derivado_regra"


def _should_ignore_field_change(field: str, previous_value: str, current_value: str) -> bool:
    if field in IGNORED_CHANGE_FIELDS:
        return True

    # When the deadline touches the global Casa Civil cutoff, the change is
    # systemic and does not reflect a record-level update worth surfacing here.
    if field == "prazo_homolog_licitacao_calc":
        return previous_value == "2026-06-01" or current_value == "2026-06-01"

    return False


def _row_metadata(row: dict[str, str], key: str) -> dict[str, str]:
    return {
        "num_convenio": _normalize(row.get(KEY_FIELD)) or key,
        "cod_tci": _normalize(row.get(FALLBACK_KEY_FIELD)),
        "uf": _normalize(row.get("txt_uf_tci")),
        "secretaria": _normalize(row.get("txt_sigla_secretaria_tci")),
    }


def _copy_snapshot(current_csv: Path, history_dir: Path, snapshot_date: date) -> Path:
    history_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = history_dir / f"base_pc_32_{snapshot_date.isoformat()}.csv"
    shutil.copyfile(current_csv, snapshot_path)
    return snapshot_path


def _latest_previous_snapshot(history_dir: Path, current_snapshot: Path) -> Path | None:
    snapshots = sorted(
        path for path in history_dir.glob("base_pc_32_*.csv") if path != current_snapshot
    )
    if not snapshots:
        return None
    return snapshots[-1]


def _oldest_snapshot(history_dir: Path) -> Path | None:
    snapshots = sorted(history_dir.glob("base_pc_32_*.csv"))
    if not snapshots:
        return None
    return snapshots[0]


def _summarize_status_changes(detail_rows: list[dict[str, str]]) -> dict[str, int]:
    counter = Counter()
    for row in detail_rows:
        if row["tipo_alteracao"] != "alterado":
            continue
        field = row["campo"]
        if field in SUMMARY_STATUS_FIELDS:
            counter[field] += 1
    return {field: counter.get(field, 0) for field in SUMMARY_STATUS_FIELDS}


def _classify_record_change(changed_fields: list[str]) -> str:
    source_changes = [field for field in changed_fields if field in SOURCE_FIELDS]
    derived_changes = [field for field in changed_fields if field not in SOURCE_FIELDS]

    if source_changes and derived_changes:
        return "dados_e_derivados"
    if source_changes:
        return "dados"
    return "derivados_tempo"


def _build_detail_rows(
    previous_rows: dict[str, dict[str, str]],
    current_rows: dict[str, dict[str, str]],
    current_header: list[str],
    previous_header: list[str],
) -> tuple[list[dict[str, str]], dict[str, int]]:
    detail_rows: list[dict[str, str]] = []
    stats = {
        "entered": 0,
        "exited": 0,
        "changed_records": 0,
        "changed_data_records": 0,
        "changed_time_records": 0,
    }

    previous_keys = set(previous_rows)
    current_keys = set(current_rows)

    for key in sorted(current_keys - previous_keys):
        row = current_rows[key]
        metadata = _row_metadata(row, key)
        stats["entered"] += 1
        detail_rows.append(
            {
                "tipo_alteracao": "entrou",
                "categoria_alteracao": "novo_registro",
                "natureza_campo": "novo_registro",
                "num_convenio": metadata["num_convenio"],
                "cod_tci": metadata["cod_tci"],
                "campo": "vlr_repasse_tci",
                "valor_anterior": "",
                "valor_atual": _normalize(row.get("vlr_repasse_tci")),
            }
        )

    for key in sorted(previous_keys - current_keys):
        row = previous_rows[key]
        metadata = _row_metadata(row, key)
        stats["exited"] += 1
        detail_rows.append(
            {
                "tipo_alteracao": "saiu",
                "categoria_alteracao": "registro_removido",
                "natureza_campo": "registro_removido",
                "num_convenio": metadata["num_convenio"],
                "cod_tci": metadata["cod_tci"],
                "campo": "vlr_repasse_tci",
                "valor_anterior": _normalize(row.get("vlr_repasse_tci")),
                "valor_atual": "",
            }
        )

    comparable_fields = _comparable_fields(current_header, previous_header)

    for key in sorted(previous_keys & current_keys):
        previous = previous_rows[key]
        current = current_rows[key]
        changed_fields = [
            field
            for field in comparable_fields
            if _normalize(previous.get(field)) != _normalize(current.get(field))
            and not _should_ignore_field_change(
                field,
                _normalize(previous.get(field)),
                _normalize(current.get(field)),
            )
        ]

        if not changed_fields:
            continue

        stats["changed_records"] += 1
        category = _classify_record_change(changed_fields)
        if category == "derivados_tempo":
            stats["changed_time_records"] += 1
        else:
            stats["changed_data_records"] += 1

        metadata = _row_metadata(current, key)
        if not metadata["cod_tci"]:
            metadata["cod_tci"] = _row_metadata(previous, key)["cod_tci"]
        for field in changed_fields:
            detail_rows.append(
                {
                    "tipo_alteracao": "alterado",
                    "categoria_alteracao": category,
                    "natureza_campo": _field_nature(field, "alterado"),
                    "num_convenio": metadata["num_convenio"],
                    "cod_tci": metadata["cod_tci"],
                    "campo": field,
                    "valor_anterior": _normalize(previous.get(field)),
                    "valor_atual": _normalize(current.get(field)),
                }
            )

    return detail_rows, stats


def _build_cumulative_diff(history_dir: Path) -> list[dict[str, str]]:
    """Compara cada par consecutivo de snapshots e retorna todas as mudanças com data."""
    snapshots = sorted(history_dir.glob("base_pc_32_*.csv"))
    if len(snapshots) < 2:
        return []

    all_rows: list[dict[str, str]] = []

    for i in range(1, len(snapshots)):
        prev_path = snapshots[i - 1]
        curr_path = snapshots[i]
        snapshot_date = curr_path.stem.replace("base_pc_32_", "")

        curr_header_raw, curr_raw = _read_csv(curr_path)
        prev_header_raw, prev_raw = _read_csv(prev_path)

        curr_header = _canonicalize_header(curr_header_raw)
        prev_header = _canonicalize_header(prev_header_raw)
        curr_indexed = _canonicalize_indexed_rows(_index_rows(curr_raw, f"Cumul. atual ({curr_path.name})"))
        prev_indexed = _canonicalize_indexed_rows(_index_rows(prev_raw, f"Cumul. anterior ({prev_path.name})"))

        prev_keys = set(prev_indexed)
        curr_keys = set(curr_indexed)

        for key in sorted(curr_keys - prev_keys):
            row = curr_indexed[key]
            metadata = _row_metadata(row, key)
            all_rows.append({
                "data": snapshot_date,
                "tipo": "Novo",
                "categoria": "novo_registro",
                "natureza": "novo_registro",
                "num_convenio": metadata["num_convenio"],
                "cod_tci": metadata["cod_tci"],
                "uf": metadata["uf"],
                "secretaria": metadata["secretaria"],
                "campo": "vlr_repasse_tci",
                "valor_anterior": "",
                "valor_atual": _normalize(row.get("vlr_repasse_tci")),
            })

        for key in sorted(prev_keys - curr_keys):
            row = prev_indexed[key]
            metadata = _row_metadata(row, key)
            all_rows.append({
                "data": snapshot_date,
                "tipo": "Removido",
                "categoria": "registro_removido",
                "natureza": "registro_removido",
                "num_convenio": metadata["num_convenio"],
                "cod_tci": metadata["cod_tci"],
                "uf": metadata["uf"],
                "secretaria": metadata["secretaria"],
                "campo": "vlr_repasse_tci",
                "valor_anterior": _normalize(row.get("vlr_repasse_tci")),
                "valor_atual": "",
            })

        comparable = _comparable_fields(curr_header, prev_header)
        for key in sorted(prev_keys & curr_keys):
            prev = prev_indexed[key]
            curr = curr_indexed[key]
            changed = [
                f
                for f in comparable
                if _normalize(prev.get(f)) != _normalize(curr.get(f))
                and not _should_ignore_field_change(
                    f,
                    _normalize(prev.get(f)),
                    _normalize(curr.get(f)),
                )
            ]
            if not changed:
                continue
            category = _classify_record_change(changed)
            metadata = _row_metadata(curr, key)
            if not metadata["cod_tci"]:
                metadata["cod_tci"] = _row_metadata(prev, key)["cod_tci"]
            for field in changed:
                all_rows.append({
                    "data": snapshot_date,
                    "tipo": "Alterado",
                    "categoria": category,
                    "natureza": _field_nature(field, "alterado"),
                    "num_convenio": metadata["num_convenio"],
                    "cod_tci": metadata["cod_tci"],
                    "uf": metadata["uf"],
                    "secretaria": metadata["secretaria"],
                    "campo": field,
                    "valor_anterior": _normalize(prev.get(field)),
                    "valor_atual": _normalize(curr.get(field)),
                })

    return all_rows


def _write_cumulative_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["data", "tipo", "categoria", "natureza", "num_convenio", "cod_tci", "uf", "secretaria", "campo", "valor_anterior", "valor_atual"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter=";", quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)


def _write_detail_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "tipo_alteracao",
        "categoria_alteracao",
        "natureza_campo",
        "num_convenio",
        "cod_tci",
        "campo",
        "valor_anterior",
        "valor_atual",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            delimiter=";",
            quoting=csv.QUOTE_ALL,
        )
        writer.writeheader()
        writer.writerows(rows)


def _write_summary_md(
    path: Path,
    snapshot_date: date,
    previous_snapshot: Path,
    current_total: int,
    previous_total: int,
    stats: dict[str, int],
    status_changes: dict[str, int],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Diferença da base PC 32 - {snapshot_date.isoformat()}",
        "",
        f"- Snapshot atual: `{snapshot_date.isoformat()}`",
        f"- Snapshot anterior: `{previous_snapshot.stem.replace('base_pc_32_', '')}`",
        f"- Total anterior: **{previous_total}**",
        f"- Total atual: **{current_total}**",
        "",
        "## Resumo",
        "",
        f"- Entraram na base: **{stats['entered']}**",
        f"- Saíram da base: **{stats['exited']}**",
        f"- Registros com alguma alteração: **{stats['changed_records']}**",
        f"- Registros com mudança de dados de origem: **{stats['changed_data_records']}**",
        f"- Registros com mudança apenas em campos derivados/status: **{stats['changed_time_records']}**",
        "",
        "## Mudanças por status",
        "",
    ]

    for field in SUMMARY_STATUS_FIELDS:
        lines.append(f"- `{field}`: **{status_changes.get(field, 0)}**")

    lines.extend(
        [
            "",
            "## Leitura recomendada",
            "",
            "- `categoria_alteracao = dados_e_derivados`: mudou dado de origem e isso também repercutiu em campos calculados.",
            "- `categoria_alteracao = dados`: mudou apenas dado de origem, sem alterar status calculado.",
            "- `categoria_alteracao = derivados_tempo`: o dado-base ficou igual; a alteração veio só de regra derivada/data corrente.",
        ]
    )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_latest_json(
    path: Path,
    snapshot_date: date,
    previous_snapshot: Path | None,
    first_snapshot: Path | None,
    current_total: int,
    previous_total: int | None,
    stats: dict[str, int] | None,
    status_changes: dict[str, int] | None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "snapshot_atual": snapshot_date.isoformat(),
        "snapshot_anterior": None if previous_snapshot is None else previous_snapshot.stem.replace("base_pc_32_", ""),
        "snapshot_primeiro": None if first_snapshot is None else first_snapshot.stem.replace("base_pc_32_", ""),
        "total_atual": current_total,
        "total_anterior": previous_total,
        "delta_total": None if previous_total is None else current_total - previous_total,
        "resumo": stats,
        "mudancas_status": status_changes,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_previous_csv(path: Path, source_snapshot: Path | None, fallback_snapshot: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_snapshot or fallback_snapshot, path)


def generate_daily_snapshot_diff(
    current_csv: str | Path,
    history_dir: str | Path,
    diff_dir: str | Path,
    latest_json_path: str | Path | None = None,
    previous_csv_path: str | Path | None = None,
    first_csv_path: str | Path | None = None,
    cumulative_csv_path: str | Path | None = None,
    snapshot_date: date | None = None,
) -> DiffArtifacts:
    snapshot_date = snapshot_date or date.today()
    current_csv = Path(current_csv)
    history_dir = Path(history_dir)
    diff_dir = Path(diff_dir)

    snapshot_path = _copy_snapshot(current_csv, history_dir, snapshot_date)
    previous_snapshot = _latest_previous_snapshot(history_dir, snapshot_path)
    latest_json = Path(latest_json_path) if latest_json_path else None
    previous_csv = Path(previous_csv_path) if previous_csv_path else None
    first_csv = Path(first_csv_path) if first_csv_path else None
    cumulative_csv = Path(cumulative_csv_path) if cumulative_csv_path else None

    if previous_csv is not None:
        _write_previous_csv(previous_csv, previous_snapshot, snapshot_path)

    if first_csv is not None:
        first_snapshot = _oldest_snapshot(history_dir)
        if first_snapshot is not None:
            first_csv.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(first_snapshot, first_csv)

    if cumulative_csv is not None:
        _write_cumulative_csv(cumulative_csv, _build_cumulative_diff(history_dir))

    if previous_snapshot is None:
        if latest_json is not None:
            _write_latest_json(
                latest_json,
                snapshot_date=snapshot_date,
                previous_snapshot=None,
                first_snapshot=_oldest_snapshot(history_dir),
                current_total=len(_read_csv(snapshot_path)[1]),
                previous_total=None,
                stats=None,
                status_changes=None,
            )
        return DiffArtifacts(
            snapshot_path=snapshot_path,
            detail_csv_path=None,
            summary_md_path=None,
            latest_json_path=latest_json,
            previous_csv_path=previous_csv,
            first_csv_path=first_csv,
            cumulative_csv_path=cumulative_csv,
        )

    current_header_raw, current_rows_raw = _read_csv(snapshot_path)
    previous_header_raw, previous_rows_raw = _read_csv(previous_snapshot)

    current_header = _canonicalize_header(current_header_raw)
    previous_header = _canonicalize_header(previous_header_raw)
    current_rows = _canonicalize_indexed_rows(_index_rows(current_rows_raw, f"Snapshot atual ({snapshot_path.name})"))
    previous_rows = _canonicalize_indexed_rows(_index_rows(previous_rows_raw, f"Snapshot anterior ({previous_snapshot.name})"))

    detail_rows, stats = _build_detail_rows(previous_rows, current_rows, current_header, previous_header)
    status_changes = _summarize_status_changes(detail_rows)

    detail_csv_path = diff_dir / f"detalhe_{snapshot_date.isoformat()}.csv"
    summary_md_path = diff_dir / f"relatorio_{snapshot_date.isoformat()}.md"

    _write_detail_csv(detail_csv_path, detail_rows)
    _write_summary_md(
        summary_md_path,
        snapshot_date,
        previous_snapshot,
        current_total=len(current_rows_raw),
        previous_total=len(previous_rows_raw),
        stats=stats,
        status_changes=status_changes,
    )
    if latest_json is not None:
        _write_latest_json(
            latest_json,
            snapshot_date=snapshot_date,
            previous_snapshot=previous_snapshot,
            first_snapshot=_oldest_snapshot(history_dir),
            current_total=len(current_rows_raw),
            previous_total=len(previous_rows_raw),
            stats=stats,
            status_changes=status_changes,
        )

    return DiffArtifacts(
        snapshot_path=snapshot_path,
        detail_csv_path=detail_csv_path,
        summary_md_path=summary_md_path,
        latest_json_path=latest_json,
        previous_csv_path=previous_csv,
        first_csv_path=first_csv,
        cumulative_csv_path=cumulative_csv,
    )
