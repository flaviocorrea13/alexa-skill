# AGENTS.md

Contexto permanente do projeto **alexa-ma-skill** para futuras sessões de
desenvolvimento. Leia este arquivo antes de alterar o repositório.

## 1. Objetivo

Construir uma solução para Home Assistant que permita controlar o **Music
Assistant** por voz usando a **Alexa**, sem depender de Nabu Casa e sem
serviços de terceiros gerenciados pelo projeto.

A solução prevê duas partes:

1. **Add-on do Home Assistant** (`alexa_ma_skill/`): executa o contêiner
   upstream `ghcr.io/alams154/music-assistant-skill`, com credenciais
   persistentes, geração segura de senhas e documentação de exposição pública.
2. **Integração personalizada** (`custom_components/`, Fase 2): camada opcional
   para configurar o add-on pela interface do Home Assistant, reportar
   diagnóstico e guiar o setup da skill Alexa. Está implementada, mas os testes
   completos em Linux e o Hassfest ainda estão pendentes; não é necessária para
   o add-on.

O add-on e a integração são peças separadas. Uma integração do Home Assistant
**não pode iniciar contêineres**; ela configura o add-on via Supervisor/opções
e consulta o serviço interno.

## 2. Arquitetura

### 2.1 Add-on

- Imagem base upstream fixada por tag e digest no `FROM` do
  `alexa_ma_skill/Dockerfile`.
- O add-on publica a porta `5000/tcp` no host (padrão `5000`).
- O entrypoint é `alexa_ma_skill/run.sh`; ele prepara credenciais e ambiente e
  executa o CMD original da imagem.
- A aplicação Flask upstream roda em `0.0.0.0:5000`.
- A Alexa chama `POST /` em `https://SKILL_HOSTNAME/`.
- `/setup` e `/status` existem para configuração e diagnóstico, mas devem ficar
  acessíveis **somente na rede local**.
- O áudio vem do Music Assistant. O add-on reescreve a URL do stream para
  `https://MA_HOSTNAME/...`; o túnel deve encaminhar `MA_HOSTNAME` para a porta
  de stream do Music Assistant (normalmente `8097`).
- O projeto **não** cria túneis, **não** gerencia certificados e **não**
  configura DNS. O usuário fornece o túnel/reverse proxy HTTPS.
- **Não** adicionar Caddy, nginx ou terminação TLS ao add-on. O TLS é
  responsabilidade da borda do usuário.

### 2.2 Integração personalizada (Fase 2)

Implementada como camada **opcional**, mas ainda **não validada** por testes
completos em Linux/Hassfest. O add-on funciona sem ela. A Fase 2 só pode ser
considerada concluída após os testes de config flow/options flow passarem no CI,
Hassfest e revisão de segurança final.

- Fica em `custom_components/alexa_ma_skill/`.
- Configura o add-on pela UI do Home Assistant (config flow).
- Gera credenciais e grava as opções do add-on via Supervisor.
- Consulta o serviço interno do add-on no hostname derivado do slug do
  Supervisor, trocando `_` por `-`: `http://<slug-com-hifens>:5000` (por
  exemplo `0a1b2c3d-alexa-ma-skill`).
- O acesso ao setup suportado é **local**:
  `http://<IP_DO_HOME_ASSISTANT>:5000/setup`. Nunca usar
  `https://<SKILL_HOSTNAME>/setup`; esse caminho é bloqueado pela regra de
  segurança do hostname público.
- Deve ser compatível com HACS e ter `manifest.json` completo.
- **Pendência registrada:** avaliar os helpers do componente `hassio` em vez de
  HTTP cru no Supervisor e declarar a dependência no `manifest.json`.

## 3. Decisões e restrições

### 3.1 Rede e exposição pública

- Dois hostnames públicos no **domínio próprio** do usuário, sem esquema:
  - `SKILL_HOSTNAME`: skill Alexa, aponta para a porta `5000` do add-on.
  - `MA_HOSTNAME`: stream do Music Assistant, aponta para a porta `8097` do MA.
- Hostnames devem ser bare hostnames: sem `http://`, sem `https://`, sem
  caminho, sem query e sem porta.
- **Nabu Casa não é usado.**
- **Cloudflare Tunnel** é um exemplo; qualquer túnel/reverse proxy HTTPS com
  certificado válido serve.
- Expor publicamente **apenas** `POST /` em `SKILL_HOSTNAME`.
- Bloquear na borda `/setup`, `/status`, `/devices`, `/docs`, `/ma` e `/alexa`.
- Regra Cloudflare recomendada (ação **Block**):

  ```text
  (http.host eq "skill.exemplo.com" and not (http.request.uri.path eq "/" and http.request.method eq "POST"))
  ```

- Manter `/setup` e `/status` acessíveis apenas na rede local, por exemplo em
  `http://<IP_DO_HOME_ASSISTANT>:5000/setup`.
- TLS mínimo **1.2**. A imagem upstream **não suporta TLS 1.3**.
- A Alexa exige HTTPS na porta `443` com certificado confiável; não usar
  certificado autoassinado.

### 3.2 Imagem e build

- Imagem base:

  ```text
  ghcr.io/alams154/music-assistant-skill:0.0.39-beta
  sha256:b1ef33ad0b05b7e0a315535e8141177898be4b6a0401decf43dedf424f0d90f1
  ```

- Nunca usar `:latest`.
- A imagem é multi-arch; o mesmo `FROM` serve para `amd64` e `aarch64`.
- **Não recriar `build.yaml`.** Ele está depreciado; o `FROM` do `Dockerfile` é
  a fonte da verdade.
- O `Dockerfile` instala `tzdata` porque a imagem upstream não inclui o banco de
  fusos horários.
- O `Dockerfile` define `ENTRYPOINT ["/run.sh"]` e **redeclara o CMD original**
  da imagem base, porque definir `ENTRYPOINT` limpa o CMD herdado. O fallback
  dentro de `run.sh` é apenas reserva para execução manual sem argumentos.

### 3.3 Configuração e credenciais

- Toda configuração do add-on é feita pelas opções do Home Assistant.
- `SKILL_HOSTNAME` é obrigatório e não tem valor padrão em `options`; o
  Supervisor exige o preenchimento antes de iniciar.
- `MA_HOSTNAME` é opcional, mas obrigatório na prática para dispositivos sem
  tela (Echo Dot etc.) e para exibir capa.
- `PORT` é fixo em `5000` (`list(5000)`).
- `LOCALE` aceita: `pt-BR`, `en-US`, `en-GB`, `en-AU`, `en-CA`, `en-IN`,
  `de-DE`, `es-ES`, `es-MX`, `fr-FR`, `fr-CA`, `it-IT`, `nl-NL`.
- `APP_USERNAME` e `APP_PASSWORD` protegem `/setup`, `/status`, `/devices`,
  `/docs`, `/ma` e `/alexa`. `POST /` é isento para a Alexa.
- **Nunca** usar credenciais padrão (`admin`, `teste` etc.).
- Se `APP_USERNAME`/`APP_PASSWORD` estiverem vazios, gerar valores aleatórios:
  - usuário: prefixo `alexa_` + token hexadecimal;
  - senha: `secrets.token_urlsafe(32)`.
- **Nunca** registrar senhas ou tokens nos logs. Mensagens podem informar
  apenas o caminho do arquivo e o modo `600`.
- `SKILL_ID` é opcional durante o primeiro setup. Depois que a skill é criada,
  preencher com o ID `amzn1.ask.skill...` para restringir a skill às próprias
  requisições. Sem ele, o upstream aceita qualquer skill assinada pela Amazon.
- `MA_API_URL` é a API WebSocket do Music Assistant na porta **8095**. Não é a
  porta de stream **8097**. Exemplo: `http://192.0.2.10:8095`.
- `MA_API_TOKEN` é opcional. Quando informado, é gravado em
  `/data/generated_ma_api_token` (modo `600`) e o add-on passa apenas o caminho
  para a aplicação, para não expor o token no log do upstream.
- Não incluir usuário/senha dentro de `MA_API_URL`; usar `MA_API_TOKEN`.

### 3.4 Persistência do ASK CLI

- Credenciais do ASK CLI ficam em `/data/ask`, persistidas entre reinícios e
  backups.
- O caminho esperado pela imagem original, `/root/.ask`, é um symlink para
  `/data/ask`.
- **Nunca definir `ASK_CREDENTIALS_DIR`.** O `setup_helpers.py` do upstream dá
  prioridade a essa variável e passaria a usar `/data/.ask` em vez do symlink
  `/root/.ask`. O `run.sh` faz `unset ASK_CREDENTIALS_DIR`.
- Ordem de resolução do upstream: `ASK_CREDENTIALS_DIR` → `/root/.ask` →
  `~/.ask`.

### 3.5 Licenciamento

- Código original deste repositório: **MIT** (`LICENSE`).
- Imagem base upstream: **Amazon Software License 1.0** (ASL 1.0), texto
  integral em `LICENSE-AMAZON-SOFTWARE-1.0`.
- `THIRD_PARTY_NOTICES.md` explica a ASL 1.0: não é licença OSI, tem limitação
  de uso (Seção 3.3), exige cópia completa da licença, preservação de avisos e
  identificação de obras derivadas.
- O uso pretendido é integração com a Alexa, uma plataforma da Amazon.
- Não afiliado, endossado ou patrocinado pela Amazon ou pela Music Assistant.

### 3.6 Desenvolvimento

- Idioma principal: **pt-BR**. Inglês é secundário.
- Textos de UI do add-on em `alexa_ma_skill/translations/pt-BR.yaml` e
  `en.yaml`. A integração opcional usa os arquivos de tradução do HA Core
  (`translations/pt-BR.json` e `en.json`).
- Integração em **Python async e tipado**, sem bloquear o event loop.
- O script de entrypoint do add-on (`addon_options.py`) é um CLI de startup
  síncrono e usa apenas a biblioteca padrão; isso é intencional.
- Um commit por fase, com mensagem clara. Não misturar fases no mesmo commit.
- Line endings LF; `.gitattributes` e `.gitignore` já configurados.
- Não commitar segredos, credenciais, `options.json` real ou diretórios de
  dados locais.
- Antes de abrir PR, rode `python scripts/validate_repo.py`, `ruff check .`,
  `ruff format --check .` e os testes locais possíveis. O target do ruff é
  `py311` porque o add-on roda no Python da imagem upstream, não no Python do
  harness de testes.
- A CI não publica imagens, tags ou Releases. Publicação exige autorização
  explícita.

## 4. Variáveis reais do contêiner

### 4.1 Opções do add-on

Definidas em `alexa_ma_skill/config.yaml`:

| Variável | Obrigatória | Padrão | Observação |
|---|:---:|---|---|
| `SKILL_HOSTNAME` | Sim | — | Bare hostname público da skill. |
| `MA_HOSTNAME` | Não | — | Bare hostname público do stream do MA. |
| `APP_USERNAME` | Não | gerado | Basic auth do painel. |
| `APP_PASSWORD` | Não | gerado | Basic auth do painel; nunca logar. |
| `PORT` | Não | `5000` | Fixo em `5000`. |
| `LOCALE` | Não | `pt-BR` | Lista de locales suportados. |
| `TZ` | Não | `America/Sao_Paulo` | Fuso do contêiner. |
| `AWS_DEFAULT_REGION` | Não | `us-east-1` | Região do ASK CLI. |
| `ENABLE_APL` | Não | `false` | APL em dispositivos com tela. |
| `SKIP_URL_VALIDATION` | Não | `false` | Pula validação da URL de áudio. |
| `SKILL_ID` | Não | — | Restringe a skill às próprias requisições. |
| `MA_API_URL` | Não | — | API WebSocket do MA, porta `8095`. |
| `MA_API_TOKEN` | Não | — | Token do MA; gravado como arquivo `600`. |

### 4.2 Variáveis fixas do entrypoint

`run.sh` exporta, independentemente das opções:

```text
HOST=0.0.0.0
QUIET_HTTP=1
FLASK_DEBUG=0
FLASK_RELOADER=0
PYTHONUNBUFFERED=1
DEBUG_PORT=0
```

### 4.3 Como o `app.py` recarrega o ambiente

O upstream `app/app.py` executa `_load_addon_options_into_env()` no import:

- lê `/data/options.json`;
- para cada chave com valor não nulo, faz `os.environ[str(key)] = str(value)`;
- isso **sobrescreve** variáveis exportadas pelo `run.sh`.

Por isso, o `addon_options.py` **reescreve** `/data/options.json` antes de
iniciar a aplicação:

- credenciais vazias viram caminhos de arquivo:
  - `/data/generated_app_username`
  - `/data/generated_app_password`
- o token do MA vira `/data/generated_ma_api_token`;
- os arquivos são criados com modo `600`;
- `APP_USERNAME`/`APP_PASSWORD` são redigidos no log pelo upstream
  (`_safe_options_for_log`);
- `MA_API_TOKEN` **não** é redigido pelo upstream, por isso é sempre passado
  como caminho de arquivo, nunca como valor bruto.

O `env_secrets.get_env_secret(name)` do upstream trata o valor como segredo em
arquivo quando o caminho existe e é um arquivo; caso contrário, usa o valor
bruto. Essa é a base do funcionamento das credenciais em arquivo.

## 5. Persistência do ASK CLI

Fluxo implementado em `run.sh`:

1. `mkdir -p /data/ask` e `chmod 700 /data/ask`.
2. Garante `/root/.ask` como symlink para `/data/ask`.
3. Se `/root/.ask` for um diretório legado, copia o conteúdo para `/data/ask`
   com `cp -an` (sem sobrescrever o que já é persistente).
4. Nunca exporta `ASK_CREDENTIALS_DIR`.
5. Executa `addon_options.py`, exporta o ambiente e inicia o CMD.

Os backups do add-on incluem `/data`, portanto incluem `/data/ask`, as
credenciais geradas e o token do MA. Tratar backups como material sensível.

## 6. Fluxo de setup da skill

- `/setup` inicia `ask configure --no-browser` quando não há credenciais ASK
  funcionais.
- O login e a autorização na Amazon são **manuais**: o usuário abre a URL,
  autoriza e cola o código no painel.
- Depois da autenticação, o upstream executa `scripts/ask_create_skill.sh`.
- O script monta o manifesto com `https://SKILL_HOSTNAME`, envia modelos de
  interação, aguarda a compilação e tenta habilitar a skill para testes.
- Ele procura skills existentes com o nome exato **"Music Assistant"**:
  - se houver uma, reutiliza;
  - se houver mais de uma, apaga as extras e mantém a primeira.
- O manifesto construído pelo upstream sobrescreve o nome de exibição para
  **"Music Assistant"**.
- O `scripts/ask_create_skill.sh` do upstream sobrescreve o `invocationName`
  de todos os modelos para **"music assistant"** antes do upload. O valor
  final no console é `music assistant` em todos os locales; os valores dos
  modelos brutos (`minha rádio`, `my radio` etc.) não são usados.
- Não há endpoint no contêiner que exponha o `invocationName`. A integração
  usa a constante `INVOCATION_NAME = "music assistant"` em `const.py`; se o
  upstream mudar o script, essa constante precisa ser atualizada.
- Os modelos brutos `fr-CA` e `nl-NL` têm `invocationName` vazio, mas o script
  o substitui por `music assistant` antes do upload. A criação nesses locales
  **não foi validada** por outros motivos (manifesto/ícones); não afirmar que a
  falha é por invocation vazia.
- O manifesto gerado usa `sslCertificateType: Wildcard`. Se a Amazon recusar o
  endpoint, ajustar para **Trusted** no console.
- Ao final, copiar o `Done. Skill ID: amzn1.ask.skill...` para `SKILL_ID` e
  reiniciar o add-on.

## 7. Pendências por fase

### 7.1 Fase 2 — integração personalizada

Implementada, **opcional**, com testes de helpers e config flow aprovados no CI
Linux, Hassfest e HACS Action aprovados. Falta um teste dedicado do options flow
e a validação em HA OS.

- `custom_components/alexa_ma_skill/` com `manifest.json` existe.
- Config flow pela UI do Home Assistant existe, incluindo descoberta de slug,
  seletor para múltiplos add-ons e modo manual sem Supervisor.
- Geração/reuso de credenciais e gravação das opções do add-on existem.
- Diagnóstico, sensores, binary sensors e diagnostics existem.
- Orientação do setup da skill existe no código.
- **Usar os helpers do componente `hassio` em vez de HTTP cru no Supervisor**
  foi implementado; a dependência declarada é `after_dependencies`.
- Compatibilidade HACS ainda não validada (`hacs.json` existe na raiz).
- O add-on é consultado no hostname derivado do slug do Supervisor, por
  exemplo `http://0a1b2c3d-alexa-ma-skill:5000`.
- O acesso ao setup é local:
  `http://<IP_DO_HOME_ASSISTANT>:5000/setup`. A URL pública
  `https://<SKILL_HOSTNAME>/setup` é bloqueada e não deve ser usada.
- Pendente: executar `tests/test_config_flow.py` no Linux, Hassfest/HACS,
  validação em HA OS e revisão de segurança final.

### 7.2 Fase 3 — setup assistido

Implementado no código, **opcional**; testes de helpers aprovados, validação
completa em Linux/HA pendente.

- Checklist de 16 etapas com estados, progresso e próxima ação.
- Modelo distingue etapas automáticas e manuais.
- Confirmações manuais persistidas em `Store` por entry.
- Invalidação seletiva por chave de configuração.
- Aviso explícito sobre skills "Music Assistant" duplicadas antes da etapa
  sensível.
- `SKILL_ID` detectado/configurado/sugerido e `binary_sensor.skill_id_valid`.
- Instruções do provider Alexa do MA, portas `5000`, `8095` e `8097`.
- Testes de reprodução e comandos dependem de confirmação manual real.
- Pendente: executar config flow/options flow no Linux, Hassfest, HACS Action,
  CI e validação em HA OS.

### 7.3 Fase 4 — distribuição

Preparada, **não publicada**. Documentação, validador local, CI, templates,
matriz de validação, checklist de prontidão e rascunho de release existem.
Hassfest, HACS Action, `pytest` no Linux, instalação da `0.2.0` em HA OS e
screenshots reais continuam pendentes. Ver seção 15.

## 8. Regras de implementação

- Credenciais nunca padrão e nunca logadas.
- Senhas e tokens apenas em arquivos `600`, ou em opções quando o upstream
  exige, sempre com redação nos logs.
- Textos em `translations` pt-BR e en.
- Integração em Python async e tipado; não usar I/O bloqueante no event loop.
- Um commit por fase.
- Não alterar o código interno da imagem upstream; o projeto é um wrapper.
- Não adicionar `build.yaml`.
- Não usar `:latest`.
- Não definir `ASK_CREDENTIALS_DIR`.
- Não expor `/setup`, `/setup/*`, `/status`, `/status/*`, `/devices`, `/docs`,
  `/openapi.json`, `/ma`, `/alexa`, `/simulator` ou `/invocations` publicamente.
- Não adicionar Caddy/nginx/túnel ao add-on.
- Não commitar segredos ou dados de `/data`.
- Manter line endings LF.

## 9. Estado atual

### 9.1 Fase 1 implementada; validação real parcial

- Commit inicial: `92b3d21`
- Mensagem: `feat(addon): adiciona add-on Alexa MA Skill com persistência de credenciais ASK`
- Branch: `main`
- Estado: implementação concluída, testes locais possíveis executados e
  evidência real parcial em HA OS. A matriz manual completa continua pendente;
  a Fase 1 **não** é declarada integralmente validada.

### 9.2 Arquivos principais

```text
.
├── repository.yaml
├── hacs.json
├── pyproject.toml                   # ruff + pytest
├── README.md
├── AGENTS.md
├── requirements_test.txt            # harness Home Assistant (Linux)
├── requirements_ci.txt              # ruff + PyYAML
├── scripts/
│   ├── validate_repo.py             # validação local/CI
│   └── run_hassfest_subset.py       # Hassfest local sem Docker
├── .github/
│   ├── workflows/ci.yml
│   ├── ISSUE_TEMPLATE/
│   └── pull_request_template.md
├── docs/
│   ├── DISTRIBUTION-READINESS.md
│   ├── VALIDATION-MATRIX.md
│   ├── releases/RELEASE-DRAFT.md
│   └── images/README.md             # capturas pendentes
├── LICENSE
├── LICENSE-AMAZON-SOFTWARE-1.0
├── THIRD_PARTY_NOTICES.md
├── custom_components/
│   └── alexa_ma_skill/              # Integração opcional
├── tests/
│   ├── conftest.py
│   ├── test_addon_options.py
│   ├── test_integration_helpers.py
│   └── test_config_flow.py
└── alexa_ma_skill/
    ├── config.yaml
    ├── Dockerfile
    ├── run.sh
    ├── addon_options.py
    ├── DOCS.md
    ├── CHANGELOG.md
    └── translations/
        ├── pt-BR.yaml
        └── en.yaml
```

O `PLANO-PUBLICACAO.md` é um documento interno de planejamento mantido no
worktree local e **fora do repositório público/PR**.

### 9.3 Validação já executada

- YAML/JSON parseados.
- `addon_options.py` compilado.
- `bash -n alexa_ma_skill/run.sh` aprovado (Git Bash).
- `ruff check` e `ruff format --check` aprovados.
- `tests/test_addon_options.py` com `unittest`: geração/reuso de credenciais,
  remoção de credenciais geradas ao usar credenciais explícitas, token do MA,
  validação de `MA_API_URL`, hostnames inválidos, porta/idioma inválidos e
  normalização de booleanos. Permissões POSIX ficam puladas no Windows.
- `tests/test_integration_helpers.py` com `unittest` e as bibliotecas do HA:
  descoberta de slug, validação de hostname/URL, preservação de opções,
  parsing de `/status`/`/setup`, checklist, sensores, diagnostics e lógica do
  coordinator. Executado com `.venv` no Windows.
- `tests/test_config_flow.py`: escrito para o harness Linux do Home Assistant,
  mas **não executado** no Windows. Apenas `--collect-only`: 6 testes coletados.
- Em 23/11/2026, para validação operacional da Fase 4, a suíte foi executada no
  Windows com shims `fcntl`/`resource` e sockets habilitados, mantidos **fora do
  repositório**: **6 config flow OK** e **55 passed, 1 skipped, 26 subtests** no
  `pytest` completo. Isso é evidência suplementar, **não** substitui Linux/CI.
- `scripts/validate_repo.py`: valida metadados, versões, manifestos, links,
  traduções (URLs/HTML/placeholders), steps/menu do config flow, LF e padrões de
  segredo. A auditoria estática do Hassfest corrigiu a ordem do `manifest.json`
  e removeu URLs das traduções.
- Hassfest: **10 plugins oficiais** (HA Core `2026.10.4`) passaram localmente
  com 0 erros; a execução oficial da imagem, incluindo `dependencies`, passou no
  CI (run 45276992158).
- CI Linux, Hassfest e HACS Action: **executados e aprovados** no commit
  `ee16d8b` (run 45276992158). O job de integração aprovou 56 testes e 26
  subtestes. A autenticação básica deixou de usar `aiohttp.BasicAuth` depreciado
  e as actions foram atualizadas para versões Node 24.
- Verificação de LF.
- Em HA OS real, com evidência do usuário: add-on `0.1.1` instalado e
  atualizado pela loja, `/setup` reutilizou a skill, provider Alexa do Music
  Assistant configurado, áudio e invocação `music assistant` funcionaram em um
  Echo Cozinha. Isso não cobre a matriz completa de testes manuais.
- A versão candidata `0.2.0` **não foi instalada** em HA OS nesta etapa.

Build Docker e testes em HA OS ainda são manuais; não há Docker/HA OS no
ambiente de desenvolvimento usado até agora.

### 9.4 Testes manuais pendentes

O checklist completo está no final da entrega da Fase 1 e em `DOCS.md`.
Cobrir, no mínimo:

- instalação e validação do formulário de opções;
- bloqueio sem `SKILL_HOSTNAME` e rejeição de hostname com esquema;
- geração, leitura e reuso das credenciais;
- symlink `/root/.ask` e persistência de `/data/ask`;
- `/setup` e `/status` com basic auth;
- `POST /` sem basic auth, mas com validação de assinatura da Alexa;
- setup completo na Amazon, `Done. Skill ID`, habilitação da skill;
- regra Cloudflare bloqueando tudo exceto `POST /`;
- matriz externa de `/setup`, `/status`, `/devices`, `/docs`, `/ma` e `/alexa`;
- provider Alexa do Music Assistant e `/ma/latest-url`;
- áudio via `MA_HOSTNAME` e comandos via `MA_API_URL` (e `MA_API_TOKEN`
  quando a API exigir autenticação);
- Echo com tela e Echo sem tela;
- backup/restauração `cold`;
- build/início em `amd64` e `aarch64`.

## 10. Comandos úteis

Validação completa disponível sem Docker (Windows ou Linux):

```bash
python scripts/validate_repo.py
python -m unittest tests.test_addon_options
ruff check .
ruff format --check .
python -m compileall -q alexa_ma_skill custom_components tests scripts
bash -n alexa_ma_skill/run.sh
```

`scripts/validate_repo.py` usa `requirements_ci.txt` (PyYAML e ruff fixados) e
verifica metadados do add-on e da integração, consistência de versão entre
`config.yaml`, `manifest.json` e CHANGELOG, links relativos, line endings LF e
padrões comuns de segredo.

### Hassfest local (sem Docker)

Quando não houver Docker, é possível rodar os plugins oficiais do Hassfest com:

```bash
git clone --depth 1 --filter=blob:none --sparse \
  https://github.com/home-assistant/core.git /tmp/ha-core
git -C /tmp/ha-core sparse-checkout set script/hassfest script/translations
git -C /tmp/ha-core fetch --depth 1 origin tag 2026.10.4
git -C /tmp/ha-core checkout --detach 2026.10.4
python scripts/run_hassfest_subset.py --core-path /tmp/ha-core
```

Use a tag do Core que corresponda à versão do pacote `homeassistant` instalado.
O script roda `json`, `manifest`, `translations`, `services`, `icons`,
`integration_type`, `config_schema`, `codeowners`, `requirements` e
`config_flow`. Ele **não** substitui a action oficial (que inclui o plugin
`dependencies` e roda em Docker no CI).

### Validação no Windows

A suíte completa do Home Assistant **não roda no Windows**: o
`pytest-homeassistant-custom-component`/Home Assistant importa `fcntl`.
**Não tente rodar o `pytest` completo localmente no Windows.**

> Exceção registrada na validação da Fase 4: uma execução suplementar no Windows
> usou shims `fcntl`/`resource` e sockets habilitados, mantidos **fora do
> repositório**. Ela produziu 6 config flow OK e 55 passed/1 skipped/26 subtests,
> mas **não é reproduzível pelo projeto nem substitui** a CI Linux. Não adicione
> esses shims ao repositório.

Validação local no Windows:
- `python scripts/validate_repo.py`
- `ruff check .`
- `ruff format --check .`
- `python -m compileall -q alexa_ma_skill custom_components tests scripts`
- testes que não importam Home Assistant:
  `python -m unittest tests.test_addon_options`
- testes dos helpers da integração, usando o virtualenv:
  `.venv/Scripts/python.exe -m unittest tests.test_integration_helpers`

O `pytest` completo da integração roda no CI Linux. O workflow está em
`.github/workflows/ci.yml` e já foi executado com sucesso no run 45276992158
(commit `ee16d8b`): 56 testes e 26 subtestes. O pacote é
`pytest-homeassistant-custom-component==0.13.375` (Home Assistant 2026.10.4,
Python >= 3.14). `tests/conftest.py` registra o plugin do
harness e `pyproject.toml` define `asyncio_mode = "auto"`.

### WSL (opcional)

Para rodar a suíte do HA no Windows via WSL, dentro do diretório do repositório:

```bash
wsl --install -d Ubuntu
# dentro do WSL:
sudo apt update
sudo apt install -y curl
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv --python 3.14 .venv
uv pip install -r requirements_test.txt
uv run pytest -q
```

Ajuste o Python/venv se a distro já tiver 3.14. `requirements_test.txt` e a
pasta `tests/` já existem; a suíte completa de config flow/options flow ainda
precisa ser executada (localmente via WSL ou no CI Linux).

Leitura das credenciais geradas (HA OS com acesso ao host):

```sh
# Substitua <slug> pelo slug real do Supervisor, por exemplo
# 0a1b2c3d_alexa_ma_skill.
docker exec addon_<slug> cat /data/generated_app_username
docker exec addon_<slug> cat /data/generated_app_password
```

## 11. Referências upstream

- Projeto upstream: <https://github.com/alams154/music-assistant-skill>
- Commit base usado no estudo: `2967b60551250bcce50586e9de0f6b036dcff237`
- Versão: `0.0.39-beta` (2026-10-15)
- Imagem: `ghcr.io/alams154/music-assistant-skill:0.0.39-beta@sha256:b1ef33ad0b05b7e0a315535e8141177898be4b6a0401decf43dedf424f0d90f1`
- Arquivos upstream relevantes:
  - `app/app.py`: carrega `/data/options.json`, basic auth, `/setup`.
  - `app/env_secrets.py`: resolve segredos em arquivo.
  - `app/setup_helpers.py`: resolução de credenciais ASK.
  - `app/endpoints/status.py`: diagnóstico de `/status`.
  - `scripts/ask_create_skill.sh`: criação/reuso de skill, exclusão de extras,
    upload de modelos e enablement.
  - `scripts/find_skills_to_delete.py`: filtra skills "Music Assistant".
  - `app/skill.json`: manifesto e nomes por locale.
  - `app/models/*.json`: modelos de interação e frases de invocação.

## 12. Lições do teste em HA OS

O add-on foi instalado e testado em Home Assistant OS com um Echo real. Os
itens abaixo são fatos observados e não devem ser revertidos sem novo teste.

### 12.1 Invocação e nome da skill

- A skill toca e responde quando invocada como **"music assistant"**, em todos
  os locales.
- O nome de exibição criado é **"Music Assistant"**.
- O `invocationName` efetivo vem do `scripts/ask_create_skill.sh` do upstream,
  que sobrescreve todos os modelos para `music assistant`.
- O contêiner **não expõe** o `invocationName` em `/status`, `/setup` ou
  `/simulator`. A integração usa a constante `INVOCATION_NAME` em `const.py`.
- `fr-CA` e `nl-NL` têm modelos brutos com invocation vazio. O script injeta
  `music assistant`, mas a **criação nesses locales não foi validada**.

### 12.2 `SKILL_ID`

- Com `SKILL_ID` errado, o contêiner registra `Skill ID Verification failed!!`
  e a Alexa responde "problema com a resposta da skill".
- O ID correto aparece nos logs de `/setup` (`Created skill:`,
  `Reusing existing skill:` e `Done. Skill ID:`).
- `/status` só expõe o ID em alguns casos (`skill_ask_html` no ramo "endpoint
  not set").
- Os logs de `/setup` ficam em memória e somem ao reiniciar o add-on; por isso
  o último ID detectado é persistido em `Store` pela integração.
- IDs devem ser mascarados em logs e diagnostics, mostrando apenas início e
  fim.

### 12.3 Cloudflare e Traefik

- Rotas curinga (`*.dominio`) colocadas **antes** das rotas específicas fazem
  o pedido cair no Traefik e retornar `404 page not found` em texto puro.
- As rotas `SKILL_HOSTNAME` e `MA_HOSTNAME` devem vir **antes** das curingas.
- Manter a rota catch-all/curinga por último.

### 12.4 Music Assistant: OTP Secret

- O campo **OTP Secret** deve ficar vazio quando não há chave TOTP válida.
- Valor inválido causa `Non-base32 digit found` e `internal_error` no MA.

### 12.5 Music Assistant: domínio da conta

- O aviso `amazon.com.br does not match account domain amazon.com` pode ser
  ignorado se o áudio tocar normalmente.
- Alternativa: reconfigurar a conta/provider Alexa no MA com o domínio correto
  da conta (por exemplo, `amazon.com`).

### 12.6 `QUIET_HTTP=1`

- `QUIET_HTTP=1` é fixado pelo `run.sh` e esconde os logs HTTP do
  werkzeug/urllib3, inclusive os `POST /`.
- Não concluir que a skill não recebeu requisições apenas pela ausência de
  logs.
- O melhor indicador é a página `/status` (recent invocations) ou
  `/invocations`.

### 12.7 Slug de add-on de repositório personalizado

- Add-ons instalados de um repositório personalizado recebem um prefixo
  `<hash>_` do Supervisor. O slug real pode ser
  `0a1b2c3d_alexa_ma_skill`, e não `alexa_ma_skill`.
- A integração **não** deve fixar o hash nem o slug completo:
  - lista os add-ons com `get_addons_info(hass)` do componente `hassio`;
  - aceita slug igual a `alexa_ma_skill` ou terminado em `_alexa_ma_skill`;
  - se houver mais de um, mostra um seletor;
  - persiste o slug escolhido em `CONF_ADDON_SLUG` na config entry;
  - usa esse slug em todas as chamadas do `AddonManager` (`info`, `options`,
    `start`, `restart`, `stop`).
- O hostname interno é derivado do slug trocando `_` por `-`:
  `0a1b2c3d_alexa_ma_skill` → `0a1b2c3d-alexa-ma-skill`. O valor fixo
  `alexa-ma-skill` não deve ser usado no modo gerenciado.
- Se nenhum add-on for encontrado, logar em `debug` a lista de slugs
  encontrados e mostrar a mensagem de add-on não instalado.

### 12.8 Provider Alexa do Music Assistant

- O provider **Alexa** do Music Assistant é quem envia o stream para o add-on
  via `POST /ma/push-url`. A skill apenas lê o último `streamUrl`.
- No provider, usar:
  - `API URL`: base interna do add-on, `http://<IP_DO_HA>:5000`, **sem** `/ma`;
  - `API Basic Auth Username`/`Password`: iguais a `APP_USERNAME`/`APP_PASSWORD`;
  - `URL`: domínio Amazon da conta (`amazon.com`, `amazon.com.br` etc.);
  - `OTP Secret`: vazio quando não há TOTP válido.
- **Nunca** usar `https://SKILL_HOSTNAME` como `API URL`: `/ma` é bloqueado
  publicamente pelo WAF. O provider precisa falar com o add-on pela rede local.
- Se o MA estiver em outro contêiner, `http://localhost:5000` aponta para o
  próprio MA; usar o IP do HA ou o hostname interno derivado do slug.
- Teste obrigatório:
  ```sh
  curl -i -u "$APP_USERNAME:$APP_PASSWORD" \
    "http://<IP_DO_HA>:5000/ma/latest-url"
  ```
  - `200` com `streamUrl`: push OK;
  - `404 No URL available`: auth OK, mas o MA ainda não enviou stream;
  - `401`: credenciais erradas no provider/`curl`;
  - erro de conexão: IP/porta/rede errados.
- O add-on guarda o último stream em memória (`shared_store`). Reiniciar o
  add-on apaga esse valor. Depois de reiniciar, tocar algo pelo MA antes de
  invocar a Alexa.
- Sintomas:
  - `could not retrieve the latest music stream from the API`: sem `streamUrl`;
  - `can't reach the audio file`: add-on não validou a URL pública; testar do
    host e de dentro do contêiner e, se for hairpin NAT, usar
    `SKIP_URL_VALIDATION: true`;
  - `Play action failed` / `This action is currently unavailable`: o provider
    não conseguiu enviar o stream/comando; conferir URL interna, porta `5000`,
    Basic Auth, sessão Amazon, Echo online e skill habilitada.
- Erro real observado: `API URL` com um dígito errado na porta `5000` fazia o
  provider falhar silenciosamente; o `curl /ma/latest-url` retornava `404`.
- Não registrar credenciais reais em documentação, logs ou commits.

## 13. Integração personalizada (Fase 2)

### 13.1 Estrutura e contratos

- Código em `custom_components/alexa_ma_skill/`.
- Metadados em `manifest.json`; dependência declarada como
  `after_dependencies: ["hassio"]`.
- `hacs.json` declara Home Assistant mínimo `2026.10.4`, a versão usada no
  desenvolvimento; versões anteriores não foram validadas.
- A integração é opcional; o add-on funciona sem ela.
- O Supervisor é acessado pelos helpers do componente `hassio`
  (`get_addons_info` e `AddonManager`), não por HTTP cru.
- O slug real é descoberto por igualdade com `alexa_ma_skill` ou sufixo
  `_alexa_ma_skill`. O hash do repositório personalizado nunca é fixado.
- O slug escolhido é persistido em `CONF_ADDON_SLUG` e usado em todas as
  operações do `AddonManager`.
- O hostname interno é o `hostname` retornado pelo Supervisor ou, como
  fallback, o slug com `_` trocado por `-`.
- A integração consulta `/status?format=json` e `/setup?format=json` com
  timeout curto; falhas do `/setup` ficam em nível debug.

### 13.2 Config flow e opções

- Modos: gerenciado, manual e reauth.
- Descoberta: nenhum add-on mostra `addon_not_installed` com instrução do
  repositório; um seleciona automaticamente; vários mostram `addon_select`.
- Credenciais existentes em texto no add-on são reutilizadas; se estiverem em
  arquivos ou ausentes, novas credenciais fortes são geradas e exibidas uma
  vez.
- O options flow usa `AddonManager.async_configure_addon`, que mescla opções
  atuais e preserva chaves desconhecidas.
- Senhas e tokens deixados em branco são preservados quando possível. Valores
  em arquivo não são usados como senha HTTP; nesse caso, a senha armazenada na
  config entry é usada para autenticação.
- `MA_API_URL` aceita `http`, `https`, `ws` e `wss`, exige host e rejeita
  credenciais embutidas. O token é opcional quando o MA não exige auth.
- `MA_HOSTNAME` é opcional, como no schema do add-on.
- `TZ` não é gerenciado pela integração; é preservado.
- Reinício do add-on exige confirmação no options flow.

### 13.3 Segurança

- Segredos não aparecem em logs, entidades ou diagnostics.
- Diagnostics mascaram `SKILL_ID` e redigem senhas/tokens/stream URLs.
- A URL pública de `/setup` não é usada nem exposta como atalho.
- Remover a integração não para o add-on, não apaga opções, credenciais ASK ou
  dados em `/data`.

### 13.4 Testes e pendências

- `python -m unittest tests.test_addon_options`: testes puros do add-on.
- `.venv/Scripts/python.exe -m unittest tests.test_integration_helpers`:
  helpers da integração com bibliotecas do HA.
- `python -m pytest tests/test_config_flow.py`: harness Linux do HA.
- Pendente: executar config flow/options flow completos no Linux, Hassfest,
  HACS Action, CI e validação em HA OS.
- Fase 3 implementada no código; validação completa pendente.

## 14. Setup assistido (Fase 3)

### 14.1 Arquitetura

- O checklist vive em `custom_components/alexa_ma_skill/setup.py`.
- 16 etapas em `STEP_DEFINITIONS`, com IDs estáveis, dependências, modo
  automático/manual e textos pt-BR/en.
- Estados: `not_started`, `pending`, `checking`, `done`, `attention`,
  `blocked`, `not_applicable`.
- O sensor `sensor.setup_checklist` expõe `progress`, `checklist`,
  `manual_steps` e a próxima etapa nos atributos.
- O acesso ao setup é pelo options flow: **Configurar > Setup assistido**.
- O menu do options flow separa **Configurar opções** de **Setup assistido**.

### 14.2 Persistência

- Confirmações manuais em `Store` separado por config entry:
  `alexa_ma_skill.<entry_id>.checklist`.
- Armazena apenas `{step_id: {"at": timestamp}}`; não armazena senhas, tokens,
  cookies ou dados Amazon.
- O progresso sobrevive a reinícios do HA, reinícios do add-on, atualização da
  integração e fechamento da UI.
- `ChecklistManager.async_clear_for_keys()` invalida seletivamente:
  - `SKILL_HOSTNAME` não apaga autorização Amazon;
  - `MA_HOSTNAME` invalida provider/stream/reprodução;
  - `MA_API_URL`/token invalidam API/comandos;
  - credenciais invalidam acesso local/provider/comandos;
  - mudança de slug/add-on invalida etapas dependentes.
- Alterações feitas fora da integração só são refletidas nas etapas
  automáticas; confirmações manuais antigas podem permanecer até a próxima
  alteração via options flow.

### 14.3 Etapas automáticas

- add-on instalado/iniciado, credenciais, hostnames, `SKILL_ID`,
  `/status`/`/setup` e HTTPS do stream.
- O teste da API do MA **não** é automático: não há contrato confiável no add-on
  para testar a porta `8095`, e uma conexão de teste poderia alterar estado do
  player. Só o formato de `MA_API_URL` é validado.
- Automático significa “evidência disponível”; não significa validação
  externa completa.

### 14.4 Etapas manuais

- acesso local ao `/setup`;
- autorização Amazon;
- criação/reutilização da skill (com aviso de duplicatas);
- habilitação da skill;
- provider Alexa no MA;
- teste da API do MA (quando `MA_API_URL` estiver configurada);
- teste de reprodução;
- teste de comandos.

Nenhuma etapa Amazon é executada automaticamente. A integração não solicita
senha Amazon, não acessa a conta e não executa o script de criação de skill.
Desmarcar uma etapa manual remove as confirmações das etapas manuais
dependentes, para não reutilizar confirmação fora de contexto.

### 14.5 Testes

- `tests/test_integration_helpers.py` cobre IDs, progresso, estados,
  persistência, invalidação seletiva, parsing e segurança.
- O options flow completo ainda depende do harness Linux.
- Testes de reprodução/comandos e provider exigem HA OS, MA e Echo reais.

## 15. Fase 4 — distribuição e CI

### 15.1 Versão

- Versão candidata única: **`0.2.0`**, presente em `alexa_ma_skill/config.yaml`,
  `custom_components/alexa_ma_skill/manifest.json` e no topo do
  `alexa_ma_skill/CHANGELOG.md`.
- O add-on não declara `image:`; o Supervisor constrói a imagem localmente a
  partir do `Dockerfile`. Não é necessário publicar imagem para testar a versão.
- A `0.2.0` **não foi publicada, tagueada ou instalada** em HA OS.
- `scripts/validate_repo.py` falha se as três versões divergirem ou se o
  CHANGELOG não tiver a seção correspondente.

### 15.2 Estrutura de distribuição

- `README.md`: página pública (apresentação, recursos, requisitos, instalação,
  arquitetura, segurança, problemas, suporte, licença).
- `alexa_ma_skill/DOCS.md`: manual completo do add-on, exibido na loja.
- `AGENTS.md`: contexto de desenvolvimento e manutenção.
- `docs/VALIDATION-MATRIX.md`: ambiente, procedimento, resultado, evidência e
  pendência por componente.
- `docs/HAOS-TEST-PLAN.md`: roteiro reproduzível de instalação, backup,
  restauração e testes reais.
- `docs/DISTRIBUTION-READINESS.md`: checklist objetivo de prontidão.
- `docs/releases/RELEASE-DRAFT.md`: rascunho não publicado.
- `docs/images/README.md`: capturas pendentes e regras de privacidade.
- `.github/ISSUE_TEMPLATE/`: bug e feature request; `config.yml` aponta para a
  documentação e a matriz.
- `pyproject.toml`: configuração de ruff e pytest (`asyncio_mode = "auto"`).
- `requirements_ci.txt`: PyYAML e ruff fixados.

### 15.3 CI

`.github/workflows/ci.yml` roda em Linux com `permissions: contents: read` e
`concurrency`. Jobs:

1. `repository`: instala `requirements_ci.txt`, roda
   `scripts/validate_repo.py`, `compileall`, `bash -n`, testes do add-on,
   `ruff check` e `ruff format --check`.
2. `integration`: instala `requirements_test.txt` e roda `python -m pytest -q`
   com `tests/conftest.py` e o harness do Home Assistant.
3. `hassfest`: `home-assistant/actions/hassfest@<sha>` (fixado por commit).
4. `hacs`: `hacs/action@<sha>` com `category: integration`,
   `ignore: brands description issues topics` (separado por espaço) e
   `comment: "false"`.

As actions são fixadas por SHA de commit e o `.github/dependabot.yml` mantém os
SHAs atualizados. `actions/checkout@v7.0.1` e `actions/setup-python@v7.1.0`
usam Node 24. Nota: Hassfest e HACS são Docker actions publicadas pelos
mantenedores; o SHA fixa o repositório da action, mas a imagem Docker referenciada
internamente continua sendo resolvida pelo mantenedor. Regras: não publicar
imagens, tags ou Releases; não usar `:latest`; não exigir credenciais pessoais;
não mascarar falhas com `continue-on-error`. A CI foi **executada com sucesso**
no run 45276992158 (commit `ee16d8b`), com os 4 jobs aprovados. O `actionlint`
também passou com 0 erros.

### 15.4 Validador local

`scripts/validate_repo.py` verifica:

- `repository.yaml`, `hacs.json`, `config.yaml` e `manifest.json`;
- coerência de nome, slug, domínio, URL, issue tracker e versões;
- `SKILL_HOSTNAME` obrigatório, opções com schema, portas, watchdog e webui;
- `FROM` com tag e digest, sem `:latest`, com `ENTRYPOINT`/`CMD`;
- traduções do add-on e da integração (estrutura, placeholders de entidade,
  URLs/HTML não permitidos e espaços nas pontas);
- steps e `menu_options` do config flow contra o `strings.json`;
- chaves permitidas no `hacs.json` e uma única integração em
  `custom_components/`;
- actions da CI fixadas por SHA e lista `ignore` do HACS separada por espaço;
- parse de todos os YAML/JSON, links relativos e LF;
- padrões comuns de segredo (GitHub, AWS, chaves privadas, Slack);
- existência dos documentos de distribuição e do workflow.
- `scripts/run_hassfest_subset.py`: executa plugins oficiais do Hassfest contra
  um checkout do Core, útil quando não há Docker; não substitui a action
  oficial.

### 15.5 HACS e add-on

- HACS: instalação documentada como **repositório personalizado**. A HACS
  Action passou no CI com ignores de metadados do GitHub. A inclusão no catálogo
  padrão **não** foi solicitada e exige Action sem ignores, Hassfest, Release
  completa, metadados do GitHub e `brand/icon.png`.
- Falta `custom_components/alexa_ma_skill/brand/icon.png`; o HACS usa o domínio
  em `home-assistant/brands` como alternativa, mas o arquivo local ainda não
  existe.
- O HACS Action valida o repositório **remoto**; sem push, ele não enxerga o
  worktree atual.
- A `0.2.0` está apenas no branch `validation/phase-4-ci`; loja e HACS
  personalizado apontando para `main` entregam a 0.1.x. O teste manual usa
  add-on **local** (`/addons` em HA 2026.10.x, `/local_apps` em 2026.11+) e
  integração copiada do commit, conforme `docs/HAOS-TEST-PLAN.md`.
- Add-on: `repository.yaml` na raiz e `alexa_ma_skill/config.yaml` com `slug`,
  `arch`, `ports`, `schema`, `watchdog`, `webui` e `backup: cold`.
- A imagem upstream permanece
  `ghcr.io/alams154/music-assistant-skill:0.0.39-beta@sha256:b1ef...0f90f1`.
  Em 23/11/2026 o registry respondeu HTTP 200 com esse digest e um índice OCI
  contendo `linux/amd64` e `linux/arm64`; o build do add-on não foi executado.
- Nenhum build ou publicação de imagem foi executado.

### 15.6 Pendências da Fase 4

- Instalação da `0.2.0` em HA OS `amd64` e, se possível, `aarch64`.
- Teste ponta a ponta com Alexa e Music Assistant na `0.2.0`.
- Comandos, backup/restauração e acesso externo completo.
- `brand/icon.png` e uma Release completa para o catálogo padrão do HACS.
- Screenshots reais sem dados sensíveis.
- Autorização explícita antes de tag, Release ou anúncio.

A Fase 4 **não é declarada concluída** enquanto os itens acima estiverem
pendentes. A Fase 5 não foi iniciada.
