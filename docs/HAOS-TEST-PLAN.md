# Roteiro de validação em Home Assistant OS

> **STATUS: NÃO EXECUTADO.** Este roteiro depende de uma instância de teste do
> Home Assistant OS, Music Assistant, Echo e conta Amazon. Nenhum passo foi
> executado nesta máquina. Não execute nada em produção sem autorização.

Este documento descreve o procedimento reproduzível para fechar as validações
manuais da Fase 4. Use uma instalação de teste, nunca a produção.

## 1. Preparação do ambiente

- Home Assistant OS ou Supervised, `amd64` (obrigatório) e, se possível,
  `aarch64`.
- Music Assistant instalado e funcional na mesma rede.
- Conta Amazon de teste com **Skill Access Management** habilitado.
- Um Echo físico na mesma conta.
- Dois hostnames HTTPS de teste (`SKILL_HOSTNAME` e `MA_HOSTNAME`) e um túnel ou
  reverse proxy controlado por você.
- Backup da instância de teste antes de começar.

Registre: versão do HA OS, arquitetura, versão do Music Assistant, túnel/proxy e
data.

## 2. Instalação do add-on `0.2.0`

1. **Configurações > Add-ons > Loja de add-ons > Repositórios**.
2. Adicione `https://github.com/flaviocorrea13/alexa-skill`.
3. Instale **Alexa MA Skill** e confirme a versão `0.2.0`.
4. Abra a aba **Configuração** e preencha:
   - `SKILL_HOSTNAME` (hostname puro);
   - `MA_HOSTNAME` (hostname puro);
   - `APP_USERNAME` e `APP_PASSWORD` fortes (ou deixe vazio para gerar);
   - `LOCALE`, `TZ` e, opcionalmente, `MA_API_URL`/`MA_API_TOKEN`.
5. Inicie o add-on e confirme no log que não há erro de validação de opção.

**Evidência:** captura da página do add-on (versão), da configuração com
credenciais ocultas e trecho do log sem segredos.

## 3. Serviço local

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

## 4. Persistência após reinício

1. Reinicie o Home Assistant.
2. Confirme que o add-on volta a iniciar sozinho.
3. Repita o login em `/status` com as mesmas credenciais.
4. Confirme que o `SKILL_ID` e as opções continuam preenchidos.
5. Repita após reiniciar apenas o add-on.

**Evidência:** `uptime`/logs do add-on e `/status` após cada reinício.

## 5. Backup e restauração

O add-on usa `backup: cold`; ele é parado durante o backup.

1. **Configurações > Sistema > Backups > Criar backup** (inclua o add-on
   Alexa MA Skill).
2. Anote o nome/data do backup.
3. Em uma instância de teste, desinstale o add-on. Se o Home Assistant
   perguntar sobre remover dados, registre a escolha.
4. Reinstale o add-on `0.2.0` (sem restaurar ainda) e confirme o estado inicial.
5. Restaure o backup criado no passo 1.
6. Inicie o add-on e confirme:
   - login em `/status` com as credenciais anteriores;
   - `/data/ask` presente (credenciais ASK);
   - `SKILL_ID` e opções preservados;
   - se usava token do MA, `/data/generated_ma_api_token` presente e modo `600`.

**Atenção:** não presuma que desinstalar sem backup preserva `/data`. O caminho
suportado de recuperação é o backup/restauração. Trate o backup como material
sensível.

**Evidência:** lista de arquivos em `/data` (sem conteúdo), permissões e
`/status` pós-restauração.

## 6. Integração personalizada

1. Instale `custom_components/alexa_ma_skill` (manual ou HACS personalizado).
2. Reinicie o HA e adicione a integração.
3. Confirme a descoberta do slug `<hash>_alexa_ma_skill`.
4. Abra **Configurar > Setup assistido**.
5. Percorra as 16 etapas; confirme que as automáticas refletem o add-on e que
   as manuais só ficam disponíveis após as dependências.
6. Feche e reabra a tela e reinicie o HA: as confirmações devem persistir.
7. Altere `SKILL_HOSTNAME` nas opções e confirme que apenas as etapas
   dependentes foram invalidadas (autorização Amazon preservada).

**Evidência:** capturas do checklist, progresso e diagnóstico com `SKILL_ID`
mascarado.

## 7. Music Assistant e Alexa

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

## 8. Exposição externa e HTTPS

1. Confirme que apenas `POST /` é permitido em `SKILL_HOSTNAME` pela regra de
   WAF/proxy.
2. De uma rede externa, teste `GET https://SKILL_HOSTNAME/setup` → deve ser
   bloqueado.
3. Teste `GET https://MA_HOSTNAME/` no caminho do stream → deve responder.
4. Confirme TLS 1.2+ e certificado válido.
5. Teste as rotas específicas antes das curingas.

**Evidência:** códigos HTTP, `curl -I` e captura da regra de WAF (sem dados
sensíveis).

## 9. Arquiteturas

- `amd64`: executar os passos 2 a 8.
- `aarch64`: repetir em hardware real ou runner com HA OS. A presença no índice
  OCI **não** conta como validação de execução.

## 10. Critérios de aprovação

- Instalação e reinício sem intervenção manual inesperada.
- `/setup` e `/status` acessíveis apenas na rede local.
- Backup/restauração preservando credenciais ASK, painel e opções.
- Integração carregando, descobrindo o slug e persistindo o checklist.
- Provider, stream na `8097`, API na `8095`, áudio e comandos funcionando.
- Nenhum segredo em evidências.

Se qualquer item falhar, registre a versão, o passo, a mensagem exata e o log
revisado antes de abrir uma issue.
