#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pygame import *
from credit import credit

display.set_mode((800,500))

text = """CREDIT
_                                                 _

_StoryBoard_\\Alex Kid
\\Mario Bross

_Ingénieurs du Sons_\\Mad Max
\\Tintin & Milou
\\l'équipe des Schtroumphs

_Directeur de la photographie_\\Sam le Pirate
_et d'autres trucs_\\


bonne idée volée à SPACEMAX :p
https://sites.google.com/site/gamemaxpy/

_                                                 _

©Copyright 2012"""

#~ utiliser '\\' pour aligner les lignes de texte

font = font.Font("Roboto-MediumItalic.ttf",20)
color = 0xa0a0a000

credit(text,font,color)
