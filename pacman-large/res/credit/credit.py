#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pygame import *
font.init()

def credit(text,font,color,image1, image2, image3):

    try: text = text.decode('utf-8')
    except: pass

    try: color = Color(color)
    except: color = Color(*color)

    clk = time.Clock()

    scr = display.get_surface()
    scr_w = scr.get_size()[0]
    image1_w = image1.get_size()[0]
    image2_w = image2.get_size()[0]
    image3_w = image3.get_size()[0]
    scrrect = scr.get_rect()
    bg = scr.copy()

    w,h = font.size(' ')
    Rright = scrrect.centerx + w*3
    Rleft = scrrect.centerx - w*3

    foo = []
    for i,l in enumerate(text.splitlines()):
        a,b,c = l.partition('\\')
        u = False
        if a:
            if a.startswith('_') and a.endswith('_'):
                u = True
                a = a.strip('_')
            rect = Rect((0,0),font.size(a))
            if b: rect.topright = Rleft,scrrect.bottom+h*i
            else: rect.midtop = scrrect.centerx,scrrect.bottom+h*i
            foo.append([a,rect,u])
        u = False
        if c:
            if c.startswith('_') and c.endswith('_'):
                u = True
                c = c.strip('_')
            rect = Rect((0,0),font.size(c))
            rect.topleft = Rright,scrrect.bottom+h*i
            foo.append([c,rect,u])

    y = 0
    while foo and not event.peek(QUIT):
        event.clear()
        y -= 1
        for p in foo[:]:
            r = p[1].move(0,y)
            if r.bottom < 0:
                foo.pop(0)
                continue
            if not isinstance(p[0],Surface):
                if p[2]: font.set_underline(1)
                p[0] = font.render(p[0],1,color)
                font.set_underline(0)
            scr.blit(p[0],r)
            if r.top >= scrrect.bottom:
                break
        clk.tick(40)
        display.flip()
        scr.blit(bg,(0,0))
        scr.blit(image1,(scr_w/2 - image1_w/2,y+650))
        scr.blit(image2,(Rleft - image2_w,y+1030))
        scr.blit(image3,(Rright,y+1520))

    display.flip()



