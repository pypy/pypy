from __future__ import generators
import autopath
import sys, os, re
import pygame
from pygame.locals import *
from drawgraph import GraphRenderer, build_layout


class Display(object):
    
    def __init__(self, (w,h)=(800,740)):
        pygame.init()
        self.resize((w,h))

    def resize(self, (w,h)):
        self.width = w
        self.height = h
        self.screen = pygame.display.set_mode((w, h), HWSURFACE|RESIZABLE)


class GraphDisplay(Display):
    STATUSBARFONT = os.path.join(autopath.this_dir, 'VeraMoBd.ttf')
    SCALE = 60

    def __init__(self, translator, functions=None):
        super(GraphDisplay, self).__init__()
        self.translator = translator
        self.annotator = translator.annotator
        self.font = pygame.font.Font(self.STATUSBARFONT, 16)

        self.variables_by_name = {}
        if self.annotator:
            for var in self.annotator.bindings:
                self.variables_by_name[var.name] = var

        functions = functions or self.translator.functions
        graphs = [self.translator.getflowgraph(func) for func in functions]
        layout = build_layout(graphs)
        self.viewer = GraphRenderer(self.screen, layout, self.SCALE)
        # center horizonally
        self.viewer.setoffset((self.viewer.width - self.width) // 2, 0)
        self.sethighlight()
        self.statusbarinfo = None
        self.must_redraw = True

    def setstatusbar(self, text, fgcolor=(255,255,80), bgcolor=(128,0,0)):
        info = (text, fgcolor, bgcolor)
        if info != self.statusbarinfo:
            self.statusbarinfo = info
            self.must_redraw = True

    def drawstatusbar(self):
        text, fgcolor, bgcolor = self.statusbarinfo
        words = text.split(' ')
        lines = []
        totalh = 0
        while words:
            line = words.pop(0)
            img = self.font.render(line, 1, fgcolor)
            while words:
                longerline = line + ' ' + words[0]
                longerimg = self.font.render(longerline, 1, fgcolor)
                w, h = longerimg.get_size()
                if w > self.width:
                    break
                words.pop(0)
                line = longerline
                img = longerimg
            lines.append(img)
            w, h = img.get_size()
            totalh += h
        
        y = self.height - totalh
        self.screen.fill(bgcolor, (0, y-16, self.width, totalh+16))
        for img in lines:
            w, h = img.get_size()
            self.screen.blit(img, ((self.width-w)//2, y-8))
            y += h

    def notifymousepos(self, pos):
        word = self.viewer.at_position(pos)
        if word in self.variables_by_name:
            var = self.variables_by_name[word]
            s_value = self.annotator.binding(var)
            info = '%s: %s' % (var.name, s_value)
            self.setstatusbar(info)
            self.sethighlight(word)

    def sethighlight(self, word=None):
        self.viewer.highlightwords = {}
        for name in self.variables_by_name:
            self.viewer.highlightwords[name] = ((128,0,0), None)
        if word:
            self.viewer.highlightwords[word] = ((255,255,80), (128,0,0))

    def run(self):
        dragging = None
        while 1:
            if self.must_redraw:
                self.viewer.render()
                if self.statusbarinfo:
                    self.drawstatusbar()
                pygame.display.flip()
                self.must_redraw = False
            
            event = pygame.event.wait()
            if event.type == MOUSEMOTION:
                # short-circuit if there are more motion events pending
                if pygame.event.peek([MOUSEMOTION]):
                    continue
                if dragging:
                    dx = event.pos[0] - dragging[0]
                    dy = event.pos[1] - dragging[1]
                    if event.buttons[2]:   # right mouse button
                        self.viewer.shiftscale(1.003 ** dy)
                    else:
                        self.viewer.shiftoffset(-2*dx, -2*dy)
                    dragging = event.pos
                    self.must_redraw = True
                else:
                    self.notifymousepos(event.pos)
            if event.type == MOUSEBUTTONDOWN:
                dragging = event.pos
                pygame.event.set_grab(True)
            if event.type == MOUSEBUTTONUP:
                dragging = None
                pygame.event.set_grab(False)
                self.notifymousepos(event.pos)
            if event.type == VIDEORESIZE:
                # short-circuit if there are more resize events pending
                if pygame.event.peek([VIDEORESIZE]):
                    continue
                self.resize(event.size)
                self.must_redraw = True
            if event.type == QUIT:
                break
        pygame.display.quit()


if __name__ == '__main__':
    from pypy.translator.translator import Translator
    from pypy.translator.test import snippet
    
    t = Translator(snippet.poor_man_range)
    t.simplify()
    a = t.annotate([int])
    a.simplify()
    GraphDisplay(t).run()
