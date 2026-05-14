#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="$PROJECT_DIR/scripts/update.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

append_path_if_exists() {
    local dir="$1"
    if [[ -d "$dir" && ":$PATH:" != *":$dir:"* ]]; then
        PATH="$dir:$PATH"
    fi
}

append_path_if_exists "$HOME/.local/bin"
append_path_if_exists "/opt/homebrew/bin"
append_path_if_exists "/usr/local/bin"
export PATH

require_command() {
    local cmd="$1"
    if ! command -v "$cmd" >/dev/null 2>&1; then
        log "ERRO: comando '$cmd' não encontrado no PATH"
        exit 1
    fi
}

cd "$PROJECT_DIR"
mkdir -p "$(dirname "$LOG_FILE")"

require_command uv
require_command node
require_command npm
require_command git

DATA_PATHS=(
    "src/data/base_pc_32.csv"
    "src/data/base_pc_32_previous.csv"
    "src/data/base_pc_32_first.csv"
    "src/data/base_alteracoes.csv"
    "src/data/base_diff_latest.json"
    "src/data/source_freshness.json"
    "data/historico"
    "data/diff"
)

log "Iniciando atualização..."

log "Subindo arquivos para o banco..."
if ! uv run --project python python/1_sincronizar_xlsx_caixa.py >> "$LOG_FILE" 2>&1; then
    log "ERRO: Falha no upload dos arquivos para o banco"
    exit 1
fi
log "Upload concluído"

if ! uv run --project python python/2_gerar_base_pc32.py >> "$LOG_FILE" 2>&1; then
    log "ERRO: Falha na extração de dados"
    exit 1
fi
log "Extração concluída"

log "Executando build..."
if ! npm run build >> "$LOG_FILE" 2>&1; then
    log "ERRO: Falha no build"
    exit 1
fi
log "Build concluído"

if [[ -z "$(git status --short --untracked-files=all -- "${DATA_PATHS[@]}")" ]]; then
    log "Sem alterações nos artefatos de dados. Abortando."
    exit 0
fi

DATA_REF="$(
    node --input-type=module -e '
        import fs from "node:fs";
        const path = "src/data/base_diff_latest.json";
        if (!fs.existsSync(path)) process.exit(1);
        const payload = JSON.parse(fs.readFileSync(path, "utf8"));
        if (!payload?.snapshot_atual) process.exit(1);
        process.stdout.write(String(payload.snapshot_atual));
    ' 2>/dev/null || date "+%Y-%m-%d"
)"

git add "${DATA_PATHS[@]}"
git commit -m "Atualiza dados PC 32 — $DATA_REF"
git push
log "Commit e push realizados — data de referência: $DATA_REF"
