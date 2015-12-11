#! /usr/bin/python


from collections import OrderedDict, namedtuple
from math import sqrt
from pygame.transform import flip
import pygame, sys, os, random
from pygame.locals import *
from credits.credit import pacman_credits


SCRIPT_PATH = sys.path[0]

TILE_WIDTH = TILE_HEIGHT = 24

# cross ref config
NO_GIF_TILES = [23]  # currently only "23" for the high-score list
CROSS_REF_EMPTY_LINE = ["'", "", "#"]

# Joystick defaults - maybe add a Preferences dialog in the future?
JS_DEVNUM = 0  # device 0 (pygame joysticks always start at 0). if JS_DEVNUM is not a valid device, will use 0
JS_XAXIS = 0  # axis 0 for left/right (default for most joysticks)
JS_YAXIS = 1  # axis 1 for up/down (default for most joysticks)
JS_STARTBUTTON = 9  # button number to start the game. this is a matter of personal preference, and will vary from device to device

# See GetCrossRef() -- where these colors occur in a GIF, they are replaced according to the level file
IMG_EDGE_LIGHT_COLOR = (0xff, 0xce, 0xff, 0xff)
IMG_FILL_COLOR = (0x84, 0x00, 0x84, 0xff)
IMG_EDGE_SHADOW_COLOR = (0xff, 0x00, 0xff, 0xff)
IMG_PELLET_COLOR = (0x80, 0x00, 0x80, 0xff)

# Must come before pygame.init()
pygame.mixer.pre_init(44100, -16, 2, 4096)
pygame.mixer.init()
MUTE_SOUNDS = False

clock = pygame.time.Clock()
pygame.init()

# display setup
DISPLAY_MODE_FLAGS = pygame.FULLSCREEN
# enable this to run in windowed mode
# DISPLAY_MODE_FLAGS = 0

window = pygame.display.set_mode((1, 1))
pygame.display.set_caption("Pacman")
screen = pygame.display.get_surface()
RES_W = 1280  # your computer actual resolution width
RES_H = 768  # your computer actual resolution height

img_Background = pygame.image.load(os.path.join(SCRIPT_PATH, "res", "backgrounds", "1.gif")).convert_alpha()

# sound setup
snd_pellet = {
    0: pygame.mixer.Sound(os.path.join(SCRIPT_PATH, "res", "sounds", "pellet1.wav")),
    1: pygame.mixer.Sound(os.path.join(SCRIPT_PATH, "res", "sounds", "pellet2.wav"))
}
snd_powerpellet = pygame.mixer.Sound(os.path.join(SCRIPT_PATH, "res", "sounds", "powerpellet.wav"))
snd_eatgh = pygame.mixer.Sound(os.path.join(SCRIPT_PATH, "res", "sounds", "eatgh2.wav"))
snd_fruitbounce = pygame.mixer.Sound(os.path.join(SCRIPT_PATH, "res", "sounds", "fruitbounce.wav"))
snd_eatfruit = pygame.mixer.Sound(os.path.join(SCRIPT_PATH, "res", "sounds", "eatfruit.wav"))
snd_extralife = pygame.mixer.Sound(os.path.join(SCRIPT_PATH, "res", "sounds", "extralife.wav"))
snd_killpac = pygame.mixer.Sound(os.path.join(SCRIPT_PATH, "res", "sounds", "killpac.wav"))
snd_ready = pygame.mixer.Sound(os.path.join(SCRIPT_PATH, "res", "sounds", "ready.wav"))
snd_eyes = pygame.mixer.Sound(os.path.join(SCRIPT_PATH, "res", "sounds", "eyes.wav"))
snd_siren = pygame.mixer.Sound(os.path.join(SCRIPT_PATH, "res", "sounds", "siren.wav"))

# ghosts setup
GHOST_REF_MIN = 10  # min value of cross ref for ghosts
GHOST_REF_MAX = 13  # max value of cross ref for ghosts
VULNERABLE_TIMER = 200

# ghosts controls setup
CONTROLS_DEF = ['right', 'left', 'down', 'up', 'joystick']
Control = namedtuple("Control", CONTROLS_DEF)
KEYS = [
    [pygame.K_d, pygame.K_a, pygame.K_s, pygame.K_w],
    [pygame.K_h, pygame.K_f, pygame.K_g, pygame.K_t],
    [pygame.K_l, pygame.K_j, pygame.K_k, pygame.K_i],
    [pygame.K_RIGHT, pygame.K_LEFT, pygame.K_DOWN, pygame.K_UP],
]

# colors for the ghosts
RED = (255, 0, 0, 255)
PINK = (255, 128, 255, 255)
CYAN = (128, 255, 255, 255)
ORANGE = (255, 128, 0, 255)
BLUE_VULNERABLE = (50, 50, 255, 255)
WHITE_FLASHING = (255, 255, 255, 255)

# pacman setup
LIVES = 2

# unused yet
MODE_MENU_INTRO = 0
MODE_MENU_SETUP = 1
MODE_GAME_PLAY = 2
MODE_GAME_PACMAN_DEAD = 3
MODE_GAME_GHOST_DEAD = 4
MODE_GAME_ZERO_PELLETS = 5
MODE_GAME_NO_LIVES = 6
MODE_MENU_GAME_OVER = 7
MODE_MENU_HIGH_SCORES = 8


def play_sound(snd, loops=0):
    if not MUTE_SOUNDS:
        snd.play(loops)


class Game:
    def __init__(self):
        self.levelNum = 0
        self.score = 0
        self.lives = LIVES

        # game "mode" variable
        # 1 = normal
        # 2 = hit ghost
        # 3 = game over
        # 4 = wait to start
        # 5 = wait after eating ghost
        # 6 = wait after finishing level
        self.mode = 0
        self.modeTimer = 0
        self.ghostTimer = 0
        self.ghostValue = 0
        self.fruitTimer = 0
        self.fruitScoreTimer = 0
        self.fruitScorePos = (0, 0)

        self.SetMode(3)

        # camera variables
        self.screenPixelPos = (0, 0)  # absolute x,y position of the screen from the upper-left corner of the level
        self.screenNearestTilePos = (0, 0)  # nearest-tile position of the screen from the UL corner
        self.screenPixelOffset = (0, 0)  # offset in pixels of the screen from its nearest-tile position
        self.screenTileSize = (60, 60)
        self.screenSize = (RES_W, RES_H)

        # numerical display digits
        self.digit = {}
        for i in range(0, 10, 1):
            self.digit[i] = pygame.image.load(os.path.join(SCRIPT_PATH, "res", "text", str(i) + ".gif")).convert_alpha()
        self.imLife = pygame.image.load(os.path.join(SCRIPT_PATH, "res", "text", "life.gif")).convert_alpha()
        self.imGameOver = pygame.image.load(os.path.join(SCRIPT_PATH, "res", "text", "gameover.gif")).convert_alpha()
        self.imReady = pygame.image.load(os.path.join(SCRIPT_PATH, "res", "text", "ready.gif")).convert_alpha()
        self.imLogo = pygame.image.load(os.path.join(SCRIPT_PATH, "res", "text", "logo.gif")).convert()
        self.imPowPel = pygame.image.load(os.path.join(SCRIPT_PATH, "res", "tiles", "pellet-power-white.gif")).convert_alpha()
        self.imNeg = pygame.image.load(os.path.join(SCRIPT_PATH, "res", "text", "-.gif")).convert_alpha()
        self.imPower = pygame.image.load(os.path.join(SCRIPT_PATH, "res", "text", "power.gif")).convert_alpha()
        self.imScore = pygame.image.load(os.path.join(SCRIPT_PATH, "res", "text", "score.gif")).convert_alpha()
        self.imLives = pygame.image.load(os.path.join(SCRIPT_PATH, "res", "text", "lives.gif")).convert_alpha()

        self.controls_pressed_right_image = pygame.image.load(os.path.join(SCRIPT_PATH, "res", "text", "controls-p-r.gif")).convert_alpha()
        self.controls_pressed_left_image = pygame.image.load(os.path.join(SCRIPT_PATH, "res", "text", "controls-p-l.gif")).convert_alpha()

        self.ghosts_quantity = 0
        self.ghosts = []
        self.vulnerable_ghost_id = -1
        self.flashing_ghost_id = -1
        self.vulnerable_ghost = None
        self.flashing_ghost = None
        self.ghost_colors = {}

    def StartNewGame(self):
        self.levelNum = 1
        self.score = 0
        self.lives = LIVES

        self.SetMode(4)
        thisLevel.LoadLevel(thisGame.GetLevelNum())

        thisGame.screenSize = (thisLevel.lvlWidth * 25, thisLevel.lvlHeight * 27)
        pygame.display.set_mode(thisGame.screenSize, DISPLAY_MODE_FLAGS)

    def AddToScore(self, amount):

        extraLifeSet = [25000, 50000, 100000, 150000]

        for specialScore in extraLifeSet:
            if self.score < specialScore and self.score + amount >= specialScore:
                play_sound(snd_extralife)
                thisGame.lives += 1

        self.score += amount

    def DrawScore(self):
        half_screen_w = thisGame.screenSize[0] / 2
        third_screen_w = half_screen_w / 2

        score_title_w = self.imScore.get_size()[0]
        score_title_y_pad = 35
        score_base_x_bottom = half_screen_w - third_screen_w - score_title_w / 2
        score_base_x_top = half_screen_w + third_screen_w - score_title_w / 2
        screen.blit(self.imScore, (score_base_x_bottom, self.screenSize[1] - score_title_y_pad))
        screen.blit(flip(self.imScore, True, True), (score_base_x_top, score_title_y_pad))
        num_pos_bottom = score_base_x_bottom
        self.DrawNumber(self.score, (num_pos_bottom, self.screenSize[1] - score_title_y_pad / 2))
        num_pos_top = score_base_x_top - self.imNeg.get_size()[0] + score_title_w
        self.DrawNumber(self.score, (num_pos_top, score_title_y_pad / 2), flip_xy=True)

        lives_title_w = self.imLives.get_size()[0]
        life_w = self.imLife.get_size()[0]
        lives_base_x = half_screen_w - lives_title_w / 2
        lives_title_y_pad = 35
        screen.blit(self.imLives, (lives_base_x, self.screenSize[1] - lives_title_y_pad))
        screen.blit(flip(self.imLives, True, True), (lives_base_x, lives_title_y_pad))
        for i in range(self.lives):
            life_pos = i * life_w
            screen.blit(self.imLife, (life_pos + lives_base_x, self.screenSize[1] - lives_title_y_pad / 2))
            life_pos *= -1
            # crazy math that just works
            life_pos -= life_w
            life_pos += lives_title_w
            screen.blit(flip(self.imLife, True, True), (life_pos + lives_base_x, lives_title_y_pad / 2))

        powers_title_w = self.imPower.get_size()[0]
        pow_pel_w = self.imPowPel.get_size()[0]
        powers_title_y_pad = 35
        power_base_x_bottom = half_screen_w + third_screen_w - powers_title_w / 2
        power_base_x_top = half_screen_w - third_screen_w - powers_title_w / 2
        screen.blit(self.imPower, (power_base_x_bottom, self.screenSize[1] - powers_title_y_pad))
        screen.blit(flip(self.imPower, True, True), (power_base_x_top, powers_title_y_pad))
        for i in range(0, THE_PACMAN.power_pellets):
            pow_pel_pos = i * pow_pel_w
            screen.blit(self.imPowPel, (pow_pel_pos + power_base_x_bottom, self.screenSize[1] - powers_title_y_pad / 2))
            pow_pel_pos *= -1
            pow_pel_pos -= pow_pel_w
            pow_pel_pos += powers_title_w
            screen.blit(flip(self.imPowPel, True, True), (pow_pel_pos + power_base_x_top, powers_title_y_pad / 2))

        # Draw fruit of this map:
        # screen.blit(thisFruit.imFruit[thisFruit.fruitType], (4 + 16, self.screenSize[1] - 28))

        if self.mode == 3:
            # hack x.x
            if self.levelNum != 0 and thisGame.modeTimer >= 150:
                GAME_OVER_BASE_X = -270
                screen.blit(self.imGameOver, (GAME_OVER_BASE_X, 0))

        if self.mode == 4:
            READY_BASE_Y = 10
            screen.blit(self.imReady, (self.screenSize[0] / 2 - self.imReady.get_size()[0] / 2, self.screenSize[1] / 2 + READY_BASE_Y))

    def DrawNumber(self, number, (x, y), flip_xy=False):
        if self.score > 0:
            screen.blit(self.imNeg, (x, y))

        str_number = str(number)
        for i in range(len(str(number))):
            int_digit = int(str_number[i])
            digit_w = self.digit[int_digit].get_size()[0]
            digit_pos = i * digit_w
            if not flip_xy:
                digit_pos += + self.imNeg.get_size()[0]
                screen.blit(self.digit[int_digit], (digit_pos + x, y))
            else:
                digit_pos -= self.imNeg.get_size()[0]
                digit_pos *= -1
                digit_pos -= digit_w * 2
                screen.blit(flip(self.digit[int_digit], flip_xy, flip_xy), (digit_pos + x, y))

    def GetScreenPos(self):
        return self.screenPixelPos

    def GetLevelNum(self):
        return self.levelNum

    def SetNextLevel(self):
        self.levelNum += 1

        self.lives = LIVES

        self.SetMode(4)
        thisLevel.LoadLevel(thisGame.GetLevelNum())

        thisGame.screenSize = (thisLevel.lvlWidth * 25, thisLevel.lvlHeight * 27)
        pygame.display.set_mode(thisGame.screenSize, DISPLAY_MODE_FLAGS)

        THE_PACMAN.vel_x = 0
        THE_PACMAN.vel_y = 0
        THE_PACMAN.anim_current = THE_PACMAN.anim_stopped

    def SetMode(self, newMode):
        self.mode = newMode
        self.modeTimer = 0

    def setup_ghosts(self, players):
        self.ghosts_quantity = len(players)
        self.ghost_colors = {0: RED, 1: PINK, 2: CYAN, 3: ORANGE}
        self.vulnerable_ghost_id = players[-1] + 1
        self.flashing_ghost_id = self.vulnerable_ghost_id + 1
        self.ghost_colors[self.vulnerable_ghost_id] = BLUE_VULNERABLE
        self.ghost_colors[self.flashing_ghost_id] = WHITE_FLASHING
        self.ghosts = []
        for player in players:
            g = ghost(player)
            joystick = None
            try:
                joystick = pygame.joystick.Joystick(player)
            except pygame.error:  # this joystick id is not connected
                pass
            g.controls = build_controls(KEYS[player], joystick)
            self.ghosts.append(g)
        self.vulnerable_ghost = ghost(self.vulnerable_ghost_id)
        self.flashing_ghost = ghost(self.flashing_ghost_id)


class node():
    def __init__(self):
        self.g = -1  # movement cost to move from previous node to this one (usually +10)
        self.h = -1  # estimated movement cost to move from this node to the ending node (remaining horizontal and vertical steps * 10)
        self.f = -1  # total movement cost of this node (= g + h)
        # parent node - used to trace path back to the starting node at the end
        self.parent = (-1, -1)
        # node type - 0 for empty space, 1 for wall (optionally, 2 for starting node and 3 for end)
        self.type = -1


class PathFinder:
    def __init__(self):
        # map is a 1-DIMENSIONAL array.
        # use the Unfold( (row, col) ) function to convert a 2D coordinate pair into a 1D index to use with this array.
        self.map = {}
        self.size = (-1, -1)  # rows by columns
        self.path_chain_rev = ""
        self.path_chain = ""
        # starting and ending nodes
        self.start = (-1, -1)
        self.end = (-1, -1)
        # current node (used by algorithm)
        self.current = (-1, -1)
        # open and closed lists of nodes to consider (used by algorithm)
        self.open_list = []
        self.closed_list = []
        # used in algorithm (adjacent neighbors path finder is allowed to consider)
        self.neighbor_set = [(0, -1), (0, 1), (-1, 0), (1, 0)]

    def resize_map(self, (num_rows, num_cols)):
        self.map = {}
        self.size = (num_rows, num_cols)
        # initialize path_finder map to a 2D array of empty nodes
        for row in range(0, self.size[0]):
            for col in range(0, self.size[1]):
                self.set((row, col), node())
                self.set_type((row, col), 0)

    def clean_up_temp(self):
        # this resets variables needed for a search (but preserves the same map / maze)
        self.path_chain_rev = ""
        self.path_chain = ""
        self.current = (-1, -1)
        self.open_list = []
        self.closed_list = []

    def find_path(self, start_pos, end_pos):
        self.clean_up_temp()
        self.start = start_pos
        self.end = end_pos
        # add start node to open list
        self.add_to_open_list(self.start)
        self.set_g(self.start, 0)
        self.set_h(self.start, 0)
        self.set_f(self.start, 0)

        do_continue = True
        this_lowest_f_node = False
        while do_continue:
            this_lowest_f_node = self.get_lowest_f_node()
            if not this_lowest_f_node == self.end and this_lowest_f_node:
                self.current = this_lowest_f_node
                self.remove_from_open_list(self.current)
                self.add_to_closed_list(self.current)
                for offset in self.neighbor_set:
                    this_neighbor = (self.current[0] + offset[0], self.current[1] + offset[1])
                    if not this_neighbor[0] < 0 and not this_neighbor[1] < 0 and not this_neighbor[0] > self.size[0] - 1 and not this_neighbor[1] > self.size[1] - 1 and not self.get_type(this_neighbor) == 1:
                        cost = self.get_g(self.current) + 10
                        if self.is_in_open_list(this_neighbor) and cost < self.get_g(this_neighbor):
                            self.remove_from_open_list(this_neighbor)
                        if not self.is_in_open_list(this_neighbor) and not self.is_in_closed_list(this_neighbor):
                            self.add_to_open_list(this_neighbor)
                            self.set_g(this_neighbor, cost)
                            self.calc_h(this_neighbor)
                            self.calc_f(this_neighbor)
                            self.set_parent(this_neighbor, self.current)
            else:
                do_continue = False

        if not this_lowest_f_node:
            return ""

        # reconstruct path
        self.current = self.end
        while not self.current == self.start:
            # build a string representation of the path using R, L, D, U
            if self.current[1] > self.get_parent(self.current)[1]:
                self.path_chain_rev += 'R'
            elif self.current[1] < self.get_parent(self.current)[1]:
                self.path_chain_rev += 'L'
            elif self.current[0] > self.get_parent(self.current)[0]:
                self.path_chain_rev += 'D'
            elif self.current[0] < self.get_parent(self.current)[0]:
                self.path_chain_rev += 'U'
            self.current = self.get_parent(self.current)
            self.set_type(self.current, 4)

        # because path_chain_rev was constructed in reverse order, it needs to be reversed!
        for i in range(len(self.path_chain_rev) - 1, -1, -1):
            self.path_chain += self.path_chain_rev[i]

        # set start and ending positions for future reference
        self.set_type(self.start, 2)
        self.set_type(self.end, 3)

        return self.path_chain

    def unfold(self, (row, col)):
        # this function converts a 2D array coordinate pair (row, col) to a 1D-array index, for the object's 1D map array.
        return (row * self.size[1]) + col

    def set(self, (row, col), new_node):
        # sets the value of a particular map cell (usually refers to a node object)
        self.map[self.unfold((row, col))] = new_node

    def get_type(self, (row, col)):
        return self.map[self.unfold((row, col))].type

    def set_type(self, (row, col), new_value):
        self.map[self.unfold((row, col))].type = new_value

    def get_f(self, (row, col)):
        return self.map[self.unfold((row, col))].f

    def get_g(self, (row, col)):
        return self.map[self.unfold((row, col))].g

    def get_h(self, (row, col)):
        return self.map[self.unfold((row, col))].h

    def set_g(self, (row, col), new_value):
        self.map[self.unfold((row, col))].g = new_value

    def set_h(self, (row, col), new_value):
        self.map[self.unfold((row, col))].h = new_value

    def set_f(self, (row, col), new_value):
        self.map[self.unfold((row, col))].f = new_value

    def calc_h(self, (row, col)):
        self.map[self.unfold((row, col))].h = abs(row - self.end[0]) + abs(col - self.end[0])

    def calc_f(self, (row, col)):
        unfold_index = self.unfold((row, col))
        self.map[unfold_index].f = self.map[unfold_index].g + self.map[unfold_index].h

    def add_to_open_list(self, (row, col)):
        self.open_list.append((row, col))

    def remove_from_open_list(self, (row, col)):
        self.open_list.remove((row, col))

    def is_in_open_list(self, (row, col)):
        return self.open_list.count((row, col))

    def get_lowest_f_node(self):
        lowest_value = 1000  # start arbitrarily high
        lowest_pair = (-1, -1)
        for i_ordered_pair in self.open_list:
            if self.get_f(i_ordered_pair) < lowest_value:
                lowest_value = self.get_f(i_ordered_pair)
                lowest_pair = i_ordered_pair

        if not lowest_pair == (-1, -1):
            return lowest_pair
        else:
            return False

    def add_to_closed_list(self, (row, col)):
        self.closed_list.append((row, col))

    def is_in_closed_list(self, (row, col)):
        return self.closed_list.count((row, col))

    def set_parent(self, (row, col), (parent_row, parent_col)):
        self.map[self.unfold((row, col))].parent = (parent_row, parent_col)

    def get_parent(self, (row, col)):
        return self.map[self.unfold((row, col))].parent

    def draw(self):
        for row in range(0, self.size[0]):
            for col in range(0, self.size[1]):
                this_tile = self.get_type((row, col))
                screen.blit(tileIDImage[this_tile], (col * (TILE_WIDTH * 2), row * (TILE_WIDTH * 2)))


class ghost():
    def __init__(self, ghostID):
        self.x = 0
        self.y = 0
        self.vel_x = 0
        self.vel_y = 0
        self.speed = 2

        self.nearest_row = 0
        self.nearest_col = 0

        self.id = ghostID

        # ghost "state" variable
        # 1 = normal
        # 2 = vulnerable
        # 3 = spectacles
        self.state = 1

        self.homeX = 0
        self.homeY = 0

        self.currentPath = ""

        self.anim = {}
        for i in range(1, 7, 1):
            self.anim[i] = pygame.image.load(os.path.join(SCRIPT_PATH, "res", "sprite", "ghost " + str(i) + ".gif")).convert_alpha()
            # change the ghost color in this frame
            for y in range(0, TILE_HEIGHT, 1):
                for x in range(0, TILE_WIDTH, 1):
                    if self.anim[i].get_at((x, y)) == RED:
                        # default, red ghost body color
                        self.anim[i].set_at((x, y), thisGame.ghost_colors[self.id])

        self.animFrame = 1
        self.animDelay = 0

        # default controls is just the keyboard, in main menu we add the joystick if it's available
        if self.id < thisGame.ghosts_quantity:  # no controls for vulnerable/white ghosts
            self.controls = build_controls(KEYS[self.id] + [None])

    def Draw(self):
        for y in range(6, 12, 1):
            for x in [5, 6, 8, 9]:
                self.anim[self.animFrame].set_at((x, y), (0xf8, 0xf8, 0xf8, 255))
                self.anim[self.animFrame].set_at((x + 9, y), (0xf8, 0xf8, 0xf8, 255))

        if THE_PACMAN.x > self.x and THE_PACMAN.y > self.y:  # THE_PACMAN is to lower-right
            pupilSet = (8, 9)
        elif THE_PACMAN.x > self.x and THE_PACMAN.y < self.y:  # THE_PACMAN is to upper-right
            pupilSet = (8, 6)
        elif THE_PACMAN.x < self.x and THE_PACMAN.y < self.y:  # THE_PACMAN is to upper-left
            pupilSet = (5, 6)
        else:  # THE_PACMAN.x < self.x and THE_PACMAN.y > self.y:  # THE_PACMAN is to lower-left
            pupilSet = (5, 9)

        for y in range(pupilSet[1], pupilSet[1] + 3, 1):
            for x in range(pupilSet[0], pupilSet[0] + 2, 1):
                self.anim[self.animFrame].set_at((x, y), (0, 0, 255, 255))
                self.anim[self.animFrame].set_at((x + 9, y), (0, 0, 255, 255))

        # ghost skin
        if self.state == 1:  # draw regular ghost
            screen.blit(self.anim[self.animFrame], (self.x - thisGame.screenPixelPos[0], self.y - thisGame.screenPixelPos[1]))
        elif self.state == 2:  # draw vulnerable ghost
            if thisGame.ghostTimer > 100:  # blue
                screen.blit(thisGame.vulnerable_ghost.anim[self.animFrame], (self.x - thisGame.screenPixelPos[0], self.y - thisGame.screenPixelPos[1]))
            else:  # blue/white flashing
                blink_timer = int(thisGame.ghostTimer / 10)
                if blink_timer == 1 or blink_timer == 3 or blink_timer == 5 or blink_timer == 7 or blink_timer == 9:
                    screen.blit(thisGame.flashing_ghost.anim[self.animFrame], (self.x - thisGame.screenPixelPos[0], self.y - thisGame.screenPixelPos[1]))
                else:
                    screen.blit(thisGame.vulnerable_ghost.anim[self.animFrame], (self.x - thisGame.screenPixelPos[0], self.y - thisGame.screenPixelPos[1]))
        elif self.state == 3:  # draw glasses
            screen.blit(tileIDImage[tileID['glasses']], (self.x - thisGame.screenPixelPos[0], self.y - thisGame.screenPixelPos[1]))

        if thisGame.mode == 6 or thisGame.mode == 7:  # don't animate ghost if the level is complete
            pass
        else:
            self.animDelay += 1
            if self.animDelay == 2:
                self.animFrame += 1
                if self.animFrame == 7:  # wrap to beginning
                    self.animFrame = 1
                self.animDelay = 0

    def Move(self):
        if self.state == 1 or self.state == 2:
            self.nearest_row = int(((self.y + (TILE_WIDTH / 2)) / TILE_WIDTH))
            self.nearest_col = int(((self.x + (TILE_HEIGHT / 2)) / TILE_HEIGHT))
            # make sure the current velocity will not cause a collision before moving
            if not thisLevel.CheckIfHitWall((self.x + self.vel_x, self.y + self.vel_y), (self.nearest_row, self.nearest_col)):
                self.x += self.vel_x
                self.y += self.vel_y
            # we're going to hit a wall -> stop moving
            else:
                self.vel_x = 0
                self.vel_y = 0
        elif self.state == 3:
            self.x += self.vel_x
            self.y += self.vel_y
            if (self.x % TILE_WIDTH) == 0 and (self.y % TILE_HEIGHT) == 0:
                if len(self.currentPath) > 0:
                    self.currentPath = self.currentPath[1:]
                    self.FollowNextPathWay()
                else:
                    self.speed /= 4
                    self.state = 1
                    for i in range(len(thisGame.ghosts)):
                        if thisGame.ghosts[i].state == 3:
                            return
                    snd_eyes.stop()

    def FollowNextPathWay(self):
        # only follow this pathway if there is a possible path found!
        if len(self.currentPath) > 0:
            if self.currentPath[0] == "L":
                (self.vel_x, self.vel_y) = (-self.speed, 0)
            elif self.currentPath[0] == "R":
                (self.vel_x, self.vel_y) = (self.speed, 0)
            elif self.currentPath[0] == "U":
                (self.vel_x, self.vel_y) = (0, -self.speed)
            elif self.currentPath[0] == "D":
                (self.vel_x, self.vel_y) = (0, self.speed)


class fruit():
    def __init__(self):
        # when fruit is not in use, it's in the (-1, -1) position off-screen.
        self.slowTimer = 0
        self.x = -TILE_WIDTH
        self.y = -TILE_HEIGHT
        self.velX = 0
        self.velY = 0
        self.speed = 2
        self.active = False

        self.bouncei = 0
        self.bounceY = 0

        self.nearestRow = (-1, -1)
        self.nearestCol = (-1, -1)

        self.imFruit = {}
        for i in range(0, 5, 1):
            self.imFruit[i] = pygame.image.load(os.path.join(SCRIPT_PATH, "res", "sprite", "fruit " + str(i) + ".gif")).convert_alpha()

        self.currentPath = ""
        self.fruitType = 1

    def Draw(self):

        if thisGame.mode == 3 or self.active == False:
            return False

        screen.blit(self.imFruit[self.fruitType], (self.x - thisGame.screenPixelPos[0], self.y - thisGame.screenPixelPos[1] - self.bounceY))

    def Move(self):

        if self.active == False:
            return False

        self.bouncei += 1
        if self.bouncei == 1:
            self.bounceY = 2
        elif self.bouncei == 2:
            self.bounceY = 4
        elif self.bouncei == 3:
            self.bounceY = 5
        elif self.bouncei == 4:
            self.bounceY = 5
        elif self.bouncei == 5:
            self.bounceY = 6
        elif self.bouncei == 6:
            self.bounceY = 6
        elif self.bouncei == 9:
            self.bounceY = 6
        elif self.bouncei == 10:
            self.bounceY = 5
        elif self.bouncei == 11:
            self.bounceY = 5
        elif self.bouncei == 12:
            self.bounceY = 4
        elif self.bouncei == 13:
            self.bounceY = 3
        elif self.bouncei == 14:
            self.bounceY = 2
        elif self.bouncei == 15:
            self.bounceY = 1
        elif self.bouncei == 16:
            self.bounceY = 0
            self.bouncei = 0
            play_sound(snd_fruitbounce)

        self.slowTimer += 1
        if self.slowTimer == 2:
            self.slowTimer = 0

            self.x += self.velX
            self.y += self.velY

            self.nearestRow = int(((self.y + (TILE_WIDTH / 2)) / TILE_WIDTH))
            self.nearestCol = int(((self.x + (TILE_HEIGHT / 2)) / TILE_HEIGHT))

            if (self.x % TILE_WIDTH) == 0 and (self.y % TILE_HEIGHT) == 0:
                # if the fruit is lined up with the grid again
                # meaning, it's time to go to the next path item

                if len(self.currentPath) > 0:
                    self.currentPath = self.currentPath[1:]
                    self.FollowNextPathWay()

                else:
                    self.x = self.nearestCol * TILE_WIDTH
                    self.y = self.nearestRow * TILE_HEIGHT

                    self.active = False
                    thisGame.fruitTimer = 0

    def FollowNextPathWay(self):


        # only follow this pathway if there is a possible path found!
        if not self.currentPath == False:

            if len(self.currentPath) > 0:
                if self.currentPath[0] == "L":
                    (self.velX, self.velY) = (-self.speed, 0)
                elif self.currentPath[0] == "R":
                    (self.velX, self.velY) = (self.speed, 0)
                elif self.currentPath[0] == "U":
                    (self.velX, self.velY) = (0, -self.speed)
                elif self.currentPath[0] == "D":
                    (self.velX, self.velY) = (0, self.speed)


class PacMan:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.vel_x = 0
        self.vel_y = 0
        self.speed = 4

        self.nearest_row = 0
        self.nearest_col = 0

        self.home_x = 0
        self.home_y = 0

        self.anim_left = {}
        self.anim_right = {}
        self.anim_up = {}
        self.anim_down = {}
        self.anim_stopped = {}
        self.anim_current = {}

        self.currentPath = ""
        self.steps_to_change_path = 2

        for i in range(1, 9, 1):
            self.anim_left[i] = pygame.image.load(os.path.join(SCRIPT_PATH, "res", "sprite", "pacman-l " + str(i) + ".gif")).convert_alpha()
            self.anim_right[i] = pygame.image.load(os.path.join(SCRIPT_PATH, "res", "sprite", "pacman-r " + str(i) + ".gif")).convert_alpha()
            self.anim_up[i] = pygame.image.load(os.path.join(SCRIPT_PATH, "res", "sprite", "pacman-u " + str(i) + ".gif")).convert_alpha()
            self.anim_down[i] = pygame.image.load(os.path.join(SCRIPT_PATH, "res", "sprite", "pacman-d " + str(i) + ".gif")).convert_alpha()
            self.anim_stopped[i] = pygame.image.load(os.path.join(SCRIPT_PATH, "res", "sprite", "pacman.gif")).convert_alpha()

        self.pellet_snd_num = 0  # ?

        self.power_pellets = 0

    def move(self):
        self.x += self.vel_x
        self.y += self.vel_y
        self.nearest_row = int(((self.y + (TILE_HEIGHT / 2)) / TILE_HEIGHT))
        self.nearest_col = int(((self.x + (TILE_HEIGHT / 2)) / TILE_WIDTH))

        thisLevel.CheckIfHitSomething((self.x, self.y), (self.nearest_row, self.nearest_col))
        for i in range(0, len(thisGame.ghosts)):
            ghost = thisGame.ghosts[i]
            dist = sqrt(pow(self.x - ghost.x, 2) + pow(self.y - ghost.y, 2))
            # if we get to close to ghosts, use a power pellet to smash them >:D
            if dist < 15 and ghost.state == 1:
                if self.power_pellets:
                    self.power_pellets -= 1
                    pygame.mixer.stop()
                    play_sound(snd_powerpellet)
                    thisGame.ghostValue = 200
                    thisGame.ghostTimer = VULNERABLE_TIMER
                    for g in range(0, thisGame.ghosts_quantity, 1):
                        if thisGame.ghosts[g].state == 1:
                            thisGame.ghosts[g].state = 2
            # otherwise, try to escape
            elif dist < 100 and ghost.state != 2 and not self.power_pellets:
                if (self.x % TILE_WIDTH) == 0 and (self.y % TILE_HEIGHT) == 0 and self.steps_to_change_path <= 0:
                    thisLevel.get_quadrant(ghost.nearest_col, ghost.nearest_row, self.nearest_col, self.nearest_row)
            if thisLevel.CheckIfHit((self.x, self.y), (thisGame.ghosts[i].x, thisGame.ghosts[i].y), TILE_WIDTH / 2):
                if thisGame.ghosts[i].state == 1:
                    # ghost is normal, pacman dies
                    play_sound(snd_killpac)
                    snd_eyes.stop()
                    thisGame.SetMode(2)
                elif thisGame.ghosts[i].state == 2:
                    # ghost is vulnerable, ghost dies
                    thisGame.AddToScore(thisGame.ghostValue)
                    thisGame.ghostValue = thisGame.ghostValue * 2
                    play_sound(snd_eatgh)
                    thisGame.ghosts[i].state = 3
                    thisGame.ghosts[i].speed = thisGame.ghosts[i].speed * 4
                    snd_eyes.stop()
                    play_sound(snd_eyes, loops=-1)
                    # and send them to the ghost box
                    thisGame.ghosts[i].x = thisGame.ghosts[i].nearest_col * TILE_WIDTH
                    thisGame.ghosts[i].y = thisGame.ghosts[i].nearest_row * TILE_HEIGHT
                    thisGame.ghosts[i].currentPath = path.find_path((thisGame.ghosts[i].nearest_row, thisGame.ghosts[i].nearest_col), (thisLevel.GetGhostBoxPos()[0], thisLevel.GetGhostBoxPos()[1]))
                    thisGame.ghosts[i].FollowNextPathWay()
                    # set game mode to brief pause after eating
                    thisGame.SetMode(5)

        # decrease ghost vulnerable timer
        if thisGame.ghostTimer > 0:
            thisGame.ghostTimer -= 1
            if thisGame.ghostTimer == 0:
                for i in range(thisGame.ghosts_quantity):
                    if thisGame.ghosts[i].state == 2:
                        thisGame.ghosts[i].state = 1
                    snd_powerpellet.stop()
                thisGame.ghostValue = 0

        if (self.x % TILE_WIDTH) == 0 and (self.y % TILE_HEIGHT) == 0:
            # pacman is lined up with the grid again, meaning it's time to go to the next path item
            if len(self.currentPath) > 0:
                self.currentPath = self.currentPath[1:]
                if len(self.currentPath) > 0:
                    check_row = self.nearest_row
                    check_col = self.nearest_col
                    if self.currentPath[0] == "L":
                        check_col -= 1
                    elif self.currentPath[0] == "R":
                        check_col += 1
                    elif self.currentPath[0] == "U":
                        check_row -= 1
                    elif self.currentPath[0] == "D":
                        check_row += 1
                    valid = [0, tileID['pellet'], tileID['pellet-power']]
                    if thisLevel.GetMapTile((check_row, check_col)) not in valid:
                        (rand_row, rand_col) = (0, 0)
                        while not thisLevel.GetMapTile((rand_row, rand_col)) == tileID['pellet'] or (rand_row, rand_col) == (0, 0):
                            rand_row = random.randint(1, thisLevel.lvlHeight - 2)
                            rand_col = random.randint(1, thisLevel.lvlWidth - 2)
                        self.currentPath = path.find_path((self.nearest_row, self.nearest_col), (rand_row, rand_col))
                self.steps_to_change_path -= 1
            else:
                self.x = self.nearest_col * TILE_WIDTH
                self.y = self.nearest_row * TILE_HEIGHT
            self.FollowNextPathWay()

    def FollowNextPathWay(self):
        if len(self.currentPath) > 0:
            if self.currentPath[0] == "L":
                (self.vel_x, self.vel_y) = (-self.speed, 0)
            elif self.currentPath[0] == "R":
                (self.vel_x, self.vel_y) = (self.speed, 0)
            elif self.currentPath[0] == "U":
                (self.vel_x, self.vel_y) = (0, -self.speed)
            elif self.currentPath[0] == "D":
                (self.vel_x, self.vel_y) = (0, self.speed)
        else:
            self.vel_x = 0
            self.vel_y = 0
            (rand_row, rand_col) = (0, 0)
            pellets = [tileID['pellet'], tileID['pellet-power']]
            # before sending pacman to a random pellet, check if there is no pellets around him to keep eating
            if thisLevel.GetMapTile((self.nearest_row + 1, self.nearest_col)) in pellets:
                (rand_row, rand_col) = (self.nearest_row + 1, self.nearest_col)
            elif thisLevel.GetMapTile((self.nearest_row - 1, self.nearest_col)) in pellets:
                (rand_row, rand_col) = (self.nearest_row - 1, self.nearest_col)
            elif thisLevel.GetMapTile((self.nearest_row, self.nearest_col + 1)) in pellets:
                (rand_row, rand_col) = (self.nearest_row, self.nearest_col + 1)
            elif thisLevel.GetMapTile((self.nearest_row, self.nearest_col - 1)) in pellets:
                (rand_row, rand_col) = (self.nearest_row, self.nearest_col - 1)
            else:
                # give pacman a path to a random spot (containing a pellet)
                while not thisLevel.GetMapTile((rand_row, rand_col)) == tileID['pellet'] or (rand_row, rand_col) == (0, 0):
                    rand_row = random.randint(1, thisLevel.lvlHeight - 2)
                    rand_col = random.randint(1, thisLevel.lvlWidth - 2)
            self.currentPath = path.find_path((self.nearest_row, self.nearest_col), (rand_row, rand_col))
            self.FollowNextPathWay()

    def draw(self):
        # if thisGame.mode == 3:
        #     return False
        # set the current frame array to match the direction pacman is facing
        if self.vel_x > 0:
            self.anim_current = self.anim_right
        elif self.vel_x < 0:
            self.anim_current = self.anim_left
        elif self.vel_y > 0:
            self.anim_current = self.anim_down
        elif self.vel_y < 0:
            self.anim_current = self.anim_up
        screen.blit(self.anim_current[self.animFrame], (self.x - thisGame.screenPixelPos[0], self.y - thisGame.screenPixelPos[1]))
        # Animate mouth movement
        if thisGame.mode == 1:
            if not self.vel_x == 0 or not self.vel_y == 0:  # Only animate when Pac-Man moves
                self.animFrame += 1
            if self.animFrame == 9:  # Reset
                self.animFrame = 1


class level():
    def __init__(self):
        self.lvlWidth = 0
        self.lvlHeight = 0
        self.pad_w = 0
        self.pad_h = 0
        self.edgeLightColor = (255, 255, 0, 255)
        self.edgeShadowColor = (255, 150, 0, 255)
        self.fillColor = (0, 255, 255, 255)
        self.pelletColor = (255, 255, 255, 255)

        self.map = {}

        self.pellets = 0
        self.powerPelletBlinkTimer = 0

        self.q00 = (0, 0)
        self.q01 = (0, 0)
        self.q10 = (0, 0)
        self.q11 = (0, 0)
        self.quadrant_mapping = {}

    def calculate_quadrants_ranges(self):
        actual_map_w = self.lvlWidth - self.pad_w
        actual_map_h = self.lvlHeight - self.pad_h
        w0 = (self.pad_w, (actual_map_w / 2) + self.pad_w)
        w1 = ((actual_map_w / 2) + self.pad_w, self.lvlWidth)
        h0 = (self.pad_h, (actual_map_h / 2) + self.pad_h)
        h1 = ((actual_map_h / 2) + self.pad_h, self.lvlHeight)
        self.q00 = (w0, h0)
        self.q01 = (w1, h0)
        self.q10 = (w0, h1)
        self.q11 = (w1, h1)
        # * means it's a dangerous choice, will make pacman go for the power pellet later in these situations
        self.quadrant_mapping = {
            lambda g_x, g_y, p_x, p_y: g_x < p_x and g_y < p_y:
                [
                    [self.q01, self.q10, self.q11],
                    [self.q11],
                    [self.q11],
                    [self.q00, self.q01, self.q10],  # *
                ],
            lambda g_x, g_y, p_x, p_y: g_x == p_x and g_y < p_y:
                [
                    [self.q10],
                    [self.q11],
                    [self.q11],
                    [self.q10],
                ],
            lambda g_x, g_y, p_x, p_y: g_x > p_x and g_y < p_y:
                [
                    [self.q10],
                    [self.q00, self.q10, self.q11],
                    [self.q00, self.q01, self.q11],
                    [self.q10],
                ],
            lambda g_x, g_y, p_x, p_y: g_x < p_x and g_y == p_y:
                [
                    [self.q01],
                    [self.q11],
                    [self.q11],
                    [self.q01],
                ],
            lambda g_x, g_y, p_x, p_y: g_x > p_x and g_y == p_y:
                [
                    [self.q10],
                    [self.q00],
                    [self.q00],
                    [self.q10],
                ],
            lambda g_x, g_y, p_x, p_y: g_x < p_x and g_y > p_y:
                [
                    [self.q01],
                    [self.q00, self.q10, self.q11],  # *
                    [self.q00, self.q01, self.q11],
                    [self.q01],
                ],
            lambda g_x, g_y, p_x, p_y: g_x == p_x and g_y > p_y:
                [
                    [self.q01],  # *
                    [self.q00],  # *
                    [self.q00],
                    [self.q01],
                ],
            lambda g_x, g_y, p_x, p_y: g_x > p_x and g_y > p_y:
                [
                    [self.q01, self.q10, self.q11],  # *
                    [self.q00],
                    [self.q00],
                    [self.q00, self.q01, self.q10],
                ],
        }

    def SetMapTile(self, (row, col), newValue):
        self.map[(row * self.lvlWidth) + col] = newValue

    def GetMapTile(self, (row, col), printed=False):
        if row >= 0 and row < self.lvlHeight and col >= 0 and col < self.lvlWidth:
            return self.map[(row * self.lvlWidth) + col]
        return 0

    def IsWall(self, (row, col)):
        if row > thisLevel.lvlHeight - 1 or row < 0:
            return True

        if col > thisLevel.lvlWidth - 1 or col < 0:
            return True

        # check the offending tile ID
        result = thisLevel.GetMapTile((row, col))

        # if the tile was a wall
        if result >= 100 and result <= 199:
            return True
        else:
            return False

    def CheckIfHitWall(self, (possiblePlayerX, possiblePlayerY), (row, col)):
        numCollisions = 0

        # check each of the 9 surrounding tiles for a collision
        for iRow in range(row - 1, row + 2, 1):
            for iCol in range(col - 1, col + 2, 1):

                if (possiblePlayerX - (iCol * TILE_WIDTH) < TILE_WIDTH) and (possiblePlayerX - (iCol * TILE_WIDTH) > -TILE_WIDTH) and (possiblePlayerY - (iRow * TILE_HEIGHT) < TILE_HEIGHT) and (possiblePlayerY - (iRow * TILE_HEIGHT) > -TILE_HEIGHT):

                    if self.IsWall((iRow, iCol)):
                        numCollisions += 1

        if numCollisions > 0:
            return True
        else:
            return False

    def CheckIfHit(self, (playerX, playerY), (x, y), cushion):
        if (playerX - x < cushion) and (playerX - x > -cushion) and (playerY - y < cushion) and (playerY - y > -cushion):
            return True
        else:
            return False

    def CheckIfHitSomething(self, (playerX, playerY), (row, col)):
        for iRow in range(row - 1, row + 2, 1):
            for iCol in range(col - 1, col + 2, 1):

                if (playerX - (iCol * TILE_WIDTH) < TILE_WIDTH) and (playerX - (iCol * TILE_WIDTH) > -TILE_WIDTH) and (playerY - (iRow * TILE_HEIGHT) < TILE_HEIGHT) and (playerY - (iRow * TILE_HEIGHT) > -TILE_HEIGHT):
                    # check the offending tile ID
                    result = thisLevel.GetMapTile((iRow, iCol))

                    if result == tileID['pellet']:
                        # got a pellet
                        thisLevel.SetMapTile((iRow, iCol), 0)
                        play_sound(snd_pellet[THE_PACMAN.pellet_snd_num])
                        THE_PACMAN.pellet_snd_num = 1 - THE_PACMAN.pellet_snd_num

                        thisLevel.pellets -= 1

                        thisGame.AddToScore(10)

                        if thisLevel.pellets == 0:
                            # no more pellets left!
                            # WON THE LEVEL
                            # thisGame.SetMode(6)
                            play_sound(snd_killpac)
                            thisGame.SetMode(3)

                    elif result == tileID['pellet-power']:
                        # pacman got a power pellet, store it to use later
                        THE_PACMAN.power_pellets += 1
                        thisLevel.SetMapTile((iRow, iCol), 0)
                        thisGame.AddToScore(100)

                    elif result == tileID['door-h']:
                        # ran into a horizontal door
                        for i in range(0, thisLevel.lvlWidth, 1):
                            if not i == iCol:
                                if thisLevel.GetMapTile((iRow, i)) == tileID['door-h']:
                                    THE_PACMAN.x = i * TILE_WIDTH

                                    if THE_PACMAN.vel_x > 0:
                                        THE_PACMAN.x += TILE_WIDTH
                                    else:
                                        THE_PACMAN.x -= TILE_WIDTH

                    elif result == tileID['door-v']:
                        # ran into a vertical door
                        for i in range(0, thisLevel.lvlHeight, 1):
                            if not i == iRow:
                                if thisLevel.GetMapTile((i, iCol)) == tileID['door-v']:
                                    THE_PACMAN.y = i * TILE_HEIGHT

                                    if THE_PACMAN.vel_y > 0:
                                        THE_PACMAN.y += TILE_HEIGHT
                                    else:
                                        THE_PACMAN.y -= TILE_HEIGHT

    def GetGhostBoxPos(self):
        for row in range(0, self.lvlHeight, 1):
            for col in range(0, self.lvlWidth, 1):
                if self.GetMapTile((row, col)) == tileID['ghost-door']:
                    return row, col

        return False

    def PrintMap(self):
        for row in range(0, self.lvlHeight, 1):
            outputLine = ""
            for col in range(0, self.lvlWidth, 1):
                outputLine += str(self.GetMapTile((row, col))) + ", "

    def DrawMap(self):
        self.powerPelletBlinkTimer += 1
        if self.powerPelletBlinkTimer == 60:
            self.powerPelletBlinkTimer = 0

        for row in range(-1, thisGame.screenTileSize[0] + 1, 1):
            for col in range(-1, thisGame.screenTileSize[1] + 1, 1):
                # row containing tile that actually goes here
                actualRow = thisGame.screenNearestTilePos[0] + row
                actualCol = thisGame.screenNearestTilePos[1] + col
                useTile = self.GetMapTile((actualRow, actualCol))
                if not useTile == 0 and \
                        not useTile == tileID['door-h'] and not useTile == tileID['door-v'] and \
                        not (GHOST_REF_MIN <= useTile <= GHOST_REF_MAX):
                    # if this isn't a blank tile
                    if useTile == tileID['pellet-power']:
                        if self.powerPelletBlinkTimer < 30:
                            screen.blit(tileIDImage[useTile], (col * TILE_WIDTH - thisGame.screenPixelOffset[0], row * TILE_HEIGHT - thisGame.screenPixelOffset[1]))
                    elif useTile == tileID['showlogo']:
                        screen.blit(thisGame.imLogo, (-255, 0))
                    elif useTile == tileID['hiscores']:
                        pass
                    else:
                        screen.blit(tileIDImage[useTile], (col * TILE_WIDTH - thisGame.screenPixelOffset[0], row * TILE_HEIGHT - thisGame.screenPixelOffset[1]))

    def LoadLevel(self, levelNum):
        self.map = {}

        self.pellets = 0

        f = open(os.path.join(SCRIPT_PATH, "res", "levels", str(levelNum) + ".txt"), 'r')
        lineNum = -1
        rowNum = 0
        useLine = False
        isReadingLevelData = False

        for line in f:

            lineNum += 1

            while len(line) > 0 and (line[-1] == "\n" or line[-1] == "\r"): line = line[:-1]
            while len(line) > 0 and (line[0] == "\n" or line[0] == "\r"): line = line[1:]
            str_splitBySpace = line.split(' ')

            j = str_splitBySpace[0]

            if (j == "'" or j == ""):
                # comment / whitespace line
                useLine = False
            elif j == "#":
                # special divider / attribute line
                useLine = False

                firstWord = str_splitBySpace[1]

                if firstWord == "lvlwidth":
                    self.lvlWidth = int(str_splitBySpace[2])

                elif firstWord == "lvlheight":
                    self.lvlHeight = int(str_splitBySpace[2])

                elif firstWord == "padw":
                    self.pad_w = int(str_splitBySpace[2])
                elif firstWord == "padh":
                    self.pad_h = int(str_splitBySpace[2])

                elif firstWord == "edgecolor":
                    # edge color keyword for backwards compatibility (single edge color) mazes
                    red = int(str_splitBySpace[2])
                    green = int(str_splitBySpace[3])
                    blue = int(str_splitBySpace[4])
                    self.edgeLightColor = (red, green, blue, 255)
                    self.edgeShadowColor = (red, green, blue, 255)

                elif firstWord == "edgelightcolor":
                    red = int(str_splitBySpace[2])
                    green = int(str_splitBySpace[3])
                    blue = int(str_splitBySpace[4])
                    self.edgeLightColor = (red, green, blue, 255)

                elif firstWord == "edgeshadowcolor":
                    red = int(str_splitBySpace[2])
                    green = int(str_splitBySpace[3])
                    blue = int(str_splitBySpace[4])
                    self.edgeShadowColor = (red, green, blue, 255)

                elif firstWord == "fillcolor":
                    red = int(str_splitBySpace[2])
                    green = int(str_splitBySpace[3])
                    blue = int(str_splitBySpace[4])
                    self.fillColor = (red, green, blue, 255)

                elif firstWord == "pelletcolor":
                    red = int(str_splitBySpace[2])
                    green = int(str_splitBySpace[3])
                    blue = int(str_splitBySpace[4])
                    self.pelletColor = (red, green, blue, 255)

                elif firstWord == "fruittype":
                    thisFruit.fruitType = int(str_splitBySpace[2])

                elif firstWord == "startleveldata":
                    isReadingLevelData = True
                    rowNum = 0

                elif firstWord == "endleveldata":
                    isReadingLevelData = False

            else:
                useLine = True

            # this is a map data line
            if useLine == True:

                if isReadingLevelData == True:
                    for k in range(0, self.lvlWidth, 1):
                        self.SetMapTile((rowNum, k), int(str_splitBySpace[k]))

                        thisID = int(str_splitBySpace[k])
                        if thisID == 4:
                            # starting position for pac-man

                            THE_PACMAN.home_x = k * TILE_WIDTH
                            THE_PACMAN.home_y = rowNum * TILE_HEIGHT
                            self.SetMapTile((rowNum, k), 0)

                        elif thisID >= 10 and thisID <= 13:
                            # one of the ghosts
                            try:
                                thisGame.ghosts[thisID - 10].homeX = k * TILE_WIDTH
                                thisGame.ghosts[thisID - 10].homeY = rowNum * TILE_HEIGHT
                                self.SetMapTile((rowNum, k), 0)
                            except:
                                pass

                        elif thisID == 2:
                            # pellet

                            self.pellets += 1

                    rowNum += 1

        # reload all tiles and set appropriate colors
        load_cross_reference()

        # load map into the pathfinder object
        path.resize_map((self.lvlHeight, self.lvlWidth))

        for row in range(0, path.size[0], 1):
            for col in range(0, path.size[1], 1):
                if self.IsWall((row, col)):
                    path.set_type((row, col), 1)
                else:
                    path.set_type((row, col), 0)

        # Calculate the quadrants after level is loaded
        self.calculate_quadrants_ranges()

        # do all the level-starting stuff
        self.Restart()

    def Restart(self):
        for i in range(0, thisGame.ghosts_quantity, 1):
            # move ghosts back to home
            thisGame.ghosts[i].x = thisGame.ghosts[i].homeX
            thisGame.ghosts[i].y = thisGame.ghosts[i].homeY
            thisGame.ghosts[i].vel_x = 0
            thisGame.ghosts[i].vel_y = 0
            thisGame.ghosts[i].state = 1
            thisGame.ghosts[i].speed = 2

        thisFruit.active = False

        thisGame.fruitTimer = 0

        THE_PACMAN.x = THE_PACMAN.home_x
        THE_PACMAN.y = THE_PACMAN.home_y
        THE_PACMAN.vel_x = 0
        THE_PACMAN.vel_y = 0

        THE_PACMAN.anim_current = THE_PACMAN.anim_stopped
        THE_PACMAN.animFrame = 3

        THE_PACMAN.power_pellets = 0

    def get_quadrant(self, ghost_x, ghost_y, player_x, player_y):
        actual_ghost_pos_x = ghost_x - self.pad_w
        actual_ghost_pos_y = ghost_y - self.pad_h
        actual_player_pos_x = player_x - self.pad_w
        actual_player_pos_y = player_y - self.pad_h

        actual_map_w = self.lvlWidth - self.pad_w
        actual_map_h = self.lvlHeight - self.pad_h
        w0 = (self.pad_w, (actual_map_w / 2) + self.pad_w)
        w1 = ((actual_map_w / 2) + self.pad_w, self.lvlWidth)
        h0 = (self.pad_h, (actual_map_h / 2) + self.pad_h)
        h1 = ((actual_map_h / 2) + self.pad_h, self.lvlHeight)
        in_c0 = w0[0] < ghost_x <= w0[1]
        in_c1 = w1[0] <= ghost_x < w1[1]
        in_l0 = h0[0] < ghost_y <= h0[1]
        in_l1 = h1[0] <= ghost_y < h1[1]

        for lambda_check, quadrants_mapping in self.quadrant_mapping.items():
            if lambda_check(actual_ghost_pos_x, actual_ghost_pos_y, actual_player_pos_x, actual_player_pos_y):
                if in_c0 and in_l0:
                    we_at = "in_c0 and in_l0"
                    possible_quadrants = quadrants_mapping[0]
                elif in_c1 and in_l0:
                    we_at = "in_c1 and in_l0"
                    possible_quadrants = quadrants_mapping[1]
                elif in_c0 and in_l1:
                    we_at = "in_c0 and in_l1"
                    possible_quadrants = quadrants_mapping[2]
                else:  # condition: "in_c1 and in_l1":
                    we_at = "in_c1 and in_l1"
                    possible_quadrants = quadrants_mapping[3]
                # print '-+THE_PACMAN at Y:%sxX:%s, ghost at Y:%sxX:%s aka %s' % (actual_player_pos_y, actual_player_pos_x, actual_ghost_pos_y, actual_ghost_pos_x, we_at)
                # print ' |-+we can go to: ' + str(possible_quadrants)
                go_to_quadrant = random.choice(possible_quadrants)
                # print '   |-+but we will go to: %s with padding %s' % (str(go_to_quadrant), str((self.pad_h, self.pad_w)))
                (go_to_row, go_to_col) = (0, 0)
                tries = 1024
                while not thisLevel.GetMapTile((go_to_row, go_to_col)) == tileID['pellet'] or thisLevel.GetMapTile((go_to_row, go_to_col)) == 0 or (go_to_row, go_to_col) == (0, 0):
                    if not tries:
                        break
                    tries -= 1
                    go_to_col = random.randint(go_to_quadrant[0][0], go_to_quadrant[0][1])
                    go_to_row = random.randint(go_to_quadrant[1][0], go_to_quadrant[1][1])
                if tries == 0:
                    pass
                    # print '     |-+nao achei nada'
                else:
                    # print '     |-+more specifically, col%dxrow%d from col%dxrow%d' % (go_to_col, go_to_row, THE_PACMAN.nearest_col, THE_PACMAN.nearest_row)
                    next_path = path.find_path((THE_PACMAN.nearest_row, THE_PACMAN.nearest_col), (go_to_row + self.pad_h, go_to_col + self.pad_w))
                    if next_path:
                        THE_PACMAN.currentPath = next_path[0] + next_path
                        THE_PACMAN.steps_to_change_path = 2
                        # print '       |-+with path: %s' % next_path
                    else:
                        pass
                        # print '       |-+but cant get there...'


def check_inputs():
    if thisGame.mode == 1:
        for i in range(0, thisGame.ghosts_quantity, 1):
            ghost = thisGame.ghosts[i]
            controls = ghost.controls
            js = controls.joystick
            if ghost.state != 3:  # Can't move manually if the ghost is returning to the box
                # right
                if pygame.key.get_pressed()[controls.right] or (js and js.get_axis(JS_XAXIS) > 0.5):
                    if not (ghost.vel_x == ghost.speed and ghost.vel_y == 0) and not thisLevel.CheckIfHitWall((ghost.x + ghost.speed, ghost.y), (ghost.nearest_row, ghost.nearest_col)):
                        ghost.vel_x = ghost.speed
                        ghost.vel_y = 0
                # left
                elif pygame.key.get_pressed()[controls.left] or (js and js.get_axis(JS_XAXIS) < -0.5):
                    if not (ghost.vel_x == -ghost.speed and ghost.vel_y == 0) and not thisLevel.CheckIfHitWall((ghost.x - ghost.speed, ghost.y), (ghost.nearest_row, ghost.nearest_col)):
                        ghost.vel_x = -ghost.speed
                        ghost.vel_y = 0
                # down
                elif pygame.key.get_pressed()[controls.down] or (js and js.get_axis(JS_YAXIS) > 0.5):
                    if not (ghost.vel_x == 0 and ghost.vel_y == ghost.speed) and not thisLevel.CheckIfHitWall((ghost.x, ghost.y + ghost.speed), (ghost.nearest_row, ghost.nearest_col)):
                        ghost.vel_x = 0
                        ghost.vel_y = ghost.speed
                # up
                elif pygame.key.get_pressed()[controls.up] or (js and js.get_axis(JS_YAXIS) < -0.5):
                    if not (ghost.vel_x == 0 and ghost.vel_y == -ghost.speed) and not thisLevel.CheckIfHitWall((ghost.x, ghost.y - ghost.speed), (ghost.nearest_row, ghost.nearest_col)):
                        ghost.vel_x = 0
                        ghost.vel_y = -ghost.speed
    elif thisGame.mode == 3:
        if pygame.key.get_pressed()[pygame.K_RETURN]:
            if thisGame.levelNum != 0:
                # we at game over and will show the menu again
                thisLevel.LoadLevel(0)
                thisGame.levelNum = 0
    if pygame.key.get_pressed()[pygame.K_F5]:
        sys.exit(0)


def check_events(event):
    if event.type == KEYDOWN or event.type == JOYBUTTONDOWN:
        if thisGame.mode == 3:
            if thisGame.levelNum == 0:
                # players joining and leaving
                for idx, player in enumerate(JOIN_KEYS.items()):
                    key, image = player
                    joystick = None
                    try:
                        joystick = pygame.joystick.Joystick(idx)
                        joystick.init()
                    except pygame.error:
                        pass
                    if pygame.key.get_pressed()[key] or (joystick and joystick.get_button(JOYSTICK_JOIN_BUTTON)):
                        if PLAYERS[idx]:
                            PLAYERS[idx] = None
                        else:
                            PLAYERS[idx] = image
                # start the game
                if pygame.key.get_pressed()[pygame.K_RETURN]:
                    players = [player for player, image in PLAYERS.items() if image]
                    if len(players) > 0:  # only start with at least 1 player
                        thisGame.setup_ghosts(players)
                        thisGame.StartNewGame()
                        play_sound(snd_ready)


def build_controls(keys, joystick=None):
    return Control(**{name: control for name, control in zip(CONTROLS_DEF, keys + [joystick])})


def load_cross_reference():
    cross_ref_file = open(os.path.join(SCRIPT_PATH, "res/config", "crossref.txt"), 'r')
    line_num = 0
    for line in cross_ref_file.readlines():
        # ???
        while len(line) > 0 and (line[-1] == '\n' or line[-1] == '\r'):
            line = line[:-1]
        while len(line) > 0 and (line[0] == '\n' or line[0] == '\r'):
            line = line[1:]

        split_by_space = line.split(' ')

        if split_by_space[0] in CROSS_REF_EMPTY_LINE:
            continue

        tileIDName[int(split_by_space[0])] = split_by_space[1]
        tileID[split_by_space[1]] = int(split_by_space[0])

        this_id = int(split_by_space[0])
        if this_id not in NO_GIF_TILES:
            tileIDImage[this_id] = pygame.image.load(os.path.join(SCRIPT_PATH, "res", "tiles", split_by_space[1] + ".gif")).convert_alpha()
        else:
            tileIDImage[this_id] = pygame.Surface((TILE_WIDTH, TILE_HEIGHT))

        # change colors in tileIDImage to match maze colors
        for y in range(TILE_WIDTH):
            for x in range(TILE_HEIGHT):
                if tileIDImage[this_id].get_at((x, y)) == IMG_EDGE_LIGHT_COLOR:  # wall edge
                    tileIDImage[this_id].set_at((x, y), thisLevel.edgeLightColor)
                elif tileIDImage[this_id].get_at((x, y)) == IMG_FILL_COLOR:  # wall fill
                    tileIDImage[this_id].set_at((x, y), thisLevel.fillColor)
                elif tileIDImage[this_id].get_at((x, y)) == IMG_EDGE_SHADOW_COLOR:  # pellet color
                    tileIDImage[this_id].set_at((x, y), thisLevel.edgeShadowColor)
                elif tileIDImage[this_id].get_at((x, y)) == IMG_PELLET_COLOR:  # pellet color
                    tileIDImage[this_id].set_at((x, y), thisLevel.pelletColor)
        line_num += 1


# create the pacman
THE_PACMAN = PacMan()

# players indicators
PLAYERS = OrderedDict({0: None, 1: None, 2: None, 3: None})
PLAYER_RED = pygame.image.load(os.path.join(SCRIPT_PATH, "res", "text", "ghost_red.gif")).convert_alpha()
PLAYER_PINK = pygame.image.load(os.path.join(SCRIPT_PATH, "res", "text", "ghost_pink.gif")).convert_alpha()
PLAYER_CYAN = pygame.image.load(os.path.join(SCRIPT_PATH, "res", "text", "ghost_blue.gif")).convert_alpha()
PLAYER_ORANGE = pygame.image.load(os.path.join(SCRIPT_PATH, "res", "text", "ghost_orange.gif")).convert_alpha()
PLAYER_NONE = pygame.image.load(os.path.join(SCRIPT_PATH, "res", "text", "ghost_vulnerable.gif")).convert_alpha()
JOIN_KEYS = {pygame.K_1: PLAYER_RED, pygame.K_2: PLAYER_PINK, pygame.K_3: PLAYER_CYAN, pygame.K_4: PLAYER_ORANGE}
JOYSTICK_JOIN_BUTTON = 5
JOYSTICKS = []
for j in range(pygame.joystick.get_count()):
    new_joystick = pygame.joystick.Joystick(j)
    new_joystick.init()
    JOYSTICKS.append(new_joystick)
CONTROLS_PRESS_TIMER_MAX = 25
controls_press_timer = CONTROLS_PRESS_TIMER_MAX

# create a path_finder object
path = PathFinder()

# create piece of fruit
thisFruit = fruit()

tileIDName = {}  # gives tile name (when the ID# is known)
tileID = {}  # gives tile ID (when the name is known)
tileIDImage = {}  # gives tile image (when the ID# is known)

# create game and level objects and load first level
thisGame = Game()
thisLevel = level()
thisLevel.LoadLevel(thisGame.GetLevelNum())
MAX_LEVEL = 11

thisGame.screenSize = (thisLevel.lvlWidth * 25, thisLevel.lvlHeight * 27)
pygame.display.set_mode(thisGame.screenSize, DISPLAY_MODE_FLAGS)

while True:
    for event in pygame.event.get():
        check_events(event)

    if thisGame.mode == 1:  # normal gameplay mode
        check_inputs()

        thisGame.modeTimer += 1

        THE_PACMAN.move()

        for i in range(thisGame.ghosts_quantity):
            thisGame.ghosts[i].Move()

        thisFruit.Move()

    elif thisGame.mode == 2:  # waiting after getting hit by a ghost
        thisGame.modeTimer += 1

        if thisGame.modeTimer == 90:
            thisLevel.Restart()

            thisGame.lives -= 1
            if thisGame.lives == 0:
                thisGame.SetMode(6)
            else:
                thisGame.SetMode(4)

    elif thisGame.mode == 3:  # game over
        check_inputs()

        if thisGame.levelNum != 0:
            thisGame.modeTimer += 1
            if thisGame.modeTimer == 60:
                oldEdgeLightColor = thisLevel.edgeLightColor
                oldEdgeShadowColor = thisLevel.edgeShadowColor
                oldFillColor = thisLevel.fillColor
            elif 60 < thisGame.modeTimer < 150:
                whiteSet = [70, 90, 110, 130]
                normalSet = [80, 100, 120, 140]
                if not whiteSet.count(thisGame.modeTimer) == 0:
                    thisLevel.edgeLightColor = (255, 255, 254, 255)
                    thisLevel.edgeShadowColor = (255, 255, 254, 255)
                    thisLevel.fillColor = (0, 0, 0, 255)
                    load_cross_reference()
                elif not normalSet.count(thisGame.modeTimer) == 0:
                    thisLevel.edgeLightColor = oldEdgeLightColor
                    thisLevel.edgeShadowColor = oldEdgeShadowColor
                    thisLevel.fillColor = oldFillColor
                    load_cross_reference()

    elif thisGame.mode == 4:  # waiting to start
        thisGame.modeTimer += 1

        if thisGame.modeTimer == 90:
            thisGame.SetMode(1)

    elif thisGame.mode == 5:  # brief pause after munching a vulnerable ghost
        thisGame.modeTimer += 1

        if thisGame.modeTimer == 30:
            thisGame.SetMode(1)

    elif thisGame.mode == 6:  # pause after eating all the pellets
        thisGame.modeTimer += 1

        if thisGame.modeTimer == 60:
            thisGame.SetMode(7)
            oldEdgeLightColor = thisLevel.edgeLightColor
            oldEdgeShadowColor = thisLevel.edgeShadowColor
            oldFillColor = thisLevel.fillColor

    elif thisGame.mode == 7:  # flashing maze after finishing level
        thisGame.modeTimer += 1

        whiteSet = [10, 30, 50, 70]
        normalSet = [20, 40, 60, 80]

        if not whiteSet.count(thisGame.modeTimer) == 0:
            thisLevel.edgeLightColor = (255, 255, 254, 255)
            thisLevel.edgeShadowColor = (255, 255, 254, 255)
            thisLevel.fillColor = (0, 0, 0, 255)
            load_cross_reference()
        elif not normalSet.count(thisGame.modeTimer) == 0:
            thisLevel.edgeLightColor = oldEdgeLightColor
            thisLevel.edgeShadowColor = oldEdgeShadowColor
            thisLevel.fillColor = oldFillColor
            load_cross_reference()
        elif thisGame.modeTimer == 150:
            thisGame.SetMode(8)

    elif thisGame.mode == 8:  # blank screen before changing levels
        thisGame.modeTimer += 1
        if thisGame.modeTimer == 10:
            if thisGame.levelNum != MAX_LEVEL:
                thisGame.SetNextLevel()
            else:
                # full screen for the credits
                pygame.display.set_mode((RES_W, RES_H), DISPLAY_MODE_FLAGS)
                pacman_credits()
                # we will show the high scores here later too
                # go back to the main menu and clear the players
                thisGame.levelNum = 0
                for pid, player in PLAYERS.items():
                    PLAYERS[pid] = None

    screen.blit(img_Background, (0, 0))

    if not thisGame.mode == 8:
        thisLevel.DrawMap()

        if thisGame.fruitScoreTimer > 0:
            if thisGame.modeTimer % 2 == 0:
                thisGame.DrawNumber(2500, (thisFruit.x - thisGame.screenPixelPos[0] - 16, thisFruit.y - thisGame.screenPixelPos[1] + 4))

        if thisGame.levelNum != 0:
            for i in range(thisGame.ghosts_quantity):
                thisGame.ghosts[i].Draw()

            thisFruit.Draw()

            THE_PACMAN.draw()

    if thisGame.mode == 5:
        thisGame.DrawNumber(thisGame.ghostValue / 2, (THE_PACMAN.x - thisGame.screenPixelPos[0] - 4, THE_PACMAN.y - thisGame.screenPixelPos[1] + 6))

    if thisGame.levelNum == 0:
        screen_w, screen_h = thisGame.screenSize
        quarter_screen_w = thisGame.screenSize[0] / 4
        eighth_screen_w = quarter_screen_w / 2
        for idx, player_img in enumerate(PLAYERS.values(), 1):
            if player_img is None:
                player_img = PLAYER_NONE
            player_w, player_h = player_img.get_size()
            player_base_x_top = eighth_screen_w + player_w / 2
            player_base_x_bottom = eighth_screen_w - player_w / 2
            player_y_pad = player_h * 2 + player_h / 2
            player_pos = idx * quarter_screen_w
            player_pos_bottom = (4 - idx) * quarter_screen_w
            screen.blit(player_img, (player_pos - player_base_x_top, screen_h - player_y_pad))
            screen.blit(flip(player_img, True, True), (player_pos_bottom + player_base_x_bottom, player_y_pad - player_h))

        controls_w, controls_h = thisGame.controls_pressed_right_image.get_size()
        if controls_press_timer > 0:
            screen.blit(thisGame.controls_pressed_right_image, (screen_w / 2 - controls_w / 2, screen_h - controls_h))
            screen.blit(flip(thisGame.controls_pressed_right_image, True, True), (screen_w / 2 - controls_w / 2, 0))
        else:
            screen.blit(thisGame.controls_pressed_left_image, (screen_w / 2 - controls_w / 2, screen_h - controls_h))
            screen.blit(flip(thisGame.controls_pressed_left_image, True, True), (screen_w / 2 - controls_w / 2, 0))
            if controls_press_timer == -CONTROLS_PRESS_TIMER_MAX:
                controls_press_timer = CONTROLS_PRESS_TIMER_MAX
        controls_press_timer -= 1
    else:
        thisGame.DrawScore()

    pygame.display.flip()

    clock.tick(30)
