# Matriz de compatibilidade e validação

**Atualizado em:** 23 de novembro de 2026\
**Versão candidata:** `0.2.0` (não publicada)\
**Ambiente de preparação:** Windows 11, Python 3.14.10, virtualenv do projeto,
sem Docker, sem WSL, sem Home Assistant OS, sem Music Assistant, sem Echo e sem
conta Amazon.

Esta matriz separa o que foi realmente executado do que depende de ambiente
externo. Testes unitários **não** equivalem a validação ponta a ponta.

> **Nota sobre a execução no Windows:** a suíte `pytest` também foi executada
> no Windows com shims locais mantidos **fora do repositório** (`fcntl` e
> `resource`, além de sockets habilitados para o event loop). Isso serviu como
> verificação suplementar; a execução oficial em Linux foi concluída no CI.
> O projeto continua sem suporte oficial a Windows para o harness do Home
> Assistant.

## 0. CI remoto — GitHub Actions

| Item | Valor |
|---|---|
| Run | [45276992158](https://github.com/flaviocorrea13/alexa-skill/actions/runs/45276992158) |
| Commit | `ee16d8b32f442afa40cb598a4d5fee64cec647c1` |
| Evento | `pull_request` (PR #1, Draft) |
| Resultado geral | **success** |

| Job | Resultado |
|---|---|
| Repository and add-on validation | **Sucesso** |
| Integration tests (Home Assistant harness) | **Sucesso** — 56 testes, 26 subtestes, Linux/Python 3.14.10/HA 2026.10.4 |
| Hassfest | **Sucesso** |
| HACS validation | **Sucesso** |

## 1. Testes automatizados locais

| Componente | Versão | Arquitetura | Ambiente | Procedimento | Resultado | Evidência | Pendência |
|---|---|---|---|---|---|---|---|
| Add-on (`addon_options.py`, `run.sh`) | `0.2.0` (worktree) | independente | Windows 11, Python 3.14.10 | `python -m unittest tests.test_addon_options` | **16 testes, OK, 1 pulo** | saída do unittest | Pulo é a asserção de permissão POSIX, indisponível no Windows |
| Integração (helpers, checklist, persistência) | `0.2.0` (worktree) | independente | Windows 11, Python 3.14.7 (`.venv`), HA libs 2026.10.x | `.venv\Scripts\python.exe -m unittest tests.test_integration_helpers` | **34 testes, OK** | saída do unittest | Não substitui o harness de config flow |
| **Suíte pytest completa** | `0.2.0` (worktree) | independente | Windows 11, Python 3.14.7, `pytest-homeassistant-custom-component==0.13.375` + shims locais | `.venv\Scripts\python.exe -m pytest -q -p winsocket` | **55 passaram, 1 pulo, 26 subtests** | saída do pytest em 23/11/2026 | **Não é Linux/CI**; o pulo é a permissão POSIX |
| Repositório (metadados, versões, links, segredos, LF, traduções) | `0.2.0` (worktree) | independente | Windows 11, Python 3.14.10 | `python scripts/validate_repo.py` | **PASSOU** (2 avisos) | saída do script | Avisos: sem screenshots e sem `brand/icon.png` |
| Lint | config do repositório | independente | Windows 11 | `ruff check .` | **PASSOU** | saída do ruff | — |
| Formatação | config do repositório | independente | Windows 11 | `ruff format --check .` | **PASSOU** | saída do ruff | — |
| Sintaxe Python | — | independente | Windows 11 | `python -m compileall -q alexa_ma_skill custom_components tests scripts` | **PASSOU** | saída do compileall | — |
| Sintaxe shell | — | independente | Git Bash (Windows) | `bash -n alexa_ma_skill/run.sh` | **PASSOU** | saída do bash | Não executa o entrypoint |
| Traduções e JSON | — | independente | Windows 11 | validação em `scripts/validate_repo.py` (URLs, HTML, placeholders e estrutura) | **PASSOU** | saída do script | Regras espelham o Hassfest, mas não substituem a ferramenta oficial |

## 2. Testes de integração com o harness do Home Assistant

| Componente | Versão | Ambiente | Procedimento | Resultado | Evidência | Pendência |
|---|---|---|---|---|---|---|
| **Config flow (6 testes)** | `0.2.0` | Linux + harness HA no CI; Windows com shim como verificação suplementar | `python -m pytest -q` no job `integration` | **6 testes OK no CI Linux** | run 45276992158 | — |
| Options flow / setup assistido | `0.2.0` | Linux + harness HA | `python -m pytest -q` | **PARCIAL** | cobertura indireta por testes de helpers e pelo formulário simulado; options flow completo não tem teste dedicado | Adicionar teste de options flow no harness |
| Ciclo de vida (load/unload/reload) | `0.2.0` | Linux + harness HA + HA OS | CI / HA OS | **NÃO EXECUTADO** | revisão de código apenas | Depende de HA OS |

## 3. CI, Hassfest e HACS

| Verificação | Ferramenta | Estado | Evidência | Pendência |
|---|---|---|---|---|
| Workflow de CI | `.github/workflows/ci.yml` | **EXECUTADO — SUCESSO** | run 45276992158 no commit `ee16d8b`; 4 jobs aprovados; actionlint também passou | Reexecutar após as correções de aviso |
| Auditoria estática do Hassfest | Código do Hassfest (`2026.10.4`) | **CONCLUÍDO** | ordem do manifesto e URLs em traduções corrigidas | — |
| **Hassfest (plugins oficiais)** | HA Core `2026.10.4`, `scripts/run_hassfest_subset.py` | **PARCIAL — 0 erros** | 10 plugins, 1 integração, 0 erros | — |
| Hassfest oficial | `ghcr.io/home-assistant/hassfest` | **EXECUTADO — SUCESSO** | job `hassfest` do run 45276992158 | — |
| Auditoria estática do HACS | Schemas/documentação oficiais | **CONCLUÍDO** | `hacs.json`/manifesto conformes; `ignore` corrigido | `brand/icon.png` e release para catálogo padrão |
| HACS Action oficial | `hacs/action` | **EXECUTADO — SUCESSO** | job `hacs` do run 45276992158, com ignores de metadados do GitHub | Catálogo padrão exige Action sem ignores, brand e release |
| Build do add-on | Docker/Supervisor | **NÃO EXECUTADO** | — | Sem Docker no ambiente local; o build real ocorre no HA OS |
| Build multi-arquitetura | CI/Supervisor | **NÃO EXECUTADO** | — | `aarch64` não testado em execução |
| Artefato upstream (tag + digest) | GHCR | **VERIFICADO** | consulta read-only em 23/11/2026: HTTP 200, digest `sha256:b1ef33ad0b05b7e0a315535e8141177898be4b6a0401decf43dedf424f0d90f1`, índice OCI com `linux/amd64` e `linux/arm64` | O digest confere com o `FROM`; build e execução locais não foram feitos |

Para reproduzir a linha “Hassfest (plugins oficiais)”, use um checkout do Core
no tag correspondente e o utilitário do repositório:

```bash
python scripts/run_hassfest_subset.py --core-path /caminho/para/ha-core
```

O script roda 10 plugins e não substitui a action oficial (que inclui o plugin
`dependencies` e executa em Docker).

## 4. Validação manual em ambiente real

Evidências registradas em `AGENTS.md` a partir de uma instalação real anterior.
**Não foram reexecutadas nesta etapa.**

> Para testar a `0.2.0`, não use a loja/HACS apontando para `main`: eles
> entregam a versão da `main` (0.1.x). O roteiro em
> [`HAOS-TEST-PLAN.md`](HAOS-TEST-PLAN.md) instala o add-on **local** e a
> integração copiada do commit `5b75b63`.

| Item | Versão observada | Arquitetura | Ambiente | Resultado | Evidência | Pendência |
|---|---|---|---|---|---|---|
| Instalação e atualização do add-on | `0.1.1` | `amd64` | Home Assistant OS | **PARCIAL — OK** | relato em `AGENTS.md` §9.3 e §12 | Repetir com `0.2.0` |
| `/setup` reutilizando skill existente | `0.1.1` | `amd64` | HA OS | **PARCIAL — OK** | `AGENTS.md` §9.3 | Confirmar com a versão candidata |
| Provider Alexa do Music Assistant | `0.1.1` | `amd64` | HA OS + MA | **PARCIAL — OK** | `AGENTS.md` §12.8 | Validar comandos e dispositivos sem tela |
| Áudio e invocação em Echo | `0.1.1` | `amd64` | Echo físico | **PARCIAL — OK** | `AGENTS.md` §9.3 | Repetir após mudanças da Fase 3 |
| Comandos de controle (próxima/anterior) | `0.1.1` | `amd64` | MA + Echo | **PENDENTE** | — | Depende de `MA_API_URL` e associação em `/devices` |
| Backup e restauração | — | — | HA OS | **PENDENTE** | — | Executar backup `cold` e restaurar |
| Exposição externa completa (WAF/rotas) | — | — | Cloudflare/Traefik | **PARCIAL** | relato em `AGENTS.md` §12.3 | Matriz externa de todos os caminhos |
| `aarch64` | — | `aarch64` | HA OS | **NÃO EXECUTADO** | — | Sem hardware/CI de execução |

## 5. Versões declaradas x versões validadas

| Item | Declarado | Validado | Situação |
|---|---|---|---|
| Home Assistant mínimo | `2026.10.4` (`hacs.json`) | Bibliotecas 2026.10.x no ambiente de desenvolvimento; HA OS real em versão não registrada | **PARCIAL** — declarar apenas como versão de desenvolvimento até teste em HA OS |
| Music Assistant | sem versão mínima declarada | Integração real observada, versão não registrada | **PENDENTE** — não há versão mínima comprovada |
| Add-on | `0.2.0` candidata | `0.1.1` em uso real; `0.2.0` não instalada | **PENDENTE** — validar a candidata em HA OS |
| Integração | `0.2.0` candidata | 56 testes no CI Linux (inclui 6 config flow) + 10 plugins Hassfest | **PARCIAL** — falta HA OS e options flow dedicado |
| Arquiteturas | `amd64`, `aarch64` (`config.yaml`) | `amd64` com evidência real; índice OCI contém `amd64` e `arm64`; `aarch64` sem execução | **PARCIAL** — não declarar `aarch64` como validada |

### Arquiteturas em níveis

| Nível | `amd64` | `aarch64` |
|---|---|---|
| Declarada no manifesto | sim | sim |
| Publicada no índice OCI da imagem upstream | sim | sim (`linux/arm64`) |
| Build do add-on executado | não nesta etapa | não nesta etapa |
| Execução real do contêiner | sim, com `0.1.1` | não |
| Instalação funcional no HA OS | sim, com `0.1.1` | não |

A presença no índice OCI prova que a imagem upstream publica a arquitetura, **não**
que o add-on foi construído, iniciado ou testado nela.

## 6. Como atualizar esta matriz

1. Execute o procedimento indicado no ambiente correto.
2. Registre a versão exata, arquitetura, data e o resultado observado.
3. Anexe a evidência (log revisado, saída de comando ou captura sem dados
   sensíveis) na issue ou no pull request correspondente.
4. Só altere `NÃO EXECUTADO`/`PENDENTE` para resultado positivo com evidência
   verificável.
