# Checklist de prontidão para distribuição

**Data:** 23 de novembro de 2026\
**Versão candidata:** `0.2.0`\
**Decisão:** **NÃO DISTRIBUIR AINDA.** Os quatro jobs do CI passaram no commit
`ee16d8b`, incluindo Hassfest e HACS Action. Restam as validações manuais em
Home Assistant OS, Music Assistant/Alexa, backup/restauração, `aarch64`, além
de screenshots, `brand/icon.png` e release.

Cada item abaixo tem estado e evidência. Documentação existente não conta como
teste executado.

| # | Item | Estado | Evidência | O que falta |
|---|---|---|---|---|
| 1 | Auditoria das Etapas 1, 2 e 3 | **CONCLUÍDO** | matriz de validação e auditoria interna registrada no plano de publicação (mantido fora do PR) | — |
| 2 | Bloqueios críticos resolvidos | **CONCLUÍDO** | CI, Hassfest e HACS Action aprovados; nenhum bloqueio de segurança/instalação encontrado | Revalidar após alterações |
| 3 | README público revisado | **CONCLUÍDO** | `README.md` reestruturado | — |
| 4 | Documentação técnica coerente | **CONCLUÍDO** | `DOCS.md`, `AGENTS.md` e `docs/` revisados | Repetir após cada mudança funcional |
| 5 | CHANGELOG atualizado | **CONCLUÍDO** | `CHANGELOG.md` com `0.2.0` (não publicado) e categorias | Publicar após validação |
| 6 | Versões consistentes | **CONCLUÍDO** | `config.yaml`, `manifest.json` e CHANGELOG em `0.2.0`; validadas por `scripts/validate_repo.py` | — |
| 7 | Manifestos validados | **CONCLUÍDO** | Hassfest oficial aprovado no CI (run 45276992158) | — |
| 8 | CI configurada e executada | **CONCLUÍDO** | 4 jobs aprovados no run 45276992158, commit `ee16d8b` | Reexecutar após as correções de aviso |
| 9 | Testes automatizados executados | **CONCLUÍDO** | **56 testes e 26 subtestes** no Linux/CI (Python 3.14.10, HA 2026.10.4) | — |
| 10 | Hassfest validado | **CONCLUÍDO** | job `hassfest` aprovado no run 45276992158 | — |
| 11 | Requisitos HACS verificados | **PARCIAL** | HACS Action aprovada com ignores de metadados do GitHub | `brand/icon.png`, release e Action sem ignores para o catálogo padrão |
| 12 | Repositório de add-ons validado | **PARCIAL** | metadados validados; tag/digest upstream confirmada no GHCR com `linux/amd64` e `linux/arm64` | Instalação da `0.2.0` pelo add-on local ainda não reexecutada |
| 13 | Arquiteturas documentadas | **CONCLUÍDO** | `amd64` e `aarch64` em `config.yaml`; matriz distingue declaração, índice OCI e execução | `aarch64` não executado |
| 14 | Segurança revisada | **CONCLUÍDO** | validador de segredos/LF/links; actions fixadas por SHA; exposição documentada | Repetir antes de cada release |
| 15 | Screenshots reais disponíveis | **BLOQUEADO** | `docs/images/README.md` lista as capturas | Sem instalação real disponível |
| 16 | Rascunho de Release preparado | **CONCLUÍDO** | `docs/releases/RELEASE-DRAFT.md` | Publicação não autorizada |
| 17 | Instruções de suporte disponíveis | **CONCLUÍDO** | README, templates de issue e `DOCS.md` | — |
| 18 | Testes manuais pendentes identificados | **CONCLUÍDO** | `docs/VALIDATION-MATRIX.md` | Executar antes do beta |

## CI remoto — 23/11/2026

| Item | Resultado |
|---|---|
| Run | [45276992158](https://github.com/flaviocorrea13/alexa-skill/actions/runs/45276992158) |
| Commit | `ee16d8b32f442afa40cb598a4d5fee64cec647c1` |
| PR | #1, Draft |
| Repository and add-on validation | **Sucesso** |
| Integration tests (Linux, Python 3.14.10, HA 2026.10.4) | **Sucesso — 56 testes, 26 subtestes** |
| Hassfest | **Sucesso** |
| HACS validation | **Sucesso** |

## Validação local complementar

| Comando | Resultado |
|---|---|
| `python scripts/validate_repo.py` | **PASSOU** (2 avisos: screenshots e `brand/icon.png`) |
| `ruff check .` / `ruff format --check .` | **PASSOU** |
| `python -m unittest tests.test_addon_options` | **16 OK**, 1 pulo POSIX |
| `.venv\Scripts\python.exe -m unittest tests.test_integration_helpers` | **34 OK** |
| `.venv\Scripts\python.exe -m pytest -q -p winsocket` | **55 passed, 1 skipped, 26 subtests** |
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
conformes com o schema do HACS, mas o **HACS Action não foi executado** e ele
valida o repositório **remoto** (o worktree atual não foi enviado).

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
GHCR. A instalação da `0.2.0` pelo store continua pendente.

Enquanto a `0.2.0` não estiver na `main`, a loja e o HACS personalizado
entregam a versão da `main` (0.1.x). O teste da `0.2.0` deve usar o add-on
**local** e a integração copiada do mesmo commit, conforme
[`HAOS-TEST-PLAN.md`](HAOS-TEST-PLAN.md).

## Bloqueios para a primeira distribuição

1. **Versão `0.2.0` não instalada em HA OS.** Ela não está na `main`; a loja
   entrega a `0.1.1`. Use o add-on local do commit de validação.
2. **Teste ponta a ponta com Alexa e Music Assistant não executado na `0.2.0`.**
3. **Backup e restauração não testados.**
4. **`aarch64` sem execução real.**
5. **`brand/icon.png` ausente e nenhuma Release publicada** (requisitos do
   catálogo padrão, não do repositório personalizado).
6. **Screenshots reais não capturadas.**

## O que não bloqueia a preparação

- README, DOCS, AGENTS, CHANGELOG e documentos de distribuição estão prontos.
- CI, Hassfest e HACS Action aprovados no commit `ee16d8b`.
- O validador local cobre metadados, versões, links, LF, segredos e regras de
  tradução equivalentes às que mais quebram o Hassfest.
- O rascunho de Release pode ser revisado antes da publicação.

## Próximo passo permitido

Seguir [`HAOS-TEST-PLAN.md`](HAOS-TEST-PLAN.md) para validar a `0.2.0` em HA OS
`amd64` e, se possível, `aarch64`: instalação, `/setup`, `/status`, provider
Alexa, áudio, comandos, backup/restauração e reinício. Depois, capturar as telas
reais e, se desejado, adicionar `brand/icon.png`. Nenhuma tag, Release ou
publicação de imagem deve ocorrer antes disso.
