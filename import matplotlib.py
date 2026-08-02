import matplotlib.pyplot as plt

# Configurações estéticas gerais
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['text.color'] = '#1a1a1a'
plt.rcParams['axes.labelcolor'] = '#1a1a1a'
plt.rcParams['xtick.color'] = '#1a1a1a'
plt.rcParams['ytick.color'] = '#1a1a1a'

# Criando a figura do dashboard (3 gráficos)
fig, axs = plt.subplots(1, 3, figsize=(18, 5))
fig.suptitle('Dashboard: População Indígena Contemporânea no Brasil (Censo IBGE)', fontsize=16, fontweight='bold', pad=20)

# Grafico 1: Distribuição por Região (Barras)
regioes = ['Norte', 'Nordeste', 'Centro-Oeste\n/ Sul / Sudeste']
porcentagens_regiao = [44.5, 31.2, 24.3]
cores_regiao = ['#006400', '#228B22', '#8FBC8F']

axs[0].bar(regioes, porcentagens_regiao, color=cores_regiao, width=0.5)
axs[0].set_title('Distribuição por Região (%)', fontsize=12, fontweight='bold', pad=10)
axs[0].set_ylim(0, 60)
for i, v in enumerate(porcentagens_regiao):
    axs[0].text(i, v + 1, f"{v}%", ha='center', fontweight='bold')
axs[0].spines['top'].set_visible(False)
axs[0].spines['right'].set_visible(False)

# Grafico 2: Local de Residência - Urbana vs Rural (Pizza)
labels_local = ['Urbana', 'Rural']
tamanhos_local = [53.97, 46.03]
cores_local = ['#4682B4', '#D2691E']

axs[1].pie(tamanhos_local, labels=labels_local, autopct='%1.1f%%', startangle=140, colors=cores_local, 
           textprops={'fontweight': 'bold'}, explode=(0.05, 0))
axs[1].set_title('Área de Residência (%)', fontsize=12, fontweight='bold', pad=10)

# Grafico 3: Localização em Relação às Terras Indígenas (Pizza)
labels_ti = ['Fora de TI', 'Dentro de TI']
tamanhos_ti = [63.3, 36.7]
cores_ti = ['#CD853F', '#556B2F']

axs[2].pie(tamanhos_ti, labels=labels_ti, autopct='%1.1f%%', startangle=90, colors=cores_ti, 
           textprops={'fontweight': 'bold'}, explode=(0.05, 0))
axs[2].set_title('Vínculo com Terras Indígenas (TI) (%)', fontsize=12, fontweight='bold', pad=10)

plt.tight_layout()

# Salva a imagem em arquivo local
saida = 'dashboard_populacao_indigena_brasil.png'
plt.savefig(saida, format='png', bbox_inches='tight', dpi=100)
plt.close()
print(f'Imagem salva em: {saida}')
