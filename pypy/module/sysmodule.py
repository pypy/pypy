from pypy.interpreter.extmodule import *
import sys

class Sys(BuiltinModule):
    __pythonname__ = 'sys'
    stdout = appdata(sys.stdout)
    displayhook = appdata(sys.displayhook)
