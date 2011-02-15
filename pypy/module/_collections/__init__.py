import py

from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    appleveldefs = {}

    interpleveldefs = {
        'deque' : 'interp_deque.W_Deque',
        }
