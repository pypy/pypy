from __future__ import print_function
from os.path import join, dirname

from rpython.rtyper.lltypesystem import rffi
from pypy import pypydir
from pypy.interpreter import gateway
from pypy.interpreter.error import OperationError, oefmt
from pypy.module.cpyext.api import cts, CANNOT_FAIL
from pypy.module.cpyext.state import State

filename = join(pypydir, 'interpreter', 'app_main.py')
app = gateway.applevel(open(filename).read(), 'app_main.py', 'app_main')

@cts.decl("void Py_InitializeEx(int install_sigs)", error=CANNOT_FAIL)
def Py_InitializeEx(space, install_sigs):
    runtime_initialized = space.fromcache(State).get_runtime_initialized()
    if runtime_initialized:
        return
    try:
        # CPython uses _Py_path_config.program_name
        argv_w = space.sys.get('argv')
        if space.len_w(argv_w):
            w_progname = space.getitem(argv_w, space.newint(0))
        else:
            w_progname = space.newtext("pypy3")

        w_setup_bootstrap_path_and_encoding = app.wget(space,
                            "setup_bootstrap_path_and_encoding")
        space.call_function(w_setup_bootstrap_path_and_encoding, w_progname)

        w_parse_command_line = app.wget(space, "parse_command_line")
        w_cmdline = space.call_function(w_parse_command_line, space.newbytes(''), argv_w)

        w_setup_and_fix_paths = app.wget(space, "setup_and_fix_paths")
        space.call(w_setup_and_fix_paths, space.newlist([]), w_cmdline)

        w_startup_interpreter = app.wget(space, "startup_interpreter")
        space.call(w_startup_interpreter, space.newlist([]), w_cmdline)
    except OperationError:
        raise
    except Exception as e:
        raise oefmt(space.w_SystemExit, "%s", str(e))
    
    space.fromcache(State).set_runtime_initialized()

@cts.decl("void Py_Initialize(void)", error=CANNOT_FAIL)
def Py_Initialize(space):
    Py_InitializeEx(space, 1)

@cts.decl("void Py_Finalize(void)", error=CANNOT_FAIL)
def Py_Finalize(space):
    Py_FinalizeEx(space)

@cts.decl("void Py_FinalizeEx(void)", error=CANNOT_FAIL)
def Py_FinalizeEx(space):
    # sync with app_main.run_toplevel shutdown code
    if space.config.translation.reverse_debugger:
        from pypy.interpreter.reverse_debugging import stop_point
        stop_point()
    space.getexecutioncontext().settrace(None)
    space.getexecutioncontext().setprofile(None)
