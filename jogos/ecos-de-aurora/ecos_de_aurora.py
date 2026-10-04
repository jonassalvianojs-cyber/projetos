"""Ecos de Aurora. Execute com Python 3.10+ e Tkinter. Veja README.txt."""
import json
import math
import random
import time
from pathlib import Path
import tkinter as tk

W, H, TILE, COLS, ROWS = 960, 640, 40, 64, 48
SAVE = Path.home() / '.ecos_de_aurora_save.json'
SHRINES = [(12, 10), (49, 12), (17, 37)]
BOSS = (51, 37)


class Game:
    def __init__(self, root):
        self.root = root
        root.title('Ecos de Aurora • RPG de aventura')
        root.resizable(False, False)
        self.c = tk.Canvas(root, width=W, height=H, bg='#101e29', highlightthickness=0)
        self.c.pack()
        self.keys = set()
        self.mode = 'title'
        self.map_open = False
        self.last = time.monotonic()
        self.reset()
        root.bind('<KeyPress>', self.press)
        root.bind('<KeyRelease>', lambda e: self.keys.discard(e.keysym.lower()))
        root.bind('<FocusOut>', self.focus_out)
        self.tick()

    def reset(self):
        rng = random.Random(18)
        self.tiles = [[0 for _ in range(COLS)] for _ in range(ROWS)]
        for y in range(ROWS):
            for x in range(COLS):
                edge = x < 2 or y < 2 or x > 61 or y > 45
                water = 28 <= x <= 32 and y not in range(21, 26)
                self.tiles[y][x] = 2 if water else (1 if edge or rng.random() < .12 else 0)
        # Guaranteed clear trails connect every objective to camp.
        self.trails = set()
        for tx, ty in SHRINES + [BOSS, (8, 24), (40, 24), (43, 8), (10, 34)]:
            for x in range(min(8, tx), max(8, tx) + 1):
                for dy in (-1, 0, 1):
                    self.tiles[24 + dy][x] = 0
                    self.trails.add((x, 24 + dy))
            for y in range(min(24, ty), max(24, ty) + 1):
                for dx in (-1, 0, 1):
                    self.tiles[y][tx + dx] = 0
                    self.trails.add((tx + dx, y))
            for y in range(ty - 3, ty + 4):
                for x in range(tx - 3, tx + 4):
                    self.tiles[y][x] = 0
        self.x, self.y = 8.5 * TILE, 24.5 * TILE
        self.face = (1, 0)
        self.hp, self.maxhp, self.level, self.xp = 8, 8, 1, 0
        self.coins, self.potions = 0, 3
        self.crystals, self.opened = set(), set()
        self.invuln = self.attack = self.cooldown = self.dash = self.dash_cd = 0
        self.boss_dead = False
        self.effects = []
        self.message = 'E: fale com a guardiã junto à fogueira.'
        self.msg_time = 7
        self.chests = [(10, 34), (43, 8), (40, 24), (19, 14)]
        for tx, ty in self.chests:
            for yy in range(ty - 1, ty + 2):
                for xx in range(tx - 1, tx + 2):
                    self.tiles[yy][xx] = 0
        self.enemies = []
        for i, (tx, ty) in enumerate(SHRINES):
            for dx, dy in [(-2, 1), (2, 1), (0, -2)]:
                self.enemy((tx + dx + .5) * TILE, (ty + dy + .5) * TILE, i)
        for tx, ty in [(18, 24), (24, 23), (39, 24), (47, 22), (17, 30), (12, 17)]:
            self.enemy((tx + .5) * TILE, (ty + .5) * TILE, -1)
        self.enemy(51.5 * TILE, 37.5 * TILE, 3, True)

    def enemy(self, x, y, group, boss=False):
        self.enemies.append(dict(x=x, y=y, ox=x, oy=y, group=group,
                                 hp=30 if boss else 3, maxhp=30 if boss else 3,
                                 boss=boss, flash=0, timer=2.0, warning=0))

    def focus_out(self, _):
        self.keys.clear()
        if self.mode == 'play':
            self.mode = 'pause'

    def say(self, message):
        self.message, self.msg_time = message, 6

    def press(self, e):
        k = e.keysym.lower()
        fresh = k not in self.keys
        self.keys.add(k)
        if not fresh:
            return
        if k == 'return' and self.mode in ('title', 'dead', 'win'):
            self.reset()
            self.mode = 'play'
        elif k == 'f9':
            self.load()
        elif k == 'escape' and self.mode in ('play', 'pause'):
            self.mode = 'pause' if self.mode == 'play' else 'play'
        elif self.mode == 'play':
            if k == 'm':
                self.map_open = not self.map_open
            elif k == 'f5':
                self.save()
            elif k == 'e':
                self.interact()
            elif k == 'q' and self.potions and self.hp < self.maxhp:
                self.potions -= 1
                self.hp = min(self.maxhp, self.hp + 5)
                self.say('Poção usada: +5 de vida.')
            elif k in ('shift_l', 'shift_r') and self.dash_cd <= 0:
                self.dash, self.dash_cd = .17, 1.1
                self.invuln = max(self.invuln, .24)
            elif k == 'space' and self.cooldown <= 0:
                self.swing()

    def walkable(self, x, y):
        for dx, dy in [(-10, -9), (10, -9), (-10, 9), (10, 9)]:
            tx, ty = int((x + dx) // TILE), int((y + dy) // TILE)
            if not (0 <= tx < COLS and 0 <= ty < ROWS) or self.tiles[ty][tx]:
                return False
        return True

    def move(self, obj, dx, dy):
        if self.walkable(obj['x'] + dx, obj['y']):
            obj['x'] += dx
        if self.walkable(obj['x'], obj['y'] + dy):
            obj['y'] += dy

    def swing(self):
        self.attack, self.cooldown = .2, .34
        fx, fy = self.face
        for en in self.enemies:
            dx, dy = en['x'] - self.x, en['y'] - self.y
            dist = math.hypot(dx, dy)
            if en['hp'] > 0 and dist < (92 if en['boss'] else 76) and (dist < 25 or (dx * fx + dy * fy) / dist > .15):
                if en['boss'] and len(self.crystals) < 3:
                    self.say('O escudo ancestral exige os três cristais.')
                    continue
                en['hp'] -= 1 + (self.level - 1) // 2
                en['flash'] = .16
                if not en['boss'] and dist:
                    self.move(en, dx / dist * 18, dy / dist * 18)
                if en['hp'] <= 0:
                    self.coins += 5
                    self.gain_xp(12 if not en['boss'] else 80)
                    if en['boss']:
                        self.boss_dead = True
                        self.mode = 'win'
                        self.save(quiet=True)

    def gain_xp(self, amount):
        self.xp += amount
        while self.xp >= self.level * 35:
            self.xp -= self.level * 35
            self.level += 1
            self.maxhp += 2
            self.hp = self.maxhp
            self.say(f'Nível {self.level}! Vida restaurada e atributos aumentados.')

    def near(self, tx, ty, distance=85):
        return math.hypot(self.x - (tx + .5) * TILE, self.y - (ty + .5) * TILE) < distance

    def interact(self):
        if self.near(8, 24):
            self.hp = self.maxhp
            self.save(quiet=True)
            self.say('Fogueira: vida restaurada e progresso salvo.')
            return
        if self.near(10, 24):
            if self.coins >= 15 and self.hp == self.maxhp:
                self.coins -= 15
                self.potions += 1
                self.say('Guardiã: uma poção por 15 moedas. Boa jornada!')
            else:
                self.say('Guardiã: encontre 3 cristais; depois vá às ruínas no sudeste. Poção: 15 moedas.')
            return
        for i, (tx, ty) in enumerate(self.chests):
            if i not in self.opened and self.near(tx, ty):
                self.opened.add(i)
                self.coins += 15
                self.potions += 1
                self.gain_xp(10)
                self.save(quiet=True)
                self.say('Tesouro! +15 moedas, +1 poção e +10 experiência.')
                return
        for i, (tx, ty) in enumerate(SHRINES):
            if i not in self.crystals and self.near(tx, ty):
                if any(en['hp'] > 0 and en['group'] == i for en in self.enemies):
                    self.say('Derrote os três sentinelas deste santuário primeiro.')
                else:
                    self.crystals.add(i)
                    self.gain_xp(25)
                    self.hp = self.maxhp
                    self.save(quiet=True)
                    self.say(f'Cristal recuperado! {len(self.crystals)}/3. ' + ('Siga às ruínas no sudeste!' if len(self.crystals) == 3 else 'A floresta recupera sua luz.'))
                return
        self.say('Aproxime-se de um baú, fogueira, guardiã ou cristal e pressione E.')

    def save(self, quiet=False):
        data = {k: getattr(self, k) for k in ('x', 'y', 'hp', 'maxhp', 'level', 'xp', 'coins', 'potions', 'boss_dead')}
        data.update(version=1, crystals=sorted(self.crystals), opened=sorted(self.opened), enemies=self.enemies)
        try:
            temp = SAVE.with_suffix('.tmp')
            temp.write_text(json.dumps(data), encoding='utf-8')
            temp.replace(SAVE)
            if not quiet:
                self.say('Progresso salvo. F9 para continuar depois.')
        except OSError:
            self.say('Não foi possível salvar na pasta pessoal.')

    def load(self):
        try:
            data = json.loads(SAVE.read_text(encoding='utf-8'))
            assert data['version'] == 1
            for k in ('x', 'y', 'hp', 'maxhp', 'level', 'xp', 'coins', 'potions'):
                assert isinstance(data[k], (int, float)) and math.isfinite(data[k])
            assert 1 <= data['level'] <= 100 and 0 < data['maxhp'] <= 1000
            assert isinstance(data['enemies'], list) and len(data['enemies']) == 16
            for en in data['enemies']:
                for k in ('x', 'y', 'ox', 'oy', 'group', 'hp', 'maxhp', 'flash', 'timer', 'warning'):
                    assert isinstance(en[k], (int, float)) and math.isfinite(en[k])
                assert isinstance(en['boss'], bool)
            crystals, opened = set(data['crystals']), set(data['opened'])
            assert crystals <= {0, 1, 2} and opened <= {0, 1, 2, 3}
            assert 0 <= data['x'] < COLS * TILE and 0 <= data['y'] < ROWS * TILE
            self.reset()
            for k in ('x', 'y', 'hp', 'maxhp', 'level', 'xp', 'coins', 'potions', 'boss_dead', 'enemies'):
                setattr(self, k, data[k])
            self.crystals, self.opened = crystals, opened
            if not self.walkable(self.x, self.y) or self.hp <= 0:
                self.x, self.y, self.hp = 340, 980, self.maxhp
            self.mode = 'win' if self.boss_dead else 'play'
            self.say('Jornada restaurada.')
        except (OSError, ValueError, KeyError, TypeError, AssertionError):
            self.say('Nenhum progresso válido encontrado. Enter inicia uma aventura.')

    def update(self, dt):
        for attr in ('invuln', 'attack', 'cooldown', 'dash', 'dash_cd', 'msg_time'):
            setattr(self, attr, max(0, getattr(self, attr) - dt))
        dx = int(bool(self.keys & {'d', 'right'})) - int(bool(self.keys & {'a', 'left'}))
        dy = int(bool(self.keys & {'s', 'down'})) - int(bool(self.keys & {'w', 'up'}))
        length = math.hypot(dx, dy)
        if length:
            self.face = (dx / length, dy / length)
        if self.dash > 0 or length:
            speed = 470 if self.dash > 0 else 175
            p = dict(x=self.x, y=self.y)
            self.move(p, self.face[0] * speed * dt, self.face[1] * speed * dt)
            self.x, self.y = p['x'], p['y']
        for en in self.enemies:
            if en['hp'] <= 0:
                continue
            en['flash'] = max(0, en['flash'] - dt)
            dx, dy = self.x - en['x'], self.y - en['y']
            dist = math.hypot(dx, dy)
            if en['boss']:
                if len(self.crystals) < 3 or dist > 390:
                    continue
                if en['warning'] > 0:
                    en['warning'] -= dt
                    if en['warning'] <= 0 and dist < 125:
                        self.hurt(3)
                else:
                    en['timer'] -= dt
                    if en['timer'] <= 0:
                        en['warning'], en['timer'] = .85, 2.6
                    elif dist > 45:
                        self.move(en, dx / dist * 65 * dt, dy / dist * 65 * dt)
            elif 0 < dist < 240:
                self.move(en, dx / dist * 77 * dt, dy / dist * 77 * dt)
            if dist < (38 if en['boss'] else 25):
                self.hurt(2 if en['boss'] else 1)

    def hurt(self, damage):
        if self.invuln <= 0:
            self.hp -= damage
            self.invuln = 1.0
            if self.hp <= 0:
                self.hp, self.mode = 0, 'dead'

    def text(self, x, y, value, size=12, color='#f4ebd5', anchor='nw', bold=False):
        return self.c.create_text(x, y, text=value, fill=color, anchor=anchor,
                                  font=('DejaVu Sans', size, 'bold' if bold else 'normal'))

    def rect(self, x, y, w, h, color, outline=''):
        self.c.create_rectangle(x, y, x+w, y+h, fill=color, outline=outline)

    def oval(self, x, y, w, h, color, outline=''):
        self.c.create_oval(x, y, x+w, y+h, fill=color, outline=outline)

    def draw(self):
        c = self.c
        c.delete('all')
        cx = min(max(self.x - W/2, 0), COLS*TILE-W)
        cy = min(max(self.y - H/2, 0), ROWS*TILE-H)
        self.camera = (cx, cy)
        for ty in range(int(cy // TILE), min(ROWS, int((cy+H)//TILE)+1)):
            for tx in range(int(cx // TILE), min(COLS, int((cx+W)//TILE)+1)):
                x, y = tx*TILE-cx, ty*TILE-cy
                kind = self.tiles[ty][tx]
                shade = (tx*17+ty*31) % 4
                base = ['#304f40', '#345441', '#385942', '#36533e'][shade]
                if (tx, ty) in self.trails:
                    base = '#6b6b4a'
                if tx > 43 and ty > 30:
                    base = ['#45545a', '#49595d'][shade % 2]
                self.rect(x, y, TILE+1, TILE+1, '#235566' if kind == 2 else base)
                if kind == 2:
                    offset = math.sin(time.monotonic()*2 + ty) * 4
                    c.create_line(x+8+offset, y+18, x+25+offset, y+18, fill='#4d8790', width=2)
                elif kind == 1:
                    self.oval(x+2, y+23, 37, 15, '#233d33')
                    self.rect(x+17, y+15, 7, 23, '#77523d')
                    self.oval(x-2, y-4, 43, 35, '#173c35')
                    self.oval(x+3, y-5, 31, 25, '#26604b')
                    self.rect(x+10, y+1, 9, 4, '#458365')
                elif shade == 0:
                    c.create_line(x+10, y+28, x+8, y+23, x+12, y+25, fill='#779264')
        # Landmarks are all drawn in world coordinates.
        for i, (tx, ty) in enumerate(SHRINES):
            x, y = (tx+.5)*TILE-cx, (ty+.5)*TILE-cy
            self.oval(x-49, y-28, 98, 58, '#3f6261', '#94b4a1')
            self.rect(x-19, y-8, 38, 25, '#8a9a8a')
            if i not in self.crystals:
                bob = math.sin(time.monotonic()*2)*4
                c.create_polygon(x, y-42+bob, x+13, y-25+bob, x, y-8+bob, x-13, y-25+bob,
                                 fill=['#76e3c3', '#9bc5ff', '#e8b6fa'][i], outline='#e8fff6', width=2)
            self.text(x, y+34, ['Santuário da Folha', 'Santuário da Brisa', 'Santuário da Lua'][i], 9, anchor='center')
        for i, (tx, ty) in enumerate(self.chests):
            x, y = (tx+.5)*TILE-cx, (ty+.5)*TILE-cy
            self.rect(x-15, y-11, 30, 23, '#5b4434' if i in self.opened else '#bc8645', '#e3c185')
            self.rect(x-2, y-9, 4, 16, '#e8ce87')
            if i in self.opened:
                self.rect(x-12, y-8, 24, 8, '#262b2c')
        x, y = 340-cx, 980-cy
        self.oval(x-28, y-14, 56, 35, '#273f37', '#b7ad84')
        c.create_polygon(x-13, y+7, x-5, y-22, x+3, y-9, x+9, y-27, x+16, y+7, fill='#f2a34c')
        self.text(x, y+32, 'FOGUEIRA · E', 9, anchor='center')
        self.person(420-cx, 980-cy, '#a29cdb', npc=True)
        self.text(420-cx, 1018-cy, 'Guardiã · E', 9, anchor='center')
        bx, by = 2060-cx, 1500-cy
        self.oval(bx-120, by-100, 240, 200, '', '#718782')
        for ox, oy in [(-110, -80), (90, -80), (-110, 65), (90, 65)]:
            self.rect(bx+ox, by+oy, 21, 44, '#84938b', '#bac3aa')
        for en in sorted(self.enemies, key=lambda a: a['y']):
            if en['hp'] <= 0:
                continue
            x, y = en['x']-cx, en['y']-cy
            if not (-150 < x < W+150 and -150 < y < H+150):
                continue
            if en['warning'] > 0:
                self.oval(x-125, y-125, 250, 250, '', '#ff9e73')
                self.text(x, y-65, 'AFASTE-SE!', 12, '#ffb58d', 'center', True)
            size = 30 if en['boss'] else 17
            self.oval(x-size, y-6, size*2, size, '#20372f')
            color = '#f5e6d3' if en['flash'] else ('#a17bb6' if en['boss'] else '#b87573')
            self.oval(x-size, y-size, size*2, size*1.6, color, '#352e47')
            self.rect(x-9, y-9, 5, 5, '#fff0bb')
            self.rect(x+5, y-9, 5, 5, '#fff0bb')
            if en['boss']:
                c.create_polygon(x-23, y-21, x-30, y-45, x-9, y-28, x+9, y-28, x+30, y-45, x+23, y-21, fill='#d9b981')
                self.text(x, y-61, 'GUARDIÃO DO ECLIPSE', 10, anchor='center', bold=True)
            self.rect(x-size, y+size, size*2, 4, '#202e32')
            self.rect(x-size, y+size, size*2*max(0,en['hp'])/en['maxhp'], 4, '#e5ab89')
        px, py = self.x-cx, self.y-cy
        if self.invuln <= 0 or int(time.monotonic()*16) % 2:
            self.person(px, py, '#53b7ac')
        if self.attack > 0:
            angle = math.degrees(math.atan2(-self.face[1], self.face[0]))
            c.create_arc(px-66, py-66, px+66, py+66, start=angle-65, extent=130,
                         style='arc', outline='#fff3bf', width=8)
            c.create_line(px+self.face[0]*20, py+self.face[1]*20,
                          px+self.face[0]*66, py+self.face[1]*66, fill='#ecf9ef', width=5)
        self.hud()
        if self.map_open:
            self.minimap(240, 123, 7)
        if self.mode != 'play':
            self.overlay()

    def person(self, x, y, color, npc=False):
        self.oval(x-15, y+8, 30, 12, '#213c33')
        self.rect(x-9, y+7, 7, 12, '#293747')
        self.rect(x+3, y+7, 7, 12, '#293747')
        self.rect(x-12, y-12, 24, 24, color)
        self.rect(x-8, y-24, 16, 16, '#e7bf8f')
        self.rect(x-10, y-29, 20, 9, '#ebe1bc' if npc else '#493e3a')
        self.rect(x-12, y+3, 24, 5, '#684b3c')
        if not npc:
            self.rect(x-19, y-4, 9, 17, '#bca36e', '#e6d5a4')

    def hud(self):
        self.rect(0, 0, W, 79, '#13282d')
        self.text(22, 13, 'ECOS DE AURORA', 16, '#e8d6a5', bold=True)
        self.text(23, 44, f'Vida {self.hp}/{self.maxhp}   •   Nível {self.level}   •   XP {self.xp}/{self.level*35}', 11)
        self.text(340, 16, f'◈ {len(self.crystals)}/3 cristais    ● {self.coins} moedas    ✦ {self.potions} poções', 12)
        self.text(340, 45, 'Missão: ' + ('vença o Guardião no sudeste' if len(self.crystals)==3 else 'recupere os três cristais'), 11, '#9fceb9')
        self.minimap(805, 9, 2)
        self.rect(0, H-35, W, 35, '#13282d')
        self.text(20, H-25, 'WASD mover  •  Espaço espada  •  E interagir  •  Q poção  •  Shift esquiva  •  M mapa  •  Esc pausa', 10)
        if self.msg_time > 0:
            self.rect(24, H-94, W-48, 44, '#20373b', '#7b927d')
            self.text(W/2, H-72, self.message, 10, anchor='center')

    def minimap(self, x, y, s):
        self.rect(x-5, y-5, COLS*s+10, ROWS*s+10, '#142930', '#9caa83')
        for ty in range(ROWS):
            for tx in range(COLS):
                if self.tiles[ty][tx] == 2:
                    self.rect(x+tx*s, y+ty*s, s, s, '#3b7182')
        for i, (tx, ty) in enumerate(SHRINES):
            color = '#67806e' if i in self.crystals else '#a4f5de'
            self.oval(x+tx*s-3, y+ty*s-3, 7, 7, color)
        self.rect(x+51*s-3, y+37*s-3, 7, 7, '#e194a1')
        self.rect(x+8*s-3, y+24*s-3, 6, 6, '#f4bd6b')
        self.oval(x+self.x/TILE*s-3, y+self.y/TILE*s-3, 7, 7, '#fff9db')
        if s > 2:
            self.text(x, y+ROWS*s+18, 'Branco: você   Verde: cristais   Rosa: chefe   Ouro: fogueira', 10)

    def overlay(self):
        self.rect(133, 119, 694, 410, '#122a30', '#b5b48a')
        self.text(W/2, 156, '✦  ECOS DE AURORA  ✦', 29, '#edd6a0', 'center', True)
        if self.mode == 'title':
            lines = ['Uma luz esquecida. Três cristais. Uma floresta para explorar.',
                     'Você é o viajante que pode despertar o Vale de Aurora.',
                     'Explore santuários, descubra tesouros e enfrente o Eclipse.',
                     '', 'ENTER  •  Nova aventura       F9  •  Continuar',
                     'WASD / setas: mover   |   Espaço: espada   |   E: interagir',
                     'Q: poção   |   Shift: esquiva   |   M: mapa   |   F5: salvar']
        elif self.mode == 'pause':
            lines = ['JORNADA EM PAUSA', '', 'ESC para voltar ao vale.',
                     'F9 carrega o último progresso salvo.',
                     'Fogueiras curam. Poções recuperam 5 pontos de vida.',
                     'O círculo do chefe anuncia um ataque: use Shift para escapar.']
        elif self.mode == 'dead':
            lines = ['A luz vacilou… mas a jornada pode continuar.', '',
                     'F9  •  Retomar o último salvamento', 'ENTER  •  Começar de novo',
                     'Dica: recue entre golpes e use Q para recuperar vida.']
        else:
            lines = ['O VALE VOLTOU A BRILHAR', '',
                     'Os três cristais romperam o Eclipse. Aurora está livre.',
                     f'Jornada concluída • Nível {self.level} • {self.coins} moedas',
                     '', 'ENTER  •  Viver uma nova aventura']
        for i, line in enumerate(lines):
            self.text(W/2, 221+i*37, line, 12, '#cbdcd0', 'center')
        if self.mode == 'title' and self.message.startswith('Nenhum'):
            self.text(W/2, 506, self.message, 10, '#efb28e', 'center')

    def tick(self):
        now = time.monotonic()
        dt, self.last = min(now-self.last, .035), now
        if self.mode == 'play':
            self.update(dt)
        self.draw()
        self.root.after(16, self.tick)


if __name__ == '__main__':
    try:
        window = tk.Tk()
        Game(window)
        window.mainloop()
    except tk.TclError as error:
        print('O jogo precisa de uma interface gráfica com Tkinter disponível.')
        print(error)
