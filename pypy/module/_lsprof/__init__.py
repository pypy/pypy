
""" _lsprof module
"""

from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    applevelname = '_lsprof'

    interpleveldefs = {'Profiler':'interp_lsprof.W_Profiler'}

    appleveldefs = {}
