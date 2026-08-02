import tkinter as tk
from tkinter import scrolledtext, messagebox
import datetime
import requests

# Função para obter resposta do Codex (OpenAI)
def responder_codex(pergunta, api_key):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "Você é um assistente útil e objetivo."},
            {"role": "user", "content": pergunta}
        ],
        "max_tokens": 200,
        "temperature": 0.7
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=20)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content'].strip()
        elif response.status_code == 401:
            return "Chave de API inválida."
        else:
            return f"Erro: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Erro de conexão: {e}"

import threading

# Função para processar a entrada do usuário
def enviar():
    pergunta = entrada.get()
    api_key = api_entry.get()
    if not api_key:
        messagebox.showwarning("API Key", "Por favor, insira sua chave de API da OpenAI.")
        return
    if not pergunta.strip():
        return
    
    chat_area.config(state='normal')
    chat_area.insert(tk.END, f'Você: {pergunta}\n')
    chat_area.see(tk.END)
    chat_area.config(state='disabled')
    entrada.delete(0, tk.END)
    
    botao_enviar.config(state='disabled')
    entrada.config(state='disabled')

    def thread_request():
        resposta = responder_codex(pergunta, api_key)
        
        # Atualiza a interface (deve ser thread-safe no tkinter simples ou apenas chamado com cuidado)
        chat_area.config(state='normal')
        chat_area.insert(tk.END, f'Assistente: {resposta}\n\n')
        chat_area.see(tk.END)
        chat_area.config(state='disabled')
        botao_enviar.config(state='normal')
        entrada.config(state='normal')
        entrada.focus()

    threading.Thread(target=thread_request, daemon=True).start()

# Interface gráfica profissional
janela = tk.Tk()
janela.title('Mini Assistente de IA')
janela.geometry('480x540')
janela.configure(bg='#222831')

# Estilo
fonte_titulo = ("Segoe UI", 18, "bold")
fonte_padrao = ("Segoe UI", 12)
cor_fundo = '#222831'
cor_entrada = '#393e46'
cor_texto = '#eeeeee'
cor_botao = '#00adb5'
cor_botao_texto = '#222831'

frame_top = tk.Frame(janela, bg=cor_fundo)
frame_top.pack(pady=10)

label_titulo = tk.Label(frame_top, text="Mini Assistente de IA", font=fonte_titulo, bg=cor_fundo, fg=cor_texto)
label_titulo.pack()

frame_api = tk.Frame(janela, bg=cor_fundo)
frame_api.pack(pady=5, fill=tk.X, padx=20)
tk.Label(frame_api, text="Chave API OpenAI:", font=fonte_padrao, bg=cor_fundo, fg=cor_texto).pack(side=tk.LEFT)
api_entry = tk.Entry(frame_api, show='*', font=fonte_padrao, bg=cor_entrada, fg=cor_texto, insertbackground=cor_texto)
api_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

frame_chat = tk.Frame(janela, bg=cor_fundo)
frame_chat.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)

chat_area = scrolledtext.ScrolledText(frame_chat, state='disabled', wrap=tk.WORD, font=fonte_padrao, bg=cor_entrada, fg=cor_texto, insertbackground=cor_texto, borderwidth=0, relief=tk.FLAT)
chat_area.pack(fill=tk.BOTH, expand=True)

frame_entrada = tk.Frame(janela, bg=cor_fundo)
frame_entrada.pack(padx=20, pady=10, fill=tk.X)

entrada = tk.Entry(frame_entrada, font=fonte_padrao, bg=cor_entrada, fg=cor_texto, insertbackground=cor_texto)
entrada.pack(side=tk.LEFT, fill=tk.X, expand=True)
entrada.bind('<Return>', lambda event: enviar())

botao_enviar = tk.Button(frame_entrada, text='Enviar', font=fonte_padrao, bg=cor_botao, fg=cor_botao_texto, activebackground=cor_botao, activeforeground=cor_texto, command=enviar, borderwidth=0, padx=20, pady=5)
botao_enviar.pack(side=tk.LEFT, padx=5)

janela.mainloop()
