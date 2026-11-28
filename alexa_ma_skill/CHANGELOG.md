# Changelog

Todas as mudanças relevantes do projeto. As versões anteriores a `0.2.0` foram
usadas em desenvolvimento e não tiveram distribuição pública.

## 0.2.0 — não publicado

Primeira versão candidata à distribuição. A publicação depende das validações
descritas em `docs/DISTRIBUTION-READINESS.md`.

### Adicionado

- Integração personalizada opcional em `custom_components/alexa_ma_skill/`, com
  config flow gerenciado, manual e reauth.
- Descoberta do add-on por `alexa_ma_skill` ou `*_alexa_ma_skill`, com seletor
  para múltiplas instalações e persistência do slug real.
- Options flow com atualização parcial, preservação de opções desconhecidas e
  confirmação antes de reiniciar o add-on.
- Sensores, binary sensors e diagnostics com `SKILL_ID` mascarado.
- Painel administrativo **Alexa MA** no menu lateral (`/alexa-ma`), somente para
  administradores, com visão geral somente leitura, seleção de config entry,
  atualização manual com cooldown e recuperação de erros.
- Setup assistido de 16 etapas, com estados, progresso, dependências, próxima
  ação e orientação de correção.
- Persistência das confirmações manuais em `Store`, com invalidação seletiva por
  chave de configuração.
- Aviso destacado e confirmação explícita sobre o comportamento do script
  upstream com skills "Music Assistant" duplicadas.
- Textos do checklist em pt-BR e inglês.
- Validador local/CI `scripts/validate_repo.py` para metadados, versões, links,
  line endings e padrões de segredo.
- Workflow de CI em `.github/workflows/ci.yml`, com testes, ruff, Hassfest e
  HACS Action, sem publicação de imagens, tags ou Releases.
- Templates de issue, matriz de validação, checklist de prontidão e rascunho de
  release em `docs/`.

### Alterado

- `README.md` reestruturado como página pública: apresentação, recursos,
  requisitos, instalação, arquitetura, segurança, problemas e suporte.
- `alexa_ma_skill/DOCS.md` com instalação manual e via HACS, validação,
  distribuição e suporte.
- `AGENTS.md` com a arquitetura da Fase 4, regras de CI e estado real.
- Versão do add-on e da integração alinhada em `0.2.0`.
- `sensor.setup_checklist` passou a publicar apenas uma allowlist de atributos:
  `console_values`, URLs internas e públicas, regras de Cloudflare e Skill IDs
  completos não são mais expostos nas entidades. Textos passam por sanitização
  e valores suspeitos são mascarados. O Options Flow continua usando os dados
  completos internamente por meio de `build_setup_checklist()`.
- Bundle do painel passa a preservar o banner da licença BSD-3-Clause do Lit
  3.3.3; o aviso integral foi incluído em `THIRD_PARTY_NOTICES.md`.
- `pyproject.toml` centraliza a configuração de ruff e pytest.

### Corrigido

- Migração de `/root/.ask` para `/data/ask` preserva a única cópia das
  credenciais quando a cópia falha, em vez de apagar o diretório legado.
- Credenciais geradas obsoletas são removidas ao definir credenciais explícitas,
  evitando reutilização de segredo antigo.
- `MA_API_URL` valida esquema HTTP(S)/WS(S), host e ausência de credenciais
  embutidas.
- `device_info` deixou de apontar a URL de configuração para a página pública
  `/setup`.
- Cache de checagem HTTPS limitado, evitando crescimento com URLs de stream
  rotativas.
- O checklist de setup não falha quando o coordinator ainda não tem dados.
- `manifest.json` reordenado conforme o Hassfest (`after_dependencies` após
  `name`).
- Removidas URLs dos valores de tradução, que o Hassfest rejeita.
- Corrigido o separador do `ignore` do HACS Action (lista separada por espaço) e
  desabilitado o comentário automático em PR com token somente leitura.
- Autenticação básica passou a usar `aiohttp.encode_basic_auth` com cabeçalho
  `Authorization`, removendo a depreciação de `aiohttp.BasicAuth` para o
  aiohttp 4.0.
- `actions/checkout` e `actions/setup-python` atualizados para versões Node 24
  (v7), eliminando os avisos de transição do runner.

### Segurança

- Nenhuma senha Amazon é solicitada ou armazenada pela integração.
- Nenhuma operação Amazon é executada automaticamente.
- Credenciais do add-on continuam em arquivos `600`; tokens não aparecem em
  logs, entidades ou diagnostics.
- `/setup` e `/status` permanecem restritos à rede local.
- Workflows usam permissões mínimas (`contents: read`), actions fixadas por SHA
  e não publicam artefatos. Dependabot mantém os SHAs atualizados.

### Compatibilidade

- Home Assistant mínimo declarado em `hacs.json`: `2026.10.4`, a versão do
  ambiente de desenvolvimento. Versões anteriores não foram validadas.
- Arquiteturas do add-on: `amd64` e `aarch64` declaradas. Execução real
  comprovada apenas em `amd64`.
- Music Assistant: sem versão mínima comprovada.
- Não há dependência de Nabu Casa.

### Pendente de validação

- Execução em `aarch64`.
- Backup/restauração e atualização `0.1.1 → 0.2.0` pela loja.
- Teste end-to-end dedicado do options flow e do reauth.
- Screenshots reais, `brand/icon.png` e uma Release completa para o catálogo
  padrão do HACS.

### Validação automatizada

- CI do GitHub Actions aprovada no commit `8ab7492` (run `45716728724`): 5 jobs,
  107 testes Linux/HA, 26 subtests e 38 testes de frontend.
- Validação local suplementar no Windows: 106 testes aprovados, 1 ignorado e 26
  subtests; typecheck, Ruff, formatação, `compileall`, `bash -n` e
  `validate_repo.py` aprovados.

### Validação manual

- Em Home Assistant real, a `0.2.0` foi instalada e seis cenários funcionais
  foram aprovados pelo usuário: invocação sem música ativa, troca de música,
  pausa/retomada, próxima música, reprodução em múltiplos Echos e painel
  lateral. Esses testes não fazem parte da CI.

## 0.1.1 - 2026-11-23

### Corrigido

- URL do repositório corrigida para
  `https://github.com/flaviocorrea13/alexa-skill`.
- Migração de `/root/.ask` para `/data/ask`: se a cópia falhar, o diretório
  legado é preservado em vez de ser apagado.
- Arquivos de credenciais geradas são removidos quando o usuário define
  credenciais explícitas.
- `MA_API_URL` validada como HTTP(S)/WS(S), sem credenciais embutidas.

### Alterado

- Documentação da invocação `music assistant`, do nome de exibição
  `Music Assistant` e da detecção de `SKILL_ID`.
- Documentação do slug de add-on de repositório personalizado
  (`<hash>_alexa_ma_skill`) e do hostname interno derivado.
- Documentação do provider Alexa do Music Assistant, da URL interna na porta
  `5000`, das credenciais Basic Auth e do teste de `/ma/latest-url`.
- Aviso de skills duplicadas antes do setup e separação entre acesso local e
  público aos endpoints administrativos.

## 0.1.0 - 2026-11-22

### Adicionado

- Versão inicial do add-on.
- Execução da imagem upstream `ghcr.io/alams154/music-assistant-skill` fixada por
  versão e digest.
- Persistência das credenciais do ASK CLI em `/data/ask` com symlink em
  `/root/.ask`.
- Geração de usuário e senha aleatórios quando as opções estão vazias, sem
  registrar segredos nos logs.
- Reescrita de `/data/options.json` com caminhos de segredo para evitar que o
  upstream sobrescreva as credenciais no import.
- Token da API do Music Assistant gravado em arquivo com permissão `600`.
- Traduções pt-BR e en para as opções e a porta.
- Documentação da exposição pública somente de `POST /`, mantendo `/setup` e
  `/status` na rede local.
- Avisos de licença MIT e Amazon Software License 1.0.
