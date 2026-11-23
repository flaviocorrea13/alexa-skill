# Alexa MA Skill

Add-on do Home Assistant para executar a skill Alexa do
[Music Assistant](https://www.music-assistant.io/) e controlar seus players por
voz.

O add-on empacota a imagem upstream
[`alams154/music-assistant-skill`](https://github.com/alams154/music-assistant-skill)
com uma camada de configuração pensada para o Home Assistant: credenciais
persistentes, geração segura de senhas, documentação de exposição pública e
diagnóstico pela página `/status`.

## Status do projeto

| Fase | Escopo | Situação |
|---|---|---|
| Fase 1 | Add-on, persistência de credenciais, documentação, licenças | Implementada |
| Fase 2 | Integração personalizada para configurar o add-on pela UI do Home Assistant | Planejada |
| Fase 3 | Setup assistido com checklist, valores de console e confirmação | Planejada |

> Esta versão implementa apenas a Fase 1. A integração HACS e o setup assistido
> serão adicionados nas próximas fases.

Decisões registradas para as próximas fases:

- **Fase 2:** avaliar os helpers do componente `hassio` em vez de HTTP cru no
  Supervisor e declarar a dependência no `manifest.json` da integração.
- **Fase 3:** o setup assistido avisará que o script upstream apaga skills
  extras chamadas "Music Assistant" e pedirá confirmação antes de continuar.

## O que o add-on faz

- Executa a aplicação Flask upstream na porta `5000`.
- Expõe `POST /` para a Alexa e mantém `/setup` e `/status` para a rede local.
- Persiste as credenciais do ASK CLI em `/data/ask` (symlink `/root/.ask`).
- Gera usuário e senha aleatórios quando `APP_USERNAME`/`APP_PASSWORD` estão
  vazios, sem nunca registrar a senha nos logs.
- Reescreve `/data/options.json` com caminhos de arquivos de segredo para que o
  upstream não sobrescreva as credenciais no import.
- Grava o token da API do Music Assistant em arquivo com permissão `600` para
  não expô-lo em logs.
- Publica a porta `5000` no host e usa watchdog TCP.
- Documenta a regra de exposição pública: somente `POST /` da skill deve ser
  acessível pela internet.

## Requisitos

- Home Assistant OS ou Home Assistant Supervised.
- Arquitetura `amd64` ou `aarch64`.
- Music Assistant instalado.
- Conta de desenvolvedor da Amazon com "Skill Access Management" habilitado.
- Dois hostnames públicos com certificado válido (o segundo é obrigatório para
  dispositivos sem tela e para exibir capa):
  - `SKILL_HOSTNAME` para a skill (porta `5000` do add-on);
  - `MA_HOSTNAME` para o stream do Music Assistant (porta `8097`).
- Um túnel ou reverse proxy HTTPS. O projeto **não** cria túneis e **não** usa
  Nabu Casa.
- TLS 1.2 ou superior. A imagem upstream não suporta TLS 1.3.

## Instalação

1. No Home Assistant, abra **Configurações > Add-ons > Loja de add-ons**.
2. No menu de três pontos, escolha **Repositórios**.
3. Adicione:

   ```text
   https://github.com/flaviocorrea13/alexa-skill
   ```

4. Instale o add-on **Alexa MA Skill**.
5. Configure as opções. `SKILL_HOSTNAME` é obrigatório.
6. Inicie o add-on.
7. Abra `http://<IP_DO_HOME_ASSISTANT>:5000/setup` e siga o setup da skill.
8. Depois de habilitar a skill no aplicativo Alexa, invoque com
   **"Alexa, abra music assistant"**. O nome de exibição é **Music Assistant**;
   o invocation é **`music assistant`** em todos os idiomas.

A documentação completa está em
[`alexa_ma_skill/DOCS.md`](alexa_ma_skill/DOCS.md).

## Configuração resumida

| Opção | Obrigatória | Padrão | Descrição |
|---|:---:|---|---|
| `SKILL_HOSTNAME` | Sim | — | Hostname público da skill, sem `https://`. |
| `MA_HOSTNAME` | Não* | — | Hostname público do stream do Music Assistant. |
| `APP_USERNAME` | Não | gerado | Usuário de `/setup` e `/status`. |
| `APP_PASSWORD` | Não | gerado | Senha de `/setup` e `/status`. |
| `PORT` | Não | `5000` | Porta interna; mantenha `5000`. |
| `LOCALE` | Não | `pt-BR` | Idioma da skill. |
| `TZ` | Não | `America/Sao_Paulo` | Fuso horário. |
| `AWS_DEFAULT_REGION` | Não | `us-east-1` | Região do ASK CLI. |
| `ENABLE_APL` | Não | `false` | Habilita APL em dispositivos com tela. |
| `SKIP_URL_VALIDATION` | Não | `false` | Pula a validação da URL de áudio. |
| `SKILL_ID` | Não | — | Restringe a skill às próprias requisições. A integração detecta e sugere o valor. |
| `MA_API_URL` | Não** | — | API WebSocket do Music Assistant (porta `8095`). |
| `MA_API_TOKEN` | Não** | — | Token da API do Music Assistant. |

\* Necessário para dispositivos sem tela e para capa em dispositivos com tela.

\** Necessário para comandos de voz que controlam o player do Music Assistant.

## Segurança

- Exponha publicamente apenas `POST /` em `SKILL_HOSTNAME`.
- Mantenha `/setup`, `/status`, `/devices`, `/docs`, `/ma` e `/alexa` na rede
  local.
- Use a regra de WAF documentada em
  [`DOCS.md`](alexa_ma_skill/DOCS.md#exposição-pública-e-https).
- As credenciais geradas ficam em `/data` com permissão `600` e não aparecem
  nos logs.
- Proteja os backups do add-on: eles incluem as credenciais do ASK CLI.
- Não use credenciais padrão como `admin`/`teste`.

## Solução de problemas rápida

- **`SKILL_ID` vazio ou errado:** com um ID incorreto, o contêiner registra
  `Skill ID Verification failed!!` e a Alexa responde "problema com a resposta
  da skill". A integração lê o ID nos logs de `/setup` e avisa quando vazio ou
  divergente, sugerindo o valor correto. O ID aparece como `Done. Skill ID:`.
- **Cloudflare/Traefik retorna `404 page not found` em texto puro:** as rotas
  específicas de `SKILL_HOSTNAME` e `MA_HOSTNAME` devem vir **antes** das rotas
  curinga (`*.dominio`). Deixe a curinga/catch-all por último.
- **Music Assistant com `Non-base32 digit found`/`internal_error`:** deixe o
  campo **OTP Secret** vazio quando não houver uma chave TOTP válida.
- **Aviso `amazon.com.br does not match account domain amazon.com`:** pode ser
  ignorado se o áudio tocar. Alternativa: reconfigurar a conta/provider Alexa
  no MA com o domínio correto (por exemplo, `amazon.com`).
- **Nenhum `POST /` aparece no log:** `QUIET_HTTP=1` esconde os logs HTTP. Use
  `/status` (recent invocations) ou `/invocations` como indicador.
- **Frase de invocação:** use **"music assistant"** em qualquer locale. O
  script upstream sobrescreve o `invocationName` dos modelos.

## Estrutura do repositório

```text
.
├── repository.yaml                 # Repositório de add-ons do Home Assistant
├── hacs.json                       # Metadados para a futura integração HACS
├── README.md
├── LICENSE                         # MIT para o código original
├── LICENSE-AMAZON-SOFTWARE-1.0     # Licença da imagem upstream
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

## Desenvolvimento

O add-on é construído a partir da imagem upstream fixada por versão e digest no
`FROM` de `alexa_ma_skill/Dockerfile`. Para atualizar a versão upstream:

1. Altere a tag e o digest na linha `FROM` do `Dockerfile`.
2. Atualize `version` em `alexa_ma_skill/config.yaml`.
3. Revise as notas de versão do upstream.
4. Teste o add-on em uma instância de teste do Home Assistant OS.

O código Python do entrypoint usa apenas a biblioteca padrão e não bloqueia o
event loop.

## Licença

O código original deste repositório é licenciado sob a **licença MIT**. A
imagem base upstream é licenciada sob a **Amazon Software License 1.0**. Leia:

- [`LICENSE`](LICENSE)
- [`LICENSE-AMAZON-SOFTWARE-1.0`](LICENSE-AMAZON-SOFTWARE-1.0)
- [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)

## Aviso

Este projeto não é afiliado, endossado ou patrocinado pela Amazon.com, Inc. ou
pela Music Assistant. Amazon, Alexa e nomes relacionados são marcas da
Amazon.com, Inc. ou de suas afiliadas.

## English

This repository contains a Home Assistant add-on that runs the upstream
`music-assistant-skill` container with persistent ASK CLI credentials, safe
credential generation, and Home Assistant-friendly documentation.

Phase 1 (add-on) is implemented. The custom integration (Phase 2) and the
assisted setup flow (Phase 3) are planned.

Quick start:

1. Add `https://github.com/flaviocorrea13/alexa-skill` as an add-on
   repository.
2. Install **Alexa MA Skill**.
3. Set `SKILL_HOSTNAME`, `MA_HOSTNAME`, `LOCALE`, and `TZ`.
4. Start the add-on and open `http://<HA_IP>:5000/setup` on your local network.
5. Follow the Amazon authorization flow and enable the skill in the Alexa app.
6. Invoke the skill with **"Alexa, open music assistant"**. The display name is
   **Music Assistant**, and the invocation name is **`music assistant`** for
   every locale.

Expose only `POST /` publicly. Keep `/setup`, `/status`, `/devices`, `/docs`,
`/ma`, and `/alexa` on the local network. Use TLS 1.2 or newer.

See [`alexa_ma_skill/DOCS.md`](alexa_ma_skill/DOCS.md) for the complete
documentation.
