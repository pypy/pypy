import autopath
import sys, os, re
import pygame
from pygame.locals import *
from pypy.translator.tool.make_dot import make_dot_graphs


class Display(object):
    
    def __init__(self, (w,h)=(800,740)):
        pygame.init()
        self.resize((w,h))

    def resize(self, (w,h)):
        self.width = w
        self.height = h
        self.screen = pygame.display.set_mode((w, h), HWSURFACE|RESIZABLE)

class GraphViewer(object):
    FONT = os.path.join(autopath.this_dir, 'cyrvetic.ttf')
    xscale = 1
    yscale = 1
    offsetx = 0
    offsety = 0

    def __init__(self, xdotfile, pngfile):
        pygame.init()
        g = open(str(pngfile), 'rb')
        try:
            self.bkgnd = pygame.image.load(pngfile)
        except Exception, e:
            print >> sys.stderr, '* Pygame cannot load "%s":' % pngfile
            print >> sys.stderr, '* %s: %s' % (e.__class__.__name__, e)
            print >> sys.stderr, '* Trying with pngtopnm.'
            import os
            g = os.popen("pngtopnm '%s'" % pngfile, 'r')
            w, h, data = decodepixmap(g)
            g.close()
            self.bkgnd = pygame.image.fromstring(data, (w, h), "RGB")
        self.width, self.height = self.bkgnd.get_size()
        self.font = pygame.font.Font(self.FONT, 18)

        # compute a list of  (rect, originalw, text, name)
        # where text is some text from the graph,
        #       rect is its position on the screen,
        #       originalw is its real (dot-computed) size on the screen,
        #   and name is XXX
        self.positions = []
        g = open(xdotfile, 'rb')
        lines = g.readlines()
        g.close()
        self.parse_xdot_output(lines)

    def render(self, dpy):
        ox = -self.offsetx
        oy = -self.offsety
        dpy.screen.blit(self.bkgnd, (ox, oy))
        # gray off-bkgnd areas
        gray = (128, 128, 128)
        if ox > 0:
            dpy.screen.fill(gray, (0, 0, ox, dpy.height))
        if oy > 0:
            dpy.screen.fill(gray, (0, 0, dpy.width, oy))
        w = dpy.width - (ox + self.width)
        if w > 0:
            dpy.screen.fill(gray, (dpy.width-w, 0, w, dpy.height))
        h = dpy.height - (oy + self.height)
        if h > 0:
            dpy.screen.fill(gray, (0, dpy.height-h, dpy.width, h))

    def at_position(self, (x, y), re_nonword=re.compile(r'(\W+)')):
        """Compute (word, text, name) where word is the word under the cursor,
        text is the complete line, and name is XXX.  All three are None
        if no text is under the cursor."""
        x += self.offsetx
        y += self.offsety
        for (rx,ry,rw,rh), originalw, text, name in self.positions:
            if rx <= x < rx+originalw and ry <= y < ry+rh:
                dx = x - rx
                # scale dx to account for small font mismatches
                dx = int(float(dx) * rw / originalw)
                words = [s for s in re_nonword.split(text) if s]
                segment = ''
                word = ''
                for word in words:
                    segment += word
                    img = self.font.render(segment, 1, (255, 0, 0))
                    w, h = img.get_size()
                    if dx < w:
                        break
                return word, text, name
        return None, None, None

    def parse_xdot_output(self, lines):
        for i in range(len(lines)):
            if lines[i].endswith('\\\n'):
                lines[i+1] = lines[i][:-2] + lines[i+1]
                lines[i] = ''
        for line in lines:
            self.parse_xdot_line(line)

    def parse_xdot_line(self, line,
            re_bb   = re.compile(r'\s*graph\s+[[]bb=["]0,0,(\d+),(\d+)["][]]'),
            re_text = re.compile(r"\s*T" + 5*r"\s+(-?\d+)" + r"\s+-"),
            matchtext = ' _ldraw_="'):
        match = re_bb.match(line)
        if match:
            self.xscale = float(self.width-12) / int(match.group(1))
            self.yscale = float(self.height-12) / int(match.group(2))
            return
        p = line.find(matchtext)
        if p < 0:
            return
        p += len(matchtext)
        line = line[p:]
        while 1:
            match = re_text.match(line)
            if not match:
                break
            x = 10+int(float(match.group(1)) * self.xscale)
            y = self.height-2-int(float(match.group(2)) * self.yscale)
            n = int(match.group(5))
            end = len(match.group())
            text = line[end:end+n]
            line = line[end+n:]
            if text:
                img = self.font.render(text, 1, (255, 0, 0))
                w, h = img.get_size()
                align = int(match.group(3))
                if align == 0:
                    x -= w//2
                elif align > 0:
                    x -= w
                rect = x, y-h, w, h
                originalw = int(float(match.group(4)) * self.xscale)
                self.positions.append((rect, originalw, text, 'XXX'))



def decodepixmap(f):
    sig = f.readline().strip()
    assert sig == "P6"
    while 1:
        line = f.readline().strip()
        if not line.startswith('#'):
            break
    wh = line.split()
    w, h = map(int, wh)
    sig = f.readline().strip()
    assert sig == "255"
    data = f.read()
    f.close()
    return w, h, data


class GraphDisplay(Display):
    STATUSBARFONT = os.path.join(autopath.this_dir, 'VeraMoBd.ttf')

    def __init__(self, translator):
        super(GraphDisplay, self).__init__()
        self.translator = translator
        self.annotator = translator.annotator
        self.font = pygame.font.Font(self.STATUSBARFONT, 16)

        self.variables_by_name = {}
        if self.annotator:
            for var in self.annotator.bindings:
                self.variables_by_name[var.name] = var

        graphs = []
        for func in self.translator.functions:
            graph = self.translator.getflowgraph(func)
            graphs.append((graph.name, graph))
        xdotfile = make_dot_graphs(self.translator.entrypoint.__name__, graphs, target='xdot')
        pngfile = make_dot_graphs(self.translator.entrypoint.__name__, graphs, target='png')
        self.viewer = GraphViewer(str(xdotfile), str(pngfile))
        self.viewer.offsetx = (self.viewer.width - self.width) // 2
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
        word, text, name = self.viewer.at_position(pos)
        if word in self.variables_by_name:
            var = self.variables_by_name[word]
            s_value = self.annotator.binding(var)
            info = '%s: %s' % (var.name, s_value)
            self.setstatusbar(info)

    def run(self):
        dragging = None
        while 1:
            if self.must_redraw:
                self.viewer.render(self)
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
                    self.viewer.offsetx -= (event.pos[0] - dragging[0])
                    self.viewer.offsety -= (event.pos[1] - dragging[1])
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
