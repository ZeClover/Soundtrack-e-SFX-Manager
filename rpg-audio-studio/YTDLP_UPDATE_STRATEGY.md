# Estratégia de atualização do yt-dlp (Etapa 6, item 63)

## Decisão

O RPG Audio Studio **não tem um atualizador do yt-dlp dentro do app**.

Um app empacotado com PyInstaller roda a partir de uma pasta extraída/
congelada, sem `pip` disponível, sem console visível (`pythonw`/`--noconsole`)
e frequentemente sem permissão de escrita na própria pasta de instalação.
Um "auto-update" que tentasse rodar `pip install --upgrade yt-dlp` (ou
`yt-dlp -U`, que baixa e substitui o próprio binário) nesse ambiente é
frágil por natureza:

- pode não ter onde escrever (pasta protegida, ex. `C:\Program Files`);
- pode não ter conectividade com o PyPI/GitHub no momento;
- pode baixar uma versão incompatível com o resto do app sem aviso;
- silenciosamente atualizado, o comportamento do Downloader mudaria sem o
  usuário nunca ter "instalado uma versão nova" de verdade — dificultando
  suporte e reprodução de bugs.

Por isso a estratégia escolhida é a mais simples e previsível das três
listadas na especificação da Etapa 6:

> **yt-dlp embutido, atualizado junto com os releases do app.**

## Como funciona na prática

1. `requirements.txt` fixa um piso de versão (`yt-dlp>=2024.1`) — não uma
   versão exata — porque sites de vídeo mudam com frequência e o yt-dlp
   lança correções de extração quase toda semana; travar uma versão exata
   por muito tempo tende a "quebrar" o Downloader sozinho, sem nenhuma
   mudança de código do RPG Audio Studio.
2. Quando o app é empacotado (`BUILD_WINDOWS.bat` → PyInstaller), a versão
   do `yt-dlp` que entra no executável é a que estiver instalada no
   ambiente virtual de build **naquele momento** — ou seja, o yt-dlp "vem
   junto" com cada release do app, como um bloco só.
3. Não existe nenhum código no app (verificado nesta auditoria) que chame
   `pip`, `yt-dlp -U`, ou qualquer endpoint de atualização em tempo de
   execução. O Downloader só usa a biblioteca `yt_dlp` já importada no
   processo.

## Como o mantenedor atualiza o yt-dlp

Antes de gerar um novo release:

```bash
pip install --upgrade yt-dlp
pip freeze | grep yt-dlp   # confirma a versão nova
# rodar os testes do módulo Downloader normalmente
python -m pytest rpg-audio-studio/tests -k downloader
```

Depois, seguir o build normal (`BUILD_WINDOWS.bat`) — a versão nova do
yt-dlp já sai embutida no `.exe` gerado. A versão usada nesta Etapa 6 foi a
`2026.08.19`.

## Como o usuário final "atualiza"

Baixando uma versão mais nova do RPG Audio Studio (novo ZIP em
`release/`), não através de nenhuma ação dentro do app. Isso é consistente
com o resto do produto: é um programa portátil, sem instalador com
auto-update, então "atualizar o programa" e "atualizar o yt-dlp embutido"
são a mesma ação — trocar de release.

## Caminho futuro (não implementado agora)

Se no futuro isso incomodar (por exemplo, um site específico parar de
funcionar entre releases), a evolução natural — fora do escopo desta
Etapa 6 — seria um **atualizador dedicado e opcional**: uma tela em
Configurações que baixa só o binário standalone do yt-dlp (não via pip)
para uma pasta gravável em `%LOCALAPPDATA%`, com o app preferindo esse
binário sobre o embutido quando presente. Isso evita os problemas de
permissão de pasta e não depende de `pip` estar disponível — mas é uma
funcionalidade nova, não uma correção, e por isso fica documentada aqui em
vez de implementada às pressas dentro da Etapa 6.
