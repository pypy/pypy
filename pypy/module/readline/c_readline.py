from pypy.rpython.tool import rffi_platform as platform
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import ObjSpace, interp2app
from pypy.translator.tool.cbuild import ExternalCompilationInfo

eci = ExternalCompilationInfo(
    includes = ["readline/readline.h", "readline/history.h"],
    libraries = ['readline']
)

def external(name, args, result):
    return rffi.llexternal(name, args, result, compilation_info=eci)

# get a binding to  c library functions and define their args and return types
# char *readline(char *)
c_readline = external('readline', [rffi.CCHARP], rffi.CCHARP)

# void rl_initiliaze(void)
c_rl_initialize = external('rl_initialize', [], lltype.Void)

# void using_history(void)
c_using_history = external('using_history', [], lltype.Void)

# void add_history(const char *)
c_add_history = external('add_history', [rffi.CCHARP], lltype.Void)

#------------------------------------------------------------
# special initialization of readline 

class ReadlineState(object):
    lastline = ""        # XXX possibly temporary hack
readlinestate = ReadlineState()

def setup_readline(space, w_module):
    c_using_history()
    # XXX CPython initializes more stuff here
    c_rl_initialize()
    # install sys.__raw_input__, a hook that will be used by raw_input()
    space.setitem(space.sys.w_dict, space.wrap('__raw_input__'),
                  space.wrap(app_readline_func))

def readline_func(space, prompt):
    ll_res = c_readline(prompt)
    if not ll_res:
        raise OperationError(space.w_EOFError, space.w_None)
    res = rffi.charp2str(ll_res)
    if res and res != readlinestate.lastline:
        readlinestate.lastline = res
        c_add_history(res)
    return space.wrap(res)

readline_func.unwrap_spec = [ObjSpace, str]
app_readline_func = interp2app(readline_func)
