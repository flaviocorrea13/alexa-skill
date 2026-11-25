# Roteiro de validação manual — Home Assistant OS (0.2.0)

> **STATUS: NÃO EXECUTADO.** Este roteiro depende de uma instância isolada do
> Home Assistant OS, Music Assistant, Echo, conta Amazon e túnel de teste.
> Nenhum passo foi executado nesta máquina. Não execute nada em produção.

Este documento valida a versão **0.2.0 do commit
`5b75b6341c2fe9a988ab354626909fc546628661`**, que está no branch
`validation/phase-4-ci` e **ainda não foi integrada à `main`**.

## 1. Versão sob teste e canais de instalação

| Canal | O que instala hoje | Usar neste roteiro? |
|---|---|---|
| Loja de add-ons apontando para `main` | Add-on **0.1.1** (a `main` remota ainda não tem a 0.2.0) | **Não** |
| HACS/repositório personalizado apontando para `main` | Integração da `main`, não a do commit de validação | **Não** |
| Add-on **local** a partir do commit `5b75b63` | Add-on **0.2.0** | **Sim** |
| Integração copiada manualmente do mesmo commit | Integração **0.2.0** | **Sim** |
| Release pública futura | 0.2.0 após merge/tag (não existe) | Ainda não |

**Regra:** para validar a 0.2.0, use o add-on local e a integração copiada do
**mesmo commit**. Adicionar o repositório GitHub à loja, ou instalar pelo HACS
personalizado, usará a `main` e poderá entregar a 0.1.x.

O Home Assistant não permite escolher um branch no repositório da loja. Não
aponte a loja para o branch de validação; use a instalação local descrita abaixo.

## 2. Pré-requisitos de ambiente isolado

- **HAOS separado da instalação principal** (VM, dispositivo reservado ou
  instância de teste). Nunca use a instalação de produção.
- **Backup completo da instância de teste** antes de começar e outro antes de
  desinstalar/restaurar.
- **Music Assistant de teste** (ou ambiente controlado), acessível na rede do
  HAOS de teste, sem players de produção.
- **Echo e conta Amazon de teste** com **Skill Access Management** habilitado.
  A conta será usada para autorizar a skill; não use a conta principal.
- **Hostnames e túnel de teste** (`SKILL_HOSTNAME` e `MA_HOSTNAME`), com
  certificado válido e TLS 1.2+.
- Acesso a arquivos para copiar o add-on e a integração:
  - **Samba share** (compartilhamento `addons` em HA 2026.10.x; nas versões que
    renomearam add-ons para Apps, use `local_apps`); ou
  - **Terminal & SSH**, trabalhando em `/addons` (HA 2026.10.x) ou
    `/local_apps` (HA 2026.11+).
- Espaço em disco para o build local da imagem (o Supervisor constrói a imagem
  a partir do `Dockerfile`).
- Navegador com acesso à interface do HAOS de teste e à rede local.

> **Não instale a versão da loja e a versão local ao mesmo tempo.** As duas usam
> a porta `5000` e a integração veria dois candidatos. Em uma instância de teste
> limpa, use apenas o add-on local deste roteiro.

Registre antes de começar: versão do HAOS, arquitetura, versão do Music
Assistant, versão do Supervisor, túnel/proxy, data e responsável pelo teste.

> **Aviso:** o script upstream procura skills chamadas exatamente **"Music
> Assistant"**. Em uma conta com mais de uma, ele pode apagar as extras e manter
> uma. Use uma conta de teste e confira as skills antes do setup.

## 3. Obter o commit exato

Baixe o arquivo do **commit**, não do branch (o branch pode avançar):

```text
https://github.com/flaviocorrea13/alexa-skill/archive/5b75b6341c2fe9a988ab354626909fc546628661.tar.gz
```

Alternativa com Git em um computador de apoio:

```sh
git clone https://github.com/flaviocorrea13/alexa-skill.git
cd alexa-skill
git checkout 5b75b6341c2fe9a988ab354626909fc546628661
git rev-parse HEAD
```

O `git rev-parse HEAD` deve retornar exatamente:

```text
5b75b6341c2fe9a988ab354626909fc546628661
```

Extraia o arquivo e localize:

```text
alexa_ma_skill/                         # pasta do add-on
custom_components/alexa_ma_skill/       # integração
```

Mantenha os arquivos com **LF**. Não copie pela metade nem use um editor que
converta `run.sh` para CRLF; o add-on não inicia com CRLF.

### Hashes esperados dos arquivos de identidade

Os hashes abaixo foram calculados a partir do conteúdo do commit, com LF.
Confirme em HAOS com `sha256sum` (ou `Get-FileHash` no Windows, após copiar):

| Arquivo | SHA-256 esperado |
|---|---|
| `alexa_ma_skill/config.yaml` | `d92c11cf1284273b02a8a6f12e715bccb268dfc7ab87a74d460e4efd3cd9bb52` |
| `alexa_ma_skill/run.sh` | `88388f3f32218a830563d984b50c98f2e43bbc4e342529c63f6ab43984b8aa4c` |
| `alexa_ma_skill/addon_options.py` | `2b5653e83da4268a3414d89764e6047c0dcd3ef041169541d85c947874d1898c` |
| `custom_components/alexa_ma_skill/manifest.json` | `7bf77c1c1f51494f188614c1922998ff11204a0601ebccd1a7d0526b7790faba` |
| `custom_components/alexa_ma_skill/api.py` | `e5d1d7498f280264cbf005a16ed799b89ef851a0549abf10433887f082a68e0f` |
| `custom_components/alexa_ma_skill/setup.py` | `1a7f7a5d5231a694c4a93ecae4206004209f612ed0e81237b713ea8ba2ce2e88` |

A versão `0.2.0` sozinha não prova o commit; os hashes provam que o conteúdo é
o esperado.

## 4. Instalar o add-on local da versão de teste

1. No HAOS de teste, abra o compartilhamento Samba de add-ons ou o terminal.
2. Crie a pasta do add-on:
   - HA 2026.10.x (Add-ons): `/addons/alexa_ma_skill`
   - HA 2026.11+ (Apps): `/local_apps/alexa_ma_skill`
3. Copie **todo o conteúdo** de `alexa_ma_skill/` para essa pasta, incluindo
   `config.yaml`, `Dockerfile`, `run.sh`, `addon_options.py`, `DOCS.md`,
   `CHANGELOG.md` e `translations/`.
4. Confirme que `config.yaml` está na raiz da pasta e que o hash corresponde ao
   da seção 3.
5. No Home Assistant: **Configurações > Add-ons (ou Apps) > Loja de add-ons**.
6. No menu de três pontos, selecione **Verificar atualizações**.
7. Atualize a página. A seção **Add-ons locais (ou Apps locais)** deve mostrar
   **Alexa MA Skill**.
8. Instale e aguarde o Supervisor construir a imagem a partir do `Dockerfile`.
9. Confirme a versão **0.2.0** na página do add-on.
10. Abra a aba **Configuração**, preencha as opções e inicie o add-on:
    - `SKILL_HOSTNAME` (hostname puro de teste);
    - `MA_HOSTNAME` (hostname puro de teste);
    - `APP_USERNAME`/`APP_PASSWORD` fortes (ou deixe vazio para gerar);
    - `LOCALE`, `TZ` e, opcionalmente, `MA_API_URL`/`MA_API_TOKEN`.

O add-on local recebe o slug **`local_alexa_ma_skill`** e o hostname interno
**`local-alexa-ma-skill`** (o Supervisor troca `_` por `-`). A integração aceita
esse slug porque ele termina em `_alexa_ma_skill`.

### Se o add-on local não aparecer

- Confirme o caminho correto para a versão do HAOS (`/addons` ou
  `/local_apps`) e que `config.yaml` está na raiz da pasta.
- Valide o YAML e o schema do `config.yaml`.
- **Configurações > Sistema > Logs > Supervisor**: procure a mensagem sobre o
  add-on.
- Selecione **Verificar atualizações** novamente e recarregue o navegador.
- Não adicione o repositório GitHub como substituto: ele instalaria a versão da
  `main`.

### Atualizar o add-on local para outro commit

Se o commit mudar e a versão continuar `0.2.0`, o Supervisor pode não oferecer
atualização. Use **Rebuild** na página do add-on quando disponível; caso
contrário, faça backup, desinstale, copie o novo conteúdo e reinstale. Não
altere `version` manualmente: isso quebraria a verificação de hashes.

## 5. Instalar a integração do mesmo commit

1. Copie `custom_components/alexa_ma_skill/` para
   `/config/custom_components/alexa_ma_skill`.
2. Confirme o hash de `manifest.json` da seção 3.
3. Reinicie o Home Assistant.
4. Abra **Configurações > Dispositivos e serviços > Adicionar integração**.
5. Escolha **Alexa MA Skill**.
6. Confirme que a integração descobre o add-on `local_alexa_ma_skill`. Se houver
   mais de um candidato, selecione o local.
7. Confirme no manifesto que a versão é `0.2.0`.

Se você já tinha a integração instalada pela `main`/HACS, substitua os arquivos
por completo e reinicie. Não misture arquivos de commits diferentes.

## 6. Confirmar que add-on e integração correspondem ao commit

Registre as evidências:

```sh
sha256sum /addons/alexa_ma_skill/config.yaml
sha256sum /addons/alexa_ma_skill/run.sh
sha256sum /config/custom_components/alexa_ma_skill/manifest.json
sha256sum /config/custom_components/alexa_ma_skill/api.py
```

Use `/local_apps/...` no lugar de `/addons/...` se a sua versão usa Apps. Se o
Terminal & SSH não montar a pasta de add-ons, copie os arquivos via Samba e
calcule o hash no computador:

```powershell
Get-FileHash .\alexa_ma_skill\config.yaml -Algorithm SHA256
Get-FileHash .\custom_components\alexa_ma_skill\manifest.json -Algorithm SHA256
```

| Verificação | Como confirmar |
|---|---|
| Commit baixado | `git rev-parse HEAD` = `5b75b63...` ou arquivo do commit |
| Add-on | Página mostra `0.2.0`; hashes de `config.yaml`/`run.sh` conferem |
| Integração | `manifest.json` mostra `0.2.0`; hash confere |
| Slug local | `local_alexa_ma_skill` |
| Versão em execução | Logs e `/status` após iniciar |

**Evidência:** captura da página do add-on com a versão, hashes calculados,
captura da integração carregada e log sem segredos.

## 7. Serviço local

1. Abra `http://<IP_DO_HA>:5000/setup` na rede local.
2. Confirme o login com as credenciais do painel.
3. Abra `http://<IP_DO_HA>:5000/status`.
4. Consulte o JSON:

   ```sh
   curl -u "$APP_USERNAME:$APP_PASSWORD" \
     "http://<IP_DO_HA>:5000/status?format=json"
   ```

5. Confirme que `/setup` e `/status` **não** respondem pelo hostname público.

**Evidência:** respostas HTTP e captura das telas, sem credenciais.

## 8. Persistência após reinício

1. Reinicie o Home Assistant.
2. Confirme que o add-on local volta a iniciar sozinho.
3. Repita o login em `/status` com as mesmas credenciais.
4. Confirme que `SKILL_ID` e as opções continuam preenchidos.
5. Repita após reiniciar apenas o add-on.

**Evidência:** logs/`uptime` e `/status` após cada reinício.

## 9. Backup e restauração

O add-on usa `backup: cold`; ele é parado durante o backup. O add-on local é
incluído no backup como qualquer add-on instalado.

1. **Configurações > Sistema > Backups > Criar backup** (inclua o add-on
   Alexa MA Skill).
2. Anote nome e data.
3. Faça um segundo backup antes de desinstalar.
4. Desinstale o add-on. Se o HA perguntar sobre remover dados, registre a
   escolha.
5. Reinstale o add-on local a partir da mesma pasta em **Add-ons/Apps locais**
   (sem restaurar ainda) e confirme a versão `0.2.0`.
6. Restaure o backup criado no passo 1.
7. Inicie o add-on e confirme:
   - login em `/status` com as credenciais anteriores;
   - `/data/ask` presente (credenciais ASK);
   - `SKILL_ID` e opções preservados;
   - se usava token do MA, `/data/generated_ma_api_token` presente e modo `600`.

**Atenção:** não presuma que desinstalar sem backup preserva `/data`. O caminho
suportado é backup/restauração. Trate o backup como material sensível.

**Evidência:** lista de arquivos em `/data` (sem conteúdo), permissões e
`/status` pós-restauração.

## 10. Integração e setup assistido

1. Confirme que a integração do commit está carregada e descobriu
   `local_alexa_ma_skill`.
2. Abra **Configurar > Setup assistido**.
3. Percorra as 16 etapas; confirme que as automáticas refletem o add-on e que
   as manuais só ficam disponíveis após as dependências.
4. Feche e reabra a tela e reinicie o HA: as confirmações devem persistir.
5. Altere `SKILL_HOSTNAME` nas opções e confirme que apenas as etapas
   dependentes foram invalidadas (autorização Amazon preservada).

**Evidência:** capturas do checklist, progresso e diagnóstico com `SKILL_ID`
mascarado.

## 11. Music Assistant e Alexa

1. Configure o provider **Alexa** do MA com:
   - `API URL`: `http://<IP_DO_HA>:5000` (sem `/ma`);
   - Basic Auth do painel;
   - domínio Amazon correto;
   - `OTP Secret` vazio se não houver TOTP.
2. Toque algo no MA e verifique `200` em `/ma/latest-url`.
3. Preencha `MA_API_URL` com a API WebSocket na porta `8095` e o token se
   necessário.
4. No aplicativo Alexa, habilite a skill em **Skills > Suas Skills > Dev**.
5. Diga **"Alexa, abra music assistant"**.
6. Confirme o áudio em um Echo real.
7. Teste próxima, anterior e pausa.
8. Repita em Echo com tela e sem tela, se disponível.

**Evidência:** `/status` (sem segredos), `/ma/latest-url`, logs do MA e relato
do teste no Echo.

## 12. Exposição externa e HTTPS

1. Confirme que apenas `POST /` é permitido em `SKILL_HOSTNAME` pela regra de
   WAF/proxy.
2. De uma rede externa, teste `GET https://SKILL_HOSTNAME/setup` → deve ser
   bloqueado.
3. Teste `GET https://MA_HOSTNAME/` no caminho do stream → deve responder.
4. Confirme TLS 1.2+ e certificado válido.
5. Teste as rotas específicas antes das curingas.

**Evidência:** códigos HTTP, `curl -I` e captura da regra de WAF (sem dados
sensíveis).

## 13. Arquiteturas

- `amd64`: executar os passos 4 a 12.
- `aarch64`: repetir em hardware real ou runner com HA OS. A presença no índice
  OCI **não** conta como validação de execução.

## 14. O que pode ser testado sem Amazon, Echo ou exposição externa

| Verificação | Sem Amazon/Echo | Sem exposição externa | Observação |
|---|:---:|:---:|---|
| Download do commit e hashes | Sim | Sim | Não requer HA |
| Instalação do add-on local e build | Sim | Sim | Requer HAOS de teste |
| Página inicial de `/setup` e login | Sim | Sim | A autorização Amazon é manual |
| `/status` com autenticação | Sim | Sim | —
| Validação de opções e hostnames | Sim | Sim | —
| Persistência após reinício | Sim | Sim | —
| Backup/restauração | Sim | Sim | Teste em instância isolada |
| Integração carrega e descobre o slug | Sim | Sim | —
| Checklist: add-on instalado/iniciado, credenciais, formato de hostnames, detecção de ID e estado de API | Parcial | Sim | Algumas etapas ficam em atenção sem Amazon/MA |
| Provider MA e `/ma/latest-url` | Parcial | Sim | O provider exige conta Amazon; o push manual pode ser testado com `curl` |
| Autorização Amazon e criação/reutilização da skill | **Não** | Sim | Conta Amazon manual |
| `SKILL_ID` real e habilitação da skill | **Não** | Sim | Depende da skill criada |
| Descoberta da skill no app Alexa | **Não** | **Não** | Requer Echo/conta |
| Reprodução de áudio e comandos por voz | **Não** | **Não** | Requer Echo, MA e skill |
| WAF/rotas externas e TLS público | Sim | **Não** | Requer túnel/DNS de teste |
| `aarch64` | — | — | Requer hardware/runner |

## 15. Critérios de aprovação

- Add-on local instalado com versão `0.2.0` e hashes do commit conferidos.
- Integração carregada do mesmo commit e descoberta do slug
  `local_alexa_ma_skill`.
- `/setup` e `/status` acessíveis apenas na rede local.
- Backup/restauração preservando credenciais ASK, painel e opções.
- Setup assistido persistindo confirmações e invalidando apenas dependentes.
- Provider, stream na `8097`, API na `8095`, áudio e comandos funcionando.
- Nenhum segredo em evidências.
- `amd64` aprovado; `aarch64` executado ou explicitamente pendente.

Se qualquer item falhar, registre a versão, o passo, a mensagem exata, o log
revisado e os hashes dos arquivos antes de abrir uma issue.

## 16. Limpeza após o teste

1. Pare e desinstale o add-on local de teste.
2. Remova `/addons/alexa_ma_skill` ou `/local_apps/alexa_ma_skill`.
3. Remova `/config/custom_components/alexa_ma_skill` e a integração de teste.
4. Restaure o backup/snapshot da instância de teste.
5. Não altere a instalação de produção nem a `main`.
