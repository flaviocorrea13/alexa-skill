# Screenshots — lista de captura

Nenhuma imagem foi capturada nesta etapa. Não existem screenshots no
repositório e **não serão criadas imagens fictícias ou simuladas**.

As capturas abaixo só podem ser produzidas em uma instalação real do Home
Assistant, preferencialmente em Home Assistant OS, com o add-on instalado e a
integração carregada. Antes de salvar, revise a tela para remover dados
sensíveis.

## Imagens necessárias

| Arquivo | Tela | O que deve mostrar | Dependência |
|---|---|---|---|
| `docs/images/addon-store.png` | Loja de add-ons | O add-on **Alexa MA Skill** no repositório personalizado | HA OS com o repositório adicionado |
| `docs/images/addon-configuration.png` | Configuração do add-on | Aba **Configuração** com `SKILL_HOSTNAME`, `MA_HOSTNAME` e credenciais **mascaradas** | Add-on instalado |
| `docs/images/integration-entry.png` | Dispositivos e serviços | A entrada **Alexa MA Skill** e o dispositivo criado | Integração instalada |
| `docs/images/assisted-setup.png` | Setup assistido | Menu **Configurar** com as opções **Configurar opções** e **Setup assistido** | Integração carregada |
| `docs/images/setup-checklist.png` | Checklist | Progresso, etapas concluídas/pendentes e a próxima ação, **sem segredos** | Integração + dados do add-on |
| `docs/images/diagnostics.png` | Diagnóstico | Resumo do diagnóstico com `SKILL_ID` mascarado e sem tokens | Integração + add-on acessível |

## Regras de captura

- Use uma instalação de teste, nunca uma conta pessoal com dados de terceiros.
- Oculte ou substitua:
  - hostnames reais por `skill.exemplo.com` / `ma.exemplo.com` quando possível;
  - endereços IP privados;
  - nomes de pessoas, e-mails e IDs de conta;
  - `APP_USERNAME`, `APP_PASSWORD`, `MA_API_TOKEN`, credenciais ASK e
    `SKILL_ID` completo;
  - URLs de stream e parâmetros de sessão.
- Não edite a imagem para simular um estado que não existe. Recorte, desfoque ou
  tarje apenas dados sensíveis.
- Prefira PNG com largura entre 1200 e 1600 px.
- Nomeie os arquivos exatamente como na tabela para que o README possa
  referenciá-los.

## Depois de capturar

1. Adicione os arquivos em `docs/images/`.
2. Atualize `docs/VALIDATION-MATRIX.md` com a data e o ambiente das capturas.
3. Referencie as imagens no README somente quando elas existirem.
4. Confirme que nenhuma imagem contém segredo antes de commitar.

## Estado

- Imagens reais disponíveis: **nenhuma**.
- Imagens pendentes: as seis da tabela.
- Caminho preparado: `docs/images/`.
