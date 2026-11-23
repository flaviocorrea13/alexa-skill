## Resumo

<!-- O que muda e por quê. -->

## Tipo de mudança

- [ ] Correção
- [ ] Recurso
- [ ] Documentação
- [ ] CI/manutenção

## Validação executada

- [ ] `ruff check .`
- [ ] `ruff format --check .`
- [ ] `python -m unittest tests.test_addon_options`
- [ ] `python scripts/validate_repo.py`
- [ ] Testes da integração no harness Linux (quando aplicável)

## Segurança

- [ ] Não incluí senhas, tokens, credenciais ASK, hostnames privados ou backups.
- [ ] Não alterei a exposição pública de `/setup`, `/status`, `/ma` ou `/devices`.
- [ ] Não adicionei ações de publicação (tag, release, push de imagem).
