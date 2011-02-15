import py

from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    appleveldefs = {
        'defaultdict': 'app_defaultdict.defaultdict',
        }

    interpleveldefs = {
        'deque' : 'interp_deque.W_Deque',
        }
