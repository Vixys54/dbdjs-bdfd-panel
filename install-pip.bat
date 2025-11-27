@echo off
title Instalador de Dependencias Python
echo ========================================
echo  AVISO: Execute este arquivo como Administrador!
echo  (Clique com o botao direito nele e selecione "Executar como administrador")
echo ========================================
echo.

echo  Verificando se o Python (e pip) esta instalado...
where pip >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [ERRO] Python ou pip nao foram encontrados no seu sistema.
    echo  Por favor, instale o Python a partir do site oficial:
    echo  https://www.python.org/downloads/
    echo.
    echo  IMPORTANTE: Durante a instalacao, na primeira tela, MARQUE a opcao:
    echo  [X] Add Python to PATH
    echo.
    pause
    exit /b
)

echo.
echo  [OK] Python encontrado! Versao:
python --version
echo Versao do pip:
pip --version
echo.
echo  Instalando as dependencias do servidor Python...
echo ----------------------------------------
pip install requests flask
echo ----------------------------------------
echo.
echo  [SUCESSO] Dependencias do Python instaladas!
echo.
pause