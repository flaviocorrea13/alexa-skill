# Alexa MA Skill

Add-on do Home Assistant que executa o contêiner do projeto
[music-assistant-skill](https://github.com/alams154/music-assistant-skill) e
expõe a skill Alexa usada para controlar o Music Assistant por voz.

> **Escopo desta versão (Fase 1):** somente o add-on. A integração personalizada
> que configura o add-on pela interface do Home Assistant será adicionada na
> Fase 2. O setup assistido com checklist e confirmação será adicionado na
> Fase 3.

## Como funciona

```text
Alexa (voz)
   |
   | HTTPS POST /
   v
https://SKILL_HOSTNAME  --->  túnel/reverse proxy  --->  add-on :5000
                                                          |
                                                          | /setup, /status
                                                          | (somente rede local)
                                                          v
                                                   ASK CLI + skill Flask

Alexa (áudio)
   |
   | HTTPS GET
   v
https://MA_HOSTNAME  --->  túnel/reverse proxy  --->  Music Assistant :8097
```

- O add-on executa a aplicação Flask original na porta `5000`.
- A Alexa chama `POST /` em `https://SKILL_HOSTNAME/`. Esse é o **único**
  caminho que deve ser exposto publicamente.
- `/setup` cria ou atualiza a skill no console da Amazon usando o ASK CLI.
- `/status` mostra o diagnóstico da skill, do ASK CLI, da API do Music
  Assistant e da API da Alexa.
- O áudio vem do Music Assistant. O add-on apenas reescreve a URL do stream
  para `https://MA_HOSTNAME/...`; o túnel precisa encaminhar esse hostname para
  a porta de stream do Music Assistant (normalmente `8097`).
- As credenciais do ASK CLI ficam em `/data/ask`, persistidas entre reinícios
  e backups. O caminho esperado pela imagem original, `/root/.ask`, é um
  symlink para `/data/ask`.
- O add-on **não cria túneis, não gerencia certificados e não abre portas no
  roteador**. Você é responsável pela exposição HTTPS pública.

## Requisitos

- Home Assistant OS ou Home Assistant Supervised, com add-ons habilitados.
- Arquitetura `amd64` ou `aarch64`.
- Music Assistant instalado e acessível na sua rede.
- Uma conta de desenvolvedor da Amazon:
  <https://developer.amazon.com/alexa/console/ask>.
- "Skill Access Management" habilitado na conta de desenvolvedor:
  <https://developer.amazon.com/alexa/console/ask/settings/access-management>.
- Dois hostnames públicos com certificado válido (o `MA_HOSTNAME` é obrigatório
  para dispositivos sem tela e para exibir capa):
  - `SKILL_HOSTNAME`: aponta para a porta `5000` deste add-on.
  - `MA_HOSTNAME`: aponta para a porta de stream do Music Assistant
    (normalmente `8097`).
- Um túnel ou reverse proxy que forneça HTTPS público. Exemplos: Cloudflare
  Tunnel, outro túnel ou um proxy reverso com certificado válido.
- A Alexa exige HTTPS na porta `443` com certificado confiável. Não use
  certificado autoassinado.
- A imagem original não suporta TLS 1.3. Se usar Cloudflare, configure a
  versão mínima de TLS como **1.2**.

> **Nabu Casa não é usado.** O projeto não cria nem gerencia túneis.

## Instalação

1. No Home Assistant, abra **Configurações > Add-ons > Loja de add-ons**.
2. No menu de três pontos, escolha **Repositórios**.
3. Adicione `https://github.com/flaviocorrea13/alexa-ma-skill`.
4. Instale o add-on **Alexa MA Skill**.
5. Abra a aba **Configuração** e preencha as opções. `SKILL_HOSTNAME` é
   obrigatório. `MA_HOSTNAME` é obrigatório para dispositivos sem tela
   (Echo Dot, por exemplo).
6. Inicie o add-on.
7. Abra a interface web em `http://<IP_DO_HOME_ASSISTANT>:5000/setup` ou use o
   botão **Abrir interface web**.
8. Faça login com as credenciais do painel (veja a seção
   [Credenciais](#credenciais)).

O Supervisor exige que `SKILL_HOSTNAME` seja preenchido antes de iniciar o
add-on. Além disso, o add-on valida o formato e se recusa a iniciar se o valor
for inválido. A mensagem aparece no log do add-on.

Se a porta `5000` do host já estiver em uso, altere o mapeamento em **Rede**
nas configurações do add-on. A porta interna continua sendo `5000`; use a porta
do host escolhida nos URLs locais e no túnel.

## Opções

| Opção | Obrigatória | Padrão | Descrição |
|---|:---:|---|---|
| `SKILL_HOSTNAME` | Sim | — | Hostname público da skill, sem `https://`. Exemplo: `skill.exemplo.com`. |
| `MA_HOSTNAME` | Não* | — | Hostname público do stream do Music Assistant, sem `https://`. Exemplo: `ma.exemplo.com`. |
| `APP_USERNAME` | Não | gerado | Usuário da autenticação básica de `/setup` e `/status`. |
| `APP_PASSWORD` | Não | gerado | Senha da autenticação básica de `/setup` e `/status`. |
| `PORT` | Não | `5000` | Porta interna. Mantenha `5000`. |
| `LOCALE` | Não | `pt-BR` | Idioma da skill e dos modelos de interação. |
| `TZ` | Não | `America/Sao_Paulo` | Fuso horário do contêiner. |
| `AWS_DEFAULT_REGION` | Não | `us-east-1` | Região usada pelo ASK CLI. |
| `ENABLE_APL` | Não | `false` | Habilita APL em dispositivos com tela. |
| `SKIP_URL_VALIDATION` | Não | `false` | Não valida a URL do stream antes de enviá-la à Alexa. |
| `SKILL_ID` | Não | — | ID `amzn1.ask.skill...` para restringir a skill às próprias requisições. |
| `MA_API_URL` | Não** | — | URL base da API WebSocket do Music Assistant, porta `8095`. |
| `MA_API_TOKEN` | Não** | — | Token da API do Music Assistant. |

\* `MA_HOSTNAME` é obrigatório na prática para Echo Dot e outros dispositivos
sem tela, e também para exibir capa em dispositivos com tela.

\** `MA_API_URL` e `MA_API_TOKEN` são necessários para comandos de voz que
controlam o player do Music Assistant (próxima, anterior, início da faixa e
sincronização de pausar/parar/continuar). A reprodução de áudio funciona sem
eles.

### `SKILL_HOSTNAME` e `MA_HOSTNAME`

Use apenas o hostname, sem esquema, sem caminho e sem porta:

- Correto: `skill.exemplo.com`
- Correto: `ma.exemplo.com`
- Incorreto: `https://skill.exemplo.com`
- Incorreto: `skill.exemplo.com/setup`
- Incorreto: `skill.exemplo.com:5000`

O add-on valida esses valores e mostra uma mensagem clara no log se estiverem
no formato errado.

## Credenciais

### Credenciais do painel (`/setup` e `/status`)

Se `APP_USERNAME` e `APP_PASSWORD` estiverem em branco, o add-on gera valores
aleatórios no primeiro início e grava:

- `/data/generated_app_username` (modo `600`)
- `/data/generated_app_password` (modo `600`)

As senhas **nunca** aparecem no log do add-on.

Para ler os valores gerados, use o add-on **Terminal & SSH** com acesso ao
host:

```sh
docker exec addon_alexa_ma_skill cat /data/generated_app_username
docker exec addon_alexa_ma_skill cat /data/generated_app_password
```

Ou, no Home Assistant OS:

```sh
sudo cat /mnt/data/supervisor/addons/data/alexa_ma_skill/generated_app_username
sudo cat /mnt/data/supervisor/addons/data/alexa_ma_skill/generated_app_password
```

Se preferir não usar SSH, defina `APP_USERNAME` e `APP_PASSWORD` você mesmo
nas opções do add-on antes do primeiro início. Não use credenciais padrão como
`admin`/`teste`.

Para trocar as credenciais depois:

1. Preencha `APP_USERNAME` e `APP_PASSWORD` com os novos valores.
2. Reinicie o add-on.

Se você deixar os campos em branco novamente, o add-on reutiliza os arquivos
gerados existentes. Para gerar novos valores, apague os arquivos em `/data`
(ou defina credenciais explícitas) e reinicie.

### Credenciais do ASK CLI

O fluxo de setup autentica o ASK CLI na sua conta Amazon. As credenciais ficam
em `/data/ask` e são incluídas nos backups do add-on. Elas dão acesso à sua
conta de desenvolvedor; proteja seus backups.

O add-on **não** define `ASK_CREDENTIALS_DIR`. O caminho `/root/.ask` é um
symlink para `/data/ask`, que é o caminho usado pela aplicação original.

### Token da API do Music Assistant

Se você informar `MA_API_TOKEN`, o add-on grava o valor em
`/data/generated_ma_api_token` (modo `600`) e passa apenas o caminho para a
aplicação. Assim o token não aparece no log do upstream.

## Exposição pública e HTTPS

### Regra recomendada no Cloudflare

A skill precisa que a Amazon alcance apenas `POST /` em `SKILL_HOSTNAME`.
Todo o resto deve ficar restrito à rede local.

Crie uma regra de WAF no Cloudflare para o hostname da skill:

```text
(http.host eq "skill.exemplo.com" and not (http.request.uri.path eq "/" and http.request.method eq "POST"))
```

Ação: **Block**.

Isso bloqueia publicamente:

- `/setup`
- `/status`
- `/devices`
- `/docs`
- `/ma`
- `/alexa`
- qualquer outro caminho

Mantenha esses caminhos acessíveis apenas pela rede local, por exemplo em
`http://<IP_DO_HOME_ASSISTANT>:5000/setup`.

> Não exponha `/setup` ou `/status` na internet. O `/setup` executa o ASK CLI
> com as suas credenciais da Amazon; o `/status` mostra informações
> operacionais.

### Cloudflare Tunnel (exemplo)

No túnel, configure dois hostnames públicos:

| Hostname público | Serviço local |
|---|---|
| `skill.exemplo.com` | `http://<IP_DO_HOME_ASSISTANT>:5000` |
| `ma.exemplo.com` | `http://<IP_DO_MUSIC_ASSISTANT>:8097` |

- O primeiro atende a skill. A regra de WAF acima limita o acesso a `POST /`.
- O segundo atende os streams de áudio do Music Assistant.
- Ative **Always Use HTTPS**.
- Configure a versão mínima de TLS como **1.2**. A imagem original não suporta
  TLS 1.3.
- Não publique a porta `5000` diretamente no roteador. Deixe o acesso público
  apenas pelo túnel.

Se o túnel roda como add-on no mesmo Home Assistant, use o IP do host ou o
nome que o add-on do túnel consegue resolver. O add-on publica a porta `5000`
no host.

### Outros túneis ou reverse proxy

O mesmo princípio se aplica:

- HTTPS público válido para `SKILL_HOSTNAME` e `MA_HOSTNAME`.
- Apenas `POST /` liberado publicamente em `SKILL_HOSTNAME`.
- `/setup`, `/status`, `/devices`, `/docs`, `/ma` e `/alexa` somente na rede
  local.
- TLS 1.2 ou superior.
- Encaminhe `X-Forwarded-For`, `X-Forwarded-Proto` e `X-Forwarded-Host` se o
  proxy permitir. A aplicação usa `ProxyFix` para respeitar esses cabeçalhos.

## Primeiro setup da skill

1. Confirme que `SKILL_HOSTNAME` e `MA_HOSTNAME` estão corretos e que os
   túneis estão ativos.
2. Abra `http://<IP_DO_HOME_ASSISTANT>:5000/setup` na rede local.
3. Faça login com as credenciais do painel.
4. Clique em **Start** (ou no botão equivalente) para iniciar o setup.
5. O add-on inicia `ask configure --no-browser` e mostra uma URL de
   autorização da Amazon.
6. Abra a URL, faça login com a conta que tem o **Skill Access Management**
   habilitado e autorize o ASK CLI.
7. Copie o código de autorização exibido pela Amazon e cole no campo do painel
   `/setup`.
8. Aguarde. O script:
   - cria ou reutiliza uma skill;
   - monta o manifesto com `https://SKILL_HOSTNAME`;
   - envia os modelos de interação;
   - aguarda a compilação dos modelos;
   - tenta habilitar a skill para testes.
9. Quando aparecer `Done. Skill ID: amzn1.ask.skill...`, copie o ID.
10. Volte às opções do add-on, preencha `SKILL_ID` com esse valor e reinicie o
    add-on. Isso restringe a skill às requisições destinadas a ela.
11. No aplicativo Alexa, abra **Mais > Skills > Suas Skills > Dev** (ou
    **Em desenvolvimento**) e habilite a skill.
12. Teste com a frase de invocação do idioma configurado:
    - `pt-BR`: **"Alexa, abra minha rádio"**
    - `en-US`: **"Alexa, open my radio"**

> **Nome da skill:** o projeto upstream usa o nome de exibição **"My Radio"**
> (e variantes por idioma) e a frase de invocação **"minha rádio"** em
> `pt-BR`. O nome não é "Alexa MA Skill". Consulte o console da Amazon para
> confirmar o nome e a frase de invocação da skill criada.

### Aviso sobre skills existentes

O script upstream procura skills existentes com o nome exato
**"Music Assistant"**:

- Se encontrar **uma**, ele reutiliza.
- Se encontrar **mais de uma**, ele **apaga as extras** e mantém a primeira.

Ele não apaga outras skills. Ainda assim, revise o console da Amazon antes de
executar o setup em uma conta que já tenha skills.

O script cria uma skill chamada "My Radio"/"Minha Rádio". Executar o setup
novamente pode criar uma skill duplicada em vez de atualizar a anterior. Se
isso acontecer, remova a skill antiga manualmente no console da Amazon.

### Tipo de certificado no manifesto

O script upstream grava `sslCertificateType: Wildcard` no manifesto. Se a
Amazon recusar o endpoint por causa do certificado, abra a skill no console da
Amazon, vá em **Endpoint** e selecione a opção de certificado de uma autoridade
confiável (**Trusted**). Use um certificado válido para o hostname; não use
certificado autoassinado.

## Comandos de voz e players

A reprodução de áudio usa o player Alexa do Music Assistant. Para os comandos
de voz que controlam o player do Music Assistant (próxima, anterior, início da
faixa e sincronização de pausar/parar/continuar), configure:

- `MA_API_URL`: URL base da API WebSocket do Music Assistant, porta `8095`.
  Exemplo: `http://192.168.1.10:8095`.
- `MA_API_TOKEN`: token da API, se o Music Assistant exigir autenticação.

Não inclua usuário ou senha na `MA_API_URL`; use `MA_API_TOKEN` para a
autenticação.

`MA_API_URL` **não** é a porta de stream `8097`. São serviços diferentes:

| Serviço | Porta padrão | Uso |
|---|---:|---|
| Stream do Music Assistant | `8097` | Áudio enviado à Alexa (`MA_HOSTNAME`) |
| API WebSocket do Music Assistant | `8095` | Comandos de controle (`MA_API_URL`) |

Para associar cada Echo ao player correto do Music Assistant, abra
`http://<IP_DO_HOME_ASSISTANT>:5000/devices` na rede local. O procedimento é:

1. Faça um comando de voz no Echo (por exemplo, "próxima").
2. Recarregue `/devices`.
3. Informe o `player_id` do Music Assistant correspondente ao device ID do
   Echo.

Próxima/anterior e início da faixa dependem do Music Assistant para escolher o
conteúdo. Pausar, parar e continuar controlam o player Alexa diretamente e
também são sincronizados com o Music Assistant quando há um player associado.

## Diagnóstico

Abra `http://<IP_DO_HOME_ASSISTANT>:5000/status` na rede local. A página mostra:

- se a aplicação está rodando;
- se o ASK CLI tem credenciais funcionais;
- se a skill existe e se o endpoint corresponde a `SKILL_HOSTNAME`;
- se os testes estão habilitados;
- o estado da API do Music Assistant;
- o estado da API da Alexa;
- metadados e invocações recentes.

Você também pode usar a versão JSON:

```sh
curl -u "$APP_USERNAME:$APP_PASSWORD" "http://<IP_DO_HOME_ASSISTANT>:5000/status?format=json"
```

Não faça chamadas públicas a `/status`.

## Solução de problemas

### O add-on não inicia

- Verifique o log do add-on.
- Confirme que `SKILL_HOSTNAME` está preenchido com um hostname puro, sem
  `https://`, sem caminho e sem porta.
- Confirme que `PORT` é `5000`.
- Confirme que `LOCALE` é um dos valores aceitos.

### Recebo 401 em `/setup` ou `/status`

- Use as credenciais do painel.
- Se você não as conhece, leia os arquivos em `/data` conforme a seção
  [Credenciais](#credenciais).
- Se preferir, defina `APP_USERNAME` e `APP_PASSWORD` nas opções e reinicie.

### O setup não mostra a URL da Amazon

- Verifique se o add-on tem saída para a internet.
- Abra os logs do `/setup` no painel.
- Pare o setup e tente novamente.
- Confirme que o "Skill Access Management" está habilitado na conta de
  desenvolvedor.

### A skill foi criada, mas a Alexa não a encontra

- Confirme que a skill está habilitada em **Skills > Suas Skills > Dev**.
- Use a mesma conta Amazon no aplicativo Alexa e no console de desenvolvedor.
- Confirme o idioma da skill e a frase de invocação.
- Em `pt-BR`, tente **"Alexa, abra minha rádio"**.
- Em `en-US`, tente **"Alexa, open my radio"**.

### O áudio não toca

- Confirme que `MA_HOSTNAME` está correto e que o túnel aponta para a porta
  `8097` do Music Assistant.
- Confirme que o certificado de `MA_HOSTNAME` é válido.
- Confirme que o player do Music Assistant está ativo.
- Se o add-on não consegue alcançar o hostname público, ative
  `SKIP_URL_VALIDATION` temporariamente.
- Verifique `/status`.

### Próxima/anterior não funcionam

- Preencha `MA_API_URL` com a API WebSocket (porta `8095`), não com a porta de
  stream.
- Preencha `MA_API_TOKEN` se a API exigir autenticação.
- Associe o Echo ao player em `/devices`.

### Erro de TLS

- A imagem original não suporta TLS 1.3. Configure o mínimo como TLS 1.2.
- Use um certificado válido e uma cadeia completa.
- Não use certificado autoassinado.

### Endpoint não corresponde a `SKILL_HOSTNAME`

- O `/status` mostra o endpoint registrado na skill.
- Se você mudou `SKILL_HOSTNAME`, execute o setup novamente ou ajuste o
  endpoint no console da Amazon.
- Evite executar o setup várias vezes sem remover skills antigas; isso pode
  criar duplicatas.

### Skills duplicadas

- O script upstream pode criar uma nova skill "My Radio"/"Minha Rádio" a cada
  execução.
- Remova as skills antigas no console da Amazon.
- Ele também pode apagar skills extras chamadas exatamente "Music Assistant"
  quando encontra mais de uma. Revise a conta antes de rodar o setup.

## Segurança

- Exponha publicamente apenas `POST /` em `SKILL_HOSTNAME`.
- Mantenha `/setup`, `/status`, `/devices`, `/docs`, `/ma` e `/alexa` somente na
  rede local.
- O `POST /` valida as assinaturas das requisições da Alexa usando o ASK SDK.
  Não desative essa validação.
- Use credenciais aleatórias fortes. O add-on gera credenciais quando os
  campos estão vazios e nunca as exibe nos logs.
- As credenciais do ASK CLI e os tokens ficam em `/data`, com permissão
  restrita. Proteja os backups do add-on.
- Se uma credencial vazar, revogue o acesso no console da Amazon e/ou no Music
  Assistant, gere novas credenciais e reinicie o add-on.
- Não publique a porta `5000` diretamente na internet.
- Use TLS 1.2 ou superior.

## Backup e persistência

O add-on usa `backup: cold`: ele é parado durante o backup. O diretório
`/data` é preservado e inclui:

- `/data/ask`: credenciais do ASK CLI;
- `/data/generated_app_username` e `/data/generated_app_password`;
- `/data/generated_ma_api_token`, se configurado;
- `/data/options.json`: cópia de runtime das opções (pode conter a senha do
  painel se você a definiu manualmente).

Trate o backup como material sensível.

## Limitações

- O add-on usa uma imagem upstream fixada por versão e digest no `FROM` do
  `Dockerfile`. Atualizações exigem alterar essa linha e a versão do add-on.
- O login da Amazon no setup é manual; não há autenticação totalmente headless.
- O script upstream pode apagar skills extras chamadas "Music Assistant" e
  pode criar skills duplicadas "My Radio" em execuções repetidas.
- O nome de exibição e a frase de invocação vêm do upstream.
- O manifesto gerado usa `sslCertificateType: Wildcard`; ajuste para `Trusted`
  no console se necessário.
- `MA_HOSTNAME` remove a porta da URL do stream; o túnel precisa mapear o
  hostname para a porta correta do Music Assistant.
- O add-on não cria túneis, não emite certificados e não configura DNS.
- Não há suporte a Nabu Casa.
- A integração personalizada e o setup assistido com checklist chegam nas
  Fases 2 e 3.

## English quick start

1. Add this repository to the Home Assistant add-on store:
   `https://github.com/flaviocorrea13/alexa-ma-skill`.
2. Install **Alexa MA Skill**.
3. Set `SKILL_HOSTNAME` (for example `skill.example.com`),
   `MA_HOSTNAME` (for example `ma.example.com`), `LOCALE` (for example
   `en-US`), and `TZ`.
4. Start the add-on.
5. Open `http://<HA_IP>:5000/setup` on your local network and sign in with the
   generated dashboard credentials (see [Credentials](#credenciais)).
6. Follow the Amazon authorization flow, paste the code, and wait for
   `Done. Skill ID: ...`.
7. Set `SKILL_ID` to that value and restart the add-on.
8. Enable the skill in the Alexa app under **Skills > Your Skills > Dev**.
9. Say **"Alexa, open my radio"**.
10. For Music Assistant player commands, set `MA_API_URL` to the WebSocket API
    on port `8095` and `MA_API_TOKEN` if required.

Public exposure: allow only `POST /` on `SKILL_HOSTNAME`. Keep `/setup`,
`/status`, `/devices`, `/docs`, `/ma`, and `/alexa` on the local network. Use
TLS 1.2 or newer; TLS 1.3 is not supported by the upstream image.

## Licença

O código original deste add-on é licenciado sob a licença MIT. A imagem base
upstream é licenciada sob a **Amazon Software License 1.0**. Consulte
`LICENSE`, `LICENSE-AMAZON-SOFTWARE-1.0` e `THIRD_PARTY_NOTICES.md` na raiz do
repositório.

Este projeto não é afiliado, endossado ou patrocinado pela Amazon.com, Inc. ou
pela Music Assistant.
