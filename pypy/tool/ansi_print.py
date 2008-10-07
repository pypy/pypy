"""
A color print.
"""

import sys

from py.__.io.terminalwriter import ansi_print
from pypy.tool.ansi_mandelbrot import Driver

class AnsiLog:
    wrote_dot = False # XXX sharing state with all instances

    KW_TO_COLOR = {
        # color supress
        'red': ((31,), True),
        'bold': ((1,), True),
        'WARNING': ((31,), False),
        'event': ((1,), True),
        'ERROR': ((1, 31), False),
        'info': ((35,), False),
        'stub': ((34,), False),
    }

    def __init__(self, kw_to_color={}, file=None):
        self.kw_to_color = self.KW_TO_COLOR.copy()
        self.kw_to_color.update(kw_to_color)
        self.file = file
        self.fancy = True
        self.isatty = getattr(sys.stderr, 'isatty', lambda: False)
        if self.fancy and self.isatty(): 
            self.mandelbrot_driver = Driver()
        else:
            self.mandelbrot_driver = None

    def __call__(self, msg):
        tty = self.isatty()
        flush = False
        newline = True
        keywords = []
        esc = []
        for kw in msg.keywords:
            color, supress = self.kw_to_color.get(kw, (None, False))
            if color:
                esc.extend(color)
            if not supress:
                keywords.append(kw)
        if 'start' in keywords:
            if tty:
                newline = False
                flush = True
                keywords.remove('start')
        elif 'done' in keywords:
            if tty:
                print >> sys.stderr
                return
        elif 'dot' in keywords:
            if tty:
                if self.fancy:
                    if not AnsiLog.wrote_dot:
                        self.mandelbrot_driver.reset()
                    self.mandelbrot_driver.dot()
                else:
                    ansi_print(".", tuple(esc), file=self.file, newline=False, flush=flush)
                AnsiLog.wrote_dot = True
                return
        if AnsiLog.wrote_dot:
            AnsiLog.wrote_dot = False
            sys.stderr.write("\n")
        esc = tuple(esc)
        for line in msg.content().splitlines():
            ansi_print("[%s] %s" %(":".join(keywords), line), esc, 
                       file=self.file, newline=newline, flush=flush)

ansi_log = AnsiLog()

# ____________________________________________________________
# Nice helper

def raise_nicer_exception(*extraargs):
    cls, e, tb = sys.exc_info()
    str_e = str(e)
    class ExcSubclass(cls):
        def __str__(self):
            lines = [str_e]
            for extra in extraargs:
                lines.append('\t.. %r' % (extra,))
            return '\n'.join(lines)
    ExcSubclass.__name__ = cls.__name__ + "'"
    ExcSubclass.__module__ = cls.__module__
    try:
        e.__class__ = ExcSubclass
    except TypeError:   # doesn't work any more on 2.5 :-(
        pass
    raise ExcSubclass, e, tb
