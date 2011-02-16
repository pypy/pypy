import py

from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    """High performance data structures.
- deque:        ordered collection accessible from endpoints only
- defaultdict:  dict subclass with a default value factory
"""

    appleveldefs = {
        'defaultdict': 'app_defaultdict.defaultdict',
        }

    interpleveldefs = {
        'deque' : 'interp_deque.W_Deque',
        }
