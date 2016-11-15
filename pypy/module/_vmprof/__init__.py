from pypy.interpreter.mixedmodule import MixedModule
from rpython.rlib.rvmprof import VMProfPlatformUnsupported

class Module(MixedModule):
    """
    VMProf for PyPy: a statistical profiler
    """
    appleveldefs = {
    }

    interpleveldefs = {
        'enable': 'interp_vmprof.enable',
        'disable': 'interp_vmprof.disable',
        'write_all_code_objects': 'interp_vmprof.write_all_code_objects',
        'VMProfError': 'space.fromcache(interp_vmprof.Cache).w_VMProfError',
    }


# Force the __extend__ hacks and method replacements to occur
# early.  Without this, for example, 'PyCode._init_ready' was
# already found by the annotator to be the original empty
# method, and the annotator doesn't notice that interp_vmprof.py
# (loaded later) replaces this method.
try:
    import pypy.module._vmprof.interp_vmprof
except VMProfPlatformUnsupported as e:
    pass
