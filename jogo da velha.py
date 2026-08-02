def exibir_tabuleiro(tabuleiro):
    print(f"\n {tabuleiro[0]} | {tabuleiro[1]} | {tabuleiro[2]} ")
    print("-----------")
    print(f" {tabuleiro[3]} | {tabuleiro[4]} | {tabuleiro[5]} ")
    print("-----------")
    print(f" {tabuleiro[6]} | {tabuleiro[7]} | {tabuleiro[8]} \n")

def verificar_vitoria(tab, jogador):
    # Condições de vitória: linhas, colunas e diagonais
    vitoria = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8], # Horizontais
        [0, 3, 6], [1, 4, 7], [2, 5, 8], # Verticais
        [0, 4, 8], [2, 4, 6]             # Diagonais
    ]
    for condicao in vitoria:
        if all(tab[i] == jogador for i in condicao):
            return True
    return False

def jogar():
    tabuleiro = [str(i) for i in range(9)]
    jogador_atual = "X"
    jogadas = 0

    print("--- Jogo da Velha do Clay ---")
    
    while jogadas < 9:
        exibir_tabuleiro(tabuleiro)
        try:
            escolha = int(input(f"Jogador {jogador_atual}, escolha uma posição (0-8): "))
            
            if tabuleiro[escolha] not in ["X", "O"]:
                tabuleiro[escolha] = jogador_atual
                jogadas += 1
                
                if verificar_vitoria(tabuleiro, jogador_atual):
                    exibir_tabuleiro(tabuleiro)
                    print(f"Parabéns! O jogador {jogador_atual} venceu!")
                    return

                # Alterna o jogador
                jogador_atual = "O" if jogador_atual == "X" else "X"
            else:
                print("Essa posição já está ocupada. Tente novamente.")
        except (ValueError, IndexError):
            print("Entrada inválida. Digite um número entre 0 e 8.")

    exibir_tabuleiro(tabuleiro)
    print("Empate! Deu velha.")

if __name__ == "__main__":
    jogar()