"""
If we are on pypy, use the real debug_* functions defined in __pypy__.

Else, use empty functions
"""

try:
    from __pypy__ import debug_start, debug_stop, debug_print, debug_print_once
except ImportError:
    def debug_start(*args):
        pass
    
    def debug_stop(*args):
        pass
    
    def debug_print(*args):
        pass
    
    def debug_print_once(*args):
        pass
