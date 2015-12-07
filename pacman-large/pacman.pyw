#! /usr/bin/python

# pacman.pyw
# By David Reilly

# Modified by Andy Sommerville, 8 October 2007:
# - Changed hard-coded DOS paths to os.path calls
# - Added constant SCRIPT_PATH (so you don't need to have pacman.pyw and res in your cwd, as long
# -   as those two are in the same directory)
# - Changed text-file reading to accomodate any known EOLn method (\n, \r, or \r\n)
# - I (happily) don't have a Windows box to test this. Blocks marked "WIN???"
# -   should be examined if this doesn't run in Windows
# - Added joystick support (configure by changing JS_* constants)
# - Added a high-score list. Depends on wx for querying the user's name

# Modified by Andy Sommerville, 11 October 2007:
# - Mom's eyes aren't what they used to be, so I'm switching 16x16 tiles to 24x24
#   Added constants TILE_WIDTH,TILE_HEIGHT to make this easier to change later.
from collections import OrderedDict, namedtuple
from math import sqrt

from pygame.transform import flip

import pygame, sys, os, random
from pygame.locals import *

# WIN???
SCRIPT_PATH = sys.path[0]

TILE_WIDTH = TILE_HEIGHT = 24

# NO_GIF_TILES -- tile numbers which do not correspond to a GIF file
# currently only "23" for the high-score list
NO_GIF_TILES = [23]

NO_WX = 1  # if set, the high-score code will not attempt to ask the user his name
USER_NAME = "User"  # USER_NAME=os.getlogin() # the default user name if wx fails to load or NO_WX
# Oops! os.getlogin() only works if you launch from a terminal
# constants for the high-score display
HS_FONT_SIZE = 14
HS_LINE_HEIGHT = 16
HS_WIDTH = 408
HS_HEIGHT = 120
HS_XOFFSET = 48
HS_YOFFSET = 384
HS_ALPHA = 200

# new constants for the score's position
SCORE_XOFFSET = 50  # pixels from left edge
SCORE_YOFFSET = 34  # pixels from bottom edge (to top of score)

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

img_Background = pygame.image.load(os.path.join(SCRIPT_PATH, "res", "backgrounds", "1.gif")).convert_alpha()

# sound setup
snd_pellet = {}
snd_pellet[0] = pygame.mixer.Sound(os.path.join(SCRIPT_PATH, "res", "sounds", "pellet1.wav"))
snd_pellet[1] = pygame.mixer.Sound(os.path.join(SCRIPT_PATH, "res", "sounds", "pellet2.wav"))
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
GHOSTS_QTY = 4
VULNERABLE_GHOST_ID = GHOSTS_QTY
FLASHING_GHOST_ID = GHOSTS_QTY + 1
VULNERABLE_TIMER = 200

# ghosts controls setup
CONTROLS_DEF = ['right', 'left', 'down', 'up', 'joystick_id']
Control = namedtuple("Control", CONTROLS_DEF)

CONTROLS = [
    [pygame.K_RIGHT, pygame.K_LEFT, pygame.K_DOWN, pygame.K_UP],
    [pygame.K_h, pygame.K_f, pygame.K_g, pygame.K_t],
    [pygame.K_d, pygame.K_a, pygame.K_s, pygame.K_w],
    [pygame.K_l, pygame.K_j, pygame.K_k, pygame.K_i],
]

# colors for the ghosts
RED = (255, 0, 0, 255)
PINK = (255, 128, 255, 255)
CYAN = (128, 255, 255, 255)
ORANGE = (255, 128, 0, 255)
BLUE_VULNERABLE = (50, 50, 255, 255)
WHITE_FLASHING = (255, 255, 255, 255)
GHOST_COLORS = {0: RED, 1: PINK, 2: CYAN, 3: ORANGE, VULNERABLE_GHOST_ID: BLUE_VULNERABLE, FLASHING_GHOST_ID: WHITE_FLASHING}

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


# ___________________
# ___/  class definitions  \_______________________________________________

class game():
    def defaulthiscorelist(self):
        return [(100000, "David"), (80000, "Andy"), (60000, "Count Pacula"), (40000, "Cleopacra"), (20000, "Brett Favre"), (10000, "Sergei Pachmaninoff")]

    def gethiscores(self):
        """If res/hiscore.txt exists, read it. If not, return the default high scores.
                   Output is [ (score,name) , (score,name) , .. ]. Always 6 entries."""
        try:
            f = open(os.path.join(SCRIPT_PATH, "res", "hiscore.txt"))
            hs = []
            for line in f:
                while len(line) > 0 and (line[0] == "\n" or line[0] == "\r"): line = line[1:]
                while len(line) > 0 and (line[-1] == "\n" or line[-1] == "\r"): line = line[:-1]
                score = int(line.split(" ")[0])
                name = line.partition(" ")[2]
                if score > 99999999: score = 99999999
                if len(name) > 22: name = name[:22]
                hs.append((score, name))
            f.close()
            if len(hs) > 6: hs = hs[:6]
            while len(hs) < 6: hs.append((0, ""))
            return hs
        except IOError:
            return self.defaulthiscorelist()

    def writehiscores(self, hs):
        """Given a new list, write it to the default file."""
        fname = os.path.join(SCRIPT_PATH, "res", "hiscore.txt")
        f = open(fname, "w")
        for line in hs:
            f.write(str(line[0]) + " " + line[1] + "\n")
        f.close()

    def getplayername(self):
        """Ask the player his name, to go on the high-score list."""
        if NO_WX: return USER_NAME
        try:
            import wx
        except:
            print "Pacman Error: No module wx. Can not ask the user his name!"
            print "     :(       Download wx from http://www.wxpython.org/"
            print "     :(       To avoid seeing this error again, set NO_WX in file pacman.pyw."
            return USER_NAME
        app = wx.App(None)
        dlog = wx.TextEntryDialog(None, "You made the high-score list! Name:")
        dlog.ShowModal()
        name = dlog.GetValue()
        dlog.Destroy()
        app.Destroy()
        return name

    def updatehiscores(self, newscore):
        """Add newscore to the high score list, if appropriate."""
        hs = self.gethiscores()
        for line in hs:
            if newscore >= line[0]:
                hs.insert(hs.index(line), (newscore, self.getplayername()))
                hs.pop(-1)
                break
        self.writehiscores(hs)

    def makehiscorelist(self):
        "Read the High-Score file and convert it to a useable Surface."
        # My apologies for all the hard-coded constants.... -Andy
        f = pygame.font.Font(os.path.join(SCRIPT_PATH, "res", "VeraMoBd.ttf"), HS_FONT_SIZE)
        scoresurf = pygame.Surface((HS_WIDTH, HS_HEIGHT), pygame.SRCALPHA)
        scoresurf.set_alpha(HS_ALPHA)
        linesurf = f.render(" " * 18 + "HIGH SCORES", 1, (255, 255, 0))
        scoresurf.blit(linesurf, (0, 0))
        hs = self.gethiscores()
        vpos = 0
        for line in hs:
            vpos += HS_LINE_HEIGHT
            linesurf = f.render(line[1].rjust(22) + str(line[0]).rjust(9), 1, (255, 255, 255))
            scoresurf.blit(linesurf, (0, vpos))
        return scoresurf

    def drawmidgamehiscores(self):
        """Redraw the high-score list image after pacman dies."""
        self.imHiscores = self.makehiscorelist()

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
        self.screenSize = (1280, 768)

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
        self.imGhostRed = pygame.image.load(os.path.join(SCRIPT_PATH, "res", "text", "ghost_red.gif")).convert()
        self.imGhostOrange = pygame.image.load(os.path.join(SCRIPT_PATH, "res", "text", "ghost_orange.gif")).convert()
        self.imGhostPink = pygame.image.load(os.path.join(SCRIPT_PATH, "res", "text", "ghost_pink.gif")).convert()
        self.imGhostBlue = pygame.image.load(os.path.join(SCRIPT_PATH, "res", "text", "ghost_orange.gif")).convert()
        self.imHiscores = self.makehiscorelist()

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
        life_w = self.imLife .get_size()[0]
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
        for i in range(0, player.power_pellets):
            pow_pel_pos = i * pow_pel_w
            screen.blit(self.imPowPel, (pow_pel_pos + power_base_x_bottom, self.screenSize[1] - powers_title_y_pad / 2))
            pow_pel_pos *= -1
            pow_pel_pos -= pow_pel_w
            pow_pel_pos += powers_title_w
            screen.blit(self.imPowPel, (pow_pel_pos + power_base_x_top, powers_title_y_pad / 2))

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

    def SmartMoveScreen(self):
        # Comentando pra nao mover a tela automaticamente
        return
        possibleScreenX = player.x - self.screenTileSize[1] / 2 * TILE_WIDTH
        possibleScreenY = player.y - self.screenTileSize[0] / 2 * TILE_HEIGHT

        if possibleScreenX < 0:
            possibleScreenX = 0
        elif possibleScreenX > thisLevel.lvlWidth * TILE_WIDTH - self.screenSize[0]:
            possibleScreenX = thisLevel.lvlWidth * TILE_HEIGHT - self.screenSize[0]

        if possibleScreenY < 0:
            possibleScreenY = 0
        elif possibleScreenY > thisLevel.lvlHeight * TILE_WIDTH - self.screenSize[1]:
            possibleScreenY = thisLevel.lvlHeight * TILE_HEIGHT - self.screenSize[1]

        thisGame.MoveScreen((possibleScreenX, possibleScreenY))

    def MoveScreen(self, (newX, newY)):
        self.screenPixelPos = (newX, newY)
        self.screenNearestTilePos = (int(newY / TILE_HEIGHT), int(newX / TILE_WIDTH))  # nearest-tile position of the screen from the UL corner
        self.screenPixelOffset = (newX - self.screenNearestTilePos[1] * TILE_WIDTH, newY - self.screenNearestTilePos[0] * TILE_HEIGHT)

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

        player.vel_x = 0
        player.vel_y = 0
        player.anim_current = player.anim_stopped

    def SetMode(self, newMode):
        self.mode = newMode
        self.modeTimer = 0


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
                        self.anim[i].set_at((x, y), GHOST_COLORS[self.id])

        self.animFrame = 1
        self.animDelay = 0

        # default controls is just the keyboard, in main menu we add the joystick if it's available
        if self.id < GHOSTS_QTY:  # no controls for vulnerable/white ghosts
            self.controls = build_controls(CONTROLS[self.id] + [None])

    def Draw(self):

        # if thisGame.mode == 3:
        #     return False

        # ghost eyes --
        for y in range(6, 12, 1):
            for x in [5, 6, 8, 9]:
                self.anim[self.animFrame].set_at((x, y), (0xf8, 0xf8, 0xf8, 255))
                self.anim[self.animFrame].set_at((x + 9, y), (0xf8, 0xf8, 0xf8, 255))

        if player.x > self.x and player.y > self.y:
            # player is to lower-right
            pupilSet = (8, 9)
        elif player.x < self.x and player.y > self.y:
            # player is to lower-left
            pupilSet = (5, 9)
        elif player.x > self.x and player.y < self.y:
            # player is to upper-right
            pupilSet = (8, 6)
        elif player.x < self.x and player.y < self.y:
            # player is to upper-left
            pupilSet = (5, 6)
        else:
            pupilSet = (5, 9)

        for y in range(pupilSet[1], pupilSet[1] + 3, 1):
            for x in range(pupilSet[0], pupilSet[0] + 2, 1):
                self.anim[self.animFrame].set_at((x, y), (0, 0, 255, 255))
                self.anim[self.animFrame].set_at((x + 9, y), (0, 0, 255, 255))
        # -- end ghost eyes

        if self.state == 1:
            # draw regular ghost (this one)
            screen.blit(self.anim[self.animFrame], (self.x - thisGame.screenPixelPos[0], self.y - thisGame.screenPixelPos[1]))
        elif self.state == 2:
            # draw vulnerable ghost
            if thisGame.ghostTimer > 100:
                # blue
                screen.blit(GHOSTS[VULNERABLE_GHOST_ID].anim[self.animFrame], (self.x - thisGame.screenPixelPos[0], self.y - thisGame.screenPixelPos[1]))
            else:
                # blue/white flashing
                tempTimerI = int(thisGame.ghostTimer / 10)
                if tempTimerI == 1 or tempTimerI == 3 or tempTimerI == 5 or tempTimerI == 7 or tempTimerI == 9:
                    screen.blit(GHOSTS[FLASHING_GHOST_ID].anim[self.animFrame], (self.x - thisGame.screenPixelPos[0], self.y - thisGame.screenPixelPos[1]))
                else:
                    screen.blit(GHOSTS[VULNERABLE_GHOST_ID].anim[self.animFrame], (self.x - thisGame.screenPixelPos[0], self.y - thisGame.screenPixelPos[1]))
        elif self.state == 3:
            # draw glasses
            screen.blit(tileIDImage[tileID['glasses']], (self.x - thisGame.screenPixelPos[0], self.y - thisGame.screenPixelPos[1]))

        if thisGame.mode == 6 or thisGame.mode == 7:
            # don't animate ghost if the level is complete
            return False

        self.animDelay += 1

        if self.animDelay == 2:
            self.animFrame += 1

            if self.animFrame == 7:
                # wrap to beginning
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
                    for i in range(0, len(GHOSTS)):
                        if GHOSTS[i].state == 3:
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
        for i in range(0, len(GHOSTS)):
            ghost = GHOSTS[i]
            dist = sqrt(pow(self.x - ghost.x, 2) + pow(self.y - ghost.y, 2))
            # if we get to close to ghosts, use a power pellet to smash them >:D
            if dist < 15 and ghost.state == 1:
                if self.power_pellets:
                    self.power_pellets -= 1
                    pygame.mixer.stop()
                    play_sound(snd_powerpellet)
                    thisGame.ghostValue = 200
                    thisGame.ghostTimer = VULNERABLE_TIMER
                    for g in range(0, GHOSTS_QTY, 1):
                        if GHOSTS[g].state == 1:
                            GHOSTS[g].state = 2
            # otherwise, try to escape
            elif dist < 100 and ghost.state != 2 and not self.power_pellets:
                if (self.x % TILE_WIDTH) == 0 and (self.y % TILE_HEIGHT) == 0 and self.steps_to_change_path <= 0:
                    thisLevel.get_quadrant(ghost.nearest_col, ghost.nearest_row, self.nearest_col, self.nearest_row)
            if thisLevel.CheckIfHit((self.x, self.y), (GHOSTS[i].x, GHOSTS[i].y), TILE_WIDTH / 2):
                if GHOSTS[i].state == 1:
                    # ghost is normal, pacman dies
                    play_sound(snd_killpac)
                    snd_eyes.stop()
                    thisGame.SetMode(2)
                elif GHOSTS[i].state == 2:
                    # ghost is vulnerable, ghost dies
                    thisGame.AddToScore(thisGame.ghostValue)
                    thisGame.ghostValue = thisGame.ghostValue * 2
                    play_sound(snd_eatgh)
                    GHOSTS[i].state = 3
                    GHOSTS[i].speed = GHOSTS[i].speed * 4
                    snd_eyes.stop()
                    play_sound(snd_eyes, loops=-1)
                    # and send them to the ghost box
                    GHOSTS[i].x = GHOSTS[i].nearest_col * TILE_WIDTH
                    GHOSTS[i].y = GHOSTS[i].nearest_row * TILE_HEIGHT
                    GHOSTS[i].currentPath = path.find_path((GHOSTS[i].nearest_row, GHOSTS[i].nearest_col), (thisLevel.GetGhostBoxPos()[0], thisLevel.GetGhostBoxPos()[1]))
                    GHOSTS[i].FollowNextPathWay()
                    # set game mode to brief pause after eating
                    thisGame.SetMode(5)

        # decrease ghost vulnerable timer
        if thisGame.ghostTimer > 0:
            thisGame.ghostTimer -= 1
            if thisGame.ghostTimer == 0:
                for i in range(GHOSTS_QTY):
                    if GHOSTS[i].state == 2:
                        GHOSTS[i].state = 1
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
                        play_sound(snd_pellet[player.pellet_snd_num])
                        player.pellet_snd_num = 1 - player.pellet_snd_num

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
                        player.power_pellets += 1
                        thisLevel.SetMapTile((iRow, iCol), 0)
                        thisGame.AddToScore(100)

                    elif result == tileID['door-h']:
                        # ran into a horizontal door
                        for i in range(0, thisLevel.lvlWidth, 1):
                            if not i == iCol:
                                if thisLevel.GetMapTile((iRow, i)) == tileID['door-h']:
                                    player.x = i * TILE_WIDTH

                                    if player.vel_x > 0:
                                        player.x += TILE_WIDTH
                                    else:
                                        player.x -= TILE_WIDTH

                    elif result == tileID['door-v']:
                        # ran into a vertical door
                        for i in range(0, thisLevel.lvlHeight, 1):
                            if not i == iRow:
                                if thisLevel.GetMapTile((i, iCol)) == tileID['door-v']:
                                    player.y = i * TILE_HEIGHT

                                    if player.vel_y > 0:
                                        player.y += TILE_HEIGHT
                                    else:
                                        player.y -= TILE_HEIGHT

    def GetGhostBoxPos(self):

        for row in range(0, self.lvlHeight, 1):
            for col in range(0, self.lvlWidth, 1):
                if self.GetMapTile((row, col)) == tileID['ghost-door']:
                    return (row, col)

        return False

    def GetPathwayPairPos(self):

        doorArray = []

        for row in range(0, self.lvlHeight, 1):
            for col in range(0, self.lvlWidth, 1):
                if self.GetMapTile((row, col)) == tileID['door-h']:
                    # found a horizontal door
                    doorArray.append((row, col))
                elif self.GetMapTile((row, col)) == tileID['door-v']:
                    # found a vertical door
                    doorArray.append((row, col))

        if len(doorArray) == 0:
            return False

        chosenDoor = random.randint(0, len(doorArray) - 1)

        if self.GetMapTile(doorArray[chosenDoor]) == tileID['door-h']:
            # horizontal door was chosen
            # look for the opposite one
            for i in range(0, thisLevel.lvlWidth, 1):
                if not i == doorArray[chosenDoor][1]:
                    if thisLevel.GetMapTile((doorArray[chosenDoor][0], i)) == tileID['door-h']:
                        return doorArray[chosenDoor], (doorArray[chosenDoor][0], i)
        else:
            # vertical door was chosen
            # look for the opposite one
            for i in range(0, thisLevel.lvlHeight, 1):
                if not i == doorArray[chosenDoor][0]:
                    if thisLevel.GetMapTile((i, doorArray[chosenDoor][1])) == tileID['door-v']:
                        return doorArray[chosenDoor], (i, doorArray[chosenDoor][1])

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
                if not useTile == 0 and not useTile == tileID['door-h'] and not useTile == tileID['door-v']:
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

                            player.home_x = k * TILE_WIDTH
                            player.home_y = rowNum * TILE_HEIGHT
                            self.SetMapTile((rowNum, k), 0)

                        elif thisID >= 10 and thisID <= 13:
                            # one of the ghosts
                            try:
                                GHOSTS[thisID - 10].homeX = k * TILE_WIDTH
                                GHOSTS[thisID - 10].homeY = rowNum * TILE_HEIGHT
                                self.SetMapTile((rowNum, k), 0)
                            except:
                                pass

                        elif thisID == 2:
                            # pellet

                            self.pellets += 1

                    rowNum += 1

        # reload all tiles and set appropriate colors
        GetCrossRef()

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
        for i in range(0, GHOSTS_QTY, 1):
            # move ghosts back to home
            GHOSTS[i].x = GHOSTS[i].homeX
            GHOSTS[i].y = GHOSTS[i].homeY
            GHOSTS[i].vel_x = 0
            GHOSTS[i].vel_y = 0
            GHOSTS[i].state = 1
            GHOSTS[i].speed = 2

        thisFruit.active = False

        thisGame.fruitTimer = 0

        player.x = player.home_x
        player.y = player.home_y
        player.vel_x = 0
        player.vel_y = 0

        player.anim_current = player.anim_stopped
        player.animFrame = 3

        player.power_pellets = 0

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
                # print '-+player at Y:%sxX:%s, ghost at Y:%sxX:%s aka %s' % (actual_player_pos_y, actual_player_pos_x, actual_ghost_pos_y, actual_ghost_pos_x, we_at)
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
                    # print '     |-+more specifically, col%dxrow%d from col%dxrow%d' % (go_to_col, go_to_row, player.nearest_col, player.nearest_row)
                    next_path = path.find_path((player.nearest_row, player.nearest_col), (go_to_row + self.pad_h, go_to_col + self.pad_w))
                    if next_path:
                        player.currentPath = next_path[0] + next_path
                        player.steps_to_change_path = 2
                        # print '       |-+with path: %s' % next_path
                    else:
                        pass
                        # print '       |-+but cant get there...'


def check_inputs():
    if thisGame.mode == 1:
        for i in range(0, GHOSTS_QTY, 1):
            ghost = GHOSTS[i]
            controls = ghost.controls
            js = JOYSTICKS[controls.joystick_id] if controls.joystick_id is not None else None
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
                # we at gameover and will show the menu again
                thisLevel.LoadLevel(0)
                thisGame.levelNum = 0
                screen.blit(thisGame.imLogo, (-255, 0))
            else:
                # we at menu and will start the game
                thisGame.StartNewGame()
                play_sound(snd_ready)
        # map available joysticks to matching ghost (by id)
        for j_id, joystick in enumerate(JOYSTICKS):
            if joystick.get_button(5):
                for ghost in GHOSTS:
                    if ghost.id == j_id:
                        if ghost.controls.joystick_id is None:
                            control1 = build_controls(CONTROLS[j_id] + [j_id])
                            ghost.controls = control1
    if pygame.key.get_pressed()[pygame.K_F5]:
        sys.exit(0)


def build_controls(controls_list):
    return Control(**{name: control for name, control in zip(CONTROLS_DEF, controls_list)})


# _____________________________________________
# ___/  function: Get ID-Tilename Cross References  \______________________________________

def GetCrossRef():
    f = open(os.path.join(SCRIPT_PATH, "res", "crossref.txt"), 'r')

    lineNum = 0
    useLine = False

    for i in f.readlines():
        while len(i) > 0 and (i[-1] == '\n' or i[-1] == '\r'): i = i[:-1]
        while len(i) > 0 and (i[0] == '\n' or i[0] == '\r'): i = i[1:]
        str_splitBySpace = i.split(' ')

        j = str_splitBySpace[0]

        if (j == "'" or j == "" or j == "#"):
            # comment / whitespace line
            useLine = False
        else:
            useLine = True

        if useLine == True:
            tileIDName[int(str_splitBySpace[0])] = str_splitBySpace[1]
            tileID[str_splitBySpace[1]] = int(str_splitBySpace[0])

            thisID = int(str_splitBySpace[0])
            if not thisID in NO_GIF_TILES:
                tileIDImage[thisID] = pygame.image.load(os.path.join(SCRIPT_PATH, "res", "tiles", str_splitBySpace[1] + ".gif")).convert_alpha()
            else:
                tileIDImage[thisID] = pygame.Surface((TILE_WIDTH, TILE_HEIGHT))

            # change colors in tileIDImage to match maze colors
            for y in range(0, TILE_WIDTH, 1):
                for x in range(0, TILE_HEIGHT, 1):

                    if tileIDImage[thisID].get_at((x, y)) == IMG_EDGE_LIGHT_COLOR:
                        # wall edge
                        tileIDImage[thisID].set_at((x, y), thisLevel.edgeLightColor)

                    elif tileIDImage[thisID].get_at((x, y)) == IMG_FILL_COLOR:
                        # wall fill
                        tileIDImage[thisID].set_at((x, y), thisLevel.fillColor)

                    elif tileIDImage[thisID].get_at((x, y)) == IMG_EDGE_SHADOW_COLOR:
                        # pellet color
                        tileIDImage[thisID].set_at((x, y), thisLevel.edgeShadowColor)

                    elif tileIDImage[thisID].get_at((x, y)) == IMG_PELLET_COLOR:
                        # pellet color
                        tileIDImage[thisID].set_at((x, y), thisLevel.pelletColor)
        lineNum += 1


# create the pacman
player = PacMan()

# create a path_finder object
path = PathFinder()

# setup joysticks
JOYSTICKS = []
joystick_count = pygame.joystick.get_count()
for j in range(joystick_count):
    new_joystick = pygame.joystick.Joystick(j)
    new_joystick.init()
    JOYSTICKS.append(new_joystick)

# create ghosts
GHOSTS = []
for g_id in range(GHOSTS_QTY):
    GHOSTS.append(ghost(g_id))
GHOSTS += [ghost(VULNERABLE_GHOST_ID), ghost(FLASHING_GHOST_ID)]

# create piece of fruit
thisFruit = fruit()

tileIDName = {}  # gives tile name (when the ID# is known)
tileID = {}  # gives tile ID (when the name is known)
tileIDImage = {}  # gives tile image (when the ID# is known)

# create game and level objects and load first level
thisGame = game()
thisLevel = level()
thisLevel.LoadLevel(thisGame.GetLevelNum())

thisGame.screenSize = (thisLevel.lvlWidth * 25, thisLevel.lvlHeight * 27)
pygame.display.set_mode(thisGame.screenSize, DISPLAY_MODE_FLAGS)

while True:
    for event in pygame.event.get():
        pass

    if thisGame.mode == 1:  # normal gameplay mode
        check_inputs()

        thisGame.modeTimer += 1

        player.move()

        for i in range(GHOSTS_QTY):
            GHOSTS[i].Move()

        thisFruit.Move()

    elif thisGame.mode == 2:  # waiting after getting hit by a ghost
        thisGame.modeTimer += 1

        if thisGame.modeTimer == 90:
            thisLevel.Restart()

            thisGame.lives -= 1
            if thisGame.lives == 0:
                thisGame.updatehiscores(thisGame.score)
                thisGame.SetMode(6)
                thisGame.drawmidgamehiscores()
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
                    GetCrossRef()
                elif not normalSet.count(thisGame.modeTimer) == 0:
                    thisLevel.edgeLightColor = oldEdgeLightColor
                    thisLevel.edgeShadowColor = oldEdgeShadowColor
                    thisLevel.fillColor = oldFillColor
                    GetCrossRef()

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
            GetCrossRef()
        elif not normalSet.count(thisGame.modeTimer) == 0:
            thisLevel.edgeLightColor = oldEdgeLightColor
            thisLevel.edgeShadowColor = oldEdgeShadowColor
            thisLevel.fillColor = oldFillColor
            GetCrossRef()
        elif thisGame.modeTimer == 150:
            thisGame.SetMode(8)

    elif thisGame.mode == 8:  # blank screen before changing levels
        thisGame.modeTimer += 1
        if thisGame.modeTimer == 10:
            thisGame.SetNextLevel()

    thisGame.SmartMoveScreen()

    screen.blit(img_Background, (0, 0))

    if not thisGame.mode == 8:
        thisLevel.DrawMap()

        if thisGame.fruitScoreTimer > 0:
            if thisGame.modeTimer % 2 == 0:
                thisGame.DrawNumber(2500, (thisFruit.x - thisGame.screenPixelPos[0] - 16, thisFruit.y - thisGame.screenPixelPos[1] + 4))

        if thisGame.levelNum != 0:
            for i in range(0, GHOSTS_QTY, 1):
                GHOSTS[i].Draw()

            thisFruit.Draw()

            player.draw()

    if thisGame.mode == 5:
            thisGame.DrawNumber(thisGame.ghostValue / 2, (player.x - thisGame.screenPixelPos[0] - 4, player.y - thisGame.screenPixelPos[1] + 6))

    thisGame.DrawScore()

    pygame.display.flip()

    clock.tick(30)
