# Configuração persistente do agent-browser (guia temporário)

> **Status:** temporário. Remova este arquivo depois que a instalação persistente tiver passado
> pelo teste de aceite ao final do guia.

Este guia substitui a instalação isolada feita em `/tmp` durante a validação visual de 2026-09-16.
Ele não é requisito de runtime do QA Method: serve apenas para automação e inspeção do frontend.

## Ambiente já verificado

- Ubuntu 24.04;
- Node.js 24.20.0 administrado pelo mise;
- npm 11.19.0;
- `agent-browser` 0.37.1;
- Chrome for Testing 153.0.8010.47.

## Opção recomendada: instalação no host

Execute estes comandos em um terminal comum do host, fora de um sandbox do agente. Não use `sudo`
no comando do npm: o prefixo global do Node instalado pelo mise pertence ao usuário.

```bash
node --version
npm --version
npm prefix -g
test -w "$(npm prefix -g)/lib/node_modules" && echo "prefixo npm gravável"

npm install -g agent-browser
agent-browser --version
agent-browser install --with-deps
agent-browser doctor
```

O `install --with-deps` baixa o Chrome for Testing e solicita elevação apenas para as bibliotecas
Linux necessárias. Se o Chrome já estiver instalado no sistema, o `agent-browser` normalmente o
detecta sem configuração adicional.

Se o `npm install -g` falhar por permissão, confirme primeiro se o shell está usando o Node do mise:

```bash
mise which node
npm prefix -g
ls -ld "$(npm prefix -g)" "$(npm prefix -g)/lib/node_modules"
```

O prefixo esperado neste computador é
`/home/unicheld/.local/share/mise/installs/node/24.20.0`. Corrija a propriedade desse diretório no
host somente se ela não pertencer ao usuário; não altere o prefixo do npm para `/usr`.

## Usar um Chrome já instalado

Localize um navegador compatível:

```bash
command -v google-chrome
command -v google-chrome-stable
command -v chromium
```

Se a detecção automática não funcionar, informe o executável explicitamente. Use apenas o caminho
que existir no computador:

```bash
export AGENT_BROWSER_EXECUTABLE_PATH=/usr/bin/google-chrome
agent-browser doctor
```

Depois do teste, torne a variável persistente no arquivo de inicialização do shell, por exemplo
`~/.zshrc`. Essa variável não é necessária quando `agent-browser install` consegue administrar o
Chrome sozinho.

## Alternativa sem acesso root: instalação persistente no workspace

Use esta alternativa apenas quando não for possível instalar bibliotecas no sistema. Os binários
ficarão locais, mas fora do Git. Ela reproduz a configuração que funcionou em `/tmp`, usando um
diretório persistente e gravável do projeto.

Na raiz do repositório:

```bash
agent_browser_root="$PWD/.codex/agent-browser"
mkdir -p "$agent_browser_root/npm" \
  "$agent_browser_root/chrome" \
  "$agent_browser_root/libs" \
  "$agent_browser_root/packages" \
  "$agent_browser_root/xdg/config" \
  "$agent_browser_root/xdg/data" \
  "$agent_browser_root/xdg/cache" \
  "$agent_browser_root/xdg/runtime"
chmod 700 "$agent_browser_root/xdg/runtime"

npm install --prefix "$agent_browser_root/npm" agent-browser@0.37.1
```

Baixe a versão de Chrome for Testing já validada:

```bash
curl --fail --location \
  --output "$agent_browser_root/packages/chrome-linux64.zip" \
  https://storage.googleapis.com/chrome-for-testing-public/153.0.8010.47/linux64/chrome-linux64.zip
unzip "$agent_browser_root/packages/chrome-linux64.zip" -d "$agent_browser_root/chrome"
```

No Ubuntu 24.04, as duas bibliotecas ausentes neste ambiente podem ser extraídas sem privilégios de
administrador:

```bash
cd "$agent_browser_root/packages"
apt download libnss3 libasound2t64
for package in ./*.deb; do
  dpkg-deb -x "$package" "$agent_browser_root/libs"
done
cd -
```

Crie o wrapper `~/.local/bin/agent-browser` com o conteúdo abaixo, ajustando apenas o caminho do
repositório se ele mudar. Esse diretório já faz parte do `PATH` desta máquina. As variáveis XDG
ficam restritas ao processo do `agent-browser` e não alteram a configuração dos outros programas:

```bash
#!/usr/bin/env zsh
root=/home/unicheld/projects/personal/tcc-qamethod-snpg/.codex/agent-browser
export XDG_CONFIG_HOME="$root/xdg/config"
export XDG_DATA_HOME="$root/xdg/data"
export XDG_CACHE_HOME="$root/xdg/cache"
export XDG_RUNTIME_DIR="$root/xdg/runtime"
export AGENT_BROWSER_EXECUTABLE_PATH="$root/chrome/chrome-linux64/chrome"
export LD_LIBRARY_PATH="$root/libs/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec "$root/npm/node_modules/.bin/agent-browser" "$@"
```

Torne o wrapper executável e confirme que o shell o encontra:

```bash
chmod 755 ~/.local/bin/agent-browser
command -v agent-browser
agent-browser --version
```

Não redefina `HOME`. Para evitar que os binários locais apareçam no Git, acrescente esta entrada a
`.git/info/exclude`:

```text
/.codex/agent-browser/
```

Em ambientes Linux restritos, o Chrome também pode precisar destes argumentos. Use-os somente se o
`doctor` ou a abertura de uma página informar que o Chrome encerrou antes de criar a porta DevTools:

```bash
agent-browser --args "--no-sandbox --disable-dev-shm-usage" open https://example.com
```

Se o teste confirmar essa necessidade, acrescente esta linha ao wrapper antes do `exec` para que o
`doctor` e as execuções futuras recebam a mesma configuração:

```bash
export AGENT_BROWSER_ARGS="--no-sandbox,--disable-dev-shm-usage,--disable-crash-reporter,--noerrdialogs"
```

`--no-sandbox` reduz o isolamento do Chrome. Use essa opção apenas no ambiente já isolado e para
páginas confiáveis, como a aplicação local; prefira removê-la se o host permitir iniciar o sandbox
nativo do navegador.

## Teste de aceite

O teste abaixo deve retornar `Example Domain`. O uso de `batch` também funciona em executores que
encerram processos em segundo plano entre comandos:

```bash
agent-browser --session install-check batch --bail \
  "open https://example.com" \
  "wait --load networkidle" \
  "get title" \
  "screenshot --full" \
  "close"
agent-browser doctor
```

Depois, valide o QA Method com a stack local ativa:

```bash
agent-browser --session qa-method batch --bail \
  "open http://127.0.0.1:5173/insights" \
  "wait --load networkidle" \
  "snapshot -i" \
  "errors" \
  "close"
```

A configuração está concluída quando:

1. `agent-browser doctor` não relata falha de lançamento do Chrome;
2. o título `Example Domain` é retornado;
3. a rota `/insights` produz um snapshot com os controles da tela;
4. `agent-browser errors` não apresenta erro da aplicação;
5. nenhum comando depende de `/tmp`.

Após esses cinco itens, remova este guia temporário. A instalação local do workspace, se usada,
deve permanecer ignorada e nunca ser versionada.
