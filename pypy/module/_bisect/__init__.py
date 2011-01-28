"""
Mixed-module definition for the _bisect module.
This is an optional module; if not present, bisect.py uses the
pure Python version of these functions.
"""

from pypy.interpreter.mixedmodule import MixedModule


class Module(MixedModule):
    """\
This module provides support for maintaining a list in sorted order without
having to sort the list after each insertion. For long lists of items with
expensive comparison operations, this can be an improvement over the more
common approach."""

    appleveldefs = {
        'insort':        'app_bisect.insort_right',
        'insort_left':   'app_bisect.insort_left',
        'insort_right':  'app_bisect.insort_right',
        }

    interpleveldefs = {
        'bisect':        'interp_bisect.bisect_right',
        'bisect_left':   'interp_bisect.bisect_left',
        'bisect_right':  'interp_bisect.bisect_right',
        }
