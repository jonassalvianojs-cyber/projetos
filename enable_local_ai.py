import json
import os
import subprocess
import time

local_state_path = os.path.expanduser('~/.config/google-chrome/Local State')

print("🍑 Fechando o Chrome para aplicar as alterações com segurança...")
# Matar processos do Chrome para evitar que ele sobrescreva o arquivo ao fechar
subprocess.run(["pkill", "-f", "/opt/google/chrome/chrome"])
time.sleep(2)  # Aguarda o encerramento completo

# Carregar o Local State
if os.path.exists(local_state_path):
    try:
        with open(local_state_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Erro ao ler o arquivo Local State: {e}")
        data = {}
else:
    data = {}

if 'browser' not in data:
    data['browser'] = {}

# Obter ou criar a lista de experimentos
experiments = data['browser'].get('enabled_labs_experiments', [])

# Flags que precisamos para ativar o Gemini Nano
flags_to_add = [
    "optimization-guide-on-device-model@2",  # Enabled BypassPerfRequirement
    "prompt-api-for-gemini-nano@1"            # Enabled
]

# Remover flags antigas semelhantes e adicionar as novas
new_experiments = []
for exp in experiments:
    if not exp.startswith("optimization-guide-on-device-model") and not exp.startswith("prompt-api-for-gemini-nano"):
        new_experiments.append(exp)

new_experiments.extend(flags_to_add)
data['browser']['enabled_labs_experiments'] = new_experiments

# Gravar de volta no Local State
try:
    with open(local_state_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print("✅ Flags do Gemini Nano e Prompt API configuradas com sucesso no arquivo Local State!")
except Exception as e:
    print(f"❌ Erro ao salvar o arquivo Local State: {e}")

# Reabrir o Chrome com a página do testador
print("🚀 Reabrindo o Chrome...")
env = os.environ.copy()
env["DISPLAY"] = ":0"
subprocess.Popen(["/opt/google/chrome/chrome", "file:///home/jonas/projetos/teste_ia_local.html"], env=env, start_new_session=True)
print("✨ Prontinho!")
