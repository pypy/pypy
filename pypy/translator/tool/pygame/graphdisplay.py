from __future__ import generators
import autopath
import os, time
import pygame
from pygame.locals import *
from drawgraph import GraphRenderer


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
    ANIM_STEP = 0.07

    def __init__(self, layout):
        super(GraphDisplay, self).__init__()
        self.font = pygame.font.Font(self.STATUSBARFONT, 16)
        self.viewers_history = []
        self.viewer = None
        self.setlayout(layout)

    def setlayout(self, layout):
        if self.viewer:
            self.viewers_history.append(self.viewer)
        self.layout = layout
        self.viewer = GraphRenderer(self.screen, layout)
        # center and scale to view the whole graph
        self.viewer.setoffset((self.viewer.width - self.width) // 2,
                              (self.viewer.height - self.height) // 2)
        f = min(float(self.width-40) / self.viewer.width,
                float(self.height-40) / self.viewer.height)
        if f < 1.0:
            self.viewer.shiftscale(f)
        self.updated_viewer()

    def updated_viewer(self):
        self.sethighlight()
        self.statusbarinfo = None
        self.must_redraw = True
        if self.viewers_history:
            info = 'Press Left Arrow to go back to previous screen'
        else:
            info = ('Click to move around, or drag mouse buttons '
                    '(left to zoom, right to scroll)')
        self.setstatusbar(info)

    def layout_back(self):
        if self.viewers_history:
            self.viewer = self.viewers_history.pop()
            self.layout = self.viewer.graphlayout
            self.updated_viewer()

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
        if word in self.layout.links:
            info = self.layout.links[word]
            self.setstatusbar(info)
            self.sethighlight(word)

    def notifyclick(self, pos):
        word = self.viewer.at_position(pos)
        if word in self.layout.links:
            newlayout = self.layout.followlink(word)
            if newlayout is not None:
                self.setlayout(newlayout)
                return
        node = self.viewer.node_at_position(pos)
        if node:
            self.look_at_node(node)
        else:
            edge = self.viewer.edge_at_position(pos)
            if edge:
                if not self.look_at_node(edge.head):
                    self.look_at_node(edge.tail)

    def sethighlight(self, word=None):
        self.viewer.highlightwords = {}
        for name in self.layout.links:
            self.viewer.highlightwords[name] = ((128,0,0), None)
        if word:
            self.viewer.highlightwords[word] = ((255,255,80), (128,0,0))

    def animation(self, expectedtime=0.6):
        start = time.time()
        step = 0.0
        n = 0
        while True:
            step += self.ANIM_STEP
            if step >= expectedtime:
                break
            yield step / expectedtime
            n += 1
            now = time.time()
            frametime = (now-start) / n
            self.ANIM_STEP = self.ANIM_STEP * 0.9 + frametime * 0.1
        yield 1.0

    def look_at_node(self, node):
        """Shift the node in view."""
        endscale = min(float(self.width-40) / node.w,
                       float(self.height-40) / node.h,
                       75)
        startscale = self.viewer.scale
        cx1, cy1 = self.viewer.getcenter()
        cx2, cy2 = node.x, node.y
        moving = (abs(startscale-endscale) + abs(cx1-cx2) + abs(cy1-cy2)
                  > 0.4)
        if moving:
            # if the target is far off the window, reduce scale along the way
            tx, ty = self.viewer.map(cx2, cy2)
            offview = max(-tx, -ty, tx-self.width, ty-self.height)
            middlescale = endscale * (0.999 ** offview)
            if offview > 150 and middlescale < startscale:
                bumpscale = 4.0 * (middlescale - 0.5*(startscale+endscale))
            else:
                bumpscale = 0.0
            self.statusbarinfo = None
            self.sethighlight(None)
            for t in self.animation():
                self.viewer.setscale(startscale*(1-t) + endscale*t +
                                     bumpscale*t*(1-t))
                self.viewer.setcenter(cx1*(1-t) + cx2*t, cy1*(1-t) + cy2*t)
                self.viewer.render()
                pygame.display.flip()
        return moving

    def run(self):
        dragging = click_origin = click_time = None
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
                    if (abs(event.pos[0] - click_origin[0]) +
                        abs(event.pos[1] - click_origin[1])) > 12:
                        click_time = None
                    dx = event.pos[0] - dragging[0]
                    dy = event.pos[1] - dragging[1]
                    if event.buttons[0]:   # left mouse button
                        self.viewer.shiftscale(1.003 ** dy)
                    else:
                        self.viewer.shiftoffset(-2*dx, -2*dy)
                    dragging = event.pos
                    self.must_redraw = True
                else:
                    self.notifymousepos(event.pos)
            if event.type == MOUSEBUTTONDOWN:
                dragging = click_origin = event.pos
                click_time = time.time()
                pygame.event.set_grab(True)
            if event.type == MOUSEBUTTONUP:
                dragging = None
                pygame.event.set_grab(False)
                if click_time is not None and abs(time.time() - click_time) < 1:
                    # click (no significant dragging)
                    self.notifyclick(click_origin)
                click_time = None
                self.notifymousepos(event.pos)
            if event.type == KEYDOWN:
                if event.key in [K_p, K_LEFT, K_BACKSPACE]:
                    self.layout_back()
            if event.type == VIDEORESIZE:
                # short-circuit if there are more resize events pending
                if pygame.event.peek([VIDEORESIZE]):
                    continue
                self.resize(event.size)
                self.must_redraw = True
            if event.type == QUIT:
                break
        # cannot safely close and re-open the display, depending on
        # Pygame version and platform.
        pygame.display.set_mode((self.width,1))
