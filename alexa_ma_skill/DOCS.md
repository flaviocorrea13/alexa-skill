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

## Slug e hostname interno do add-on

Add-ons instalados de um repositório personalizado recebem um prefixo
`<hash>_` do Supervisor. Por isso, o slug real pode ser
`0cc21073_alexa_ma_skill` em vez de `alexa_ma_skill`.

A integração personalizada:

- lista os add-ons com `get_addons_info(hass)` do componente `hassio`;
- aceita o slug exato `alexa_ma_skill` ou qualquer slug terminado em
  `_alexa_ma_skill`;
- mostra um seletor quando há mais de um correspondente;
- guarda o slug escolhido na config entry e o usa em todas as chamadas ao
  Supervisor.

O hostname interno é derivado do slug trocando `_` por `-`. Exemplos:

| Slug no Supervisor | Hostname interno |
|---|---|
| `alexa_ma_skill` | `alexa-ma-skill` |
| `0cc21073_alexa_ma_skill` | `0cc21073-alexa-ma-skill` |

Use o hostname derivado ao acessar o add-on a partir de outro contêiner ou em
configurações manuais. A porta interna continua sendo `5000`.

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
3. Adicione `https://github.com/flaviocorrea13/alexa-skill`.
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
| `SKILL_ID` | Não | — | ID `amzn1.ask.skill...` para restringir a skill às próprias requisições. A integração detecta e sugere o valor. |
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
# Substitua <slug> pelo slug real do Supervisor, por exemplo
# 0cc21073_alexa_ma_skill.
docker exec addon_<slug> cat /data/generated_app_username
docker exec addon_<slug> cat /data/generated_app_password
```

Ou, no Home Assistant OS:

```sh
sudo cat /mnt/data/supervisor/addons/data/<slug>/generated_app_username
sudo cat /mnt/data/supervisor/addons/data/<slug>/generated_app_password
```

Se preferir não usar SSH, defina `APP_USERNAME` e `APP_PASSWORD` você mesmo
nas opções do add-on antes do primeiro início. Não use credenciais padrão como
`admin`/`teste`.

As mesmas credenciais protegem `/ma` e devem ser usadas no provider Alexa do
Music Assistant:

- `API Basic Auth Username` = `APP_USERNAME`
- `API Basic Auth Password` = `APP_PASSWORD`

Ao trocar a senha, atualize também o provider no MA.

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

### Ordem das rotas no Cloudflare

Se você usa rotas curinga (`*.exemplo.com`), coloque as rotas específicas
**antes** delas:

1. `skill.exemplo.com` → `http://<IP_DO_HOME_ASSISTANT>:5000`
2. `ma.exemplo.com` → `http://<IP_DO_MUSIC_ASSISTANT>:8097`
3. `*.exemplo.com` (catch-all) por último

Quando a rota curinga vem primeiro, o pedido cai no Traefik e retorna um
`404 page not found` em texto puro, mesmo com o túnel ativo. Reordene as rotas
para que as específicas tenham prioridade.

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
   - A integração personalizada (Fase 2) lê esse ID automaticamente do
     `/setup`, avisa quando `SKILL_ID` está vazio ou divergente e sugere o
     valor correto.
10. Volte às opções do add-on, preencha `SKILL_ID` com esse valor e reinicie o
    add-on. Isso restringe a skill às requisições destinadas a ela.
11. No aplicativo Alexa, abra **Mais > Skills > Suas Skills > Dev** (ou
    **Em desenvolvimento**) e habilite a skill.
12. Invoque a skill com **"Alexa, abra music assistant"** (ou
    **"Alexa, open music assistant"**). O invocation é **`music assistant`** em
    todos os idiomas.

> **Nome e invocação:** o manifesto construído pelo upstream define o nome de
> exibição **"Music Assistant"**. O `scripts/ask_create_skill.sh` sobrescreve o
> `invocationName` de todos os modelos para **`music assistant`**, então os
> valores dos modelos brutos (`minha rádio`, `my radio` etc.) não são usados.
> O console da Amazon mostra o nome de exibição e a frase de invocação
> efetivamente criados.

### Aviso sobre skills existentes

O script upstream procura skills existentes com o nome exato
**"Music Assistant"**:

- Se encontrar **uma**, ele reutiliza.
- Se encontrar **mais de uma**, ele **apaga as extras** e mantém a primeira.

Ele não apaga outras skills. Ainda assim, revise o console da Amazon antes de
executar o setup em uma conta que já tenha skills.

O script cria ou reutiliza uma skill chamada "Music Assistant". O nome de
exibição no console é "Music Assistant"; o invocation é `music assistant` em
todos os locales.

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
| Add-on / provider Alexa do MA | `5000` | `/ma/push-url`, `/setup`, `/status` |
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

## Provider Alexa do Music Assistant

A Alexa não busca o stream diretamente no Music Assistant. O provider **Alexa**
do MA envia a URL do stream para o add-on via `POST /ma/push-url`. Depois a
skill lê essa URL e responde com `AudioPlayer.Play`.

No Music Assistant, em **Settings > Providers > Alexa**, configure:

| Campo | Valor |
|---|---|
| `URL` | Domínio Amazon da conta: `amazon.com`, `amazon.com.br` etc. |
| `E-mail` | Conta Amazon usada pelos Echos. |
| `Senha` | Senha da conta Amazon. |
| `OTP Secret` | Vazio se não houver uma chave TOTP válida. |
| `API URL` | `http://<IP_DO_HOME_ASSISTANT>:5000` |
| `API Basic Auth Username` | `APP_USERNAME` do add-on. |
| `API Basic Auth Password` | `APP_PASSWORD` do add-on. |

Regras importantes:

- Use a URL **interna** do add-on, por exemplo
  `http://192.168.1.10:5000`.
- Não use `https://SKILL_HOSTNAME` como `API URL`. O caminho `/ma` é bloqueado
  publicamente pelo WAF e não deve ser exposto.
- Não use `http://localhost:5000` se o Music Assistant estiver em outro
  contêiner/add-on; nesse caso, `localhost` aponta para o próprio contêiner do
  MA.
- O `API URL` é a base, **sem** `/ma`. O provider acrescenta `/ma/push-url`.
- Se você trocar `APP_USERNAME`/`APP_PASSWORD` no add-on, atualize também o
  provider Alexa do MA.
- O `OTP Secret` só deve ser preenchido quando existe uma chave TOTP válida.

### Teste do stream no add-on

Use as credenciais do painel:

```sh
APP_USERNAME='<APP_USERNAME>'
APP_PASSWORD='<APP_PASSWORD>'

curl -i -u "$APP_USERNAME:$APP_PASSWORD" \
  "http://<IP_DO_HOME_ASSISTANT>:5000/ma/latest-url"
```

Interpretação:

| Resposta | Significado |
|---|---|
| `200` com `streamUrl` | O MA enviou o stream e o add-on tem uma URL. |
| `404 {"error":"No URL available"}` | Autenticação OK, mas o MA ainda não enviou stream. |
| `401 Unauthorized` | `APP_USERNAME`/`APP_PASSWORD` errados no provider ou no `curl`. |
| Erro de conexão | `API URL` inacessível a partir do MA; confira IP, porta `5000` e rede. |

Para testar o push manualmente:

```sh
curl -i -u "$APP_USERNAME:$APP_PASSWORD" \
  -H 'Content-Type: application/json' \
  -d '{"streamUrl":"https://example.com/test.mp3","title":"teste"}' \
  "http://<IP_DO_HOME_ASSISTANT>:5000/ma/push-url"
```

Esperado: `200` com `{"status":"ok"}`. Isso grava uma URL falsa apenas para
teste; o próximo play real do MA sobrescreve o valor.

### Depois de reiniciar o add-on

O add-on guarda o último stream em memória. Quando ele reinicia, esse valor é
perdido. A ordem correta é:

1. Reiniciar o add-on.
2. No Music Assistant, tocar algo no player do Echo.
3. O MA envia um novo `POST /ma/push-url`.
4. Conferir o `200` em `/ma/latest-url`.
5. Invocar a Alexa.

Se você invocar a Alexa antes do passo 2, a skill pode responder que não
conseguiu obter o stream.

### `Play action failed` no Music Assistant

Esse aviso é do provider Alexa do MA, não do add-on. Ele indica que o provider
não conseguiu enviar o stream ou o comando para o Echo.

Verifique:

- `API URL` interno, com a porta `5000` correta;
- `API Basic Auth Username`/`Password` iguais aos do add-on;
- provider autenticado na conta Amazon;
- Echo online e na mesma conta;
- skill habilitada em **Skills > Suas Skills > Dev**;
- logs do MA em busca de `/ma/push-url`, `401`, `Failed API request` ou
  `ActionUnavailable`.

### Domínio da conta Amazon

O aviso:

```text
amazon.com.br does not match account domain amazon.com
```

pode ser ignorado se o áudio tocar. Se o login, o `Play action failed` ou o
comando para o Echo continuarem falhando, tente o domínio correto da conta:

- conta brasileira: `amazon.com.br`;
- conta americana: `amazon.com`.

Depois de alterar o domínio, reautentique o provider e conclua o 2FA.

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

### A integração diz que o add-on não está instalado

- Add-ons de repositório personalizado têm slug com prefixo `<hash>_`, por
  exemplo `0cc21073_alexa_ma_skill`.
- A integração procura `alexa_ma_skill` ou `*_alexa_ma_skill` e guarda o slug
  encontrado. Se houver mais de um, ela mostra um seletor.
- Verifique no Supervisor qual é o slug real e reinicie a integração.
- O hostname interno é o slug com `_` trocado por `-`, por exemplo
  `0cc21073-alexa-ma-skill`.

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
- Invoque com **"Alexa, abra music assistant"** (ou
  **"Alexa, open music assistant"**). O invocation é `music assistant` em todos
  os locales.

### `Skill ID Verification failed!!` / "problema com a resposta da skill"

- O `SKILL_ID` configurado não corresponde ao ID da skill criada.
- O ID correto aparece nos logs de `/setup` como `Done. Skill ID:` e também
  pode aparecer no `/status`.
- A integração personalizada detecta o ID e sugere o valor correto no checklist
  e no `binary_sensor.skill_id_valid`.
- Corrija `SKILL_ID`, reinicie o add-on e teste novamente.
- Sem `SKILL_ID`, a skill aceita qualquer skill assinada pela Amazon. Prefira
  preencher o valor.

### Cloudflare retorna `404 page not found` em texto puro

- As rotas curinga (`*.exemplo.com`) estão vindo **antes** das rotas
  específicas `skill.exemplo.com` e `ma.exemplo.com`.
- O pedido cai no Traefik e não chega ao add-on.
- Reordene as rotas: específicas primeiro, catch-all/curinga por último.

### Music Assistant: `Non-base32 digit found` / `internal_error`

- O campo **OTP Secret** do Music Assistant está com um valor inválido.
- Se você não tem uma chave TOTP válida, deixe **OTP Secret vazio**.
- Limpe o campo, salve e teste novamente.

### Music Assistant: `amazon.com.br does not match account domain amazon.com`

- Se o áudio toca normalmente, esse aviso pode ser ignorado.
- Ele indica que o domínio da conta Alexa não corresponde ao esperado pelo
  provider.
- Alternativa: reconfigurar a conta/provider Alexa no Music Assistant com o
  domínio correto da conta (por exemplo, `amazon.com`).

### Nenhum `POST /` aparece no log

- `QUIET_HTTP=1` é fixado pelo `run.sh` e esconde os logs HTTP do
  werkzeug/urllib3, inclusive os `POST /`.
- Não conclua que a skill não recebeu requisições apenas pela ausência de
  logs.
- Use `/status` (recent invocations) ou `/invocations` como indicador.

### A Alexa responde "could not retrieve the latest music stream from the API"

- O add-on está sem `streamUrl`.
- O provider Alexa do Music Assistant não enviou `POST /ma/push-url`.
- Confira o `API URL` do provider: `http://<IP_DO_HOME_ASSISTANT>:5000`, sem
  `/ma`, e com a porta `5000` correta.
- Confira `API Basic Auth Username` e `API Basic Auth Password`.
- Teste:
  ```sh
  curl -i -u "$APP_USERNAME:$APP_PASSWORD" \
    "http://<IP_DO_HOME_ASSISTANT>:5000/ma/latest-url"
  ```
- Se retornar `404 No URL available`, toque algo pelo Music Assistant e teste
  novamente.
- Se o add-on reiniciou, o stream em memória foi perdido; toque algo no MA
  novamente antes de invocar a Alexa.
- Veja os logs do MA em busca de `/ma/push-url`, `401` ou
  `Failed API request`.

### A Alexa responde "can't reach the audio file"

- O add-on encontrou um `streamUrl`, mas não conseguiu validar a URL pública.
- Teste a URL no host:
  ```sh
  curl -I 'https://stream.exemplo.com/...'
  ```
- Teste de dentro do add-on:
  ```sh
  docker exec addon_<slug> \
    python -c "import requests; r=requests.head('<URL>', allow_redirects=True, timeout=5); print(r.status_code)"
  ```
- Se o host funciona e o contêiner falha, é hairpin NAT/DNS interno. Ative
  `SKIP_URL_VALIDATION: true` nas opções do add-on, reinicie e teste.
- Se ambos falham, confira:
  - rota de `MA_HOSTNAME` apontando para a porta `8097` do Music Assistant;
  - ordem das rotas no Cloudflare;
  - certificado válido;
  - acesso à URL fora da rede local.

### O áudio não toca

- Confirme que `MA_HOSTNAME` está correto e que o túnel aponta para a porta
  `8097` do Music Assistant.
- Confirme que o certificado de `MA_HOSTNAME` é válido.
- Confirme que o player do Music Assistant está ativo.
- Confirme que o provider Alexa do MA está configurado com a URL interna e as
  credenciais do add-on.
- Se o add-on não consegue alcançar o hostname público, ative
  `SKIP_URL_VALIDATION` temporariamente.
- Verifique `/status` e as invocações recentes.
- Veja também [Provider Alexa do Music Assistant](#provider-alexa-do-music-assistant).

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

### Skills existentes "Music Assistant"

- O script procura skills chamadas exatamente "Music Assistant".
- Se houver uma, reutiliza; se houver mais de uma, apaga as extras e mantém a
  primeira.
- O nome de exibição criado é "Music Assistant"; o invocation é `music assistant`
  em todos os locales.

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
- O script upstream pode apagar skills extras chamadas "Music Assistant"
  quando há mais de uma. O nome de exibição criado é "Music Assistant" e o
  invocation é `music assistant` em todos os locales.
- `fr-CA` e `nl-NL` têm modelos brutos com invocation vazio; o script injeta
  `music assistant`, mas a criação nesses locales **não foi validada**.
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
   `https://github.com/flaviocorrea13/alexa-skill`.
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
9. Say **"Alexa, open music assistant"**. The display name is **Music
   Assistant**, and the invocation name is **`music assistant`** for every
   locale.
10. For Music Assistant player commands, set `MA_API_URL` to the WebSocket API
    on port `8095` and `MA_API_TOKEN` if required.

Public exposure: allow only `POST /` on `SKILL_HOSTNAME`. Keep `/setup`,
`/status`, `/devices`, `/docs`, `/ma`, and `/alexa` on the local network. Use
TLS 1.2 or newer; TLS 1.3 is not supported by the upstream image. If you use
wildcard routes, place the specific `skill` and `ma` routes before the wildcard
catch-all, otherwise Traefik returns `404 page not found`.

## Licença

O código original deste add-on é licenciado sob a licença MIT. A imagem base
upstream é licenciada sob a **Amazon Software License 1.0**. Consulte
`LICENSE`, `LICENSE-AMAZON-SOFTWARE-1.0` e `THIRD_PARTY_NOTICES.md` na raiz do
repositório.

Este projeto não é afiliado, endossado ou patrocinado pela Amazon.com, Inc. ou
pela Music Assistant.
