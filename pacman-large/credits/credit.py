#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import pygame
import sys
from pygame import *
from pygame.locals import *


SCRIPT_PATH = sys.path[0]


def credit(text, font_, color_, image1, image2):
    try:
        text = text.decode('utf-8')
    except:
        pass

    try:
        the_color = Color(color_)
    except:
        the_color = Color(*color_)

    clk = time.Clock()

    scr = display.get_surface()
    scr_w = scr.get_size()[0]
    image1_w = image1.get_size()[0]
    image2_w = image2.get_size()[0]
    scrrect = scr.get_rect()
    bg = scr.copy()

    w, h = font_.size(' ')
    Rright = scrrect.centerx + w * 3
    Rleft = scrrect.centerx - w * 3

    half_screen = scr.get_size()[1] / 2 - image2.get_size()[1] / 2

    foo = []
    for i, l in enumerate(text.splitlines()):
        a, b, c = l.partition('\\')
        u = False
        if a:
            if a.startswith('_') and a.endswith('_'):
                u = True
                a = a.strip('_')
            rect = Rect((0, 0), font_.size(a))
            if b:
                rect.topright = Rleft, scrrect.bottom + h * i
            else:
                rect.midtop = scrrect.centerx, scrrect.bottom + h * i
            foo.append([a, rect, u])
        u = False
        if c:
            if c.startswith('_') and c.endswith('_'):
                u = True
                c = c.strip('_')
            rect = Rect((0, 0), font_.size(c))
            rect.topleft = Rright, scrrect.bottom + h * i
            foo.append([c, rect, u])

    y = 0
    while foo and not event.peek(QUIT):
        event.clear()
        y -= 10
        for p in foo[:]:
            r = p[1].move(0, y)
            if r.bottom < 0:
                foo.pop(0)
                continue
            if not isinstance(p[0], Surface):
                if p[2]: font_.set_underline(1)
                p[0] = font_.render(p[0], 1, the_color)
                font_.set_underline(0)
            scr.blit(p[0], r)
            if r.top >= scrrect.bottom:
                break
        clk.tick(40)
        display.flip()
        scr.blit(bg, (0, 0))
        scr.blit(image1, (scr_w / 2 - image1_w / 2, y + 650))
        photo_y = y + 2150
        if photo_y < half_screen:
            photo_y = half_screen
        scr.blit(image2, (scr_w / 2 - image2_w / 2, photo_y))
    display.flip()


def pacman_credits():
    text = """REVERSE PAC-MAN
    ___________________________________________________

    Developed by Aeroli.to

    Mothafucker software engineer\\Icaro Raupp Henrique

    Programmer\\Igor H. de Oliveira


    Source code at:
    https://github.com/iraupph/pacman-python


    Adapted from David Reilly’s Pac-Man Python Project


    Game, songs & sound effects:

    Based on “Pac-Man”
    Developed by Namco
    Published by Namco (Japan) & Midway (North America)
    Released in May 22, 1980 (Japan) & October 26, 1980 (North America)

    Also based on “Super Mario World”
    Developed by Nintendo EAD
    Published by Nintendo
    Released in November 21, 1990 (Japan)

    ___________________________________________________

    Have you heard about Konami Code?







     """
    font.init()

    font_ = pygame.font.Font(os.path.join(SCRIPT_PATH, "credits/res/font", "webpixel-bitmap_bold.otf"), 40)
    color_ = 0xa0a0a000
    image1 = image.load(os.path.join(SCRIPT_PATH, "credits/res/img/pac.gif")).convert_alpha()
    image2 = image.load(os.path.join(SCRIPT_PATH, "credits/res/photo/picture1.gif")).convert_alpha()

    credit(text, font_, color_, image1, image2)
