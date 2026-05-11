import os
import re
import base64
import telebot
from telebot import types

# CONFIGURAÇÕES
def load_env():
    if os.path.exists('.env'):
        with open('.env') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

load_env()

HTML_FILE = 'index.html'
JS_FILE = 'script_0.js'
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', "Ng200726") 

# GITHUB SYNC
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_REPO = "groupultramind-spec/nota100enem"

import requests

bot = telebot.TeleBot(BOT_TOKEN)

# Dicionário temporário para estados e login
user_states = {}
authorized_users = set()

def push_to_github(content, repo_path, is_binary=False):
    if not GITHUB_TOKEN: return
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{repo_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    try:
        response = requests.get(url, headers=headers)
        sha = response.json().get('sha') if response.status_code == 200 else None
        content_b64 = base64.b64encode(content if is_binary else content.encode('utf-8')).decode('utf-8')
        data = {"message": f"🤖 Sync via Admin Bot: {repo_path}", "content": content_b64}
        if sha: data["sha"] = sha
        requests.put(url, headers=headers, json=data)
    except Exception as e: print(f"[GitHub Error] {e}")

def create_main_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔑 Chaves SyncPay", callback_data="set_syncpay"),
        types.InlineKeyboardButton("💰 Preço Principal", callback_data="set_price"),
        types.InlineKeyboardButton("🚀 Preço Upsell", callback_data="set_upsell"),
        types.InlineKeyboardButton("📸 Instagram", callback_data="set_ig"),
        types.InlineKeyboardButton("🔗 Link do Produto", callback_data="set_link"),
        types.InlineKeyboardButton("📢 Chat ID Notif.", callback_data="set_chat"),
        types.InlineKeyboardButton("🎨 Cor do Site", callback_data="set_color"),
        types.InlineKeyboardButton("🔒 Sair", callback_data="logout")
    )
    return markup

@bot.message_handler(commands=['start', 'admin', 'menu'])
def send_welcome(message):
    chat_id = message.chat.id
    if chat_id not in authorized_users:
        bot.send_message(chat_id, "🔐 **PAINEL ADMINISTRATIVO**\n\nPor favor, digite a **SENHA MESTRE**:", parse_mode='Markdown')
        user_states[chat_id] = {'state': 'WAITING_LOGIN'}
    else:
        bot.send_message(chat_id, "🛠️ **Menu de Configuração**\nO que deseja alterar hoje?", 
                         reply_markup=create_main_menu(), parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    if chat_id not in authorized_users and call.data != "logout":
        bot.send_message(chat_id, "❌ Não autorizado.")
        return

    if call.data == "set_syncpay":
        bot.send_message(chat_id, "➡️ Digite o **Client ID** da SyncPay:")
        user_states[chat_id] = {'state': 'WAITING_SYNC_ID'}
    elif call.data == "set_price":
        bot.send_message(chat_id, "➡️ Digite o novo **Preço Principal** (Ex: 17,90):")
        user_states[chat_id] = {'state': 'WAITING_PRICE'}
    elif call.data == "set_upsell":
        bot.send_message(chat_id, "➡️ Digite o novo **Preço do Upsell** (Ex: 24,30):")
        user_states[chat_id] = {'state': 'WAITING_UPSELL_PRICE'}
    elif call.data == "set_ig":
        bot.send_message(chat_id, "➡️ Digite o **@usuario** ou link do Instagram:")
        user_states[chat_id] = {'state': 'WAITING_IG'}
    elif call.data == "set_link":
        bot.send_message(chat_id, "➡️ Digite o **Link do Produto** (PDF/Site):")
        user_states[chat_id] = {'state': 'WAITING_LINK'}
    elif call.data == "set_chat":
        bot.send_message(chat_id, "➡️ Digite o **Chat ID** (Ex: -100123...):")
        user_states[chat_id] = {'state': 'WAITING_CHAT'}
    elif call.data == "set_color":
        bot.send_message(chat_id, "➡️ Digite a **Cor Hex** (Ex: #FFD400):")
        user_states[chat_id] = {'state': 'WAITING_COLOR'}
    elif call.data == "logout":
        authorized_users.discard(chat_id)
        bot.send_message(chat_id, "🔒 Sessão encerrada.")
    
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: message.chat.id in user_states)
def handle_inputs(message):
    chat_id = message.chat.id
    data = user_states.get(chat_id)
    state = data['state']
    text = message.text.strip()
    
    if state == 'WAITING_LOGIN':
        if text == ADMIN_PASSWORD:
            authorized_users.add(chat_id)
            del user_states[chat_id]
            bot.send_message(chat_id, "✅ **ACESSO LIBERADO!**", parse_mode='Markdown')
            bot.send_message(chat_id, "Bem-vindo. Escolha uma opção:", reply_markup=create_main_menu())
        else:
            bot.send_message(chat_id, "❌ **Senha Incorreta!**")
        return

    if chat_id not in authorized_users: return

    try:
        # Decidir qual arquivo abrir
        target_file = HTML_FILE if state == 'WAITING_COLOR' else JS_FILE
        with open(target_file, 'r', encoding='utf-8') as f: content = f.read()
        
        if state == 'WAITING_SYNC_ID':
            if len(text) < 10: raise ValueError("Client ID parece muito curto.")
            content = re.sub(r"SYNC_KEY: '.*?'", f"SYNC_KEY: '{text}'", content)
            user_states[chat_id] = {'state': 'WAITING_SYNC_SECRET', 'temp_content': content}
            bot.send_message(chat_id, "✅ ID recebido! Agora digite o **Client Secret**:")
            return

        elif state == 'WAITING_SYNC_SECRET':
            content = data['temp_content']
            content = re.sub(r"SYNC_TOKEN: '.*?'", f"SYNC_TOKEN: '{text}'", content)
            bot.send_message(chat_id, "⏳ Salvando chaves SyncPay...")

        elif state == 'WAITING_PRICE':
            if not re.match(r"^\d+([,.]\d{2})?$", text): raise ValueError("Formato de preço inválido. Use 17,90")
            text = text.replace('.', ',')
            content = re.sub(r"PRICE_MAIN: '.*?'", f"PRICE_MAIN: '{text}'", content)
            bot.send_message(chat_id, f"✅ Alterando preço para R$ {text}...")
            
        elif state == 'WAITING_UPSELL_PRICE':
            if not re.match(r"^\d+([,.]\d{2})?$", text): raise ValueError("Formato de preço inválido. Use 24,30")
            text = text.replace('.', ',')
            content = re.sub(r"PRICE_UPSELL: '.*?'", f"PRICE_UPSELL: '{text}'", content)
            bot.send_message(chat_id, f"✅ Alterando upsell para R$ {text}...")
            
        elif state == 'WAITING_IG':
            if text.startswith('@'): text = f"https://instagram.com/{text[1:]}"
            if not text.startswith('http'): raise ValueError("Link do Instagram inválido.")
            content = re.sub(r"INSTAGRAM_URL: '.*?'", f"INSTAGRAM_URL: '{text}'", content)
            bot.send_message(chat_id, "✅ Instagram atualizado!")

        elif state == 'WAITING_LINK':
            if not text.startswith('http'): raise ValueError("Link inválido. Deve começar com http")
            content = re.sub(r"PRODUCT_LINK: '.*?'", f"PRODUCT_LINK: '{text}'", content)
            bot.send_message(chat_id, "✅ Link do produto atualizado!")
            
        elif state == 'WAITING_CHAT':
            if not re.match(r"^-?\d+$", text): raise ValueError("Chat ID deve ser apenas números.")
            content = re.sub(r"TG_CHAT_ID: '.*?'", f"TG_CHAT_ID: '{text}'", content)
            bot.send_message(chat_id, "✅ Chat ID de notificações atualizado!")
            
        elif state == 'WAITING_COLOR':
            if not re.match(r"^#[0-9A-Fa-f]{6}$", text): raise ValueError("Cor deve ser #RRGGBB")
            hex_color = text.lstrip('#')
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            content = re.sub(r"--primary: #.*?;", f"--primary: #{hex_color};", content)
            content = re.sub(r"--primary-rgb: .*?;", f"--primary-rgb: {r}, {g}, {b};", content)
            bot.send_message(chat_id, "✅ Cor do site atualizada!")

        with open(target_file, 'w', encoding='utf-8') as f: f.write(content)
        push_to_github(content, target_file)
        del user_states[chat_id]
        bot.send_message(chat_id, "✨ **Alterações aplicadas e sincronizadas com sucesso!**", reply_markup=create_main_menu(), parse_mode='Markdown')

    except Exception as e:
        bot.send_message(chat_id, f"⚠️ **ERRO:** {str(e)}\n\nTente novamente:")

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    chat_id = message.chat.id
    if chat_id not in authorized_users: return
        
    try:
        file_info = bot.get_file(message.document.file_id)
        if not message.document.file_name.lower().endswith('.pdf'):
            bot.send_message(chat_id, "❌ Por favor, envie um arquivo **PDF**.")
            return
            
        bot.send_message(chat_id, "📥 Baixando e configurando o PDF...")
        downloaded_file = bot.download_file(file_info.file_path)
        
        os.makedirs('uploads', exist_ok=True)
        safe_name = message.document.file_name.replace(" ", "_")
        filepath = os.path.join('uploads', safe_name)
        
        with open(filepath, 'wb') as new_file: new_file.write(downloaded_file)
        push_to_github(downloaded_file, f"uploads/{safe_name}", is_binary=True)
            
        with open(JS_FILE, 'r', encoding='utf-8') as f: content = f.read()
        # No script_0.js, o link geralmente está em alguma variável de config ou PRODUCT_LINK
        if "PRODUCT_LINK" in content:
            content = re.sub(r"PRODUCT_LINK: '.*?'", f"PRODUCT_LINK: './uploads/{safe_name}'", content)
        else:
            bot.send_message(chat_id, "⚠️ **Aviso:** Variável 'PRODUCT_LINK' não encontrada no script_0.js. O arquivo foi salvo, mas o link automático falhou.")
            
        with open(JS_FILE, 'w', encoding='utf-8') as f: f.write(content)
        push_to_github(content, JS_FILE)
        
        bot.send_message(chat_id, f"✅ PDF salvo e sincronizado!\nArquivo: `{safe_name}`", parse_mode='Markdown', reply_markup=create_main_menu())
        
    except Exception as e:
        bot.send_message(chat_id, f"❌ Erro ao salvar o PDF: {e}")

if __name__ == "__main__":
    print("-" * 30)
    print("ADMIN BOT - PORTUGUESE EDITION")
    print(f"Monitorando: {HTML_FILE} & {JS_FILE}")
    print("-" * 30)
    bot.infinity_polling()
