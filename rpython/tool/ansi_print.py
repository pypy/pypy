"""
A simple color logger.
"""

import sys
from py.io import ansi_print
from rpython.tool.ansi_mandelbrot import Driver


isatty = getattr(sys.stderr, 'isatty', lambda: False)
mandelbrot_driver = Driver()
wrote_dot = False     # global shared state


class Logger(object):

    def __init__(self, name):
        self.name = name

    def _make_method(subname, colors):
        #
        def logger_method(self, text):
            global wrote_dot
            text = "[%s%s] %s" % (self.name, subname, text)
            if isatty():
                col = colors
            else:
                col = ()
            if wrote_dot:
                text = '\n' + text
            ansi_print(text, col)
            wrote_dot = False
        #
        return logger_method

    red      = _make_method('', (31,))
    bold     = _make_method('', (1,))
    WARNING  = _make_method(':WARNING', (31,))
    event    = _make_method('', (1,))
    ERROR    = _make_method(':ERROR', (1, 31))
    Error    = _make_method(':Error', (1, 31))
    info     = _make_method(':info', (35,))
    stub     = _make_method(':stub', (34,))
    __call__ = _make_method('', ())

    def dot(self):
        global wrote_dot
        if not wrote_dot:
            mandelbrot_driver.reset()
            wrote_dot = True
        mandelbrot_driver.dot()
