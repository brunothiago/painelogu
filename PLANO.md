# Plano Operacional — Painel OGU (painelogu)

## Visão Geral

Este repositório publica um painel estático em Observable Framework para acompanhamento dos contratos da Portaria Conjunta 32 do Novo PAC Seleção.

Publicação:

- Domínio principal: `http://thiagobruno.com.br/painelogu/`
- GitHub Pages: `https://brunothiago.github.io/painelogu/`

Repositório: `https://github.com/brunothiago/painelogu`

O projeto tem dois blocos:

- extração e preparação de dados em `python/`
- visualização e publicação em `src/`

## Fluxo Oficial

O fluxo oficial de atualização é:

1. executar `scripts/update.sh` em macOS/Linux, ou `scripts/update.bat` no Windows
2. rodar a extração Python com `uv`
3. atualizar a base principal em `src/data/base_pc_32.csv`
4. gerar snapshots e artefatos auxiliares
5. executar `npm run build`
6. versionar e publicar os artefatos alterados

## Artefatos Gerados

### Dados consumidos pelo painel

- `src/data/base_pc_32.csv`: snapshot atual completo
- `src/data/base_pc_32_previous.csv`: snapshot anterior consumível pelo painel
- `src/data/base_pc_32_first.csv`: primeiro snapshot disponível
- `src/data/base_diff_latest.json`: resumo do snapshot atual, anterior e deltas
- `src/data/base_alteracoes.csv`: mudanças acumuladas entre snapshots

### Histórico e auditoria

- `data/historico/`: snapshots diários da base
- `data/diff/`: relatórios detalhados por execução, em CSV e Markdown

## Entrypoints

### `scripts/update.sh`

É o entrypoint canônico do projeto. Faz:

- validação de dependências (`uv`, `node`, `npm`, `git`)
- extração da base
- build do painel
- detecção de mudança nos artefatos versionados
- `git add`, `git commit` e `git push`

### `scripts/update.bat`

É apenas um wrapper Windows para o fluxo oficial. Localiza o `bash` do Git for Windows e chama `scripts/update.sh`.

### `python/executar.bat`

É um atalho manual de conveniência para rodar somente `python/2_gerar_base_pc32.py` no Windows. Ele não builda o painel, não verifica mudanças e não publica artefatos.

## Estrutura do Frontend

### `src/index.md`

Página principal do painel. Consome:

- base atual
- base anterior
- resumo de snapshot

Principais blocos:

- filtros de topo
- cards com delta contra o snapshot anterior
- análises de suspensiva
- análises de licitação
- regra Casa Civil
- análises de início de obra
- tabela final com exportação

### `src/alteracoes.md`

Página dedicada ao histórico acumulado de mudanças entre snapshots.

## Atualização exibida no cabeçalho

A data exibida em “Atualizado em” não usa a data do navegador. Ela é derivada dos metadados dos snapshots gerados no pipeline.

## Stack

- Node.js 18+
- Observable Framework
- D3 / Observable Plot
- Python com `uv`
- SQLAlchemy + psycopg2

## Observações Operacionais

- `python/config.env` contém as credenciais locais de banco e não deve ser versionado.
- `scripts/update.log` é apenas log local e não deve ser versionado.
- `data/diff/` faz parte do fluxo oficial e deve acompanhar as atualizações quando houver mudança de dados.
