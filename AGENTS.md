# AGENTS.md

Contexto permanente do projeto **alexa-ma-skill** para futuras sessões de
desenvolvimento. Leia este arquivo antes de alterar o repositório.

## 1. Objetivo

Construir uma solução para Home Assistant que permita controlar o **Music
Assistant** por voz usando a **Alexa**, sem depender de Nabu Casa e sem
serviços de terceiros gerenciados pelo projeto.

A solução tem duas partes:

1. **Add-on do Home Assistant** (`alexa_ma_skill/`): executa o contêiner
   upstream `ghcr.io/alams154/music-assistant-skill`, com credenciais
   persistentes, geração segura de senhas e documentação de exposição pública.
2. **Integração personalizada** (`custom_components/`, Fase 2): configura o
   add-on pela interface do Home Assistant, reporta diagnóstico e guia o setup
   da skill Alexa.

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

Planejada, ainda não implementada:

- Fica em `custom_components/alexa_ma_skill/`.
- Configura o add-on pela UI do Home Assistant (config flow).
- Gera credenciais e grava as opções do add-on via Supervisor.
- Consulta o serviço interno do add-on em `http://alexa-ma-skill:5000` (DNS
  interno do add-on).
- A URL voltada ao usuário para o setup é
  `https://<SKILL_HOSTNAME>/setup`.
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
  porta de stream **8097**. Exemplo: `http://192.168.1.10:8095`.
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
  `en.yaml`. A futura integração deve usar os arquivos de tradução do HA Core
  (`translations/pt-BR.json` e `en.json`).
- Integração em **Python async e tipado**, sem bloquear o event loop.
- O script de entrypoint do add-on (`addon_options.py`) é um CLI de startup
  síncrono e usa apenas a biblioteca padrão; isso é intencional.
- Um commit por fase, com mensagem clara. Não misturar fases no mesmo commit.
- Line endings LF; `.gitattributes` e `.gitignore` já configurados.
- Não commitar segredos, credenciais, `options.json` real ou diretórios de
  dados locais.

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
- A skill criada usa o nome de exibição **"My Radio"** / **"Minha Rádio"** e a
  frase de invocação **"my radio"** / **"minha rádio"** em `pt-BR`.
- Execuções repetidas do setup podem criar skills duplicadas "My Radio"; o
  console da Amazon deve ser revisado.
- O manifesto gerado usa `sslCertificateType: Wildcard`. Se a Amazon recusar o
  endpoint, ajustar para **Trusted** no console.
- Ao final, copiar o `Done. Skill ID: amzn1.ask.skill...` para `SKILL_ID` e
  reiniciar o add-on.

## 7. Pendências por fase

### 7.1 Fase 2 — integração personalizada

- Criar `custom_components/alexa_ma_skill/` com `manifest.json` completo.
- Config flow pela UI do Home Assistant.
- Gerar credenciais e gravar as opções do add-on.
- Reportar diagnóstico e status.
- Guiar o usuário no setup da skill.
- **Usar os helpers do componente `hassio` em vez de HTTP cru no Supervisor**
  e declarar a dependência no `manifest.json`.
- Garantir compatibilidade HACS (`hacs.json` já existe na raiz).
- Consultar o add-on em `http://alexa-ma-skill:5000`.
- A URL de setup para o usuário é `https://<SKILL_HOSTNAME>/setup`.

### 7.2 Fase 3 — setup assistido

- Checklist de configuração.
- Exibir valores necessários no console da Amazon.
- Assistir o `/setup` com login manual na Amazon.
- **Avisar explicitamente que o script upstream apaga skills extras chamadas
  "Music Assistant"** e pedir confirmação antes de continuar.
- Considerar o risco de skills duplicadas "My Radio".

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
- Não expor `/setup`, `/status`, `/devices`, `/docs`, `/ma` ou `/alexa`
  publicamente.
- Não adicionar Caddy/nginx/túnel ao add-on.
- Não commitar segredos ou dados de `/data`.
- Manter line endings LF.

## 9. Estado atual

### 9.1 Fase 1 concluída

- Commit: `92b3d21`
- Mensagem: `feat(addon): adiciona add-on Alexa MA Skill com persistência de credenciais ASK`
- Branch: `main`

### 9.2 Arquivos principais

```text
.
├── repository.yaml
├── hacs.json
├── README.md
├── AGENTS.md
├── LICENSE
├── LICENSE-AMAZON-SOFTWARE-1.0
├── THIRD_PARTY_NOTICES.md
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

### 9.3 Validação já executada na Fase 1

- YAML/JSON parseados.
- `addon_options.py` compilado.
- `bash -n alexa_ma_skill/run.sh` aprovado.
- Testes do script de opções: geração/reuso de credenciais, caminhos de
  arquivo, token do MA, hostnames inválidos, porta/idioma inválidos,
  exportação NUL-separated com espaços e quebras de linha.
- Verificação de LF.

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
- áudio via `MA_HOSTNAME` e comandos via `MA_API_URL`/`MA_API_TOKEN`;
- backup/restauração `cold`;
- build/início em `amd64` e `aarch64`.

## 10. Comandos úteis

Validação rápida sem Docker:

```bash
python -m py_compile alexa_ma_skill/addon_options.py
bash -n alexa_ma_skill/run.sh
python - <<'PY'
from pathlib import Path
import json
import yaml

for path in Path('.').rglob('*.yaml'):
    yaml.safe_load(path.read_text(encoding='utf-8'))
for path in Path('.').rglob('*.json'):
    json.loads(path.read_text(encoding='utf-8'))
print('YAML/JSON OK')
PY
```

Leitura das credenciais geradas (HA OS com acesso ao host):

```sh
docker exec addon_alexa_ma_skill cat /data/generated_app_username
docker exec addon_alexa_ma_skill cat /data/generated_app_password
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
