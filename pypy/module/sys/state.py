"""
Implementation of interpreter-level 'sys' routines.
"""
import os
from pypy import pypydir
from pypy.interpreter.error import oefmt
from pypy.interpreter.gateway import unwrap_spec
from pypy.module.sys.system import DEFAULT_MAX_STR_DIGITS

# ____________________________________________________________
#

class State:
    def __init__(self, space):
        self.space = space

        self.w_modules = space.newdict(module=True)
        self.w_warnoptions = space.newlist([])
        self.w_argv = space.newlist([])
        self.w_orig_argv = space.newlist([])
        self.w_int_max_str_digits = space.newint(DEFAULT_MAX_STR_DIGITS)

        self.setinitialpath(space)

    def setinitialpath(self, space):
        from pypy.module.sys.initpath import compute_stdlib_path_sourcetree
        # This initial value for sys.prefix is normally overwritten
        # at runtime by initpath.py
        srcdir = os.path.dirname(pypydir)
        self.w_initial_prefix = space.newtext(srcdir)
        # Initialize the default path
        path = compute_stdlib_path_sourcetree(self, space.config.objspace.platlibdir, srcdir)
        self.w_path = space.newlist([space.newfilename(p) for p in path])

def get(space):
    return space.fromcache(State)

def pypy_getudir(space):
    """NOT_RPYTHON
    (should be removed from interpleveldefs before translation)"""
    from rpython.tool.udir import udir
    return space.newfilename(str(udir))

@unwrap_spec(maxdigits=int)
def set_int_max_str_digits(space, maxdigits):
    """Set the maximum string digits limit for non-binary int<->str conversions
    """
    from pypy.module.sys.system import MAX_STR_DIGITS_THRESHOLD

    state = get(space)
    if maxdigits == 0 or maxdigits >= MAX_STR_DIGITS_THRESHOLD:
        state.w_int_max_str_digits = space.newint(maxdigits)
        return
    raise oefmt(space.w_ValueError,
                "maxdigits %d must be 0 or larger than %d",
                maxdigits, MAX_STR_DIGITS_THRESHOLD)

def get_int_max_str_digits(space):
    state = get(space)
    return state.w_int_max_str_digits
