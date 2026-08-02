import json
from pathlib import Path

DATA_FILE = Path(__file__).with_name("dados.json")


def carregar_dados() -> list[dict]:
	"""Load saved records if the file exists."""
	if DATA_FILE.exists():
		try:
			with DATA_FILE.open("r", encoding="utf-8") as arquivo:
				return json.load(arquivo)
		except json.JSONDecodeError:
			return []
	return []


def salvar_dados(dados: list[dict]) -> None:
	with DATA_FILE.open("w", encoding="utf-8") as arquivo:
		json.dump(dados, arquivo, indent=2, ensure_ascii=False)


def coletar_registro() -> dict:
	print("\nPreencha os dados do registro:")
	return {
		"nome": input("Nome: ").strip(),
		"endereco": input("Endereco: ").strip(),
		"estado": input("Estado (ex: SP): ").strip().upper(),
		"telefone": input("Telefone: ").strip(),
		"profissao": input("Profissao: ").strip(),
	}


def listar_registros(dados: list[dict]) -> None:
	if not dados:
		print("\nNenhum registro salvo.")
		return

	print("\nRegistros armazenados:")
	for indice, registro in enumerate(dados, start=1):
		print(
			f"{indice}. Nome: {registro['nome']}, "
			f"Endereco: {registro['endereco']}, "
			f"Estado: {registro['estado']}, "
			f"Telefone: {registro['telefone']}, "
			f"Profissao: {registro['profissao']}"
		)


def main() -> None:
	dados = carregar_dados()
	print("=== Cadastro simples ===")

	while True:
		print("\nMenu:")
		print("1) Adicionar registro")
		print("2) Listar registros")
		print("3) Sair")
		escolha = input("Escolha uma opcao: ").strip()

		if escolha == "1":
			novo = coletar_registro()
			dados.append(novo)
			salvar_dados(dados)
			print("Registro salvo.")
		elif escolha == "2":
			listar_registros(dados)
		elif escolha == "3":
			print("Encerrando.")
			break
		else:
			print("Opcao invalida, tente novamente.")


if __name__ == "__main__":
	main()
