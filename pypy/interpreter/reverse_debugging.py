import sys
from rpython.rlib import revdb
from rpython.rlib.debug import make_sure_not_resized
from pypy.interpreter.error import oefmt


class DBState:
    extend_syntax_with_dollar_num = False
    metavars = []

dbstate = DBState()


def setup_revdb(space):
    assert space.config.translation.reverse_debugger
    dbstate.space = space
    #make_sure_not_resized(dbstate.breakpoint_funcnames)
    #make_sure_not_resized(dbstate.watch_progs)
    make_sure_not_resized(dbstate.metavars)
    #revdb.register_debug_command(revdb.CMD_PRINT, lambda_print)
    #revdb.register_debug_command(revdb.CMD_BACKTRACE, lambda_backtrace)
    #revdb.register_debug_command(revdb.CMD_LOCALS, lambda_locals)
    #revdb.register_debug_command(revdb.CMD_BREAKPOINTS, lambda_breakpoints)
    #revdb.register_debug_command(revdb.CMD_MOREINFO, lambda_moreinfo)
    #revdb.register_debug_command("ALLOCATING", lambda_allocating)
    #revdb.register_debug_command(revdb.CMD_ATTACHID, lambda_attachid)
    #revdb.register_debug_command(revdb.CMD_CHECKWATCH, lambda_checkwatch)
    #revdb.register_debug_command(revdb.CMD_WATCHVALUES, lambda_watchvalues)

def load_metavar(oparg):
    space = dbstate.space
    metavars = dbstate.metavars
    w_var = metavars[oparg] if oparg < len(metavars) else None
    if w_var is None:
        raise oefmt(space.w_NameError, "no constant object '$%d'",
                    oparg)
    if w_var is space.w_Ellipsis:
        raise oefmt(space.w_RuntimeError,
                    "'$%d' refers to an object created later in time",
                    oparg)
    return w_var
