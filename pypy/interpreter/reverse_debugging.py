import sys
from rpython.rlib import revdb
from rpython.rlib.debug import make_sure_not_resized
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter import gateway, typedef


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
    revdb.register_debug_command(revdb.CMD_PRINT, lambda_print)
    revdb.register_debug_command(revdb.CMD_BACKTRACE, lambda_backtrace)
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

def fetch_cur_frame():
    ec = dbstate.space.getexecutioncontext()
    frame = ec.topframeref()
    if frame is None:
        revdb.send_output("No stack.\n")
    return frame

def compile(source, mode):
    space = dbstate.space
    compiler = space.createcompiler()
    code = compiler.compile(source, '<revdb>', mode, 0,
                            hidden_applevel=True)
    return code


class W_RevDBOutput(W_Root):
    softspace = 0

    def __init__(self, space):
        self.space = space

    def descr_write(self, w_buffer):
        space = self.space
        if space.isinstance_w(w_buffer, space.w_unicode):
            w_buffer = space.call_method(w_buffer, 'encode',
                                         space.wrap('utf-8'))   # safe?
        revdb.send_output(space.str_w(w_buffer))

W_RevDBOutput.typedef = typedef.TypeDef(
    "revdb_output",
    write = gateway.interp2app(W_RevDBOutput.descr_write),
    softspace = typedef.interp_attrproperty("softspace", W_RevDBOutput),
    )


def command_print(cmd, expression):
    frame = fetch_cur_frame()
    if frame is None:
        return
    space = dbstate.space
    try:
        code = compile(expression, 'exec')
        w_revdb_output = space.wrap(W_RevDBOutput(space))
        space.sys.setdictvalue(space, 'stdout', w_revdb_output)
        space.sys.setdictvalue(space, 'stderr', w_revdb_output)
        try:
            code.exec_code(space,
                           frame.get_w_globals(),
                           frame.getdictscope())

        except OperationError as operationerr:
            w_type = operationerr.w_type
            w_value = operationerr.get_w_value(space)
            w_traceback = space.wrap(operationerr.get_traceback())

            # set the sys.last_xxx attributes
            space.setitem(space.sys.w_dict, space.wrap('last_type'), w_type)
            space.setitem(space.sys.w_dict, space.wrap('last_value'), w_value)
            space.setitem(space.sys.w_dict, space.wrap('last_traceback'),
                          w_traceback)

            # call sys.excepthook if present
            w_hook = space.sys.getdictvalue(space, 'excepthook')
            if w_hook is None:
                raise
            space.call_function(w_hook, w_type, w_value, w_traceback)
            return

    except OperationError as e:
        revdb.send_output('%s\n' % e.errorstr(space, use_repr=True))
        return
lambda_print = lambda: command_print


def show_frame(frame, indent=''):
    code = frame.getcode()
    lineno = frame.get_last_lineno()
    revdb.send_output('%sFile "%s", line %d in %s\n%s  ' % (
        indent, code.co_filename, lineno, code.co_name, indent))
    revdb.send_linecache(code.co_filename, lineno)

def command_backtrace(cmd, extra):
    frame = fetch_cur_frame()
    if frame is None:
        return
    if cmd.c_arg1 == 0:
        show_frame(frame)
    else:
        revdb.send_output("Traceback (most recent call last):\n")
        frames = []
        while frame is not None:
            frames.append(frame)
            if len(frames) == 200:
                revdb.send_output("  ...\n")
                break
            frame = frame.get_f_back()
        while len(frames) > 0:
            show_frame(frames.pop(), indent='  ')
lambda_backtrace = lambda: command_backtrace
