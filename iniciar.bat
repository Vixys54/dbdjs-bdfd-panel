@echo off
title Iniciador do Servidor Python
echo Iniciando o servidor Python em uma nova janela...
echo A nova janela se chamara "Servidor Python - Styllena".
echo.

:: O comando 'start' abre uma nova janela. O primeiro parametro e o titulo da janela.
:: 'cmd /k' executa o comando e mantem a janela aberta (keep) para ver os logs.
start "Servidor Python - Styllena" cmd /k python servidor.py

echo.
echo  [OK] Servidor Python iniciado!
echo  Voce pode fechar esta janela. A janela do servidor permanecera aberta.
echo.
pause