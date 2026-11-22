# Changelog

## 0.1.0 - 2026-11-22

- Versão inicial da Fase 1 do add-on.
- Executa a imagem upstream `ghcr.io/alams154/music-assistant-skill` fixada por
  versão e digest.
- Persiste as credenciais do ASK CLI em `/data/ask` com symlink em `/root/.ask`.
- Gera usuário e senha aleatórios quando as opções estão vazias, sem registrar
  segredos nos logs.
- Reescreve `/data/options.json` com caminhos de segredo para evitar que o
  upstream sobrescreva as credenciais no import.
- Grava o token da API do Music Assistant em arquivo com permissão `600`.
- Adiciona traduções pt-BR e en para as opções e a porta.
- Documenta a exposição pública somente de `POST /` e mantém `/setup` e
  `/status` na rede local.
- Inclui avisos de licença MIT e Amazon Software License 1.0.
