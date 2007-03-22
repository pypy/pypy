import sys

from py.__.misc.terminal_helper import ansi_print, get_terminal_width

"""
Black       0;30     Dark Gray     1;30
Blue        0;34     Light Blue    1;34
Green       0;32     Light Green   1;32
Cyan        0;36     Light Cyan    1;36
Red         0;31     Light Red     1;31
Purple      0;35     Light Purple  1;35
Brown       0;33     Yellow        1;33
Light Gray  0;37     White         1;37
"""


palette = [39, 34, 35, 36, 31, 33, 32, 37]


colour_range = None # used for debugging


def print_pixel(colour, value_range, invert=1):
    chars = [".", ".", "+", "*", "%", "#"]
    idx = lambda chars: (colour+1) * (len(chars) - 1) / value_range
    if invert:
        idx = lambda chars, idx=idx:len(chars) - 1 - idx(chars)
    char = chars[idx(chars)]
    ansi_colour = palette[idx(palette)]
    ansi_print(char, ansi_colour, newline=False, flush=True)
    #if colour_range is None:
    #    global colour_range
    #    colour_range = [colour, colour]
    #else:
    #    global colour_range
    #    colour_range = [min(colour_range[0], colour), max(colour_range[1], colour)]


class Mandelbrot:
    def __init__ (self, width=100, height=28, x_pos=-0.5, y_pos=0, distance=6.75):
        self.xpos = x_pos
        self.ypos = y_pos
        aspect_ratio = 1/3.
        factor = float(distance) / width # lowering the distance will zoom in
        self.xscale = factor * aspect_ratio
        self.yscale = factor
        self.iterations = 170
        self.x = width
        self.y = height
        self.z0 = complex(0, 0)

    def init(self):
        self.do_reset = False
        xmin = self.xpos - self.xscale * self.x / 2
        ymin = self.ypos - self.yscale * self.y / 2
        self.x_range = [xmin + self.xscale * ix for ix in range(self.x)]
        self.y_range = [ymin + self.yscale * iy for iy in range(self.y)]
        
        #print "x", self.x_range[0], self.x_range[-1]
        #print "y", self.y_range[0], self.y_range[-1]

    def reset(self):
        self.do_reset = True

    def generate(self):
        for iy in range(self.y):
            ix = 0
            while ix < self.x:
                c = complex(self.x_range[ix], self.y_range[iy])
                z = self.z0
                colour = 0
                mind = 2

                for i in range(self.iterations):
                    z = z * z + c
                    d = abs(z)
                    if d >= 2:
                        colour = min(int(mind / 0.007), 254) + 1
                        break
                    else:
                        mind = min(d, mind)

                yield ix, iy, colour
                if self.do_reset: # jump to the beginning of the line
                    self.do_reset = False
                    ix = 0
                else:
                    ix += 1


class Driver(object):
    zoom_locations = [
        # x, y, "distance", range
        (0.37865401, 0.669227668, 0.04, 111 - 2),
            ]
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.zoom_location = -1
        self.colour_range = 256
        self.init()

    def init(self):
        self.width = get_terminal_width()
        self.mandelbrot = Mandelbrot(width=self.width, **self.kwargs)
        self.mandelbrot.init()
        self.gen = self.mandelbrot.generate()

    def reset(self):
        self.mandelbrot.reset()

    def jump(self, cnt):
        try:
            garbage = [self.gen.next() for _ in range(cnt)]
        except StopIteration:
            self.restart()

    def restart(self):
        print
        self.init()

    def dot(self):
        x = c = 0
        try:
            x, y, c = self.gen.next()
            if x == 0:
                width = get_terminal_width()
                if width != self.width:
                    self.init()
        except StopIteration:
            kwargs = self.kwargs
            self.zoom_location += 1
            self.zoom_location %= len(self.zoom_locations)
            loc = self.zoom_locations[self.zoom_location]
            kwargs.update({"x_pos": loc[0], "y_pos": loc[1], "distance": loc[2]})
            self.colour_range = loc[3]
            return self.restart()
        if x == self.width - 1:
            print
        print_pixel(c, self.colour_range, 1)


if __name__ == '__main__':
    import random
    from time import sleep

    d = Driver()
    for x in xrange(10000):
        #sleep(random.random() / 3000)
        d.dot()
        if 0 and random.random() < 0.001:
            print
            d.reset()
        if 0 and random.random() < 0.01:
            string = "WARNING! " * 3
            d.jump(len(string))
            print string,

