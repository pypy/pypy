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
        '__missing__': 'interp_defaultdict.missing',
        }

    def setup_after_space_initialization(self):
        """NOT_RPYTHON"""
        # must remove the interp-level name '__missing__' after it has
        # been used...  otherwise, some code is not happy about seeing
        # this code object twice
        space = self.space
        space.getattr(self, space.wrap('defaultdict'))  # force importing
        space.delattr(self, space.wrap('__missing__'))
