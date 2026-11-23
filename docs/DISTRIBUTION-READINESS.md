# Checklist de prontidão para distribuição

**Data:** 23 de novembro de 2026\
**Versão candidata:** `0.2.0`\
**Decisão:** **NÃO DISTRIBUIR AINDA.** O repositório está organizado e
documentado, e a suíte de testes passou em execução local suplementar, mas as
validações que dependem de Linux/Docker, push e Home Assistant OS continuam
bloqueadas.

Cada item abaixo tem estado e evidência. Documentação existente não conta como
teste executado.

| # | Item | Estado | Evidência | O que falta |
|---|---|---|---|---|
| 1 | Auditoria das Etapas 1, 2 e 3 | **CONCLUÍDO** | matriz de validação e auditoria interna registrada no plano de publicação (mantido fora do PR) | — |
| 2 | Bloqueios críticos resolvidos | **PARCIAL** | nenhum bloqueio de segurança/instalação encontrado; Hassfest estático corrigiu ordem do manifesto e URLs em traduções | Confirmar em CI e HA OS |
| 3 | README público revisado | **CONCLUÍDO** | `README.md` reestruturado | — |
| 4 | Documentação técnica coerente | **CONCLUÍDO** | `DOCS.md`, `AGENTS.md` e `docs/` revisados | Repetir após cada mudança funcional |
| 5 | CHANGELOG atualizado | **CONCLUÍDO** | `CHANGELOG.md` com `0.2.0` (não publicado) e categorias | Publicar após validação |
| 6 | Versões consistentes | **CONCLUÍDO** | `config.yaml`, `manifest.json` e CHANGELOG em `0.2.0`; validadas por `scripts/validate_repo.py` | — |
| 7 | Manifestos validados | **PARCIAL** | validação estrutural local + auditoria estática do Hassfest | Hassfest oficial não executado |
| 8 | CI configurada | **CONCLUÍDO** | `.github/workflows/ci.yml` auditado, actions fixadas por SHA, HACS `ignore` corrigido, dependabot | Primeira execução depende de push/PR |
| 9 | Testes automatizados executados | **PARCIAL** | **55 passed, 1 skipped, 26 subtests** no pytest completo no Windows com shims; 6 config flow passaram | Execução Linux/CI pendente |
| 10 | Hassfest validado | **PARCIAL** | 10 plugins oficiais do Hassfest (HA Core `2026.10.4`) passaram com **0 erros**; execução oficial via Docker/CI pendente | Executar no GitHub Actions |
| 11 | Requisitos HACS verificados | **PARCIAL** | schemas/documentação oficiais auditados; `hacs.json` e manifesto conformes | HACS Action, `brand/icon.png` e release |
| 12 | Repositório de add-ons validado | **PARCIAL** | metadados validados; tag/digest upstream confirmada no GHCR com `linux/amd64` e `linux/arm64` | Instalação da `0.2.0` não reexecutada |
| 13 | Arquiteturas documentadas | **CONCLUÍDO** | `amd64` e `aarch64` em `config.yaml`; matriz distingue declaração, índice OCI e execução | `aarch64` não executado |
| 14 | Segurança revisada | **CONCLUÍDO** | validador de segredos/LF/links; actions fixadas por SHA; exposição documentada | Repetir antes de cada release |
| 15 | Screenshots reais disponíveis | **BLOQUEADO** | `docs/images/README.md` lista as capturas | Sem instalação real disponível |
| 16 | Rascunho de Release preparado | **CONCLUÍDO** | `docs/releases/RELEASE-DRAFT.md` | Publicação não autorizada |
| 17 | Instruções de suporte disponíveis | **CONCLUÍDO** | README, templates de issue e `DOCS.md` | — |
| 18 | Testes manuais pendentes identificados | **CONCLUÍDO** | `docs/VALIDATION-MATRIX.md` | Executar antes do beta |

## Validação executada em 23/11/2026

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

**Limitação:** o pytest rodou no Windows com shims `fcntl`/`resource` e sockets
habilitados, mantidos fora do repositório. Não é uma execução Linux e não
substitui a CI. O pulo é a asserção de permissão POSIX.

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

## Bloqueios para a primeira distribuição

1. **Sem Linux/Docker/WSL nesta máquina.** Hassfest oficial, HACS Action e CI
   não podem ser executados localmente.
2. **Sem push autorizado.** CI e HACS Action validam o repositório remoto, que
   ainda está no commit `2444dbf`; o worktree atual não foi enviado.
3. **`pytest` oficial em Linux pendente.** A suíte passou no Windows com shims.
4. **Hassfest oficial não executado.** Dez plugins oficiais passaram localmente
   com 0 erros, mas a imagem oficial e o plugin `dependencies` continuam
   pendentes.
5. **HACS Action não executada.**
6. **Versão `0.2.0` não instalada em HA OS.** A evidência real é da `0.1.1`.
7. **`aarch64` sem execução real.**
8. **`brand/icon.png` ausente e nenhuma Release publicada** (requisitos do
   catálogo padrão, não do repositório personalizado).
9. **Screenshots reais não capturadas.**

## O que não bloqueia a preparação

- README, DOCS, AGENTS, CHANGELOG e documentos de distribuição estão prontos.
- O validador local cobre metadados, versões, links, LF, segredos e regras de
  tradução equivalentes às que mais quebram o Hassfest.
- O rascunho de Release pode ser revisado antes da publicação.

## Próximo passo permitido

Autorizar commit/push em um branch e abrir um pull request para executar CI,
Hassfest e HACS Action. Depois, seguir
[`HAOS-TEST-PLAN.md`](HAOS-TEST-PLAN.md) para validar a `0.2.0` em HA OS
`amd64`, capturar as telas reais e, se desejado, adicionar `brand/icon.png`.
Nenhuma tag, Release ou publicação de imagem deve ocorrer antes disso.
