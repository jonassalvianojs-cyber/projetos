import pygame
import random
import math
import sys

# Inicializa o Pygame
pygame.init()

# Configurações da tela
LARGURA = 800
ALTURA = 600
tela = pygame.display.set_mode((LARGURA, ALTURA))
pygame.display.set_caption("Space Invaders - Clay Edition")

# Cores
PRETO = (0, 0, 0)
BRANCO = (255, 255, 255)
VERDE = (0, 255, 0)
VERMELHO = (255, 0, 0)
AZUL = (0, 150, 255)

# Relógio
clock = pygame.time.Clock()
FPS = 60

# Fonte
fonte = pygame.font.SysFont("arial", 24, True)


# -----------------------------
# CLASSES DO JOGO
# -----------------------------

class Jogador:
    def __init__(self):
        self.largura = 50
        self.altura = 30
        self.x = LARGURA // 2 - self.largura // 2
        self.y = ALTURA - self.altura - 20
        self.velocidade = 5
        self.cor = VERDE
        self.vida = 3

    def mover(self, teclas):
        if teclas[pygame.K_LEFT] or teclas[pygame.K_a]:
            self.x -= self.velocidade
        if teclas[pygame.K_RIGHT] or teclas[pygame.K_d]:
            self.x += self.velocidade

        # Limites da tela
        if self.x < 0:
            self.x = 0
        if self.x + self.largura > LARGURA:
            self.x = LARGURA - self.largura

    def desenhar(self, tela):
        pygame.draw.rect(tela, self.cor, (self.x, self.y, self.largura, self.altura))
        # "canhão" do jogador
        pygame.draw.rect(
            tela,
            self.cor,
            (self.x + self.largura // 2 - 5, self.y - 10, 10, 10),
        )


class Tiro:
    def __init__(self, x, y, vel_y, cor=BRANCO, dono="player"):
        self.x = x
        self.y = y
        self.largura = 4
        self.altura = 12
        self.vel_y = vel_y
        self.cor = cor
        self.dono = dono  # "player" ou "inimigo"

    def atualizar(self):
        self.y += self.vel_y

    def desenhar(self, tela):
        pygame.draw.rect(tela, self.cor, (self.x, self.y, self.largura, self.altura))

    def fora_da_tela(self):
        return self.y < -self.altura or self.y > ALTURA + self.altura


class Inimigo:
    def __init__(self, x, y):
        self.largura = 40
        self.altura = 25
        self.x = x
        self.y = y
        self.cor = VERMELHO
        self.ativo = True

    def desenhar(self, tela):
        if self.ativo:
            pygame.draw.rect(tela, self.cor, (self.x, self.y, self.largura, self.altura))

    def get_centro(self):
        return self.x + self.largura // 2, self.y + self.altura // 2


# -----------------------------
# FUNÇÕES ÚTEIS
# -----------------------------

def criar_inimigos(linhas=4, colunas=8, espacamento_x=20, espacamento_y=20):
    inimigos = []
    margem = 60
    for linha in range(linhas):
        for coluna in range(colunas):
            x = margem + coluna * (40 + espacamento_x)
            y = margem + linha * (25 + espacamento_y)
            inimigos.append(Inimigo(x, y))
    return inimigos


def colisao_retangular(obj1, obj2):
    return (
        obj1.x < obj2.x + obj2.largura
        and obj1.x + obj1.largura > obj2.x
        and obj1.y < obj2.y + obj2.altura
        and obj1.y + obj1.altura > obj2.y
    )


def desenhar_texto(tela, texto, x, y, cor=BRANCO, centro=False):
    superficie = fonte.render(texto, True, cor)
    rect = superficie.get_rect()
    if centro:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    tela.blit(superficie, rect)


# -----------------------------
# LOOP PRINCIPAL DO JOGO
# -----------------------------

def jogo():
    jogador = Jogador()
    tiros = []
    tiros_inimigos = []
    inimigos = criar_inimigos()

    vel_inimigos_x = 1
    direcao = 1  # 1 direita, -1 esquerda
    descida_inimigo = 15

    recarga_tiro = 0
    recarga_tiro_max = 15

    recarga_tiro_inimigo = 0
    recarga_tiro_inimigo_max = 60

    pontuacao = 0
    rodando = True
    game_over = False
    vitoria = False

    while rodando:
        clock.tick(FPS)
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    rodando = False
                if game_over or vitoria:
                    if evento.key == pygame.K_RETURN:
                        # Reinicia o jogo
                        return jogo()

        teclas = pygame.key.get_pressed()

        if not game_over and not vitoria:
            # Movimento do jogador
            jogador.mover(teclas)

            # Disparo do jogador
            if recarga_tiro > 0:
                recarga_tiro -= 1

            if (teclas[pygame.K_SPACE] or teclas[pygame.K_UP]) and recarga_tiro == 0:
                x_tiro = jogador.x + jogador.largura // 2 - 2
                y_tiro = jogador.y - 10
                tiros.append(Tiro(x_tiro, y_tiro, vel_y=-8, cor=BRANCO, dono="player"))
                recarga_tiro = recarga_tiro_max

            # Movimento dos inimigos
            mover_para_baixo = False
            min_x = LARGURA
            max_x = 0

            for inimigo in inimigos:
                if not inimigo.ativo:
                    continue
                inimigo.x += vel_inimigos_x * direcao
                if inimigo.x < min_x:
                    min_x = inimigo.x
                if inimigo.x + inimigo.largura > max_x:
                    max_x = inimigo.x + inimigo.largura

            # Verifica limites para mudar direção
            if min_x <= 10 and direcao == -1:
                mover_para_baixo = True
                direcao = 1
            if max_x >= LARGURA - 10 and direcao == 1:
                mover_para_baixo = True
                direcao = -1

            if mover_para_baixo:
                for inimigo in inimigos:
                    if inimigo.ativo:
                        inimigo.y += descida_inimigo

            # Tiros do inimigo
            if recarga_tiro_inimigo > 0:
                recarga_tiro_inimigo -= 1
            else:
                inimigos_ativos = [i for i in inimigos if i.ativo]
                if inimigos_ativos:
                    atirador = random.choice(inimigos_ativos)
                    x_centro, y_centro = atirador.get_centro()
                    # alinhar tiro ao centro do inimigo (Tiro largura = 4)
                    tiros_inimigos.append(
                        Tiro(
                            x_centro - 2,
                            y_centro + 10,
                            vel_y=5,
                            cor=AZUL,
                            dono="inimigo",
                        )
                    )
                    recarga_tiro_inimigo = recarga_tiro_inimigo_max

            # Atualiza tiros do jogador
            for tiro in tiros[:]:
                tiro.atualizar()
                if tiro.fora_da_tela():
                    tiros.remove(tiro)
                    continue

                # Colisão com inimigos
                for inimigo in inimigos:
                    if inimigo.ativo:
                        # usar pygame.Rect para colisões mais claras
                        tiro_rect = pygame.Rect(tiro.x, tiro.y, tiro.largura, tiro.altura)
                        inimigo_rect = pygame.Rect(
                            inimigo.x, inimigo.y, inimigo.largura, inimigo.altura
                        )

                        if tiro_rect.colliderect(inimigo_rect):
                            inimigo.ativo = False
                            pontuacao += 10
                            if tiro in tiros:
                                tiros.remove(tiro)
                            break

            # Atualiza tiros dos inimigos
            for tiro in tiros_inimigos[:]:
                tiro.atualizar()
                if tiro.fora_da_tela():
                    tiros_inimigos.remove(tiro)
                    continue

                # usar pygame.Rect para colisão com o jogador
                player_rect = pygame.Rect(jogador.x, jogador.y, jogador.largura, jogador.altura)
                tiro_rect = pygame.Rect(tiro.x, tiro.y, tiro.largura, tiro.altura)

                if tiro_rect.colliderect(player_rect):
                    if tiro in tiros_inimigos:
                        tiros_inimigos.remove(tiro)
                    jogador.vida -= 1
                    if jogador.vida <= 0:
                        game_over = True

            # Verifica se algum inimigo chegou na parte de baixo
            for inimigo in inimigos:
                if inimigo.ativo and inimigo.y + inimigo.altura >= jogador.y:
                    game_over = True
                    break

            # Verifica vitória
            if all(not i.ativo for i in inimigos):
                vitoria = True

        # DESENHO NA TELA
        tela.fill(PRETO)

        # Desenha jogador
        jogador.desenhar(tela)

        # Desenha inimigos
        for inimigo in inimigos:
            inimigo.desenhar(tela)

        # Desenha tiros
        for tiro in tiros:
            tiro.desenhar(tela)
        for tiro in tiros_inimigos:
            tiro.desenhar(tela)

        # HUD
        desenhar_texto(tela, f"Pontuação: {pontuacao}", 10, 10)
        desenhar_texto(tela, f"Vidas: {jogador.vida}", 10, 40)

        if game_over:
            desenhar_texto(
                tela,
                "GAME OVER",
                LARGURA // 2,
                ALTURA // 2 - 30,
                cor=VERMELHO,
                centro=True,
            )
            desenhar_texto(
                tela,
                "Pressione ENTER para jogar novamente",
                LARGURA // 2,
                ALTURA // 2 + 10,
                centro=True,
            )

        if vitoria:
            desenhar_texto(
                tela,
                "VITÓRIA!",
                LARGURA // 2,
                ALTURA // 2 - 30,
                cor=VERDE,
                centro=True,
            )
            desenhar_texto(
                tela,
                "Pressione ENTER para jogar novamente",
                LARGURA // 2,
                ALTURA // 2 + 10,
                centro=True,
            )

        pygame.display.flip()

    # Sai do jogo
    pygame.quit()


if __name__ == "__main__":
    jogo()
