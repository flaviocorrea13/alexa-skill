# Avisos de terceiros

Este repositório contém código original e depende de software de terceiros. Os
termos abaixo explicam as licenças envolvidas. Esta é uma descrição
informativa; em caso de dúvida, o texto integral da licença prevalece.

## 1. Código original deste repositório

O código original do add-on, dos scripts de entrada, dos documentos e da
integração é licenciado sob a **licença MIT**. Consulte o arquivo
[`LICENSE`](LICENSE).

Copyright (c) 2026 flaviocorrea13.

## 2. Frontend: Lit 3.3.3

O painel administrativo é compilado com **Lit 3.3.3** (pacote npm `lit`),
distribuído no bundle `custom_components/alexa_ma_skill/frontend/dist/alexa-ma-panel.js`.
A versão é fixada em `frontend/package.json` e `frontend/package-lock.json`.

Lit é licenciado sob a **BSD 3-Clause License**. O texto integral, mantido
conforme o pacote original, é:

```text
BSD 3-Clause License

Copyright (c) 2017 Google LLC. All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

O mesmo aviso é preservado como banner no bundle final, mesmo após a minificação
com Terser.

## 3. Imagem base upstream: Amazon Software License 1.0

O add-on é construído a partir da imagem:

```text
ghcr.io/alams154/music-assistant-skill:0.0.39-beta
sha256:b1ef33ad0b05b7e0a315535e8141177898be4b6a0401decf43dedf424f0d90f1
```

A versão upstream corresponde ao commit
`2967b60551250bcce50586e9de0f6b036dcff237` (2026-10-15).

Essa imagem contém o projeto
[`alams154/music-assistant-skill`](https://github.com/alams154/music-assistant-skill),
licenciado sob a **Amazon Software License 1.0** ("ASL 1.0"). O texto integral
está em [`LICENSE-AMAZON-SOFTWARE-1.0`](LICENSE-AMAZON-SOFTWARE-1.0).

### 3.1 O que é a ASL 1.0

A ASL 1.0 é uma licença de software disponibilizada pela Amazon. Ela **não é
uma licença de código aberto aprovada pela OSI**, porque contém uma limitação
de área de uso (field-of-use). Ela permite usar, reproduzir, preparar obras
derivadas, exibir, executar, sublicenciar e distribuir o Work, desde que as
condições da licença sejam cumpridas.

### 3.2 Concessões

A ASL 1.0 concede:

- uma licença de copyright perpétua, mundial, não exclusiva e isenta de
  royalties para reproduzir, preparar obras derivadas, exibir, executar,
  sublicenciar e distribuir o Work e as obras derivadas resultantes;
- uma licença de patentes perpétua, mundial, não exclusiva e isenta de
  royalties para fabricar, usar, vender, oferecer para venda, importar e
  transferir o Work, limitada às reivindicações de patente licenciáveis pelo
  Licensor que seriam infringidas pelo Work individualmente, excluindo
  combinações com outros materiais ou tecnologias.

### 3.3 Condições de redistribuição

Se você redistribuir o Work ou uma obra derivada, a ASL 1.0 exige que você:

1. o faça sob a própria ASL 1.0;
2. inclua uma cópia completa da licença na distribuição;
3. mantenha, sem modificação, os avisos de copyright, patente, marca ou
   atribuição presentes no Work.

Se você aplicar termos adicionais ou diferentes às suas obras derivadas
("Your Terms"), esses termos só podem valer se (a) incluírem a limitação de uso
da Seção 3.3 e (b) identificarem especificamente quais obras derivadas estão
sujeitas a eles. A ASL 1.0 continua aplicável ao Work original.

### 3.4 Limitação de uso (Seção 3.3)

A limitação mais importante da ASL 1.0 está na Seção 3.3:

> O Work e suas obras derivadas só podem ser usados ou destinados ao uso com
> serviços web, plataformas de computação ou aplicações fornecidos pela
> Amazon.com, Inc. ou suas afiliadas, incluindo a Amazon Web Services, Inc.

Este projeto existe para integrar o Music Assistant à Alexa, que é uma
plataforma da Amazon. O uso pretendido está alinhado com essa limitação. Não
use o software upstream para fins não relacionados à Amazon sem antes avaliar
a licença com cuidado.

### 3.5 Patentes, marcas e rescisão

- Se você entrar com ou ameaçar entrar com uma reivindicação de patente contra
  um Licensor para fazer valer patentes que você alega serem infringidas pelo
  Work, seus direitos sob a ASL 1.0 terminam imediatamente.
- A licença não concede direitos de uso de nomes, logotipos ou marcas dos
  Licensors ou de suas afiliadas, exceto o necessário para reproduzir os
  avisos descritos na licença.
- A violação de qualquer termo da licença encerra imediatamente seus direitos
  sob ela.

### 3.6 Garantias e responsabilidade

O Work é fornecido **"AS IS"**, sem garantias de qualquer tipo, expressas ou
implícitas, incluindo comercialização, adequação a um propósito específico,
título ou não violação. A licença limita a responsabilidade dos Licensors por
danos diretos, indiretos, especiais, incidentais ou consequenciais, na máxima
extensão permitida pela lei aplicável.

### 3.7 Como este repositório cumpre a ASL 1.0

- O texto integral da ASL 1.0 é distribuído em
  [`LICENSE-AMAZON-SOFTWARE-1.0`](LICENSE-AMAZON-SOFTWARE-1.0).
- Os avisos e a atribuição do projeto upstream são preservados.
- O código original deste repositório é licenciado separadamente sob MIT; a
  licença do Work upstream não é alterada.
- A imagem base é referenciada por versão e digest, sem `:latest`.
- O uso pretendido é a integração com a Alexa, uma plataforma da Amazon.

## 4. Componentes de terceiros na imagem upstream

A imagem upstream inclui, entre outros:

- o **ASK CLI** e bibliotecas do **Alexa Skills Kit** da Amazon;
- o **ask-sdk** e dependências Python;
- Node.js e dependências npm;
- bibliotecas de sistema da imagem Ubuntu.

Esses componentes têm suas próprias licenças e avisos, definidos pelos
respectivos projetos e pela imagem upstream. Consulte o repositório upstream e
os metadados da imagem para a lista completa. Este repositório não relicencia
esses componentes.

## 5. Music Assistant

O **Music Assistant** é um projeto separado e não está incluído neste
repositório nem na imagem do add-on. O add-on apenas se comunica com um servidor
Music Assistant já instalado pelo usuário. Consulte o repositório do Music
Assistant para os termos de licença aplicáveis.

## 6. Marcas registradas

Amazon, Alexa, Amazon Web Services, AWS e nomes relacionados são marcas da
Amazon.com, Inc. ou de suas afiliadas. Music Assistant e nomes relacionados
pertencem aos seus respectivos titulares. Este projeto não é afiliado,
endossado ou patrocinado pela Amazon.com, Inc., pela Music Assistant ou por
qualquer um de seus afiliados.

O uso desses nomes é apenas descritivo, para identificar os serviços e
plataformas com os quais o projeto é compatível.

## 7. Se você redistribuir este add-on

Se você publicar uma imagem ou um fork que inclua o Work upstream:

1. mantenha o texto completo da ASL 1.0;
2. preserve os avisos de copyright, patente, marca e atribuição;
3. não aplique termos que removam a limitação de uso da Seção 3.3;
4. identifique claramente quais partes são suas e quais vêm do upstream;
5. revise as licenças dos componentes de terceiros incluídos na imagem.

## 8. English summary

The original code in this repository is MIT-licensed. The frontend panel bundles
Lit 3.3.3 under the BSD 3-Clause License; the full notice is in section 2 and in
the generated bundle. The upstream base image
(`ghcr.io/alams154/music-assistant-skill`) contains software licensed under the
**Amazon Software License 1.0**, a source-available license with a field-of-use
restriction. It is not an OSI-approved open-source license.

If you redistribute the upstream Work or a derivative work, you must:

- distribute it under the ASL 1.0;
- include a complete copy of the license;
- retain all copyright, patent, trademark, and attribution notices;
- keep the Section 3.3 use limitation (the Work may only be used with Amazon
  services, platforms, or applications);
- identify any of your own terms and the specific derivative works they cover.

The full license text is in
[`LICENSE-AMAZON-SOFTWARE-1.0`](LICENSE-AMAZON-SOFTWARE-1.0). This notice is
informational and is not legal advice. If you are unsure about your
obligations, consult a qualified attorney.

Amazon, Alexa, AWS, and related names are trademarks of Amazon.com, Inc. or its
affiliates. This project is not affiliated with, endorsed by, or sponsored by
Amazon or Music Assistant.
