@echo off
title Instalador de Dependencias NPM
echo ========================================
echo  Verificando se o Node.js (e npm) esta instalado...
echo ========================================

:: O comando 'where' procura por um executavel. Se nao encontrar, retorna um erro.
where npm >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [ERRO] Node.js ou npm nao foram encontrados no seu sistema.
    echo  Por favor, instale o Node.js a partir do site oficial:
    echo  https://nodejs.org/
    echo.
    echo  Baixe a versao "LTS" (Long Term Support) para maior compatibilidade.
    echo.
    pause
    exit /b
)

echo.
echo  [OK] Node.js encontrado! Versao:
npm --version
echo.
echo  Instalando as dependencias do projeto (isso pode levar alguns minutos)...
echo ----------------------------------------
npm install
echo ----------------------------------------
echo.
echo  [SUCESSO] Dependencias do Node.js instaladas!
echo.
pause