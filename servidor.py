import os
import json
import subprocess
import threading
import re
import shutil
import logging
from flask import Flask, request, render_template_string, jsonify
from markupsafe import escape

# --- CONFIGURAÇÃO ---
BOT_PATH = os.path.abspath('.')
BOT_FILE_NAME = 'index.js'
BOT_DISPLAY_NAME = "Styllena"

# --- Paths Derivados ---
BOT_FILE_PATH = os.path.join(BOT_PATH, BOT_FILE_NAME)
COMMANDS_PATH = os.path.join(BOT_PATH, 'commands')
VARIABLES_PATH = os.path.join(BOT_PATH, 'variables', 'defaults.js')
ENV_PATH = os.path.join(BOT_PATH, '.env')
STATUS_CONFIG_PATH = os.path.join(BOT_PATH, 'status_config.json')

# Configure o logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# --- Variáveis Globais de Controle do Bot ---
bot_process = None
bot_logs = []
log_lock = threading.Lock()
is_bot_process_running = False
is_bot_truly_online = False
bot_status_message = "Desligado"

# --- Função Auxiliar para Capturar Logs e Verificar Status ---
def stream_logs(process):
    """Lê stdout/stderr em uma thread separada para não bloquear."""
    global bot_logs, is_bot_truly_online, bot_status_message

    while True:
        output = process.stdout.readline()
        error_output = process.stderr.readline()

        if output == b'' and error_output == b'' and process.poll() is not None:
            break

        if output:
            decoded_line = output.decode('utf-8', errors='ignore').strip()
            with log_lock:
                bot_logs.append(decoded_line)
                if "PAINEL_STATUS:BOT_ONLINE_READY" in decoded_line:
                    is_bot_truly_online = True
                    bot_status_message = f"{BOT_DISPLAY_NAME} online"
                elif "Invalid Token" in decoded_line or "DISALLOWED_INTENTS" in decoded_line:
                    is_bot_truly_online = False
                    bot_status_message = "Erro de Conexão (Verifique Token/Intents)"

        if error_output:
            decoded_line = f"ERROR: {error_output.decode('utf-8', errors='ignore').strip()}"
            with log_lock:
                bot_logs.append(decoded_line)
                is_bot_truly_online = False
                bot_status_message = "Erro de Execução (Verifique logs)"
    
    is_bot_process_running = False
    if not is_bot_truly_online:
        bot_status_message = "Processo finalizado."

# HTML Template completo e funcional
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Painel de Controle - Styllena Bot</title>
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; 
            background-color: #1e1e1e; 
            color: #d4d4d4; 
            margin: 0; 
            padding: 20px; 
        }
        .container { 
            max-width: 1200px; 
            margin: auto; 
            background-color: #252526; 
            border-radius: 8px; 
            box-shadow: 0 4px 12px rgba(0,0,0,0.5); 
            overflow: hidden; 
        }
        .header { 
            background-color: #007acc; 
            color: white; 
            padding: 15px 20px; 
            text-align: center; 
        }
        .tabs { 
            display: flex; 
            background-color: #333; 
            border-bottom: 2px solid #007acc; 
        }
        .tab-button { 
            flex: 1; 
            padding: 15px; 
            background: none; 
            border: none; 
            color: #d4d4d4; 
            cursor: pointer; 
            font-size: 16px; 
            transition: background-color 0.3s; 
        }
        .tab-button:hover { 
            background-color: #444; 
        }
        .tab-button.active { 
            background-color: #007acc; 
            color: white; 
        }
        .tab-content { 
            display: none; 
            padding: 20px; 
        }
        .tab-content.active { 
            display: block; 
        }
        .card { 
            background-color: #2d2d2d; 
            border-radius: 6px; 
            padding: 20px; 
            margin-bottom: 20px; 
            border: 1px solid #444; 
        }
        .card h3 { 
            margin-top: 0; 
            color: #007acc; 
        }
        button { 
            background-color: #007acc; 
            color: white; 
            border: none; 
            padding: 10px 15px; 
            border-radius: 4px; 
            cursor: pointer; 
            font-size: 14px; 
            margin: 5px; 
        }
        button:hover { 
            background-color: #005f9e; 
        }
        button.danger { 
            background-color: #d9534f; 
        }
        button.danger:hover { 
            background-color: #c9302c; 
        }
        input, textarea, select { 
            width: 100%; 
            padding: 10px; 
            border-radius: 4px; 
            border: 1px solid #555; 
            background-color: #3c3c3c; 
            color: #d4d4d4; 
            box-sizing: border-box; 
        }
        textarea { 
            font-family: "Consolas", "Monaco", monospace; 
            min-height: 200px; 
            resize: vertical; 
        }
        .file-list { 
            list-style: none; 
            padding: 0; 
            max-height: 400px; 
            overflow-y: auto;
        }
        .file-list li { 
            background-color: #3c3c3c; 
            padding: 10px; 
            margin-bottom: 5px; 
            border-radius: 4px; 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
        }
        .file-list a { 
            color: #61dafb; 
            text-decoration: none; 
            cursor: pointer; 
        }
        .file-list a:hover { 
            text-decoration: underline; 
        }
        .log-container { 
            background-color: #0c0c0c; 
            color: #00ff00; 
            font-family: "Consolas", "Monaco", monospace; 
            padding: 15px; 
            border-radius: 4px; 
            height: 300px; 
            overflow-y: scroll; 
            white-space: pre-wrap; 
        }
        .status-indicator { 
            display: inline-block; 
            width: 12px; 
            height: 12px; 
            border-radius: 50%; 
            margin-right: 8px; 
        }
        .status-online { 
            background-color: #28a745; 
        }
        .status-offline { 
            background-color: #dc3545; 
        }
        .status-starting { 
            background-color: #f0ad4e; 
        }
        .env-entry { 
            margin-bottom: 15px; 
        }
        .env-entry label { 
            display: block; 
            margin-bottom: 5px; 
        }
        .env-input-wrapper { 
            position: relative; 
        }
        .env-input-wrapper input { 
            padding-right: 40px; 
        }
        .env-toggle { 
            position: absolute; 
            right: 10px; 
            top: 50%; 
            transform: translateY(-50%); 
            background: none; 
            border: none; 
            color: #d4d4d4; 
            cursor: pointer; 
        }
        
        .status-list {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        
        .status-card {
            background-color: #3c3c3c;
            border-radius: 6px;
            padding: 15px;
            border: 1px solid #555;
        }
        
        .status-card .status-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        
        .status-card .status-actions {
            display: flex;
            gap: 5px;
        }
        
        .form-group {
            margin-bottom: 15px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 5px;
            color: #d4d4d4;
        }
        
        .variables-list {
            display: flex;
            flex-direction: column;
            gap: 15px;
            margin: 15px 0;
        }

        .variable-card {
            background-color: #3c3c3c;
            border-radius: 6px;
            padding: 15px;
            border: 1px solid #555;
            display: flex;
            gap: 10px;
            align-items: center;
        }

        .variable-card input {
            flex: 1;
            margin: 0;
            padding: 8px;
            background-color: #2d2d2d;
            border: 1px solid #555;
            border-radius: 4px;
            color: #d4d4d4;
        }

        .variable-name {
            min-width: 150px;
        }

        .variable-value {
            flex: 2;
        }

        .remove-variable {
            background-color: #d9534f;
            color: white;
            border: none;
            padding: 8px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            width: 36px;
            height: 36px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .remove-variable:hover {
            background-color: #c9302c;
        }

        .code-editor {
    font-family: "Consolas", "Monaco", "Courier New", monospace;
    min-height: 300px;
    border: 1px solid #555;
    background-color: #1e1e1e;
    color: #83ff83ce;
    padding: 15px;
    white-space: pre-wrap;
    overflow-wrap: break-word;
    border-radius: 6px;
    line-height: 1.5;
    caret-color: #b900b3;  /* Cursor roxo/lilás */
}

        .code-editor .token-flow {
    color: #da70d6;  /* Lilás/Magenta puro */
}

.code-editor .token-command {
    color: #87ceeb;  /* Azul claro */
}

.code-editor .token-symbol {
    color: #ffa500;  /* Laranja */
}

.code-editor .token-link {
    color: #1e90ff;
    background-color: rgba(30, 144, 255, 0.2);
    border-radius: 3px;
    padding: 0 2px;
}

.code-editor .command-closed {
    background-color: rgba(0, 0, 0, 0.3);
    border-radius: 3px;
    padding: 0 2px;
}

.code-editor .command-open {
    background-color: rgba(255, 0, 0, 0.3);
    border-radius: 3px;
    padding: 0 2px;
}
    </style>
</head>
<body>
    <div class="container">
        <div class="header"><h1>Painel de Controle - Styllena Bot</h1></div>
        <div class="tabs">
            <button class="tab-button active" onclick="showTab('dashboard')">Principal</button>
            <button class="tab-button" onclick="showTab('comandos')">Comandos</button>
            <button class="tab-button" onclick="showTab('variaveis')">Variáveis</button>
            <button class="tab-button" onclick="showTab('status')">Status</button>
            <button class="tab-button" onclick="showTab('configuracoes')">Configurações</button>
        </div>

        <div id="dashboard" class="tab-content active">
            <div class="card">
                <h3>Controle do Bot</h3>
                <span id="bot-status-indicator" class="status-indicator status-offline"></span>
                <span id="bot-status-text">Desligado</span>
                <div style="margin-top: 15px;">
                    <button onclick="controlBot('start')">Ligar Bot</button>
                    <button class="danger" onclick="controlBot('stop')">Desligar Bot</button>
                    <button onclick="controlBot('restart')">Reiniciar Bot</button>
                </div>
            </div>
            <div class="card">
                <h3>Logs do Bot</h3>
                <div id="bot-logs" class="log-container">Aguardando logs...</div>
            </div>
        </div>

        <div id="comandos" class="tab-content">
            <div class="card">
                <h3>Gerenciar Comandos</h3>
                <button onclick="showNewCommandForm()">+ Novo Comando</button>
                <ul id="command-list" class="file-list"></ul>
            </div>
            <div id="command-editor" class="card" style="display: none;">
                <h3 id="editor-title">Novo Comando</h3>
                <input type="text" id="command-name" placeholder="Nome do comando (ex: trabalhar)">
                <div id="command-code" class="code-editor" contenteditable="true" spellcheck="false" placeholder="Digite o código do comando aqui..."></div>
                <div style="margin-top: 15px;">
                    <button onclick="saveCommand()">Salvar</button>
                    <button class="danger" onclick="deleteCommand()">Apagar</button>
                    <button onclick="cancelEdit()">Cancelar</button>
                </div>
            </div>
        </div>

        <div id="variaveis" class="tab-content">
            <div class="card">
                <h3>Variáveis Globais</h3>
                <button onclick="addVariableCard()">+ Nova Variável</button>
                <div id="variables-list" class="variables-list"></div>
                <button onclick="saveVariables()">Salvar Variáveis</button>
            </div>
        </div>
        
        <div id="status" class="tab-content">
            <div class="card">
                <h3>Status do Bot</h3>
                <button onclick="showNewStatusForm()">+ Novo Status</button>
                <div id="status-list" class="status-list"></div>
            </div>
            <div id="status-editor" class="card" style="display: none;">
                <h3 id="status-editor-title">Novo Status</h3>
                <div class="form-group">
                    <label>Texto:</label>
                    <input type="text" id="status-text" placeholder="Ex: Jogando...">
                </div>
                <div class="form-group">
                    <label>Tipo:</label>
                    <select id="status-type">
                        <option value="PLAYING">PLAYING</option>
                        <option value="WATCHING">WATCHING</option>
                        <option value="LISTENING">LISTENING</option>
                        <option value="STREAMING">STREAMING</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Status:</label>
                    <select id="status-status">
                        <option value="online">Online</option>
                        <option value="idle">Idle</option>
                        <option value="dnd">DND</option>
                    </select>
                </div>
                <div class="form-group" id="status-url-group" style="display: none;">
                    <label>URL (apenas STREAMING):</label>
                    <input type="text" id="status-url" placeholder="https://twitch.tv/...">
                </div>
                <div style="margin-top: 15px;">
                    <button onclick="saveStatus()">Salvar</button>
                    <button class="danger" onclick="deleteStatus()">Apagar</button>
                    <button onclick="cancelStatusEdit()">Cancelar</button>
                </div>
            </div>
        </div>

        <div id="configuracoes" class="tab-content">
            <div class="card">
                <h3>Configurações (.env)</h3>
                <div id="env-form"></div>
                <button onclick="addEnvEntry()">+ Adicionar Entrada</button>
                <button onclick="saveEnv()">Salvar .env</button>
            </div>
        </div>
    </div>

    <script>
        let currentEditingFile = null;
        let currentEditingStatusIndex = -1;

        function showTab(tabName) {
            // Esconder todas as abas
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Remover active de todos os botões
            document.querySelectorAll('.tab-button').forEach(button => {
                button.classList.remove('active');
            });
            
            // Mostrar aba selecionada
            document.getElementById(tabName).classList.add('active');
            
            // Ativar botão clicado
            event.target.classList.add('active');
            
            // Carregar conteúdo específico da aba
            if (tabName === 'comandos') {
                loadCommands();
                initializeCodeEditor();
            } else if (tabName === 'variaveis') {
                loadVariables();
            } else if (tabName === 'status') {
                loadStatus();
            } else if (tabName === 'configuracoes') {
                loadEnv();
            }
        }
        
        // Controle do Bot
        async function controlBot(action) {
            try {
                const response = await fetch('/api/bot/' + action, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                const data = await response.json();
                if (data.success) {
                    alert('Ação executada com sucesso!');
                } else {
                    alert('Erro: ' + data.message);
                }
            } catch (error) {
                alert('Erro: ' + error.message);
            }
        }
        
        // Atualizar status e logs
        async function updateStatus() {
            try {
                const statusResponse = await fetch('/api/bot/status');
                const statusData = await statusResponse.json();
                
                const indicator = document.getElementById('bot-status-indicator');
                const text = document.getElementById('bot-status-text');
                
                indicator.className = 'status-indicator';
                if (statusData.status === 'online') {
                    indicator.classList.add('status-online');
                } else if (statusData.status === 'starting') {
                    indicator.classList.add('status-starting');
                } else {
                    indicator.classList.add('status-offline');
                }
                
                text.textContent = statusData.message;
                
                // Atualizar logs
                const logsResponse = await fetch('/api/logs');
                const logsData = await logsResponse.json();
                document.getElementById('bot-logs').textContent = logsData.logs.join('\\n');
            } catch (error) {
                console.error('Erro ao atualizar status:', error);
            }
        }
        
        // Comandos
        async function loadCommands() {
            try {
                const response = await fetch('/api/commands');
                const commands = await response.json();
                const list = document.getElementById('command-list');
                list.innerHTML = '';
                
                commands.forEach(cmd => {
                    const li = document.createElement('li');
                    li.innerHTML = `<span>${cmd}</span> <a onclick="editCommand('${cmd}')">Editar</a>`;
                    list.appendChild(li);
                });
            } catch (error) {
                console.error('Erro ao carregar comandos:', error);
            }
        }
        
        function showNewCommandForm() {
            currentEditingFile = null;
            document.getElementById('editor-title').textContent = 'Novo Comando';
            document.getElementById('command-name').value = '';
            
            const editor = document.getElementById('command-code');
            editor.textContent = '';
            editor.innerHTML = '';
            
            document.getElementById('command-editor').style.display = 'block';
            
            setTimeout(() => {
                applySyntaxHighlighting(editor);
                editor.focus();
            }, 100);
        }
        
        async function editCommand(filename) {
            try {
                currentEditingFile = filename;
                document.getElementById('editor-title').textContent = 'Editar ' + filename;
                
                const response = await fetch('/api/command/' + encodeURIComponent(filename));
                const data = await response.json();
                
                document.getElementById('command-name').value = data.name || filename.replace('.js', '');
                
                const editor = document.getElementById('command-code');
                editor.textContent = data.code || '';
                
                document.getElementById('command-editor').style.display = 'block';
                
                setTimeout(() => applySyntaxHighlighting(editor), 100);
            } catch (error) {
                alert('Erro ao carregar comando: ' + error.message);
            }
        }
        
        async function saveCommand() {
            try {
                const name = document.getElementById('command-name').value.trim();
                const editor = document.getElementById('command-code');
                const code = editor.textContent || editor.innerText;
                
                if (!name || !code) {
                    alert('Preencha nome e código do comando');
                    return;
                }
                
                const filename = currentEditingFile || (name + '.js');
                const response = await fetch('/api/command/' + encodeURIComponent(filename), {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ code: code })
                });
                
                const data = await response.json();
                if (data.success) {
                    alert('Comando salvo!');
                    cancelEdit();
                    loadCommands();
                } else {
                    alert('Erro: ' + data.message);
                }
            } catch (error) {
                alert('Erro ao salvar: ' + error.message);
            }
        }
        
        async function deleteCommand() {
            if (!currentEditingFile || !confirm('Apagar este comando?')) return;
            
            try {
                const response = await fetch('/api/command/' + encodeURIComponent(currentEditingFile), {
                    method: 'DELETE'
                });
                
                const data = await response.json();
                if (data.success) {
                    alert('Comando apagado!');
                    cancelEdit();
                    loadCommands();
                } else {
                    alert('Erro: ' + data.message);
                }
            } catch (error) {
                alert('Erro ao apagar: ' + error.message);
            }
        }
        
        function cancelEdit() {
            document.getElementById('command-editor').style.display = 'none';
            currentEditingFile = null;
        }
        
        // Syntax Highlighting
        function applySyntaxHighlighting(editor) {
    // Salvar posição do cursor de forma mais confiável
    const selection = window.getSelection();
    let cursorOffset = 0;
    
    if (selection.rangeCount > 0 && editor.contains(selection.anchorNode)) {
        // Contar caracteres desde o início até o cursor
        const range = selection.getRangeAt(0).cloneRange();
        range.selectNodeContents(editor);
        range.setEnd(selection.getRangeAt(0).endContainer, selection.getRangeAt(0).endOffset);
        cursorOffset = range.toString().length;
    }
    
    const text = editor.textContent || '';
    let html = text;
    
    // Escape HTML chars first
    html = html
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
    
    // 1. URLs
    html = html.replace(/(https?:\/\/[^\s]+)/g, '<span class="token-link">$1</span>');
    
    // 2. Flow Commands (ordem: maior pra menor)
    html = html.replace(/\$endif(?![a-zA-Z0-9_])/g, '<span class="token-flow">$endif</span>');
    html = html.replace(/\$endfor(?![a-zA-Z0-9_])/g, '<span class="token-flow">$endfor</span>');
    html = html.replace(/\$endwhile(?![a-zA-Z0-9_])/g, '<span class="token-flow">$endwhile</span>');
    html = html.replace(/\$elseif(?![a-zA-Z0-9_])/g, '<span class="token-flow">$elseif</span>');
    html = html.replace(/\$else(?![a-zA-Z0-9_])/g, '<span class="token-flow">$else</span>');
    html = html.replace(/\$if(?![a-zA-Z0-9_])/g, '<span class="token-flow">$if</span>');
    html = html.replace(/\$for(?![a-zA-Z0-9_])/g, '<span class="token-flow">$for</span>');
    html = html.replace(/\$while(?![a-zA-Z0-9_])/g, '<span class="token-flow">$while</span>');
    
    // 3. Outros comandos $
    html = html.replace(/\$[a-zA-Z_][a-zA-Z0-9_]*/g, function(match) {
        const flowCommands = ['$if', '$elseif', '$else', '$endif', '$for', '$endfor', '$while', '$endwhile'];
        if (!flowCommands.includes(match) && !match.includes('span')) {
            return '<span class="token-command">' + match + '</span>';
        }
        return match;
    });
    
    // 4. Comandos com colchetes FECHADOS (colocar marcador temporário)
    html = html.replace(/\[([^\[\]]*)\]/g, '<<<CLOSED>>>[$1]<<<\/CLOSED>>>');
    
    // 5. Comandos com colchetes ABERTOS (colocar marcador temporário)
    html = html.replace(/\[([^\[\]]*?)$/gm, '<<<OPEN>>>[$1<<<\/OPEN>>>');
    
    // 6. Convertendo marcadores para spans
    html = html.replace(/<<<CLOSED>>>/g, '<span class="command-closed">');
    html = html.replace(/<<<\/CLOSED>>>/g, '</span>');
    html = html.replace(/<<<OPEN>>>/g, '<span class="command-open">');
    html = html.replace(/<<<\/OPEN>>>/g, '</span>');
    
    // 7. Apenas [ ] - SEM processar ;
    let parts = html.split(/<span[^>]*>.*?<\/span>/g);
    let spans = html.match(/<span[^>]*>.*?<\/span>/g) || [];
    
    for (let i = 0; i < parts.length; i++) {
        parts[i] = parts[i].replace(/\[/g, '<span class="token-symbol">[</span>');
        parts[i] = parts[i].replace(/\]/g, '<span class="token-symbol">]</span>');
    }
    
    html = '';
    for (let i = 0; i < parts.length; i++) {
        html += parts[i];
        if (i < spans.length) {
            html += spans[i];
        }
    }
    
    editor.innerHTML = html;
    
    // Restaurar posição do cursor de forma mais confiável
    try {
        const range = document.createRange();
        let charCount = 0;
        let nodeStack = [editor];
        let node, foundStart = false;

        while (!foundStart && (node = nodeStack.pop())) {
            if (node.nodeType === Node.TEXT_NODE) {
                const nextCharCount = charCount + node.length;
                if (cursorOffset <= nextCharCount) {
                    range.setStart(node, cursorOffset - charCount);
                    foundStart = true;
                }
                charCount = nextCharCount;
            } else {
                let i = node.childNodes.length;
                while (i--) {
                    nodeStack.push(node.childNodes[i]);
                }
            }
        }

        range.collapse(true);
        selection.removeAllRanges();
        selection.addRange(range);
    } catch (e) {
        // Se falhar, apenas foca no editor
        editor.focus();
    }
}

        let highlightTimeout;
        function scheduleHighlight(editor) {
            clearTimeout(highlightTimeout);
            highlightTimeout = setTimeout(() => applySyntaxHighlighting(editor), 300);
        }

        function initializeCodeEditor() {
            const editor = document.getElementById('command-code');
            if (editor) {
                editor.addEventListener('input', () => scheduleHighlight(editor));
                editor.addEventListener('paste', (e) => {
                    e.preventDefault();
                    const text = e.clipboardData.getData('text/plain');
                    document.execCommand('insertText', false, text);
                    scheduleHighlight(editor);
                });
                
                // Aplicar highlight inicial
                applySyntaxHighlighting(editor);
            }
        }
        
        // Variáveis
        async function loadVariables() {
            try {
                const response = await fetch('/api/variables');
                const data = await response.json();
                const variablesList = document.getElementById('variables-list');
                variablesList.innerHTML = '';

                if (data.content && typeof data.content === 'object') {
                    const entries = Object.entries(data.content);
                    if (entries.length > 0) {
                        for (const [key, config] of entries) {
                            addVariableCard(key, config.default);
                        }
                    }
                }
            } catch (error) {
                console.error('Erro ao carregar variáveis:', error);
            }
        }

        function addVariableCard(name = '', value = '') {
            const variablesList = document.getElementById('variables-list');
            const card = document.createElement('div');
            card.className = 'variable-card';
            card.innerHTML = `
                <input type="text" class="variable-name" placeholder="Nome (ex: coins)" value="${name}">
                <input type="text" class="variable-value" placeholder="Valor (ex: 100)" value="${value}">
                <button class="remove-variable" onclick="this.parentElement.remove()">×</button>
            `;
            variablesList.appendChild(card);
        }

        async function saveVariables() {
            try {
                const cards = document.querySelectorAll('.variable-card');
                const variables = {};
                
                cards.forEach(card => {
                    const name = card.querySelector('.variable-name').value.trim();
                    const value = card.querySelector('.variable-value').value.trim();
                    
                    if (name) {
                        if (!isNaN(value) && value !== '') {
                            variables[name] = Number(value);
                        } else {
                            variables[name] = value;
                        }
                    }
                });
                
                const response = await fetch('/api/variables', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ content: variables })
                });
                
                const data = await response.json();
                if (data.success) {
                    alert('Variáveis salvas!');
                } else {
                    alert('Erro: ' + data.message);
                }
            } catch (error) {
                alert('Erro ao salvar: ' + error.message);
            }
        }
        
        // Status
        async function loadStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                const statusList = document.getElementById('status-list');
                statusList.innerHTML = '';
                
                let statuses = [];
                try {
                    statuses = JSON.parse(data.content);
                } catch (e) {
                    statuses = [];
                }
                
                statuses.forEach((status, index) => {
                    const card = document.createElement('div');
                    card.className = 'status-card';
                    card.innerHTML = `
                        <div class="status-header">
                            <strong>${status.text}</strong>
                            <div class="status-actions">
                                <button onclick="editStatus(${index})">Editar</button>
                                <button class="danger" onclick="deleteStatusConfirm(${index})">Excluir</button>
                            </div>
                        </div>
                        <div>
                            <span>${status.type}</span> | 
                            <span>${status.status}</span>
                            ${status.url ? '<br>URL: ' + status.url : ''}
                        </div>
                    `;
                    statusList.appendChild(card);
                });
            } catch (error) {
                console.error('Erro ao carregar status:', error);
            }
        }
        
        function showNewStatusForm() {
            currentEditingStatusIndex = -1;
            document.getElementById('status-editor-title').textContent = 'Novo Status';
            document.getElementById('status-text').value = '';
            document.getElementById('status-type').value = 'PLAYING';
            document.getElementById('status-status').value = 'online';
            document.getElementById('status-url').value = '';
            document.getElementById('status-url-group').style.display = 'none';
            document.getElementById('status-editor').style.display = 'block';
        }
        
        async function editStatus(index) {
            try {
                currentEditingStatusIndex = index;
                const response = await fetch('/api/status');
                const data = await response.json();
                
                let statuses = [];
                try {
                    statuses = JSON.parse(data.content);
                } catch (e) {
                    statuses = [];
                }
                
                const status = statuses[index];
                document.getElementById('status-editor-title').textContent = 'Editar Status';
                document.getElementById('status-text').value = status.text;
                document.getElementById('status-type').value = status.type;
                document.getElementById('status-status').value = status.status;
                
                if (status.type === 'STREAMING') {
                    document.getElementById('status-url-group').style.display = 'block';
                    document.getElementById('status-url').value = status.url || '';
                } else {
                    document.getElementById('status-url-group').style.display = 'none';
                }
                
                document.getElementById('status-editor').style.display = 'block';
            } catch (error) {
                alert('Erro ao editar status: ' + error.message);
            }
        }
        
        async function saveStatus() {
            try {
                const text = document.getElementById('status-text').value.trim();
                const type = document.getElementById('status-type').value;
                const statusValue = document.getElementById('status-status').value;
                const url = document.getElementById('status-url').value.trim();
                
                if (!text) {
                    alert('Texto do status é obrigatório');
                    return;
                }
                
                if (type === 'STREAMING' && !url) {
                    alert('URL é obrigatória para STREAMING');
                    return;
                }
                
                const statusObject = {
                    text: text,
                    type: type,
                    status: statusValue
                };
                
                if (type === 'STREAMING') {
                    statusObject.url = url;
                }
                
                // Carregar status existentes
                const response = await fetch('/api/status');
                const data = await response.json();
                let statuses = [];
                try {
                    statuses = JSON.parse(data.content);
                } catch (e) {
                    statuses = [];
                }
                
                // Adicionar ou atualizar
                if (currentEditingStatusIndex === -1) {
                    statuses.push(statusObject);
                } else {
                    statuses[currentEditingStatusIndex] = statusObject;
                }
                
                // Salvar
                const saveResponse = await fetch('/api/status', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ content: JSON.stringify(statuses, null, 2) })
                });
                
                const saveData = await saveResponse.json();
                if (saveData.success) {
                    alert('Status salvo!');
                    cancelStatusEdit();
                    loadStatus();
                } else {
                    alert('Erro: ' + saveData.message);
                }
            } catch (error) {
                alert('Erro ao salvar status: ' + error.message);
            }
        }
        
        async function deleteStatusConfirm(index) {
            if (confirm('Excluir este status?')) {
                await deleteStatus(index);
            }
        }
        
        async function deleteStatus(index) {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                let statuses = [];
                try {
                    statuses = JSON.parse(data.content);
                } catch (e) {
                    statuses = [];
                }
                
                statuses.splice(index, 1);
                
                const saveResponse = await fetch('/api/status', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ content: JSON.stringify(statuses, null, 2) })
                });
                
                const saveData = await saveResponse.json();
                if (saveData.success) {
                    alert('Status excluído!');
                    loadStatus();
                } else {
                    alert('Erro: ' + saveData.message);
                }
            } catch (error) {
                alert('Erro ao excluir status: ' + error.message);
            }
        }
        
        function cancelStatusEdit() {
            document.getElementById('status-editor').style.display = 'none';
            currentEditingStatusIndex = -1;
        }
        
        // Configurações .env
        async function loadEnv() {
            try {
                const response = await fetch('/api/config');
                const data = await response.json();
                const form = document.getElementById('env-form');
                form.innerHTML = '';
                
                for (const [key, value] of Object.entries(data.content)) {
                    addEnvEntry(key, value, form);
                }
                
                if (Object.keys(data.content).length === 0) {
                    addEnvEntry('', '', form);
                }
            } catch (error) {
                console.error('Erro ao carregar env:', error);
            }
        }
        
        function addEnvEntry(key = '', value = '', container = null) {
            if (!container) container = document.getElementById('env-form');
            
            const entry = document.createElement('div');
            entry.className = 'env-entry';
            const isSensitive = /token|key|secret|password/i.test(key);
            
            entry.innerHTML = `
                <label>Chave:</label>
                <input type="text" class="env-key" value="${key}" placeholder="ex: TOKEN">
                <label>Valor:</label>
                <div class="env-input-wrapper">
                    <input type="${isSensitive ? 'password' : 'text'}" class="env-value" value="${value}">
                    <button type="button" class="env-toggle">👁</button>
                </div>
            `;
            
            container.appendChild(entry);
            
            // Toggle para mostrar/esconder senha
            const toggle = entry.querySelector('.env-toggle');
            const input = entry.querySelector('.env-value');
            toggle.addEventListener('click', () => {
                input.type = input.type === 'password' ? 'text' : 'password';
            });
        }
        
        async function saveEnv() {
            try {
                const entries = document.querySelectorAll('.env-entry');
                const content = {};
                
                entries.forEach(entry => {
                    const key = entry.querySelector('.env-key').value.trim();
                    const value = entry.querySelector('.env-value').value;
                    if (key) {
                        content[key] = value;
                    }
                });
                
                const response = await fetch('/api/config', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ content: content })
                });
                
                const data = await response.json();
                if (data.success) {
                    alert('.env salvo!');
                } else {
                    alert('Erro: ' + data.message);
                }
            } catch (error) {
                alert('Erro ao salvar: ' + error.message);
            }
        }
        
        // Configurar evento para mostrar/ocultar URL do streaming
        document.getElementById('status-type').addEventListener('change', function() {
            document.getElementById('status-url-group').style.display = 
                this.value === 'STREAMING' ? 'block' : 'none';
        });
        
        // Inicialização
        setInterval(updateStatus, 2000);
        updateStatus();
    </script>
</body>
</html>'''

# --- ROTAS DA API ---

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/bot/<action>', methods=['POST'])
def control_bot(action):
    global bot_process, is_bot_process_running, is_bot_truly_online, bot_status_message

    if action == 'start':
        if is_bot_process_running:
            return jsonify({"success": False, "message": "O processo do bot já está rodando."})
        
        node_executable = shutil.which('node')
        if not node_executable:
            return jsonify({"success": False, "message": "Node.js não encontrado no sistema."})
        
        is_bot_truly_online = False
        bot_status_message = "Iniciando..."
        
        try:
            command_to_run = [node_executable, BOT_FILE_NAME]
            bot_process = subprocess.Popen(
                command_to_run, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                cwd=BOT_PATH
            )
            
            is_bot_process_running = True
            threading.Thread(target=stream_logs, args=(bot_process,), daemon=True).start()
            return jsonify({"success": True, "message": "Comando de início enviado."})
            
        except Exception as e:
            is_bot_process_running = False
            bot_status_message = "Falha ao iniciar."
            return jsonify({"success": False, "message": str(e)})
            
    elif action == 'stop':
        if not is_bot_process_running:
            return jsonify({"success": False, "message": "O bot não está rodando."})
        try:
            bot_process.terminate()
            bot_process.wait(timeout=5)
        except Exception as e:
            print(f"Erro ao terminar processo: {e}")
        
        is_bot_process_running = False
        is_bot_truly_online = False
        bot_status_message = "Desligado"
        return jsonify({"success": True, "message": "Comando de parada enviado."})
        
    elif action == 'restart':
        stop_result = control_bot('stop').get_json()
        if stop_result.get("success"):
            import time
            time.sleep(1)
            start_result = control_bot('start').get_json()
            return start_result
        return stop_result
        
    return jsonify({"success": False, "message": "Ação inválida."})

@app.route('/api/bot/status', methods=['GET'])
def get_bot_status():
    global is_bot_process_running, is_bot_truly_online, bot_status_message
    if is_bot_process_running and bot_process and bot_process.poll() is not None:
        is_bot_process_running = False
        is_bot_truly_online = False
        bot_status_message = "Processo morreu inesperadamente."
    status = "offline"
    if is_bot_process_running:
        status = "online" if is_bot_truly_online else "starting"
    return jsonify({"status": status, "message": bot_status_message})

@app.route('/api/logs')
def get_logs():
    global bot_logs
    with log_lock:
        return jsonify({"logs": bot_logs[-100:]})

@app.route('/api/commands', methods=['GET'])
def list_commands():
    try:
        files = [f for f in os.listdir(COMMANDS_PATH) if f.endswith('.js')]
        return jsonify(files)
    except FileNotFoundError:
        return jsonify({"error": "Pasta de comandos não encontrada."}), 404

@app.route('/api/command/<name>', methods=['GET', 'POST', 'DELETE'])
def handle_command(name):
    name = escape(name)
    if not name or '..' in name:
        return jsonify({"success": False, "message": "Nome de comando inválido."}), 400
    
    filename = name if name.endswith('.js') else name + '.js'
    filepath = os.path.join(COMMANDS_PATH, filename)
    
    if request.method == 'GET':
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                full_content = f.read()

            name_match = re.search(r'name:\s*"([^"]*)"', full_content)
            command_name = name_match.group(1) if name_match else ""
            
            code_match = re.search(r'code:\s*`(.*?)`', full_content, re.DOTALL)
            bdfd_code = code_match.group(1) if code_match else ""

            return jsonify({"code": bdfd_code, "name": command_name})
        except FileNotFoundError:
            return jsonify({"success": False, "message": "Comando não encontrado."}), 404
        except Exception as e:
            return jsonify({"success": False, "message": f"Erro ao ler o arquivo: {str(e)}"}), 500

    elif request.method == 'POST':
        command_code = request.json.get('code')
        if command_code is None:
            return jsonify({"success": False, "message": "Código não fornecido."}), 400
        
        command_name = os.path.splitext(os.path.basename(filename))[0]
        full_code = f"""module.exports = ({{
  name: "{command_name}",
  code: `
{command_code}
  `
}});"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(full_code)
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500
            
    elif request.method == 'DELETE':
        try:
            os.remove(filepath)
            return jsonify({"success": True})
        except FileNotFoundError:
            return jsonify({"success": False, "message": "Comando não encontrado."}), 404
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/variables', methods=['GET', 'POST'])
def handle_variables():
    if request.method == 'GET':
        try:
            with open(VARIABLES_PATH, 'r', encoding='utf-8') as f:
                content = f.read()
            
            variables_dict = {}
            if "module.exports" in content:
                try:
                    start = content.find('{')
                    end = content.rfind('}') + 1
                    js_object_content = content[start:end]
                    
                    lines = js_object_content.split('\n')
                    for line in lines:
                        line = line.strip().rstrip(',')
                        if ':' in line and '"' in line:
                            key_match = re.search(r'"([^"]+)"', line)
                            if key_match:
                                key = key_match.group(1)
                                
                                type_match = re.search(r'type:\s*"([^"]+)"', line)
                                default_match = re.search(r'default:\s*([^,}]+)', line)
                                
                                if type_match and default_match:
                                    var_type = type_match.group(1)
                                    default_value = default_match.group(1).strip()
                                    
                                    if var_type == "number":
                                        try:
                                            default_value = float(default_value) if '.' in default_value else int(default_value)
                                        except ValueError:
                                            default_value = 0
                                    else:
                                        default_value = default_value.strip('"\'')
                                    
                                    variables_dict[key] = {"type": var_type, "default": default_value}
                except Exception as e:
                    print(f"Erro ao parsear variáveis: {e}")
                    variables_dict = {}
            
            return jsonify({"content": variables_dict})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
            
    elif request.method == 'POST':
        variables_dict = request.json.get('content')
        if variables_dict is None:
            return jsonify({"success": False, "message": "Conteúdo não fornecido."}), 400
        
        try:
            js_content = "module.exports = {\n"
            for key, value in variables_dict.items():
                if isinstance(value, (int, float)):
                    var_type = "number"
                    default_value = value
                else:
                    var_type = "string" 
                    default_value = f'"{value}"'
                
                js_content += f'  "{key}": {{ type: "{var_type}", default: {default_value} }},\n'
            
            js_content += "};"
            
            with open(VARIABLES_PATH, 'w', encoding='utf-8') as f:
                f.write(js_content)
                
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/status', methods=['GET', 'POST'])
def handle_status_config():
    if request.method == 'GET':
        try:
            if os.path.exists(STATUS_CONFIG_PATH):
                with open(STATUS_CONFIG_PATH, 'r', encoding='utf-8') as f:
                    content = f.read()
                return jsonify({"content": content})
            else:
                return jsonify({"content": "[]"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
            
    elif request.method == 'POST':
        raw_json_array = request.json.get('content')
        if not raw_json_array:
            return jsonify({"success": False, "message": "Conteúdo do status não fornecido."}), 400
        try:
            json.loads(raw_json_array)
            with open(STATUS_CONFIG_PATH, 'w', encoding='utf-8') as f:
                f.write(raw_json_array)
            return jsonify({"success": True})
        except json.JSONDecodeError:
            return jsonify({"success": False, "message": "O conteúdo fornecido não é um JSON array válido."}), 400
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500

def parse_env(content):
    env_dict = {}
    for line in content.splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            if '=' in line:
                key, value = line.split('=', 1)
                env_dict[key.strip()] = value.strip()
    return env_dict

@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    if request.method == 'GET':
        try:
            with open(ENV_PATH, 'r', encoding='utf-8') as f:
                content = f.read()
            env_dict = parse_env(content)
            return jsonify({"content": env_dict})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
            
    elif request.method == 'POST':
        content_dict = request.json.get('content')
        if content_dict is None:
            return jsonify({"success": False, "message": "Conteúdo não fornecido."}), 400
        try:
            content_str = '\n'.join(f"{k}={v}" for k, v in content_dict.items() if k)
            with open(ENV_PATH, 'w', encoding='utf-8') as f:
                f.write(content_str)
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500

if __name__ == '__main__':
    # Criar diretórios necessários
    os.makedirs(COMMANDS_PATH, exist_ok=True)
    os.makedirs(os.path.dirname(VARIABLES_PATH), exist_ok=True)
    
    # Garantir que o arquivo de status existe
    if not os.path.exists(STATUS_CONFIG_PATH):
        with open(STATUS_CONFIG_PATH, 'w', encoding='utf-8') as f:
            f.write('[]')
    
    # Garantir que o arquivo de variáveis existe
    if not os.path.exists(VARIABLES_PATH):
        with open(VARIABLES_PATH, 'w', encoding='utf-8') as f:
            f.write('module.exports = {};')
    
    app.run(debug=True, port=2000, use_reloader=False)
