# Matriz de compatibilidade e validação

**Atualizado em:** 25 de novembro de 2026\
**Versão candidata:** `0.2.0` (não publicada)\
**Ambiente de preparação:** Windows 11, Python 3.14.10, virtualenv do projeto,
sem Docker, sem WSL e sem Home Assistant OS local. A instalação real foi feita
pelo usuário em um Home Assistant separado, com Music Assistant, Echo e conta
Amazon; os seis cenários manuais estão registrados na seção 4.

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
| Run | [45716728724](https://github.com/flaviocorrea13/alexa-skill/actions/runs/45716728724) |
| Commit | `8ab74928d2004422a349d60cabf7672e75fccf5d` |
| Evento | `pull_request` (PR #1, Draft) |
| Resultado geral | **success — 5/5 jobs** |

| Job | Resultado |
|---|---|
| Repository and add-on validation | **Sucesso** |
| Integration tests (Home Assistant harness) | **Sucesso** — 107 testes, 26 subtestes, Linux/Python 3.14.10/HA 2026.10.4 |
| Frontend build | **Sucesso** — typecheck, 38 testes, build e bundle reproduzível |
| Hassfest | **Sucesso** |
| HACS validation | **Sucesso** |

> A evidência acima é do commit `8ab7492`. O diff documental/licença posterior
> exige uma nova execução da CI no commit final antes da publicação.

## 1. Testes automatizados locais

| Componente | Versão | Arquitetura | Ambiente | Procedimento | Resultado | Evidência | Pendência |
|---|---|---|---|---|---|---|---|
| Add-on (`addon_options.py`, `run.sh`) | `0.2.0` (worktree) | independente | Windows 11, Python 3.14.10 | `python -m unittest tests.test_addon_options` | **16 testes, OK, 1 pulo** | saída do unittest | Pulo é a asserção de permissão POSIX, indisponível no Windows |
| Integração (helpers, checklist, persistência) | `0.2.0` (worktree) | independente | Windows 11, Python 3.14.7 (`.venv`), HA libs 2026.10.x | `.venv\Scripts\python.exe -m unittest tests.test_integration_helpers` | **58 testes, OK** | saída do unittest | Não substitui o harness de config flow |
| **Suíte pytest completa** | `0.2.0` (worktree) | independente | Windows 11, Python 3.14.7, `pytest-homeassistant-custom-component==0.13.375` + shims locais | `.venv\Scripts\python.exe -m pytest -q -p winsocket` | **106 passaram, 1 pulo, 26 subtests** | saída do pytest em 25/11/2026 | **Não é Linux/CI**; o pulo é a permissão POSIX |
| Frontend (painel) | `0.2.0` (worktree) | independente | Node.js 24, TypeScript 5.9, Lit 3.3.3 | `npm run typecheck` / `npm test` | **OK / 38 testes** | saída do npm | Testes headless, sem DOM real |
| Repositório (metadados, versões, links, segredos, LF, traduções) | `0.2.0` (worktree) | independente | Windows 11, Python 3.14.10 | `python scripts/validate_repo.py` | **PASSOU** (2 avisos) | saída do script | Avisos: sem screenshots e sem `brand/icon.png` |
| Lint | config do repositório | independente | Windows 11 | `ruff check .` | **PASSOU** | saída do ruff | — |
| Formatação | config do repositório | independente | Windows 11 | `ruff format --check .` | **PASSOU** | saída do ruff | — |
| Sintaxe Python | — | independente | Windows 11 | `python -m compileall -q alexa_ma_skill custom_components tests scripts` | **PASSOU** | saída do compileall | — |
| Sintaxe shell | — | independente | Git Bash (Windows) | `bash -n alexa_ma_skill/run.sh` | **PASSOU** | saída do bash | Não executa o entrypoint |
| Traduções e JSON | — | independente | Windows 11 | validação em `scripts/validate_repo.py` (URLs, HTML, placeholders e estrutura) | **PASSOU** | saída do script | Regras espelham o Hassfest, mas não substituem a ferramenta oficial |

## 2. Testes de integração com o harness do Home Assistant

| Componente | Versão | Ambiente | Procedimento | Resultado | Evidência | Pendência |
|---|---|---|---|---|---|---|
| **Config flow (6 testes)** | `0.2.0` | Linux + harness HA no CI; Windows com shim como verificação suplementar | `python -m pytest -q` no job `integration` | **6 testes OK no CI Linux** | run 45716728724 | — |
| Options flow / setup assistido | `0.2.0` | Linux + harness HA | `python -m pytest -q` | **PARCIAL** | cobertura indireta por testes de helpers e pelo formulário simulado; options flow completo não tem teste dedicado | Adicionar teste de options flow no harness |
| Ciclo de vida (load/unload/reload) | `0.2.0` | Linux + harness HA + HA real | CI / uso real | **PARCIAL** | testes unitários do painel e uso real do usuário; sem teste E2E dedicado | Adicionar teste de lifecycle no harness |

## 3. CI, Hassfest e HACS

| Verificação | Ferramenta | Estado | Evidência | Pendência |
|---|---|---|---|---|
| Workflow de CI | `.github/workflows/ci.yml` | **EXECUTADO — SUCESSO** | run 45716728724 no commit `8ab7492`; 5 jobs aprovados; actionlint também passou | — |
| Auditoria estática do Hassfest | Código do Hassfest (`2026.10.4`) | **CONCLUÍDO** | ordem do manifesto e URLs em traduções corrigidas | — |
| **Hassfest (plugins oficiais)** | HA Core `2026.10.4`, `scripts/run_hassfest_subset.py` | **PARCIAL — 0 erros** | 10 plugins, 1 integração, 0 erros | — |
| Hassfest oficial | `ghcr.io/home-assistant/hassfest` | **EXECUTADO — SUCESSO** | job `hassfest` do run 45716728724 | — |
| Auditoria estática do HACS | Schemas/documentação oficiais | **CONCLUÍDO** | `hacs.json`/manifesto conformes; `ignore` corrigido | `brand/icon.png` e release para catálogo padrão |
| HACS Action oficial | `hacs/action` | **EXECUTADO — SUCESSO** | job `hacs` do run 45716728724, com ignores de metadados do GitHub | Catálogo padrão exige Action sem ignores, brand e release |
| Frontend | Rollup/TypeScript/Lit | **EXECUTADO — SUCESSO** | job `frontend`: 38 testes, typecheck, build e bundle reproduzível | — |
| Build do add-on | Docker/Supervisor | **PARCIAL — OK no HA real** | Build pelo Supervisor na instalação real do usuário; sem Docker no ambiente local e sem job de build na CI | Adicionar build automatizado, se desejado |
| Build multi-arquitetura | CI/Supervisor | **PARCIAL** | Instalação real com arquitetura não registrada; `aarch64` não testado em execução | Registrar a arquitetura e validar `aarch64` |
| Artefato upstream (tag + digest) | GHCR | **VERIFICADO** | consulta read-only em 23/11/2026: HTTP 200, digest `sha256:b1ef33ad0b05b7e0a315535e8141177898be4b6a0401decf43dedf424f0d90f1`, índice OCI com `linux/amd64` e `linux/arm64` | O digest confere com o `FROM`; build local/CI não executado |

Para reproduzir a linha “Hassfest (plugins oficiais)”, use um checkout do Core
no tag correspondente e o utilitário do repositório:

```bash
python scripts/run_hassfest_subset.py --core-path /caminho/para/ha-core
```

O script roda 10 plugins e não substitui a action oficial (que inclui o plugin
`dependencies` e executa em Docker).

## 4. Validação manual em ambiente real

Os seis cenários abaixo foram executados pelo **usuário** em uma instalação real
do Home Assistant com a versão `0.2.0`. Eles são evidência manual e **não** fazem
parte da CI.

> Para testar a `0.2.0` no HAOS, não use a loja/HACS apontando para `main`: eles
> entregam a versão da `main` (0.1.x). O roteiro em
> [`HAOS-TEST-PLAN.md`](HAOS-TEST-PLAN.md) instala o add-on **local** e a
> integração copiada do commit `8ab7492`.

| Cenário executado pelo usuário | Versão | Ambiente | Resultado | Evidência |
|---|---|---|---|---|
| Invocação sem música ativa | `0.2.0` | Home Assistant real + Alexa/Echo | **Aprovado manualmente** | relato do usuário; não é CI |
| Troca de música | `0.2.0` | Home Assistant real + Alexa/Echo | **Aprovado manualmente** | relato do usuário; não é CI |
| Pausa e retomada | `0.2.0` | Home Assistant real + Alexa/Echo | **Aprovado manualmente** | relato do usuário; não é CI |
| Próxima música | `0.2.0` | Home Assistant real + Alexa/Echo | **Aprovado manualmente** | relato do usuário; não é CI |
| Reprodução em múltiplos Echos | `0.2.0` | Home Assistant real + múltiplos Echos | **Aprovado manualmente** | relato do usuário; não é CI |
| Painel lateral do Home Assistant | `0.2.0` | Home Assistant real | **Aprovado manualmente** | relato do usuário; não é CI |

### Ainda pendente de validação manual

| Item | Estado | Observação |
|---|---|---|
| Backup e restauração | **PENDENTE** | Executar backup `cold` e restaurar |
| Atualização `0.1.1 → 0.2.0` pela loja | **PENDENTE** | O canal de instalação usado no teste real não está registrado |
| `aarch64` | **NÃO EXECUTADO** | Sem hardware/runner de execução |
| Options flow e reauth completos | **PENDENTE** | Sem teste E2E dedicado no harness |
| Exposição externa completa (WAF/rotas) | **PARCIAL** | Validar a matriz de todos os caminhos |
| Estados de erro e reconexão do painel | **PENDENTE** | Testar add-on parado e reconexão do WebSocket |
| Screenshots reais | **PENDENTE** | Capturas sem dados sensíveis |

## 5. Versões declaradas x versões validadas

| Item | Declarado | Validado | Situação |
|---|---|---|---|
| Home Assistant mínimo | `2026.10.4` (`hacs.json`) | Bibliotecas 2026.10.x no CI; HA real em versão não registrada | **PARCIAL** — versão real do HA não documentada |
| Music Assistant | sem versão mínima declarada | Integração real observada, versão não registrada | **PENDENTE** — não há versão mínima comprovada |
| Add-on | `0.2.0` candidata | `0.2.0` instalada e testada em HA real; atualização pela loja pendente | **PARCIAL** — falta atualização `0.1.1 → 0.2.0` e `aarch64` |
| Integração | `0.2.0` candidata | 107 testes no CI Linux + 38 frontend + 6 cenários manuais; painel validado | **PARCIAL** — falta options flow/reauth E2E |
| Arquiteturas | `amd64`, `aarch64` (`config.yaml`) | Execução real em HA (arquitetura não registrada); índice OCI contém `amd64` e `arm64`; `aarch64` sem execução | **PARCIAL** — não declarar `aarch64` como validada |

### Arquiteturas em níveis

| Nível | `amd64` | `aarch64` |
|---|---|---|
| Declarada no manifesto | sim | sim |
| Publicada no índice OCI da imagem upstream | sim | sim (`linux/arm64`) |
| Build do add-on executado | sim, via Supervisor (arquitetura não registrada) | não |
| Execução real do contêiner | sim, com `0.2.0` | não |
| Instalação funcional no Home Assistant | sim, com `0.2.0` | não |

A presença no índice OCI prova que a imagem upstream publica a arquitetura, **não**
que o add-on foi construído, iniciado ou testado nela. A arquitetura exata da
instalação real do usuário não foi registrada; a coluna `amd64` representa o
ambiente esperado, não uma confirmação documentada.

## 6. Como atualizar esta matriz

1. Execute o procedimento indicado no ambiente correto.
2. Registre a versão exata, arquitetura, data e o resultado observado.
3. Anexe a evidência (log revisado, saída de comando ou captura sem dados
   sensíveis) na issue ou no pull request correspondente.
4. Só altere `NÃO EXECUTADO`/`PENDENTE` para resultado positivo com evidência
   verificável.
