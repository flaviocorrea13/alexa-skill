# Checklist de prontidão para distribuição

**Data:** 27 de novembro de 2026\
**Versão candidata:** `0.2.0`\
**Decisão:** **PRONTO COM RESSALVAS.** O release candidate está tecnicamente
validado: CI com 5/5 jobs no commit `0a92454` (run `45983936564`), 113 testes
Linux/47 subtests, 38 testes de frontend e seis cenários funcionais aprovados
manualmente em Home Assistant real. A publicação depende de merge/tag/release e
das pendências listadas abaixo: `aarch64`, backup/restauração, atualização pela
loja, options flow/reauth E2E, screenshots, `brand/icon.png` e catálogo padrão
do HACS. Este diff documental precisa de uma nova execução da CI antes do
commit final.

Cada item abaixo tem estado e evidência. Documentação existente não conta como
teste executado.

| # | Item | Estado | Evidência | O que falta |
|---|---|---|---|---|
| 1 | Auditoria das Etapas 1, 2 e 3 | **CONCLUÍDO** | matriz de validação e auditoria interna registrada no plano de publicação (mantido fora do PR) | — |
| 2 | Bloqueios críticos resolvidos | **CONCLUÍDO** | CI, Hassfest e HACS Action aprovados; nenhum bloqueio de segurança/instalação encontrado | Revalidar após alterações |
| 3 | README público revisado | **CONCLUÍDO** | `README.md` reestruturado | — |
| 4 | Documentação técnica coerente | **CONCLUÍDO** | `DOCS.md`, `AGENTS.md` e `docs/` revisados | Repetir após cada mudança funcional |
| 5 | CHANGELOG atualizado | **CONCLUÍDO** | `CHANGELOG.md` com `0.2.0` (não publicado), painel, licença Lit e validações | Publicar após validação |
| 6 | Versões consistentes | **CONCLUÍDO** | `config.yaml`, `manifest.json` e CHANGELOG em `0.2.0`; validadas por `scripts/validate_repo.py` | — |
| 7 | Manifestos validados | **CONCLUÍDO** | Hassfest oficial aprovado no CI (run 45983936564) | — |
| 8 | CI configurada e executada | **CONCLUÍDO** | 5 jobs aprovados no run 45983936564, commit `0a92454` | — |
| 9 | Testes automatizados executados | **CONCLUÍDO** | **113 testes e 47 subtestes** no Linux/CI; 38 testes de frontend; 112/1/47 no Windows suplementar | — |
| 10 | Hassfest validado | **CONCLUÍDO** | job `hassfest` aprovado no run 45983936564 | — |
| 11 | Requisitos HACS verificados | **PARCIAL** | HACS Action aprovada com ignores de metadados do GitHub | `brand/icon.png`, release e Action sem ignores para o catálogo padrão |
| 12 | Repositório de add-ons validado | **PARCIAL** | metadados validados; tag/digest upstream confirmada no GHCR com `linux/amd64` e `linux/arm64`; `0.2.0` instalada/testada em HA real | Atualização `0.1.1 → 0.2.0` pela loja e `aarch64` |
| 13 | Arquiteturas documentadas | **CONCLUÍDO** | `amd64` e `aarch64` em `config.yaml`; matriz distingue declaração, índice OCI e execução | `aarch64` não executado |
| 14 | Segurança revisada | **CONCLUÍDO** | validador de segredos/LF/links; actions fixadas por SHA; exposição documentada | Repetir antes de cada release |
| 15 | Screenshots reais disponíveis | **PENDENTE** | `docs/images/README.md` lista as capturas | Capturas ainda não adicionadas |
| 16 | Rascunho de Release preparado | **CONCLUÍDO** | `docs/releases/RELEASE-DRAFT.md` | Publicação não autorizada |
| 17 | Instruções de suporte disponíveis | **CONCLUÍDO** | README, templates de issue e `DOCS.md` | — |
| 18 | Testes manuais | **PARCIAL** | seis cenários funcionais aprovados pelo usuário em HA real | backup/restauração, `aarch64`, atualização pela loja, options flow/reauth, WAF externo |

## CI remoto — 27/11/2026

| Item | Resultado |
|---|---|
| Run | [45983936564](https://github.com/flaviocorrea13/alexa-skill/actions/runs/45983936564) |
| Commit | `0a92454e728bb6a3957abddc4406506b63440c00` |
| PR | #1, pronto para revisão |
| Repository and add-on validation | **Sucesso** |
| Integration tests (Linux, Python 3.14.10, HA 2026.10.4) | **Sucesso — 113 testes, 47 subtestes** |
| Frontend build | **Sucesso — 38 testes, typecheck, build e bundle reproduzível** |
| Hassfest | **Sucesso** |
| HACS validation | **Sucesso** |

## Validação local complementar

| Comando | Resultado |
|---|---|
| `python scripts/validate_repo.py` | **PASSOU** (2 avisos: screenshots e `brand/icon.png`) |
| `ruff check .` / `ruff format --check .` | **PASSOU** |
| `python -m unittest tests.test_addon_options` | **16 OK**, 1 pulo POSIX |
| `.venv\Scripts\python.exe -m unittest tests.test_integration_helpers` | **64 OK** |
| `.venv\Scripts\python.exe -m pytest -q -p winsocket` | **112 passed, 1 skipped, 47 subtests** |
| `npm run typecheck` / `npm test` | **OK / 38 passed** |
| `pytest tests/test_config_flow.py -q -p winsocket` | **6 passed** |
| `python scripts/run_hassfest_subset.py --core-path <HA Core 2026.10.4>` | **10 plugins, 0 erros** |
| `actionlint .github/workflows/ci.yml` | **PASSOU** (actionlint 1.7.12, 0 erros) |
| `python -m compileall -q ...` / `bash -n run.sh` | **PASSOU** |
| Consulta read-only ao GHCR | digest confere; índice `linux/amd64` e `linux/arm64` |

**Limitação:** a execução local no Windows usou shims `fcntl`/`resource` e
sockets habilitados, mantidos fora do repositório. Ela é suplementar; a
validação Linux oficial foi concluída no CI. O pulo é a asserção de permissão
POSIX.

**Avisos tratados:** a autenticação básica passou a usar
`aiohttp.encode_basic_auth` com cabeçalho `Authorization`, removendo a
depreciação do `aiohttp.BasicAuth`; `actions/checkout` e
`actions/setup-python` foram atualizados para versões Node 24 (v7).

## HACS e distribuição do add-on

### Instalação manual da integração (sem HACS)

Copiar `custom_components/alexa_ma_skill/` para
`/config/custom_components/alexa_ma_skill` e reiniciar o Home Assistant.

### Instalação pelo HACS (repositório personalizado)

Adicionar `https://github.com/flaviocorrea13/alexa-skill` como repositório
personalizado da categoria **Integração**. O `hacs.json` e o manifesto são
conformes com o schema do HACS; a **HACS Action foi executada com sucesso** no
run `45983936564`, com ignores de metadados do GitHub.

A partir do Home Assistant 2026.11, o HACS é distribuído como **Marketplace**;
os nomes de menu podem variar. A instalação por repositório personalizado
continua sendo o caminho suportado pelo projeto.

### Requisitos para eventual inclusão no catálogo padrão

Não solicitada. Segundo a documentação oficial do HACS, antes de avaliar:

- HACS Action aprovada **sem ignores**;
- Hassfest aprovado;
- ao menos uma **Release completa** publicada;
- descrição, topics e issues habilitados no GitHub;
- **brand assets**: `custom_components/alexa_ma_skill/brand/icon.png` (ou o
  domínio em `home-assistant/brands`);
- licença reconhecida e histórico de manutenção;
- confirmação das regras vigentes na data da solicitação.

Hoje falta `brand/icon.png` e não existe Release publicada. O nome do repositório
(`alexa-skill`) também difere do domínio (`alexa_ma_skill`); isso não impede o
repositório personalizado, mas é um ponto a resolver antes do catálogo padrão.

### Distribuição do add-on

O add-on é distribuído pelo repositório de add-ons declarado em
`repository.yaml`. `config.yaml`, portas, schema, arquiteturas e Dockerfile
foram validados localmente; a tag/digest da imagem upstream foi confirmada no
GHCR. A `0.2.0` foi instalada e testada em Home Assistant real; a atualização
`0.1.1 → 0.2.0` pela loja ainda não foi executada.

Enquanto a `0.2.0` não estiver na `main`, a loja e o HACS personalizado
entregam a versão da `main` (0.1.x). O teste da `0.2.0` deve usar o add-on
**local** e a integração copiada do mesmo commit, conforme
[`HAOS-TEST-PLAN.md`](HAOS-TEST-PLAN.md).

## Pendências para a publicação

1. **Merge e tag.** O PR #1 está aberto e pronto para revisão; a `0.2.0` está
   no branch `validation/phase-4-ci`, não na `main`. A loja/HACS apontando para
   `main` ainda entrega a 0.1.x até o merge e a criação da tag/Release.
2. **Backup e restauração não testados na `0.2.0`.**
3. **`aarch64` sem execução real.**
4. **Atualização `0.1.1 → 0.2.0` pela loja não executada.**
5. **Options flow e reauth sem teste end-to-end dedicado.**
6. **`brand/icon.png` ausente e nenhuma Release publicada** (requisitos do
   catálogo padrão, não do repositório personalizado).
7. **Screenshots reais não capturadas.**

## O que não bloqueia a preparação

- README, DOCS, AGENTS, CHANGELOG e documentos de distribuição estão atualizados.
- CI, Hassfest e HACS Action aprovados no commit `0a92454` (run
  `45983936564`), com 113 testes Linux, 47 subtests e 38 testes de frontend.
- Os seis cenários funcionais principais foram aprovados em Home Assistant real.
- O validador local cobre metadados, versões, links, LF, segredos e regras de
  tradução equivalentes às que mais quebram o Hassfest.
- O rascunho de Release pode ser revisado antes da publicação.

## Próximo passo permitido

Revisar o PR #1. Depois do merge, criar a tag/Release `v0.2.0` com autorização
explícita. As validações de `aarch64`, backup/restauração, atualização pela
loja, options flow/reauth e as capturas de tela continuam recomendadas antes do
anúncio público amplo.
