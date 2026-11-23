# Rascunho de Release — Alexa MA Skill 0.2.0

> **STATUS: RASCUNHO. NÃO PUBLICADO.**
> Este arquivo prepara uma futura Release do GitHub. Ele não cria tag, Release,
> imagem Docker ou anúncio. A publicação depende das validações listadas em
> [`../DISTRIBUTION-READINESS.md`](../DISTRIBUTION-READINESS.md) e de
> autorização explícita do mantenedor.

## Título sugerido

`Alexa MA Skill 0.2.0 — setup assistido, integração opcional e preparação para distribuição`

## Texto de apresentação

O Alexa MA Skill executa a skill Alexa do Music Assistant no Home Assistant, sem
Nabu Casa e sem serviços gerenciados pelo projeto. O add-on empacota a imagem
upstream com credenciais persistentes, geração segura de senhas e diagnóstico; a
integração personalizada opcional adiciona configuração pela interface e um
checklist de 16 etapas.

## Mudanças confirmadas no código

### Adicionado

- Integração `custom_components/alexa_ma_skill/` com config flow gerenciado,
  manual e reauth.
- Descoberta do add-on por `alexa_ma_skill` ou `*_alexa_ma_skill`, com seletor
  para múltiplas instalações.
- Options flow com atualização parcial, preservação de opções desconhecidas e
  confirmação de reinício.
- Sensores, binary sensors e diagnostics com `SKILL_ID` mascarado.
- Setup assistido de 16 etapas, progresso, próxima ação e orientação de
  correção.
- Persistência das confirmações manuais em `Store`, com invalidação seletiva.
- Aviso e confirmação explícita sobre skills "Music Assistant" duplicadas.
- Textos do checklist em pt-BR e inglês.

### Alterado

- `README.md` reestruturado como página pública do projeto.
- `DOCS.md` com instalação, setup, provider Alexa, testes e recuperação.
- `CHANGELOG.md` reorganizado por categorias.
- Versão do add-on e da integração alinhada em `0.2.0`.

### Corrigido

- Migração de `/root/.ask` preserva a única cópia das credenciais se a cópia
  falhar.
- Credenciais geradas obsoletas são removidas ao definir credenciais explícitas.
- `MA_API_URL` valida esquema, host e ausência de credenciais embutidas.
- `configuration_url` deixou de apontar para a URL pública de `/setup`.
- Cache de checagem HTTPS limitado, evitando crescimento com URLs de stream
  rotativas.
- `manifest.json` reordenado conforme o Hassfest.
- Removidas URLs dos valores de tradução rejeitadas pelo Hassfest.
- Corrigido o formato do `ignore` do HACS Action e desabilitado o comentário
  automático com token somente leitura.

### Segurança

- Nenhuma senha Amazon é solicitada ou armazenada.
- Nenhuma operação Amazon é executada pela integração.
- Segredos do add-on continuam em arquivos `600`; tokens não aparecem em logs,
  entidades ou diagnostics.
- `/setup` e `/status` permanecem restritos à rede local.
- CI com permissões mínimas, actions fixadas por SHA e sem publicação
  automática.

### Compatibilidade

- Home Assistant mínimo declarado: `2026.10.4` (versão de desenvolvimento).
- Arquiteturas declaradas no add-on: `amd64` e `aarch64`.
- Music Assistant: sem versão mínima comprovada; declarada como pendência.
- Não depende de Nabu Casa.

## Requisitos

- Home Assistant OS ou Supervised com add-ons.
- Conta de desenvolvedor Amazon com "Skill Access Management".
- Dois hostnames HTTPS válidos (`SKILL_HOSTNAME` e `MA_HOSTNAME`).
- Túnel ou reverse proxy fornecido pelo usuário; TLS 1.2 ou superior.
- Music Assistant acessível na rede local.

## Instalação

1. Adicione `https://github.com/flaviocorrea13/alexa-skill` como repositório de
   add-ons.
2. Instale **Alexa MA Skill**, preencha as opções e inicie.
3. Abra `http://<IP_DO_HOME_ASSISTANT>:5000/setup` na rede local e conclua a
   autorização Amazon.
4. Preencha `SKILL_ID` e reinicie o add-on.
5. Habilite a skill em **Skills > Suas Skills > Dev**.
6. Opcionalmente, instale a integração e use **Configurar > Setup assistido**.

## Limitações conhecidas

- O login e a autorização Amazon são manuais.
- O script upstream pode excluir skills extras chamadas "Music Assistant".
- `fr-CA` e `nl-NL` não tiveram a criação de skill validada.
- O manifesto gerado usa `sslCertificateType: Wildcard`; pode ser necessário
  ajustar para `Trusted` no console.
- `MA_HOSTNAME` é necessário na prática para dispositivos sem tela e para capa.
- O add-on não cria túneis, certificados ou DNS.
- A integração é opcional e ainda não foi validada em HA OS.

## Pendências de validação antes da publicação

- Primeira execução da CI em pull request.
- Hassfest oficial aprovado.
- HACS Action aprovada.
- `pytest` oficial no Linux (a execução local no Windows com shims foi
  suplementar e passou).
- Instalação da `0.2.0` em HA OS `amd64` e, se possível, `aarch64`.
- `brand/icon.png` e uma Release completa para o catálogo padrão do HACS.
- Captura das screenshots reais sem dados sensíveis.
- Revisão final de segurança e de links.

## Checklist pré-publicação

- [ ] CI verde no commit da release.
- [ ] Hassfest verde.
- [ ] HACS Action verde.
- [ ] `pytest` completo aprovado em Linux.
- [ ] Versão `0.2.0` consistente em `config.yaml`, `manifest.json` e CHANGELOG.
- [ ] Instalação e atualização testadas em HA OS.
- [ ] `brand/icon.png` presente.
- [ ] Matriz de validação atualizada com evidências.
- [ ] Screenshots reais adicionadas em `docs/images/`.
- [ ] Nenhum segredo em diff, logs, issues ou screenshots.
- [ ] Release notes revisadas e autorizadas.
- [ ] Tag e Release criadas apenas com autorização explícita.

## Observação

Não há data de publicação definida. Este documento é um rascunho técnico, não um
anúncio.
