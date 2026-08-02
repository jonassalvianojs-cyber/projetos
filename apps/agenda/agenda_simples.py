import json
from pathlib import Path

ARQUIVO = Path(__file__).with_name("agenda.json")


def carregar_agenda():
    if ARQUIVO.exists():
        with ARQUIVO.open("r", encoding="utf-8") as f:
            return json.load(f)
    return []


def salvar_agenda(agenda):
    with ARQUIVO.open("w", encoding="utf-8") as f:
        json.dump(agenda, f, indent=4, ensure_ascii=False)


def adicionar_contato(agenda):
    nome = input("Nome: ")
    telefone = input("Telefone: ")
    email = input("Email: ")

    agenda.append({
        "nome": nome,
        "telefone": telefone,
        "email": email
    })

    salvar_agenda(agenda)
    print("✅ Contato adicionado com sucesso!")


def listar_contatos(agenda):
    if not agenda:
        print("📭 Agenda vazia.")
        return

    for i, contato in enumerate(agenda, start=1):
        print(f"\nContato {i}")
        print(f"Nome: {contato['nome']}")
        print(f"Telefone: {contato['telefone']}")
        print(f"Email: {contato['email']}")


def buscar_contato(agenda):
    nome = input("Digite o nome para buscar: ").lower()
    encontrados = [c for c in agenda if nome in c["nome"].lower()]

    if not encontrados:
        print("❌ Contato não encontrado.")
        return

    for contato in encontrados:
        print(f"\nNome: {contato['nome']}")
        print(f"Telefone: {contato['telefone']}")
        print(f"Email: {contato['email']}")


def remover_contato(agenda):
    nome = input("Digite o nome do contato a remover: ").lower()
    nova_agenda = [c for c in agenda if nome not in c["nome"].lower()]

    if len(nova_agenda) == len(agenda):
        print("❌ Contato não encontrado.")
    else:
        salvar_agenda(nova_agenda)
        agenda.clear()
        agenda.extend(nova_agenda)
        print("🗑️ Contato removido com sucesso!")


def menu():
    print("\n📒 AGENDA")
    print("1 - Adicionar contato")
    print("2 - Listar contatos")
    print("3 - Buscar contato")
    print("4 - Remover contato")
    print("0 - Sair")
    return input("Escolha uma opção: ")


def main():
    agenda = carregar_agenda()

    while True:
        opcao = menu()

        if opcao == "1":
            adicionar_contato(agenda)
        elif opcao == "2":
            listar_contatos(agenda)
        elif opcao == "3":
            buscar_contato(agenda)
        elif opcao == "4":
            remover_contato(agenda)
        elif opcao == "0":
            print("👋 Saindo da agenda...")
            break
        else:
            print("⚠️ Opção inválida!")


if __name__ == "__main__":
    main()