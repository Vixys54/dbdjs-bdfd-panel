import os
import json
import subprocess
import threading
import re
import shutil
import requests
import json
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

AUTO_START_BOT = True
RESTART_ON_CRASH = True

app = Flask(__name__)

# --- Variáveis Globais de Controle do Bot ---
bot_process = None
bot_logs = []
log_lock = threading.Lock()
is_bot_process_running = False
is_bot_truly_online = False
bot_status_message = "Desligado"
expected_stop = False


# --- Configurações da API do LM Studio ---
LM_STUDIO_URL = "http://127.0.0.1:1234/v1/chat/completions"
AI_MODEL = "qwen2.5-vl-7b-instruct-abliterated"

# --- Função Auxiliar para Capturar Logs e Verificar Status ---
def stream_logs(process):
    """Lê stdout/stderr em threads separadas para leitura em tempo real."""
    global bot_logs, is_bot_truly_online, bot_status_message, is_bot_process_running, expected_stop

    def read_stdout():
        for line in iter(process.stdout.readline, b''):
            decoded_line = line.decode('utf-8', errors='ignore').strip()
            with log_lock:
                bot_logs.append(decoded_line)
                if "PAINEL_STATUS:BOT_ONLINE_READY" in decoded_line:
                    is_bot_truly_online = True
                    bot_status_message = "online"
                elif "Invalid Token" in decoded_line or "DISALLOWED_INTENTS" in decoded_line:
                    is_bot_truly_online = False
                    bot_status_message = "Erro de Conexão (Verifique Token/Intents)"

    def read_stderr():
        for line in iter(process.stderr.readline, b''):
            decoded_line = f"ERROR: {line.decode('utf-8', errors='ignore').strip()}"
            with log_lock:
                bot_logs.append(decoded_line)
                is_bot_truly_online = False
                bot_status_message = "Erro de Execução (Verifique logs)"

    stdout_thread = threading.Thread(target=read_stdout, daemon=True)
    stderr_thread = threading.Thread(target=read_stderr, daemon=True)
    stdout_thread.start()
    stderr_thread.start()

    process.wait()  # Espera o processo terminar

    is_bot_process_running = False
    if not is_bot_truly_online:
        bot_status_message = "Processo finalizado."

    returncode = process.returncode
    print(f"Bot process ended with code {returncode}")

    if RESTART_ON_CRASH and returncode != 0 and not expected_stop:
        bot_status_message = "Bot crashed, restarting..."
        start_bot()

    expected_stop = False

def start_bot():
    global bot_process, is_bot_truly_online, bot_status_message, is_bot_process_running, expected_stop
    if is_bot_process_running:
        return False
    
    node_executable = shutil.which('node')
    if not node_executable:
        return False
    
    is_bot_truly_online = False
    bot_status_message = "Iniciando..."
    expected_stop = False
    
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
        return True
        
    except Exception as e:
        is_bot_process_running = False
        bot_status_message = "Falha ao iniciar."
        print(str(e))
        return False

def stop_bot():
    global bot_process, is_bot_process_running, is_bot_truly_online, bot_status_message, expected_stop
    if not is_bot_process_running:
        return False
    expected_stop = True
    try:
        bot_process.terminate()
        bot_process.wait(timeout=5)
    except Exception as e:
        print(f"Erro ao terminar processo: {e}")
        return False
    
    is_bot_process_running = False
    is_bot_truly_online = False
    bot_status_message = "Desligado"
    return True

# --- HTML, CSS e JavaScript (Tudo em Strings) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Painel de Controle - Bot</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #1e1e1e; color: #d4d4d4; margin: 0; padding: 20px; }
        .container { max-width: 1200px; margin: auto; background-color: #252526; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.5); overflow: hidden; }
        .header { background-color: #007acc; color: white; padding: 15px 20px; text-align: center; }
        .tabs { display: flex; background-color: #333; border-bottom: 2px solid #007acc; }
        .tab-button { flex: 1; padding: 15px; background: none; border: none; color: #d4d4d4; cursor: pointer; font-size: 16px; transition: background-color 0.3s; }
        .tab-button:hover { background-color: #444; }
        .tab-button.active { background-color: #007acc; color: white; }
        .tab-content { display: none; padding: 20px; }
        .tab-content.active { display: block; }
        .card { background-color: #2d2d2d; border-radius: 6px; padding: 20px; margin-bottom: 20px; border: 1px solid #444; }
        .card h3 { margin-top: 0; color: #007acc; }
        button { background-color: #007acc; color: white; border: none; padding: 10px 15px; border-radius: 4px; cursor: pointer; font-size: 14px; margin: 5px; }
        button:hover { background-color: #005f9e; }
        button.danger { background-color: #d9534f; }
        button.danger:hover { background-color: #c9302c; }
        input, textarea, select { width: 100%; padding: 10px; border-radius: 4px; border: 1px solid #555; background-color: #3c3c3c; color: #d4d4d4; box-sizing: border-box; }
        textarea { font-family: 'Consolas', 'Monaco', monospace; min-height: 200px; resize: vertical; }
        .file-list { list-style: none; padding: 0; max-height: 400px; overflow-y: auto;}
        .file-list li { background-color: #3c3c3c; padding: 10px; margin-bottom: 5px; border-radius: 4px; display: flex; justify-content: space-between; align-items: center; }
        .file-list a { color: #61dafb; text-decoration: none; cursor: pointer; }
        .file-list a:hover { text-decoration: underline; }
        .log-container { background-color: #0c0c0c; color: #00ff00; font-family: 'Consolas', 'Monaco', monospace; padding: 15px; border-radius: 4px; height: 300px; overflow-y: scroll; white-space: pre-wrap; }
        .status-indicator { display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin-right: 8px; }
        .status-online { background-color: #28a745; }
        .status-offline { background-color: #dc3545; }
        .status-starting { background-color: #f0ad4e; }
        .env-entry { margin-bottom: 15px; }
        .env-entry label { display: block; margin-bottom: 5px; }
        .env-input-wrapper { position: relative; }
        .env-input-wrapper input { padding-right: 40px; }
        .env-toggle { position: absolute; right: 10px; top: 50%; transform: translateY(-50%); background: none; border: none; color: #d4d4d4; cursor: pointer; }
        .tooltip { position: relative; display: inline-block; }
        .tooltip .tooltiptext { visibility: hidden; width: 200px; background-color: #555; color: #fff; text-align: center; border-radius: 6px; padding: 5px; position: absolute; z-index: 1; bottom: 125%; left: 50%; margin-left: -100px; opacity: 0; transition: opacity 0.3s; }
        .tooltip:hover .tooltiptext { visibility: visible; opacity: 1; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header"><h1>Painel de Controle - Styllena Bot (dbd.js)</h1></div>
        <div class="tabs">
            <button class="tab-button active" onclick="showTab('dashboard')">Principal</button>
            <button class="tab-button" onclick="showTab('comandos')">Comandos</button>
            <button class="tab-button" onclick="showTab('variaveis')">Variáveis</button>
            <button class="tab-button" onclick="showTab('status')">Status do Bot</button>
            <button class="tab-button" onclick="showTab('configuracoes')">Configurações (.env)</button>
        </div>

        <!-- Tab: Principal -->
        <div id="dashboard" class="tab-content active">
            <div class="card">
                <h3>Controle do Bot</h3>
                <span id="bot-status-indicator" class="status-indicator status-offline"></span>
                <span id="bot-status-text">Desligado</span>
                <div style="margin-top: 15px;">
                    <button class="tooltip" onclick="controlBot('start')"><span class="tooltiptext">Inicia o bot se não estiver rodando.</span>Ligar Bot</button>
                    <button class="danger tooltip" onclick="controlBot('stop')"><span class="tooltiptext">Para o bot se estiver rodando.</span>Desligar Bot</button>
                    <button class="tooltip" onclick="controlBot('restart')"><span class="tooltiptext">Para e reinicia o bot.</span>Reiniciar Bot</button>
                </div>
            </div>
            <div class="card">
                <h3>Logs do Bot (Hot-Reload Ativo)</h3>
                <div id="bot-logs" class="log-container">Aguardando logs...</div>
            </div>
        </div>

        <!-- Tab: Comandos -->
        <div id="comandos" class="tab-content">
            <div class="card">
                <h3>Gerenciar Comandos</h3>
                <button onclick="showNewCommandForm()">+ Novo Comando</button>
                <ul id="command-list" class="file-list"></ul>
            </div>
            <div id="command-editor" class="card" style="display: none;">
                <h3 id="editor-title">Novo Comando</h3>
                <input type="text" id="command-name" placeholder="Nome do comando (ex: trabalhar)">
                <textarea id="command-code" placeholder="Apenas o código BDFD.&#10;$nomention&#10;Você trabalhou..."></textarea>
                <button onclick="saveCommand()">Salvar</button>
                <button class="danger" onclick="deleteCommand()">Apagar</button>
                <button onclick="cancelEdit()">Cancelar</button>
            </div>
        </div>

        <!-- Tab: Variáveis -->
        <div id="variaveis" class="tab-content">
            <div class="card">
                <h3>Editar Variáveis (variables/defaults.js)</h3>
                <p>Edite apenas o conteúdo JSON. O sistema adicionará o `module.exports` para você.</p>
                <textarea id="variables-code" placeholder='&#10;"$userMoney": {&#10;  "type": "number",&#10;  "default": 0&#10;}&#10;'></textarea>
                <button onclick="saveVariables()">Salvar Variáveis</button>
            </div>
        </div>
        
        <!-- Tab: Status do Bot -->
        <div id="status" class="tab-content">
            <div class="card">
                <h3>Gerenciar Status do Bot</h3>
                <p>Edite apenas o array de status. O sistema adicionará o resto do código para você.</p>
                <textarea id="status-code" placeholder='&#10;[{ "text": "oi", "type": "PLAYING", "status": "idle" },&#10; { "text": "Styllena está aqui", "type": "WATCHING", "status": "idle" }]'></textarea>
                <button onclick="saveStatus()">Salvar Status</button>
            </div>
        </div>

        <!-- Tab: Configurações -->
        <div id="configuracoes" class="tab-content">
            <div class="card">
                <h3>Editar Arquivo .env</h3>
                <p><strong>CUIDADO:</strong> Altere apenas se souber o que está fazendo. Erros aqui podem impedir o bot de ligar.</p>
                <div id="env-form"></div>
                <button onclick="addEnvEntry()">+ Adicionar Entrada</button>
                <button onclick="saveEnv()">Salvar .env</button>
            </div>
        </div>
    </div>

    <script>
        const API_BASE = '';
        let currentEditingFile = null;

        function htmlEscape(str) {
            return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
        }

        function showTab(tabName) {
            document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
            document.querySelectorAll('.tab-button').forEach(button => button.classList.remove('active'));
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
            
            if (tabName === 'comandos') loadCommands();
            if (tabName === 'variaveis') loadVariables();
            if (tabName === 'status') loadStatus();
            if (tabName === 'configuracoes') loadEnv();
        }
        
        // --- Bot Control ---
        async function controlBot(action) {
            const response = await fetch(`${API_BASE}/api/bot/${action}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            const data = await response.json();
            if (!data.success) {
                alert(`Erro: ${data.message}`);
            }
        }
        
        // --- Status e Logs Polling ---
        async function fetchStatusAndLogs() {
            const statusResponse = await fetch(`${API_BASE}/api/bot/status`);
            const statusData = await statusResponse.json();
            updateBotStatus(statusData.status, statusData.message);

            const logsResponse = await fetch(`${API_BASE}/api/logs`);
            const logsData = await logsResponse.json();
            const logContainer = document.getElementById('bot-logs');
            logContainer.textContent = logsData.logs.join('\\n');
            logContainer.scrollTop = logContainer.scrollHeight;
        }

        function updateBotStatus(status, message) {
            const indicator = document.getElementById('bot-status-indicator');
            const text = document.getElementById('bot-status-text');
            indicator.className = 'status-indicator'; // Reseta classes
            text.textContent = htmlEscape(message);

            if (status === 'online') {
                indicator.classList.add('status-online');
            } else if (status === 'starting') {
                indicator.classList.add('status-starting');
            } else {
                indicator.classList.add('status-offline');
            }
        }

        // --- Commands ---
        async function loadCommands() {
            const response = await fetch(`${API_BASE}/api/commands`);
            const commands = await response.json();
            const list = document.getElementById('command-list');
            list.innerHTML = '';
            commands.forEach(cmd => {
                const li = document.createElement('li');
                li.innerHTML = `<span>${htmlEscape(cmd)}</span> <a onclick="editCommand('${htmlEscape(cmd)}')">Editar</a>`;
                list.appendChild(li);
            });
        }
        
        function showNewCommandForm() {
            currentEditingFile = null;
            document.getElementById('editor-title').textContent = 'Novo Comando';
            document.getElementById('command-name').value = '';
            document.getElementById('command-code').value = '';
            document.getElementById('command-editor').style.display = 'block';
        }

        async function editCommand(filename) {
            currentEditingFile = filename;
            document.getElementById('editor-title').textContent = `Editar ${htmlEscape(filename)}`;
            const response = await fetch(`${API_BASE}/api/command/${encodeURIComponent(filename)}`);
            const data = await response.json();
            document.getElementById('command-name').value = htmlEscape(data.name || filename.replace('.js', ''));
            document.getElementById('command-code').value = data.code || '';
            document.getElementById('command-editor').style.display = 'block';
        }

        async function saveCommand() {
            const name = document.getElementById('command-name').value.trim();
            const code = document.getElementById('command-code').value;
            if (!name || !code) {
                alert('Nome do comando e código não podem estar vazios.');
                return;
            }
            
            const oldFilename = currentEditingFile;
            const newFilename = `${name}.js`;
            const isEditing = oldFilename !== null;
            let needDelete = false;
            if (isEditing && newFilename !== oldFilename) {
                needDelete = true;
            }

            const saveUrl = `${API_BASE}/api/command/${encodeURIComponent(newFilename)}`;
            const response = await fetch(saveUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code: code })
            });
            const data = await response.json();
            if (data.success) {
                if (needDelete) {
                    await fetch(`${API_BASE}/api/command/${encodeURIComponent(oldFilename)}`, { method: 'DELETE' });
                }
                alert('Comando salvo! O bot deve recarregá-lo automaticamente.');
                cancelEdit();
                loadCommands();
            } else {
                alert(`Erro ao salvar: ${data.message}`);
            }
        }

        async function deleteCommand() {
            if (!currentEditingFile || !confirm(`Tem certeza que deseja apagar ${htmlEscape(currentEditingFile)}?`)) return;
            const response = await fetch(`${API_BASE}/api/command/${encodeURIComponent(currentEditingFile)}`, { method: 'DELETE' });
            const data = await response.json();
            if (data.success) {
                alert('Comando apagado!');
                cancelEdit();
                loadCommands();
            } else {
                alert(`Erro ao apagar: ${data.message}`);
            }
        }

        function cancelEdit() {
            document.getElementById('command-editor').style.display = 'none';
            currentEditingFile = null;
        }
        
        // --- Variables, Status, Config ---
        async function loadFile(url, elementId) {
            const response = await fetch(url);
            const data = await response.json();
            document.getElementById(elementId).value = data.content || '';
        }
        async function saveFile(url, elementId, successMsg) {
            const content = document.getElementById(elementId).value;
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: content })
            });
            const data = await response.json();
            if (data.success) {
                alert(successMsg);
            } else {
                alert(`Erro: ${data.message}`);
            }
        }

        function loadVariables() { loadFile(`${API_BASE}/api/variables`, 'variables-code'); }
        function saveVariables() { saveFile(`${API_BASE}/api/variables`, 'variables-code', 'Variáveis salvas! O bot deve recarregá-las.'); }
        function loadStatus() { loadFile(`${API_BASE}/api/status`, 'status-code'); }
        function saveStatus() { saveFile(`${API_BASE}/api/status`, 'status-code', 'Status salvo! Reinicie o bot para aplicar as mudanças.'); }

        async function loadEnv() {
            const response = await fetch(`${API_BASE}/api/config`);
            const data = await response.json();
            const form = document.getElementById('env-form');
            form.innerHTML = '';
            for (const [key, value] of Object.entries(data.content)) {
                addEnvEntry(key, value, form);
            }
            if (Object.keys(data.content).length === 0) {
                addEnvEntry('', '', form);
            }
        }

        function addEnvEntry(key = '', value = '', container = null) {
            if (!container) container = document.getElementById('env-form');
            const entry = document.createElement('div');
            entry.classList.add('env-entry');
            const isSensitive = /token|key|secret|password/i.test(key);
            entry.innerHTML = `
                <label for="env-key-${Date.now()}">Chave:</label>
                <input type="text" class="env-key" value="${htmlEscape(key)}" placeholder="ex: TOKEN">
                <label for="env-value-${Date.now()}">Valor:</label>
                <div class="env-input-wrapper">
                    <input type="${isSensitive ? 'password' : 'text'}" class="env-value" value="${htmlEscape(value)}">
                    <button type="button" class="env-toggle">👁</button>
                </div>
            `;
            container.appendChild(entry);
            const toggle = entry.querySelector('.env-toggle');
            const input = entry.querySelector('.env-value');
            toggle.addEventListener('click', () => {
                input.type = input.type === 'password' ? 'text' : 'password';
            });
        }

        async function saveEnv() {
            const entries = document.querySelectorAll('.env-entry');
            const content = {};
            entries.forEach(entry => {
                const key = entry.querySelector('.env-key').value.trim();
                const value = entry.querySelector('.env-value').value;
                if (key) {
                    content[key] = value;
                }
            });
            const response = await fetch(`${API_BASE}/api/config`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: content })
            });
            const data = await response.json();
            if (data.success) {
                alert('.env salvo! Reinicie o bot para aplicar as mudanças.');
            } else {
                alert(`Erro: ${data.message}`);
            }
        }
        
        // Initial Load & Polling
        window.onload = function() {
            fetchStatusAndLogs();
            setInterval(fetchStatusAndLogs, 2000);
        };
    </script>
</body>
</html>
"""

# --- ROTAS DA API ---

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, bot_file_name=BOT_FILE_NAME)

@app.route('/api/bot/<action>', methods=['POST'])
def control_bot(action):

    if action == 'start':
        if start_bot():
            return jsonify({"success": True, "message": "Comando de início enviado."})
        else:
            return jsonify({"success": False, "message": "Falha ao iniciar o bot."})
            
    elif action == 'stop':
        if stop_bot():
            return jsonify({"success": True, "message": "Comando de parada enviado."})
        else:
            return jsonify({"success": False, "message": "Falha ao parar o bot."})
        
    elif action == 'restart':
        if stop_bot():
            import time; time.sleep(1)
            if start_bot():
                return jsonify({"success": True, "message": "Bot reiniciado."})
            else:
                return jsonify({"success": False, "message": "Falha ao reiniciar o bot."})
        else:
            return jsonify({"success": False, "message": "Falha ao parar o bot para reinício."})
        
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
            
            print(f"--- Tentando ler o arquivo: {filepath} ---")
            print(f"Conteúdo bruto do arquivo:\n{full_content}\n---")

            # Regex para extrair o nome
            name_match = re.search(r'name:\s*"([^"]*)"', full_content)
            command_name = name_match.group(1) if name_match else ""
            
            # Regex para extrair o código
            code_match = re.search(r'code:\s*`(.*?)`', full_content, re.DOTALL)
            bdfd_code = code_match.group(1) if code_match else ""

            print(f"Nome extraído: '{command_name}'")
            print(f"Código extraído: '{bdfd_code}'")

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
            if "module.exports" in content:
                start = content.find("{")
                end = content.rfind("}") + 1
                return jsonify({"content": content[start:end]})
            return jsonify({"content": content})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    elif request.method == 'POST':
        raw_json = request.json.get('content')
        if raw_json is None: return jsonify({"success": False, "message": "Conteúdo não fornecido."}), 400
        try:
            json.loads(raw_json)
            full_content = f"module.exports = ({raw_json});"
            with open(VARIABLES_PATH, 'w', encoding='utf-8') as f:
                f.write(full_content)
            return jsonify({"success": True})
        except json.JSONDecodeError:
            return jsonify({"success": False, "message": "O conteúdo fornecido não é um JSON válido."}), 400
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/status', methods=['GET', 'POST'])
def handle_status_config():
    start_marker = "// Status rotativo: Idle com textos alternando"
    end_marker = "}, 12000);"
    if request.method == 'GET':
        try:
            with open(BOT_FILE_PATH, 'r', encoding='utf-8') as f:
                content = f.read()
            start_index = content.find('const statuses = [', content.find(start_marker))
            end_index = content.find('];', start_index)
            if start_index != -1 and end_index != -1:
                array_start = start_index + len('const statuses = ')
                array_end = end_index + 1
                return jsonify({"content": content[array_start:array_end]})
            else:
                return jsonify({"content": "// Estrutura do array de status não encontrada."})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    elif request.method == 'POST':
        raw_json_array = request.json.get('content')
        if not raw_json_array: return jsonify({"success": False, "message": "Conteúdo do status não fornecido."}), 400
        try:
            json.loads(raw_json_array)
            with open(BOT_FILE_PATH, 'r', encoding='utf-8') as f:
                original_content = f.read()
            start_index = original_content.find(start_marker)
            end_index = original_content.find(end_marker, start_index)
            if start_index == -1 or end_index == -1:
                return jsonify({"success": False, "message": "Não foi possível encontrar o bloco de status para substituir."}), 400
            new_block = f"""{start_marker}
  const statuses = {raw_json_array};
  let index = 0;
  
  setInterval(() => {{
    const current = statuses[index % statuses.length];
    bot.status({{
      text: current.text,
      type: current.type,
      status: current.status,
      time: 12
    }});
    index++;
  }}, 12000);"""
            new_content = original_content[:start_index] + new_block + original_content[end_index + len(end_marker):]
            with open(BOT_FILE_PATH, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print("Status saved OK")
            return jsonify({"success": True})
        except json.JSONDecodeError:
            print("Error saving status: Invalid JSON")
            return jsonify({"success": False, "message": "O conteúdo fornecido não é um JSON array válido."}), 400
        except Exception as e:
            print(f"Error saving status: {str(e)}")
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
        if content_dict is None: return jsonify({"success": False, "message": "Conteúdo não fornecido."}), 400
        try:
            content_str = '\n'.join(f"{k}={v}" for k, v in content_dict.items() if k)
            with open(ENV_PATH, 'w', encoding='utf-8') as f:
                f.write(content_str)
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500
        
@app.route('/api/ai', methods=['POST'])
def handle_ai_request():
    """
    Endpoint para processar solicitações de IA do bot Discord
    """
    try:
        # Pega os dados enviados pelo bot
        data = request.get_json()
        user_message = data.get('message', '')
        message_type = data.get('type', 'text') # 'text' ou 'image'
        image_url = data.get('image_url', None)

        if not user_message:
            return jsonify({"error": "Mensagem não fornecida"}), 400

        print(f"[PYTHON] Recebido do bot: '{user_message}' (Tipo: {message_type})")

        # Constrói o prompt para a IA
        prompt_content = [
            {
                "role": "system",
                "content": "Você é Styllena, uma IA amigável e natural em conversas de Discord. Responda de forma casual, como uma pessoa real. Se a mensagem for irrelevante, decida não responder (retorne uma string vazia)."
            }
        ]

        # Adiciona a mensagem do usuário (com ou sem imagem)
        if message_type == 'image' and image_url:
            prompt_content.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": user_message},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            })
        else:
            prompt_content.append({
                "role": "user",
                "content": user_message
            })

        # Faz a chamada para a API do LM Studio
        print(f"[PYTHON] Enviando requisição para LM Studio em {LM_STUDIO_URL}...")
        response = requests.post(
            LM_STUDIO_URL,
            headers={"Content-Type": "application/json"},
            json={
                "model": AI_MODEL,
                "messages": prompt_content,
                "temperature": 0.7,
                "max_tokens": 512
            }
        )
        response.raise_for_status()  # Lança um erro se a requisição falhar (ex: 404, 500)

        response_data = response.json()
        ai_response = response_data['choices'][0]['message']['content'].strip()

        print(f"[PYTHON] Resposta do LM Studio: '{ai_response}'")

        # Retorna a resposta para o bot
        return jsonify({"response": ai_response})

    except requests.exceptions.ConnectionError:
        print("[PYTHON ERRO] Falha ao conectar ao LM Studio. Verifique se ele está rodando na porta 1234.")
        return jsonify({"error": "Não foi possível conectar ao LM Studio."}), 503
    except requests.exceptions.RequestException as e:
        print(f"[PYTHON ERRO] Erro na requisição para LM Studio: {e}")
        return jsonify({"error": "Erro ao se comunicar com a IA."}), 500
    except Exception as e:
        print(f"[PYTHON ERRO] Erro inesperado: {e}")
        return jsonify({"error": "Ocorreu um erro no servidor Python."}), 500

if __name__ == '__main__':
    os.makedirs(COMMANDS_PATH, exist_ok=True)
    os.makedirs(os.path.dirname(VARIABLES_PATH), exist_ok=True)
    if AUTO_START_BOT:
        start_bot()
    app.run(debug=True, port=2000)