# Testes

## Testes locais sem Home Assistant

`tests/test_addon_options.py` usa apenas a biblioteca padrão e testa o script
de opções do add-on.

```bash
python -m unittest tests.test_addon_options
```

## Testes de helpers da integração

`tests/test_integration_helpers.py` importa as bibliotecas do Home Assistant,
mas não precisa de uma instância do HA. Use o virtualenv do projeto:

```bash
.venv/Scripts/python.exe -m unittest tests.test_integration_helpers
```

No Linux:

```bash
python -m unittest tests.test_integration_helpers
```

## Testes de config flow

`tests/test_config_flow.py` usa `pytest-homeassistant-custom-component` e
depende do harness Linux do Home Assistant. Ele não roda no Windows porque o
plugin do HA importa `fcntl`.

```bash
python -m pytest tests/test_config_flow.py
```

O CI Linux deve executar todos os testes.
