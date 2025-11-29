# dbdjs-bdfd-panel
Painel BDFD feito em python pra uso simplificado e rápido.


INSTALAÇÂO DBD.JS (BDFD)

# INSTALAÇÃO DBD.JS (SEU BOT)

instale as dependências com:
```
npm init -y
```
depois:
```
npm install -g dbd.js
```

# INSTALAÇÃO PYTHON (Windows/Linux/Mac?)

INSTALE O PYTHON SE NÂO TIVER
CLIQUE AQUI: [Download](https://www.python.org/downloads/release/python-3108/)


Instale as depend~encias do python:
```
pip install flask
```





# ↓↓↓ ↓↓↓ ↓↓↓ ↓↓↓






# INSTALAÇÃO VIA TERMUX (APROXIMADAMENTE 2GB):

> PERMISSÃO DE ARMAZENAMENTO:
```
termux-setup-storage
```

> CRIA UMA PASTA CHAMADA (dbdjs-bdfd-panel), EM SUA PASTA DOWNLOADS:
```
mkdir storage/downloads/dbdjs-bdfd-panel
```

> ENTRA NA PASTA:
```
cd storage/downloads/dbdjs-bdfd-panel
```

> INSTALE O NODEJS (NECESSÁRIO PARA USAR O BOT):
```
pkg install nodejs -y
```
> OU:
```
pkg install nodejs-lts
```

> INSTALE O GIT (OPCIONAL: SERVE PARA BAIXAR O PAINEL VIA CURL):
```
pkg install git -y
```

> ATUALIZE OS PACOTES PARA EVITAR BUGS:
```
pkg update && pkg upgrade -y
```

> COPIAR O PROJETO (BAIXAR PARA PASTA QUE VOCÊ ESCOLHEEU):
```
git clone https://github.com/Vixys54/dbdjs-bdfd-panel
```

> EXTRAÇÃO (EXPLICAÇÃO)

• Extraia o arquivo ZIP usando o Zarchiver da Playstore ou instale para extrair (se baixar compactado em zip):
```
pkg install wget unzip
```

use para extrair:
```
wget https://github.com/Vixys54/dbdjs-bdfd-panel/archive/refs/heads/main.zip -O dbdjs-bdfd-panel.zip && unzip dbdjs-bdfd-panel.zip && rm dbdjs-bdfd-panel.zip && cd dbdjs-bdfd-panel-main
```

• ls (ver pastas e arquivos), cd (entrar em pastas).
• arquivos .bat não são necessários no termux, você pode apagar, são apenas executáveis que funciona no windows.
• se por acaso durante as instalações aparecer [y/n] escreva apenas "y" para "sim" para instalar os pacotes e dependências.

> INSTALE O PYTHON:
```
pkg install python -y
```

> INSTALE AS DEPENDÊNCIAS: 
```
pip install flask gunicorn python-dotenv markupsafe
```

> INSTALE O DBD.JS:
```
npm install dbd.js
```

> EXECUTE O PAINEL:
```
python servidor.py
```

# ↑↑↑ ↑↑↑ ↑↑↑
> ANTES DE LIGAR A BOT NO PAINEL, CONFIGURE O .ENV:


|
|
Chave (ID do seu bot):
```
BOT_ID
```
Valor:
```
ID DO SEU BOT #Opcional, pega no Deceloper Portal.
```
|
|
Chave:
```
BOT_TOKEN
```
Valor:
```
TOKEN DO SEU BOT (OBRIGATÓRIO PRA FUNCIONAR)
```
|
|
Chave:
```
OWNER_ID
```
Valor:
```
SEU ID DO DISCORD
```

= fim =

