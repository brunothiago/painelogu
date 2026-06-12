# painelogu

Painel estático em [Observable Framework](https://observablehq.com/framework/) para acompanhamento dos contratos OGU da **Portaria Conjunta 32** — Novo PAC Novas Seleções (DMP/SE).

## Publicação

| URL | Uso |
|-----|-----|
| [thiagobruno.com.br/painelogu/](http://thiagobruno.com.br/painelogu/) | Domínio principal |
| [brunothiago.github.io/painelogu/](https://brunothiago.github.io/painelogu/) | GitHub Pages |

Deploy automático via GitHub Actions a cada push na branch `main`.

## Desenvolvimento local

```bash
npm install
npm run dev
```

Abre em `http://127.0.0.1:3000/`.

## Atualização de dados

O fluxo canônico sincroniza fontes, gera snapshots, builda o painel e publica quando há mudanças:

```bash
./scripts/update.sh
```

No Windows, use `scripts/update.bat` (wrapper para Git Bash).

Pré-requisitos: `uv`, `node` 18+, `npm`, `git` e credenciais em `python/config.env` (não versionado).

Detalhes operacionais: [`PLANO.md`](PLANO.md).

## Estrutura

```
python/          # Extração e geração da base (PostgreSQL + XLSX Caixa)
src/             # Páginas Observable (index, alterações) e dados consumidos
scripts/         # update.sh — entrypoint de atualização
data/            # Histórico de snapshots e relatórios diff
.github/         # Deploy GitHub Pages
```

## Licença

Uso interno DMP/MCid. Dados sujeitos às políticas das fontes oficiais (TransfereGov, bases internas).
