import os
import hashlib
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Escopo necessário para ler, editar e criar arquivos no Drive do usuário
SCOPES = ['https://www.googleapis.com/auth/drive']

# 1. Função para calcular o MD5 local (essencial para a otimização)
def calcular_md5(caminho_arquivo):
    hash_md5 = hashlib.md5()
    try:
        with open(caminho_arquivo, "rb") as f:
            for pedaco in iter(lambda: f.read(4096), b""):
                hash_md5.update(pedaco)
        return hash_md5.hexdigest()
    except Exception as e:
        print(f"[!] Erro ao calcular MD5 do arquivo {caminho_arquivo}: {e}")
        return None

# 2. Inicializar a API do Google Drive com fluxo de autenticação robusto
def conectar_drive():
    creds = None
    # O arquivo token.json guarda as credenciais de acesso do usuário após o primeiro login
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # Se não houver credenciais válidas, faz o login do usuário
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Salva as credenciais para a próxima execução
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('drive', 'v3', credentials=creds)

# 3. Listar arquivos na pasta do Google Drive com paginação completa
def listar_arquivos_no_drive(service, pasta_id):
    arquivos = []
    page_token = None
    
    while True:
        query = f"'{pasta_id}' in parents and trashed = false"
        resultados = service.files().list(
            q=query,
            spaces='drive',
            fields="nextPageToken, files(id, name, md5Checksum)",
            pageToken=page_token
        ).execute()
        
        arquivos.extend(resultados.get('files', []))
        page_token = resultados.get('nextPageToken', None)
        
        if not page_token:
            break
            
    # Retorna dicionário mapeando nome do arquivo -> dados (id e md5)
    return {f['name']: f for f in arquivos}

# 4. Algoritmo Incremental Principal
def executar_backup_incremental(pasta_local, pasta_id_drive):
    service = conectar_drive()
    print("[*] Conectado ao Google Drive com sucesso! Buscando arquivos remotos...")
    arquivos_no_drive = listar_arquivos_no_drive(service, pasta_id_drive)
    print(f"[*] Encontrados {len(arquivos_no_drive)} arquivos na pasta de destino do Drive.")
    
    for raiz, _, arquivos in os.walk(pasta_local):
        for nome_arquivo in arquivos:
            caminho_completo = os.path.join(raiz, nome_arquivo)
            md5_local = calcular_md5(caminho_completo)
            
            if not md5_local:
                continue # Pula se houver erro de leitura
            
            # Se o arquivo já existe no Drive (comparação por nome simples)
            if nome_arquivo in arquivos_no_drive:
                dados_drive = arquivos_no_drive[nome_arquivo]
                md5_drive = dados_drive.get('md5Checksum')
                file_id = dados_drive.get('id')
                
                if md5_local == md5_drive:
                    print(f"[-] {nome_arquivo} já está atualizado no Drive. Pulando...")
                else:
                    print(f"[^] {nome_arquivo} modificado localmente. Atualizando versão no Drive...")
                    media = MediaFileUpload(caminho_completo, mimetype='application/octet-stream', resumable=True)
                    service.files().update(
                        fileId=file_id,
                        media_body=media
                    ).execute()
                    print(f"[^] {nome_arquivo} atualizado com sucesso!")
            else:
                print(f"[+] {nome_arquivo} é um arquivo novo. Fazendo upload...")
                file_metadata = {
                    'name': nome_arquivo,
                    'parents': [pasta_id_drive]
                }
                media = MediaFileUpload(caminho_completo, mimetype='application/octet-stream', resumable=True)
                novo_arquivo = service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                print(f"[+] {nome_arquivo} enviado com ID: {novo_arquivo.get('id')}")