#!/usr/bin/env python3
# Jogo da Cobrinha (Snake) em Python usando Pygame
# Salve como snake.py e execute: python snake.py
# Controles: setas ou WASD. R para reiniciar, Esc para sair.

import pygame
import random
import sys

# Configurações
WINDOW_WIDTH = 640
WINDOW_HEIGHT = 480
CELL_SIZE = 20  # tamanho do bloco (cobrinha e comida)
assert WINDOW_WIDTH % CELL_SIZE == 0 and WINDOW_HEIGHT % CELL_SIZE == 0
GRID_WIDTH = WINDOW_WIDTH // CELL_SIZE
GRID_HEIGHT = WINDOW_HEIGHT // CELL_SIZE

# Cores (R, G, B)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DARK_GRAY = (40, 40, 40)
RED = (200, 30, 30)
GREEN = (30, 200, 30)
YELLOW = (240, 200, 20)

# Velocidade inicial (frames por segundo)
INITIAL_SPEED = 8
SPEED_INCREMENT_EVERY = 5  # a cada quantas comidas aumenta a velocidade
SPEED_INCREMENT = 1

# Direções
UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)

def get_random_food_position(snake):
    while True:
        pos = (random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1))
        if pos not in snake:
            return pos

def draw_grid(surface):
    for x in range(0, WINDOW_WIDTH, CELL_SIZE):
        pygame.draw.line(surface, DARK_GRAY, (x, 0), (x, WINDOW_HEIGHT))
    for y in range(0, WINDOW_HEIGHT, CELL_SIZE):
        pygame.draw.line(surface, DARK_GRAY, (0, y), (WINDOW_WIDTH, y))

def draw_rect(surface, color, position):
    r = pygame.Rect((position[0] * CELL_SIZE, position[1] * CELL_SIZE), (CELL_SIZE, CELL_SIZE))
    pygame.draw.rect(surface, color, r)

def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Cobrinha - Snake")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 36)
    big_font = pygame.font.SysFont(None, 72)

    def reset_game():
        start_x = GRID_WIDTH // 2
        start_y = GRID_HEIGHT // 2
        snake = [(start_x, start_y), (start_x - 1, start_y), (start_x - 2, start_y)]
        direction = RIGHT
        food = get_random_food_position(snake)
        score = 0
        speed = INITIAL_SPEED
        return snake, direction, food, score, speed

    snake, direction, food, score, speed = reset_game()
    game_over = False

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                if not game_over:
                    # Movimento: evitar voltar na direção oposta imediatamente
                    if event.key in (pygame.K_UP, pygame.K_w) and direction != DOWN:
                        direction = UP
                    elif event.key in (pygame.K_DOWN, pygame.K_s) and direction != UP:
                        direction = DOWN
                    elif event.key in (pygame.K_LEFT, pygame.K_a) and direction != RIGHT:
                        direction = LEFT
                    elif event.key in (pygame.K_RIGHT, pygame.K_d) and direction != LEFT:
                        direction = RIGHT
                else:
                    # Game over: permitir reiniciar com R
                    if event.key == pygame.K_r:
                        snake, direction, food, score, speed = reset_game()
                        game_over = False

        if not game_over:
            # Mover a cobrinha
            new_head = (snake[0][0] + direction[0], snake[0][1] + direction[1])

            # Verificar colisão com parede
            if (new_head[0] < 0 or new_head[0] >= GRID_WIDTH or
                new_head[1] < 0 or new_head[1] >= GRID_HEIGHT):
                game_over = True
            else:
                # Verificar colisão com o próprio corpo
                if new_head in snake:
                    game_over = True
                else:
                    snake.insert(0, new_head)  # adiciona novo cabeçalho
                    # Verificar se comeu a comida
                    if new_head == food:
                        score += 1
                        # aumentar velocidade a cada SPEED_INCREMENT_EVERY comidas
                        if score % SPEED_INCREMENT_EVERY == 0:
                            speed += SPEED_INCREMENT
                        food = get_random_food_position(snake)
                    else:
                        snake.pop()  # remove a cauda

        # Desenho
        screen.fill(BLACK)
        draw_grid(screen)

        # Desenha comida
        draw_rect(screen, RED, food)

        # Desenha cobrinha
        for i, segment in enumerate(snake):
            color = GREEN if i == 0 else (50, 180, 50)
            draw_rect(screen, color, segment)

        # Texto: pontuação
        score_surf = font.render(f"Pontuação: {score}", True, YELLOW)
        screen.blit(score_surf, (10, 10))

        if game_over:
            overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 140))  # semi-transparente
            screen.blit(overlay, (0, 0))
            go_text = big_font.render("Game Over", True, WHITE)
            go_rect = go_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 30))
            screen.blit(go_text, go_rect)
            info_text = font.render("Pressione R para reiniciar ou Esc para sair", True, WHITE)
            info_rect = info_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 30))
            screen.blit(info_text, info_rect)

        pygame.display.flip()
        clock.tick(speed)

if __name__ == "__main__":
    main()