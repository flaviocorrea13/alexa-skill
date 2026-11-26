# Alexa MA Skill

**Controle o [Music Assistant](https://www.music-assistant.io/) por voz com a
Alexa, dentro do Home Assistant — sem Nabu Casa e sem depender de um serviço
gerenciado pelo projeto.**

O Alexa MA Skill empacota a skill Alexa do Music Assistant em um add-on do Home
Assistant. O add-on executa a aplicação upstream, mantém as credenciais do ASK
CLI entre reinícios, gera senhas fortes quando necessário e expõe uma página de
setup e diagnóstico na rede local. Uma integração personalizada **opcional**
adiciona configuração pela interface, um checklist de configuração de 16 etapas
e um painel administrativo somente leitura.

> **Estado atual:** `0.2.0` em validação no branch `validation/phase-4-ci`
> (PR #1, Draft). A CI passou nos cinco jobs no commit `8ab7492`
> (run `45716728724`): 107 testes Linux, 26 subtests e 38 testes de frontend.
> A versão `0.2.0` foi instalada e testada em Home Assistant real; seis cenários
> funcionais foram aprovados manualmente. `aarch64`, backup/restauração e
> atualização pela loja ainda estão pendentes. Leia a
> [matriz de validação](docs/VALIDATION-MATRIX.md) antes de instalar. Este
> projeto **não** é afiliado à Amazon ou ao Music Assistant.

## O problema que este projeto resolve

O Music Assistant reproduz áudio localmente, mas não oferece sozinho uma skill
Alexa pronta para controlar os players. Expor um endpoint HTTPS, autenticar na
Amazon, persistir credenciais e publicar apenas o caminho que a Alexa precisa
são tarefas repetitivas e fáceis de configurar de forma insegura.

O Alexa MA Skill reúne essas peças:

- um add-on que executa a skill e mantém as credenciais;
- documentação de exposição pública restrita a `POST /`;
- diagnóstico local em `/status`;
- uma integração opcional que configura o add-on e guia o setup.

## Como funciona

```text
Alexa (voz)                                   Alexa (áudio)
   |                                             |
   | HTTPS POST /                                | HTTPS GET
   v                                             v
https://SKILL_HOSTNAME                     https://MA_HOSTNAME
   |                                             |
   v                                             v
túnel / reverse proxy  (fornecido por você)  túnel / reverse proxy
   |                                             |
   v                                             v
add-on Alexa MA Skill :5000                 Music Assistant :8097
   |
   +-- /setup e /status  -> somente rede local
   +-- ASK CLI           -> Amazon Developer
   +-- provider Alexa MA -> recebe /ma/push-url
```

- A Alexa chama `POST /` em `https://SKILL_HOSTNAME/`. Esse é o **único**
  caminho que deve ser exposto publicamente.
- O áudio não passa pelo add-on: o Music Assistant entrega o stream em
  `MA_HOSTNAME`.
- O add-on **não cria túneis, não emite certificados e não configura DNS**. Você
  fornece o HTTPS público.
- Nabu Casa não é usado.

## Recursos

### Disponíveis no add-on

- Executa a skill Alexa do Music Assistant na porta interna `5000`.
- Persiste as credenciais do ASK CLI em `/data/ask` (symlink `/root/.ask`).
- Gera `APP_USERNAME`/`APP_PASSWORD` aleatórios quando os campos estão vazios,
  sem registrar a senha nos logs.
- Mantém o token da API do Music Assistant em arquivo com permissão `600`.
- Página de setup em `/setup` e diagnóstico em `/status`, protegidos por
  autenticação básica e destinados à rede local.
- Expõe `/ma/latest-url` e `/ma/push-url` para o provider Alexa do Music
  Assistant na rede local.
- Valida hostnames, locale, porta, `MA_API_URL` e credenciais na inicialização.
- Backup `cold` com preservação de `/data`.

### Disponíveis na integração opcional

- Descoberta do add-on pelo slug real do Supervisor, inclusive com prefixo
  `<hash>_`.
- Config flow gerenciado, manual e reauth.
- Options flow com atualização parcial e preservação de opções desconhecidas.
- Sensores, binary sensors e diagnóstico com IDs mascarados.
- Painel administrativo **Alexa MA** no menu lateral, somente para
  administradores, com visão geral somente leitura.
- Setup assistido de 16 etapas, com progresso, dependências e confirmações
  manuais persistidas.

### Exigem configuração externa

- Dois hostnames públicos com certificado válido.
- Túnel ou reverse proxy HTTPS (Cloudflare Tunnel, Nginx, Traefik etc.).
- Conta de desenvolvedor Amazon com **Skill Access Management**.
- Autorização manual da Amazon no primeiro setup.
- Provider **Alexa** configurado no Music Assistant.
- Habilitação da skill no aplicativo Alexa.

### Parcialmente validadas

- Options flow completo e reauth, que ainda não têm teste end-to-end dedicado.
- Setup assistido e checklist.
- Locales `fr-CA` e `nl-NL` na criação da skill.
- Arquitetura `aarch64` em execução real.

### Não implementado

- Login ou autorização Amazon sem interação humana.
- Criação, exclusão ou habilitação automática de skills na conta Amazon.
- Criação de túneis, certificados ou registros DNS.
- Suporte a Nabu Casa.
- Edição do checklist fora do Options Flow.
- Gerenciamento de múltiplas contas Amazon.

## Requisitos

| Requisito | Situação |
|---|---|
| Home Assistant OS ou Supervised com add-ons | Necessário para o add-on |
| Home Assistant mínimo | `2026.10.4` declarado em `hacs.json`; é a versão do ambiente de desenvolvimento. Versões anteriores **não foram validadas** |
| Music Assistant | Necessário; **não há versão mínima comprovada** |
| Conta de desenvolvedor Amazon | Necessária, com *Skill Access Management* |
| Conta Alexa | A mesma usada no console de desenvolvedor |
| Dois hostnames públicos com HTTPS | `SKILL_HOSTNAME` e `MA_HOSTNAME` |
| TLS | 1.2 ou superior; a imagem upstream não suporta TLS 1.3 |
| Túnel ou reverse proxy | Fornecido pelo usuário |
| Arquiteturas do add-on | `amd64` e `aarch64` declaradas; execução real em HA feita, arquitetura não registrada; `aarch64` não executado |
| Portas locais | `5000` (add-on), `8095` (API do MA), `8097` (stream do MA) |

Consulte a [matriz de validação](docs/VALIDATION-MATRIX.md) para o que foi
realmente testado.

## Instalação

> **Versão 0.2.0 em validação:** ela está no branch `validation/phase-4-ci`
> (PR #1, Draft), commit `8ab7492`, e ainda não foi integrada à `main`.
> Instalar pela loja/HACS agora entrega a versão da `main` (0.1.x), não a
> 0.2.0. Para testar a 0.2.0, use o add-on local e a integração copiada do mesmo
> commit, conforme [`docs/HAOS-TEST-PLAN.md`](docs/HAOS-TEST-PLAN.md).

### 1. Adicionar o repositório de add-ons

1. Abra **Configurações > Add-ons > Loja de add-ons**.
2. No menu de três pontos, escolha **Repositórios**.
3. Adicione:

   ```text
   https://github.com/flaviocorrea13/alexa-skill
   ```

### 2. Instalar o add-on

1. Localize **Alexa MA Skill** na loja.
2. Instale o add-on.
3. Abra a aba **Configuração** e preencha as opções (veja abaixo).
4. Inicie o add-on.

`SKILL_HOSTNAME` é obrigatório, sem `https://`, sem caminho e sem porta.
`MA_HOSTNAME` é tecnicamente opcional, mas necessário na prática para Echo Dot e
outros dispositivos sem tela e para exibir capa.

As opções completas estão em [`DOCS.md`](alexa_ma_skill/DOCS.md#opções).

### 3. Instalar a integração (opcional)

A integração não é necessária para o add-on funcionar. Ela adiciona configuração
pela interface e o setup assistido.

**Instalação manual:**

1. Copie `custom_components/alexa_ma_skill` para
   `/config/custom_components/alexa_ma_skill`.
2. Reinicie o Home Assistant.
3. Abra **Configurações > Dispositivos e serviços > Adicionar integração**.
4. Escolha **Alexa MA Skill**.
5. Se houver mais de um add-on correspondente, selecione o slug correto.

**HACS:** o repositório está preparado para instalação como repositório
personalizado do HACS e a HACS Action **passou no CI**. Não há inclusão no
catálogo padrão e ainda falta
`custom_components/alexa_ma_skill/brand/icon.png`. A partir do Home Assistant
2026.11, o HACS é distribuído como **Marketplace**; os nomes de menu podem
variar.

#### Painel administrativo

A integração opcional registra o painel **Alexa MA**:

- acesso pelo menu lateral do Home Assistant ou pelo caminho `/alexa-ma`;
- visível apenas para administradores;
- visão geral **somente leitura**, sem iniciar/parar o add-on, alterar opções ou
  controlar a reprodução;
- seletor de config entry quando houver mais de uma entry carregada;
- atualização manual com cooldown de 5 segundos; cliques repetidos retornam o
  snapshot atual sem iniciar outra atualização;
- estados de erro e recuperação, incluindo a ação **Tentar novamente** quando a
  lista de config entries precisa ser recarregada;
- o painel depende do add-on acessível para obter os dados. Se o add-on estiver
  parado, o setup da integração pode não concluir e o painel pode não aparecer;
  nesse caso, verifique o estado do add-on no Supervisor.

### 4. Configuração inicial

Preencha as opções do add-on:

| Opção | Obrigatória | Descrição |
|---|:---:|---|
| `SKILL_HOSTNAME` | Sim | Hostname público da skill. Ex.: `skill.exemplo.com` |
| `MA_HOSTNAME` | Não* | Hostname público do stream. Ex.: `ma.exemplo.com` |
| `APP_USERNAME` / `APP_PASSWORD` | Não | Credenciais do painel; geradas se vazias |
| `LOCALE` | Não | Idioma da skill (padrão `pt-BR`) |
| `SKILL_ID` | Não | Restringe a skill às próprias requisições |
| `MA_API_URL` | Não** | API WebSocket do MA na porta `8095` |
| `MA_API_TOKEN` | Não** | Token do MA, quando exigido |

\* Necessário para dispositivos sem tela e para capa.
\** Necessário para comandos de voz que controlam o player.

### 5. Abrir o setup da skill

Na **rede local**, abra:

```text
http://<IP_DO_HOME_ASSISTANT>:5000/setup
```

Faça login com `APP_USERNAME`/`APP_PASSWORD` e siga a autorização Amazon. **Não
use** `https://<SKILL_HOSTNAME>/setup`: esse caminho é bloqueado pela regra de
segurança do hostname público.

O guia completo está em
[`DOCS.md`](alexa_ma_skill/DOCS.md#primeiro-setup-da-skill).

### 6. Configuração externa

1. Aponte `SKILL_HOSTNAME` para a porta `5000` do add-on e `MA_HOSTNAME` para a
   porta `8097` do Music Assistant.
2. Libere publicamente **apenas** `POST /` em `SKILL_HOSTNAME`.
3. Configure o provider **Alexa** do Music Assistant com a URL interna do add-on
   (`http://<IP_DO_HA>:5000`, sem `/ma`) e as credenciais do painel.
4. Habilite a skill em **Skills > Suas Skills > Dev** no aplicativo Alexa.

Passo a passo detalhado, incluindo a regra de WAF, em
[`DOCS.md`](alexa_ma_skill/DOCS.md#exposição-pública-e-https).

### 7. Verificação final

- [ ] O add-on está em execução e `/status` responde na rede local.
- [ ] `/status` mostra o endpoint correspondente a `SKILL_HOSTNAME`.
- [ ] `SKILL_ID` foi preenchido e o add-on foi reiniciado.
- [ ] O provider Alexa do MA mostra `/ma/latest-url` com `200` após um play.
- [ ] A skill está habilitada no aplicativo Alexa.
- [ ] **"Alexa, abra music assistant"** responde.
- [ ] O áudio toca em um Echo real.

Se você instalou a integração, use **Configurar > Setup assistido** para
acompanhar as mesmas etapas com progresso e confirmações.

## Arquitetura e responsabilidades

| Componente | Responsabilidade |
|---|---|
| Add-on | Executa a skill, persiste credenciais do ASK CLI, expõe `/setup`, `/status` e `/ma/*` na rede local |
| Integração | Configura opções via Supervisor, consulta o add-on e apresenta o checklist; não inicia nem instala contêineres |
| Supervisor | Instala e inicia o add-on, fornece slug, hostname interno e opções |
| Music Assistant | Reproduz o áudio e envia a URL do stream ao add-on pelo provider Alexa |
| Amazon / Alexa | Autentica a skill, entrega as requisições de voz e reproduz o áudio |
| Usuário | Domínio, DNS, HTTPS, túnel/proxy, conta Amazon e configuração do provider |

### Portas

| Porta | Serviço | Onde é usada |
|---:|---|---|
| `5000` | Add-on (skill, `/setup`, `/status`, `/ma`) | Túnel de `SKILL_HOSTNAME` e provider Alexa do MA |
| `8095` | API WebSocket do Music Assistant | `MA_API_URL`, comandos de controle |
| `8097` | Stream de áudio do Music Assistant | Túnel de `MA_HOSTNAME` |

Não confunda `8095` (API) com `8097` (áudio). O add-on fala com o Supervisor
pelos helpers do componente `hassio`; a integração nunca acessa o Supervisor por
HTTP cru.

## Segurança

- Exponha publicamente **apenas** `POST /` em `SKILL_HOSTNAME`.
- Mantenha `/setup`, `/status`, `/devices`, `/docs`, `/openapi.json`, `/ma`,
  `/alexa`, `/simulator` e `/invocations` na rede local.
- Use a regra de WAF documentada em
  [`DOCS.md`](alexa_ma_skill/DOCS.md#exposição-pública-e-https).
- O `POST /` valida a assinatura das requisições da Alexa. Não desative essa
  validação.
- `APP_USERNAME`/`APP_PASSWORD`, `MA_API_TOKEN` e credenciais ASK nunca devem ser
  publicados em issues, logs, capturas ou commits.
- As credenciais geradas ficam em `/data` com permissão `600`. Os backups do
  add-on incluem esses arquivos: trate-os como material sensível.
- Não use credenciais padrão como `admin`/`teste`.
- Se uma credencial vazar, revogue o acesso na Amazon e/ou no Music Assistant,
  gere uma nova e reinicie o add-on.
- Não publique a porta `5000` diretamente no roteador.

## Solução de problemas

Mensagens e procedimentos completos estão em
[`DOCS.md`](alexa_ma_skill/DOCS.md#solução-de-problemas).

### O add-on não inicia

- Confira o log do add-on.
- `SKILL_HOSTNAME` deve ser um hostname puro: sem `https://`, caminho ou porta.
- `PORT` deve ser `5000` e `LOCALE` precisa ser um valor aceito.

### A integração não encontra o add-on

- Add-ons de repositório personalizado recebem slug com prefixo, por exemplo
  `0a1b2c3d_alexa_ma_skill`.
- A integração procura `alexa_ma_skill` ou `*_alexa_ma_skill`; reinicie a
  integração após instalar o add-on.

### Recebo 401 em `/setup` ou `/status`

As credenciais do painel estão erradas. Leia os arquivos gerados em `/data` ou
defina `APP_USERNAME`/`APP_PASSWORD` nas opções e reinicie.

### `Skill ID Verification failed!!` ou "problema com a resposta da skill"

O `SKILL_ID` configurado não corresponde à skill. Copie o valor de
`Done. Skill ID:` nos logs do `/setup`, preencha `SKILL_ID` e reinicie.

### A Alexa responde "could not retrieve the latest music stream from the API"

O add-on está sem `streamUrl`. Confira a URL interna do provider
(`http://<IP_DO_HA>:5000`, sem `/ma`) e as credenciais Basic Auth. Teste:

```sh
curl -i -u "$APP_USERNAME:$APP_PASSWORD" \
  "http://<IP_DO_HA>:5000/ma/latest-url"
```

`404 No URL available` significa que o MA ainda não enviou o stream. Toque algo
pelo Music Assistant e teste de novo.

### A Alexa responde "can't reach the audio file"

O add-on não conseguiu validar a URL pública. Verifique `MA_HOSTNAME`, o
certificado e a rota para a porta `8097`. Se o host funciona mas o contêiner
falha (hairpin NAT), ative `SKIP_URL_VALIDATION: true` temporariamente.

### Cloudflare retorna `404 page not found` em texto puro

As rotas específicas de `SKILL_HOSTNAME` e `MA_HOSTNAME` devem vir **antes** das
rotas curinga. Deixe a catch-all por último.

### O setup não mostra a URL da Amazon

Confira a saída de internet do add-on, os logs do `/setup` e se o *Skill Access
Management* está habilitado na conta de desenvolvedor.

### Próxima/anterior não funcionam

Preencha `MA_API_URL` com a porta `8095` (não `8097`), informe
`MA_API_TOKEN` se exigido e associe o Echo ao player em `/devices`.

## Suporte

- **Problemas e dúvidas:** abra uma issue em
  <https://github.com/flaviocorrea13/alexa-skill/issues>.
- Use o template de **Bug report** e informe: versão do add-on, versão da
  integração (se usar), versão do Home Assistant, ambiente (HA OS/Supervised),
  arquitetura, versão do Music Assistant, túnel/proxy e passos para reproduzir.
- **Logs:** copie o log do add-on ou da integração e **remova** senhas, tokens,
  credenciais ASK, `SKILL_ID` completo, hostnames privados, IPs e e-mails antes
  de colar.
- **Diagnóstico:** em **Configurações > Dispositivos e serviços > Alexa MA Skill**,
  use o menu de três pontos > **Baixar diagnóstico** e revise o arquivo antes de
  anexar.
- **Nunca publique:** `APP_PASSWORD`, `MA_API_TOKEN`, credenciais ASK, arquivos
  de backup, tokens de acesso ou capturas com dados pessoais.
- Para relatar um problema de segurança, não abra uma issue pública com
  segredos; descreva o caso sem dados sensíveis e solicite um canal privado ao
  mantenedor pelo perfil do GitHub.

Não há canal oficial de suporte por e-mail, Discord ou comunidade. O repositório
é o canal do projeto.

## Status de validação

| Item | Estado |
|---|---|
| CI (GitHub Actions) | **5 jobs aprovados** no run `45716728724`, commit `8ab7492` |
| Suíte pytest no CI Linux | **107 testes e 26 subtestes aprovados** |
| Frontend | **38 testes aprovados**; typecheck e build aprovados |
| Config flow (6 testes) | Aprovados no CI Linux |
| Hassfest | **Aprovado no CI** |
| HACS Action | **Aprovada no CI** (com ignores de metadados do GitHub) |
| Add-on `0.2.0` em HA real | **Instalado e testado**; seis cenários funcionais manuais aprovados pelo usuário |
| Testes locais no Windows | **106 aprovados, 1 ignorado, 26 subtestes** (suplementar; não é CI) |
| Add-on (unitários) | 16 testes locais aprovados (1 pulo POSIX) |
| `aarch64` | Não executado |
| Backup/restauração e atualização pela loja | Pendentes |
| Catálogo padrão do HACS | Pendente de `brand/icon.png` e Release |

Os testes manuais foram realizados pelo usuário em Home Assistant real e não
fazem parte da CI. Os testes locais no Windows usaram shims fora do repositório e
são apenas suplementares. Não há screenshots reais e o ícone de marca do HACS
ainda precisa ser adicionado.

Detalhes e evidências em [docs/VALIDATION-MATRIX.md](docs/VALIDATION-MATRIX.md) e
[docs/DISTRIBUTION-READINESS.md](docs/DISTRIBUTION-READINESS.md). O roteiro de
validação em HA OS está em
[docs/HAOS-TEST-PLAN.md](docs/HAOS-TEST-PLAN.md) — **parcialmente executado**
(instalação e seis cenários funcionais). O rascunho da primeira release está em
[docs/releases/RELEASE-DRAFT.md](docs/releases/RELEASE-DRAFT.md) — **não
publicado**.

## Desenvolvimento

Estrutura principal:

```text
.
├── repository.yaml                    # Repositório de add-ons
├── hacs.json                          # Metadados da integração
├── pyproject.toml                     # Ruff e pytest
├── requirements_test.txt              # Harness Home Assistant (Linux)
├── requirements_ci.txt                # Ruff e PyYAML para a CI
├── .github/                           # CI, templates de issue e PR
├── scripts/validate_repo.py           # Validação local/CI
├── scripts/run_hassfest_subset.py     # Hassfest local sem Docker
├── docs/                              # Distribuição, matriz e release
├── custom_components/alexa_ma_skill/  # Integração opcional
├── tests/                             # Testes locais e de config flow
└── alexa_ma_skill/                    # Add-on
    ├── config.yaml
    ├── Dockerfile
    ├── run.sh
    ├── addon_options.py
    ├── DOCS.md
    ├── CHANGELOG.md
    └── translations/
```

Validadores locais (Windows ou Linux):

```bash
python scripts/validate_repo.py
python -m unittest tests.test_addon_options
ruff check .
ruff format --check .
python -m compileall -q alexa_ma_skill custom_components tests scripts
bash -n alexa_ma_skill/run.sh
```

Testes da integração em Linux:

```bash
python -m pip install -r requirements_test.txt
python -m pytest -q
```

A imagem upstream é fixada por tag e digest no `FROM` do
`alexa_ma_skill/Dockerfile`. Não use `:latest`. A CI está em
`.github/workflows/ci.yml` e não publica imagens, tags ou Releases.

## Licença

O código original deste repositório é **MIT** ([`LICENSE`](LICENSE)). O painel
frontend inclui **Lit 3.3.3** sob a **BSD 3-Clause License**. A imagem base
upstream é licenciada sob a **Amazon Software License 1.0**
([`LICENSE-AMAZON-SOFTWARE-1.0`](LICENSE-AMAZON-SOFTWARE-1.0)). Consulte também
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## Aviso

Este projeto não é afiliado, endossado ou patrocinado pela Amazon.com, Inc. ou
pela Music Assistant. Amazon, Alexa e nomes relacionados são marcas da
Amazon.com, Inc. ou de suas afiliadas.

## English summary

Alexa MA Skill runs the upstream Music Assistant Alexa skill inside a Home
Assistant add-on, without Nabu Casa. It keeps ASK CLI credentials, generates
panel passwords safely and exposes `/setup` and `/status` on the local network.
An optional custom integration adds UI configuration, a 16-step setup checklist,
and an admin-only read-only sidebar panel at `/alexa-ma`.

Requirements: Home Assistant OS/Supervised, a Music Assistant instance, an
Amazon developer account with Skill Access Management, two public HTTPS
hostnames and a user-provided tunnel or reverse proxy. TLS 1.2+ is required.

Install the add-on from
`https://github.com/flaviocorrea13/alexa-skill`, set `SKILL_HOSTNAME` and
`MA_HOSTNAME`, start it, then open `http://<HA_IP>:5000/setup` on the local
network. Expose only `POST /` publicly. Enable the skill in the Alexa app and
say **"Alexa, open music assistant"**.

Validation is partial but substantially complete: `0.2.0` was installed and
tested on a real Home Assistant instance, and six manual scenarios passed
(invocation without active music, track change, pause/resume, next track,
multiple Echos, and the sidebar panel). CI passed all five jobs on commit
`8ab7492` (run `45716728724`): 107 Linux tests, 26 subtests, and 38 frontend
tests. `aarch64`, backup/restore, and a store upgrade remain pending. See
[`docs/VALIDATION-MATRIX.md`](docs/VALIDATION-MATRIX.md) and
[`alexa_ma_skill/DOCS.md`](alexa_ma_skill/DOCS.md).
