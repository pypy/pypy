"""
A custom graphic renderer for the '.plain' files produced by dot.

"""

from __future__ import generators
import autopath
import re, os, math
import pygame
from pygame.locals import *


FONT = os.path.join(autopath.this_dir, 'cyrvetic.ttf')
COLOR = {
    'black': (0,0,0),
    'white': (255,255,255),
    'red': (255,0,0),
    'green': (0,255,0),
    }
re_nonword=re.compile(r'([^0-9a-zA-Z_.]+)')

def combine(color1, color2, alpha):
    r1, g1, b1 = color1
    r2, g2, b2 = color2
    beta = 1.0 - alpha
    return (int(r1 * alpha + r2 * beta),
            int(g1 * alpha + g2 * beta),
            int(b1 * alpha + b2 * beta))


def highlight_color(color):
    if color == (0, 0, 0): # black becomes magenta
        return (255, 0, 255)
    elif color == (255, 255, 255): # white becomes yellow
        return (255, 255, 0)
    intensity = sum(color)
    if intensity > 191 * 3:
        return combine(color, (128, 192, 0), 0.2)
    else:
        return combine(color, (255, 255, 0), 0.2)

def getcolor(name, default):
    if name in COLOR:
        return COLOR[name]
    elif name.startswith('#') and len(name) == 7:
        rval = COLOR[name] = (int(name[1:3],16), int(name[3:5],16), int(name[5:7],16))
        return rval
    else:
        return default


class GraphLayout:

    def __init__(self, filename):
        # parse the layout file (.plain format)
        lines = open(str(filename), 'r').readlines()
        for i in range(len(lines)-2, -1, -1):
            if lines[i].endswith('\\\n'):   # line ending in '\'
                lines[i] = lines[i][:-2] + lines[i+1]
                del lines[i+1]
        header = splitline(lines.pop(0))
        assert header[0] == 'graph'
        self.scale = float(header[1])
        self.boundingbox = float(header[2]), float(header[3])
        self.nodes = {}
        self.edges = []
        for line in lines:
            line = splitline(line)
            if line[0] == 'node':
                n = Node(*line[1:])
                self.nodes[n.name] = n
            if line[0] == 'edge':
                self.edges.append(Edge(self.nodes, *line[1:]))
            if line[0] == 'stop':
                break
        self.links = {}

    def display(self):
        from pypy.translator.tool.pygame.graphdisplay import GraphDisplay
        GraphDisplay(self).run()

class Node:
    def __init__(self, name, x, y, w, h, label, style, shape, color, fillcolor):
        self.name = name
        self.x = float(x)
        self.y = float(y)
        self.w = float(w)
        self.h = float(h)
        self.label = label
        self.style = style
        self.shape = shape
        self.color = color
        self.fillcolor = fillcolor
        self.highlight = False

    def sethighlight(self, which):
        self.highlight = bool(which)

class Edge:
    label = None
    
    def __init__(self, nodes, tail, head, cnt, *rest):
        self.tail = nodes[tail]
        self.head = nodes[head]
        cnt = int(cnt)
        self.points = [(float(rest[i]), float(rest[i+1]))
                       for i in range(0, cnt*2, 2)]
        rest = rest[cnt*2:]
        if len(rest) > 2:
            self.label, xl, yl = rest[:3]
            self.xl = float(xl)
            self.yl = float(yl)
            rest = rest[3:]
        self.style, self.color = rest
        self.highlight = False

    def sethighlight(self, which):
        self.highlight = bool(which)

    def bezierpoints(self, resolution=8):
        result = []
        pts = self.points
        for i in range(0, len(pts)-3, 3):
            result += beziercurve(pts[i], pts[i+1],
                                  pts[i+2], pts[i+3], resolution)
        return result

    def arrowhead(self):
        bottom_up = self.points[0][1] > self.points[-1][1]
        if (self.tail.y > self.head.y) != bottom_up:   # reversed edge
            head = 0
            dir = 1
        else:
            head = -1
            dir = -1
        n = 1
        while True:
            try:
                x0, y0 = self.points[head]
                x1, y1 = self.points[head+n*dir]
            except IndexError:
                return []
            vx = x0-x1
            vy = y0-y1
            try:
                f = 0.12 / math.sqrt(vx*vx + vy*vy)
                vx *= f
                vy *= f
                return [(x0 + 0.9*vx, y0 + 0.9*vy),
                        (x0 + 0.4*vy, y0 - 0.4*vx),
                        (x0 - 0.4*vy, y0 + 0.4*vx)]
            except (ZeroDivisionError, ValueError):
                n += 1

def beziercurve((x0,y0), (x1,y1), (x2,y2), (x3,y3), resolution=8):
    result = []
    f = 1.0/(resolution-1)
    for i in range(resolution):
        t = f*i
        t0 = (1-t)*(1-t)*(1-t)
        t1 =   t  *(1-t)*(1-t) * 3.0
        t2 =   t  *  t  *(1-t) * 3.0
        t3 =   t  *  t  *  t
        result.append((x0*t0 + x1*t1 + x2*t2 + x3*t3,
                       y0*t0 + y1*t1 + y2*t2 + y3*t3))
    return result

def segmentdistance((x0,y0), (x1,y1), (x,y)):
    "Distance between the point (x,y) and the segment (x0,y0)-(x1,y1)."
    vx = x1-x0
    vy = y1-y0
    try:
        l = math.sqrt(vx*vx+vy*vy)
        vx /= l
        vy /= l
        dlong = vx*(x-x0) + vy*(y-y0)
    except (ZeroDivisionError, ValueError):
        dlong = -1
    if dlong < 0.0:
        return math.sqrt((x-x0)*(x-x0) + (y-y0)*(y-y0))
    elif dlong > l:
        return math.sqrt((x-x1)*(x-x1) + (y-y1)*(y-y1))
    else:
        return abs(vy*(x-x0) - vx*(y-y0))

def splitline(line, re_word = re.compile(r'[^\s"]\S*|["]["]|["].*?[^\\]["]')):
    result = []
    for word in re_word.findall(line):
        if word.startswith('"'):
            word = eval(word)
        result.append(word)
    return result


class GraphRenderer:
    MARGIN = 0.2
    SCALEMIN = 3
    SCALEMAX = 100
    FONTCACHE = {}
    
    def __init__(self, screen, graphlayout, scale=75):
        self.graphlayout = graphlayout
        self.setscale(scale)
        self.setoffset(0, 0)
        self.screen = screen
        self.textzones = []
        self.highlightwords = {}

    def setscale(self, scale):
        scale = max(min(scale, self.SCALEMAX), self.SCALEMIN)
        self.scale = float(scale)
        w, h = self.graphlayout.boundingbox
        self.margin = int(self.MARGIN * scale)
        self.width = int(w * scale) + (2 * self.margin)
        self.height = int(h * scale) + (2 * self.margin)
        self.bboxh = h
        size = int(15 * (scale-10) / 75)
        self.font = self.getfont(size)

    def getfont(self, size):
        if size in self.FONTCACHE:
            return self.FONTCACHE[size]
        elif size < 4:
            self.FONTCACHE[size] = None
            return None
        else:
            font = self.FONTCACHE[size] = pygame.font.Font(FONT, size)
            return font
    
    def setoffset(self, offsetx, offsety):
        "Set the (x,y) origin of the rectangle where the graph will be rendered."
        self.ofsx = offsetx - self.margin
        self.ofsy = offsety - self.margin

    def shiftoffset(self, dx, dy):
        self.ofsx += dx
        self.ofsy += dy

    def getcenter(self):
        w, h = self.screen.get_size()
        return self.revmap(w//2, h//2)

    def setcenter(self, x, y):
        w, h = self.screen.get_size()
        x, y = self.map(x, y)
        self.shiftoffset(x-w//2, y-h//2)

    def shiftscale(self, factor, fix=None):
        if fix is None:
            fixx, fixy = self.screen.get_size()
            fixx //= 2
            fixy //= 2
        else:
            fixx, fixy = fix
        x, y = self.revmap(fixx, fixy)
        self.setscale(self.scale * factor)
        newx, newy = self.map(x, y)
        self.shiftoffset(newx - fixx, newy - fixy)

    def reoffset(self, swidth, sheight):
        offsetx = noffsetx = self.ofsx
        offsety = noffsety = self.ofsy
        width = self.width
        height = self.height

        # if it fits, center it, otherwise clamp
        if width <= swidth:
            noffsetx = (width - swidth) // 2
        else:
            noffsetx = min(max(0, offsetx), width - swidth)

        if height <= sheight:
            noffsety = (height - sheight) // 2
        else:
            noffsety = min(max(0, offsety), height - sheight)

        self.ofsx = noffsetx
        self.ofsy = noffsety

    def getboundingbox(self):
        "Get the rectangle where the graph will be rendered."
        return (-self.ofsx, -self.ofsy, self.width, self.height)

    def visible(self, x1, y1, x2, y2):
        """Is any part of the box visible (i.e. within the bounding box)?

        We have to perform clipping ourselves because with big graphs the
        coordinates may sometimes become longs and cause OverflowErrors
        within pygame.
        """
        return (x1 < self.width-self.ofsx and x2 > -self.ofsx and
                y1 < self.height-self.ofsy and y2 > -self.ofsy)

    def map(self, x, y):
        return (int(x*self.scale) - (self.ofsx - self.margin),
                int((self.bboxh-y)*self.scale) - (self.ofsy - self.margin))

    def revmap(self, px, py):
        return ((px + (self.ofsx - self.margin)) / self.scale,
                self.bboxh - (py + (self.ofsy - self.margin)) / self.scale)

    def draw_node_commands(self, node):
        xcenter, ycenter = self.map(node.x, node.y)
        boxwidth = int(node.w * self.scale)
        boxheight = int(node.h * self.scale)
        fgcolor = getcolor(node.color, (0,0,0))
        bgcolor = getcolor(node.fillcolor, (255,255,255))
        if node.highlight:
            fgcolor = highlight_color(fgcolor)
            bgcolor = highlight_color(bgcolor)

        text = node.label
        lines = text.replace('\\l','\\l\n').replace('\r','\r\n').split('\n')
        # ignore a final newline
        if not lines[-1]:
            del lines[-1]
        wmax = 0
        hmax = 0
        commands = []
        bkgndcommands = []

        if self.font is None:
            if lines:
                raw_line = lines[0].replace('\\l','').replace('\r','')
                if raw_line:
                    for size in (12, 10, 8, 6, 4):
                        font = self.getfont(size)
                        img = TextSnippet(self, raw_line, (0, 0, 0), bgcolor, font=font)
                        w, h = img.get_size()
                        if (w >= boxwidth or h >= boxheight):
                            continue
                        else:
                            if w>wmax: wmax = w
                            def cmd(img=img, y=hmax, w=w):
                                img.draw(xcenter-w//2, ytop+y)
                            commands.append(cmd)
                            hmax += h
                            break
        else:
            for line in lines:
                raw_line = line.replace('\\l','').replace('\r','') or ' '
                img = TextSnippet(self, raw_line, (0, 0, 0), bgcolor)
                w, h = img.get_size()
                if w>wmax: wmax = w
                if raw_line.strip():
                    if line.endswith('\\l'):
                        def cmd(img=img, y=hmax):
                            img.draw(xleft, ytop+y)
                    elif line.endswith('\r'):
                        def cmd(img=img, y=hmax, w=w):
                            img.draw(xright-w, ytop+y)
                    else:
                        def cmd(img=img, y=hmax, w=w):
                            img.draw(xcenter-w//2, ytop+y)
                    commands.append(cmd)
                hmax += h
                #hmax += 8

        # we know the bounding box only now; setting these variables will
        # have an effect on the values seen inside the cmd() functions above
        xleft = xcenter - wmax//2
        xright = xcenter + wmax//2
        ytop = ycenter - hmax//2
        x = xcenter-boxwidth//2
        y = ycenter-boxheight//2

        if node.shape == 'box':
            rect = (x-1, y-1, boxwidth+2, boxheight+2)
            def cmd():
                self.screen.fill(bgcolor, rect)
            bkgndcommands.append(cmd)
            def cmd():
                pygame.draw.rect(self.screen, fgcolor, rect, 1)
            commands.append(cmd)
        elif node.shape == 'octagon':
            step = 1-math.sqrt(2)/2
            points = [(int(x+boxwidth*fx), int(y+boxheight*fy))
                      for fx, fy in [(step,0), (1-step,0),
                                     (1,step), (1,1-step),
                                     (1-step,1), (step,1),
                                     (0,1-step), (0,step)]]
            def cmd():
                pygame.draw.polygon(self.screen, bgcolor, points, 0)
            bkgndcommands.append(cmd)
            def cmd():
                pygame.draw.polygon(self.screen, fgcolor, points, 1)
            commands.append(cmd)
        return bkgndcommands, commands

    def draw_commands(self):
        nodebkgndcmd = []
        nodecmd = []
        for node in self.graphlayout.nodes.values():
            cmd1, cmd2 = self.draw_node_commands(node)
            nodebkgndcmd += cmd1
            nodecmd += cmd2

        edgebodycmd = []
        edgeheadcmd = []
        for edge in self.graphlayout.edges:
            fgcolor = getcolor(edge.color, (0,0,0))
            if edge.highlight:
                fgcolor = highlight_color(fgcolor)
            points = [self.map(*xy) for xy in edge.bezierpoints()]

            def drawedgebody(points=points, fgcolor=fgcolor):
                pygame.draw.lines(self.screen, fgcolor, False, points)
            edgebodycmd.append(drawedgebody)

            points = [self.map(*xy) for xy in edge.arrowhead()]
            if points:
                def drawedgehead(points=points, fgcolor=fgcolor):
                    pygame.draw.polygon(self.screen, fgcolor, points, 0)
                edgeheadcmd.append(drawedgehead)

            if edge.label:
                x, y = self.map(edge.xl, edge.yl)
                img = TextSnippet(self, edge.label, (0, 0, 0))
                w, h = img.get_size()
                if self.visible(x-w//2, y-h//2, x+w//2, y+h//2):
                    def drawedgelabel(img=img, x1=x-w//2, y1=y-h//2):
                        img.draw(x1, y1)
                    edgeheadcmd.append(drawedgelabel)

        return edgebodycmd + nodebkgndcmd + edgeheadcmd + nodecmd

    def render(self):
        bbox = self.getboundingbox()
        self.screen.fill((224, 255, 224), bbox)

        # gray off-bkgnd areas
        ox, oy, width, height = bbox
        dpy_width, dpy_height = self.screen.get_size()
        gray = (128, 128, 128)
        if ox > 0:
            self.screen.fill(gray, (0, 0, ox, dpy_height))
        if oy > 0:
            self.screen.fill(gray, (0, 0, dpy_width, oy))
        w = dpy_width - (ox + width)
        if w > 0:
            self.screen.fill(gray, (dpy_width-w, 0, w, dpy_height))
        h = dpy_height - (oy + height)
        if h > 0:
            self.screen.fill(gray, (0, dpy_height-h, dpy_width, h))

        # draw the graph and record the position of texts
        del self.textzones[:]
        for cmd in self.draw_commands():
            cmd()

    def search_for_node(self, searchstr, start_at=None):
        """Find a node that contains a search string."""
        iter = self.graphlayout.nodes.itervalues()
        if start_at is not None:
            # Skip all nodes up to and including 'start_at'
            for node in iter:
                if node is start_at:
                    break
        for node in iter:
            if searchstr in node.label:
                return node
        return None

    def at_position(self, (x, y)):
        """Figure out the word under the cursor."""
        for rx, ry, rw, rh, word in self.textzones:
            if rx <= x < rx+rw and ry <= y < ry+rh:
                return word
        return None

    def node_at_position(self, (x, y)):
        """Return the Node under the cursor."""
        x, y = self.revmap(x, y)
        for node in self.graphlayout.nodes.itervalues():
            if 2.0*abs(x-node.x) <= node.w and 2.0*abs(y-node.y) <= node.h:
                return node
        return None

    def edge_at_position(self, (x, y), distmax=14):
        """Return the Edge near the cursor."""
        # XXX this function is very CPU-intensive and makes the display kinda sluggish
        distmax /= self.scale
        xy = self.revmap(x, y)
        closest_edge = None
        for edge in self.graphlayout.edges:
            pts = edge.bezierpoints()
            for i in range(1, len(pts)):
                d = segmentdistance(pts[i-1], pts[i], xy)
                if d < distmax:
                    distmax = d
                    closest_edge = edge
        return closest_edge


class TextSnippet:
    
    def __init__(self, renderer, text, fgcolor, bgcolor=None, font=None):
        self.renderer = renderer
        self.imgs = []
        self.parts = []
        if font is None:
            font = renderer.font
        if font is None:
            return
        parts = self.parts
        for word in re_nonword.split(text):
            if not word:
                continue
            if word in renderer.highlightwords:
                fg, bg = renderer.highlightwords[word]
                bg = bg or bgcolor
            else:
                fg, bg = fgcolor, bgcolor
            parts.append((word, fg, bg))
        # consolidate sequences of words with the same color
        for i in range(len(parts)-2, -1, -1):
            if parts[i][1:] == parts[i+1][1:]:
                word, fg, bg = parts[i]
                parts[i] = word + parts[i+1][0], fg, bg
                del parts[i+1]
        # delete None backgrounds
        for i in range(len(parts)):
            if parts[i][2] is None:
                parts[i] = parts[i][:2]
        # render parts
        i = 0
        while i < len(parts):
            part = parts[i]
            word = part[0]
            antialias = not re_nonword.match(word)  # SDL bug with anti-aliasing
            try:
                img = font.render(word, antialias, *part[1:])
            except pygame.error:
                del parts[i]   # Text has zero width
            else:
                self.imgs.append(img)
                i += 1

    def get_size(self):
        if self.imgs:
            sizes = [img.get_size() for img in self.imgs]
            return sum([w for w,h in sizes]), max([h for w,h in sizes])
        else:
            return 0, 0

    def draw(self, x, y):
        for part, img in zip(self.parts, self.imgs):
            word = part[0]
            self.renderer.screen.blit(img, (x, y))
            w, h = img.get_size()
            self.renderer.textzones.append((x, y, w, h, word))
            x += w


try:
    sum   # 2.3 only
except NameError:
    def sum(lst):
        total = 0
        for item in lst:
            total += lst
        return total
