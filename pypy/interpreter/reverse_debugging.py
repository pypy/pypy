import sys
from rpython.rlib import revdb
from rpython.rlib.debug import make_sure_not_resized
from rpython.rlib.objectmodel import specialize, we_are_translated
from rpython.rtyper.annlowlevel import cast_gcref_to_instance
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter import gateway, typedef, pycode, pytraceback


class DBState:
    extend_syntax_with_dollar_num = False
    breakpoint_stack_id = 0
    breakpoint_funcnames = None
    printed_objects = {}
    metavars = []
    watch_progs = []
    watch_futures = {}

dbstate = DBState()


def setup_revdb(space):
    """Called at run-time, before the space is set up.

    The various register_debug_command() lines attach functions
    to some commands that 'revdb.py' can call, if we are running
    in replay mode.
    """
    assert space.config.translation.reverse_debugger
    dbstate.space = space
    dbstate.w_future = space.w_Ellipsis    # a random prebuilt object

    make_sure_not_resized(dbstate.watch_progs)
    make_sure_not_resized(dbstate.metavars)

    revdb.register_debug_command(revdb.CMD_PRINT, lambda_print)
    revdb.register_debug_command(revdb.CMD_BACKTRACE, lambda_backtrace)
    revdb.register_debug_command(revdb.CMD_LOCALS, lambda_locals)
    revdb.register_debug_command(revdb.CMD_BREAKPOINTS, lambda_breakpoints)
    revdb.register_debug_command(revdb.CMD_STACKID, lambda_stackid)
    revdb.register_debug_command("ALLOCATING", lambda_allocating)
    revdb.register_debug_command(revdb.CMD_ATTACHID, lambda_attachid)
    #revdb.register_debug_command(revdb.CMD_CHECKWATCH, lambda_checkwatch)
    #revdb.register_debug_command(revdb.CMD_WATCHVALUES, lambda_watchvalues)


pycode.PyCode.co_revdb_linestarts = None   # or a string: an array of bits


def enter_call(caller_frame, callee_frame):
    if dbstate.breakpoint_funcnames is not None:
        name = callee_frame.getcode().co_name
        if name in dbstate.breakpoint_funcnames:
            revdb.breakpoint(dbstate.breakpoint_funcnames[name])
    if dbstate.breakpoint_stack_id != 0:
        if dbstate.breakpoint_stack_id == revdb.get_unique_id(caller_frame):
            revdb.breakpoint(-1)

def leave_call(caller_frame, callee_frame):
    if dbstate.breakpoint_stack_id != 0:
        if dbstate.breakpoint_stack_id == revdb.get_unique_id(caller_frame):
            revdb.breakpoint(-1)

def potential_stop_point(frame):
    if not we_are_translated():
        return
    #
    # We only record a stop_point at every line, not every bytecode.
    # Uses roughly the same algo as ExecutionContext.run_trace_func()
    # to know where the line starts are, but tweaked for speed,
    # avoiding the quadratic complexity when run N times with a large
    # code object.  A potential difference is that we only record
    # where the line starts are; the "We jumped backwards in the same
    # line" case of run_trace_func() is not fully reproduced.
    #
    code = frame.pycode
    lstart = code.co_revdb_linestarts
    if lstart is None:
        lstart = build_co_revdb_linestarts(code)
    index = frame.last_instr
    c = lstart[index >> 3]
    if ord(c) & (1 << (index & 7)):
        stop_point_at_start_of_line()

def build_co_revdb_linestarts(code):
    # inspired by findlinestarts() in the 'dis' standard module
    bits = [False] * len(code.co_code)
    if not code.hidden_applevel:
        lnotab = code.co_lnotab
        addr = 0
        p = 0
        newline = 1
        while p + 1 < len(lnotab):
            byte_incr = ord(lnotab[p])
            line_incr = ord(lnotab[p+1])
            if byte_incr:
                if newline != 0:
                    if addr < len(bits):
                        bits[addr] = True
                    newline = 0
                addr += byte_incr
            newline |= line_incr
            p += 2
        if newline:
            if addr < len(bits):
                bits[addr] = True
    #
    byte_list = []
    pending = 0
    nextval = 1
    for bit_is_set in bits:
        if bit_is_set:
            pending |= nextval
        if nextval < 128:
            nextval <<= 1
        else:
            byte_list.append(chr(pending))
            pending = 0
            nextval = 1
    if nextval != 1:
        byte_list.append(chr(pending))
    lstart = ''.join(byte_list)
    code.co_revdb_linestarts = lstart
    return lstart

def get_final_lineno(code):
    lineno = code.co_firstlineno
    lnotab = code.co_lnotab
    p = 1
    while p < len(lnotab):
        line_incr = ord(lnotab[p])
        lineno += line_incr
        p += 2
    return lineno


def stop_point_at_start_of_line():
    if revdb.watch_save_state():
        any_watch_point = False
        #for prog, watch_id, expected in dbstate.watch_progs:
        #    any_watch_point = True
        #    got = _watch_expr(prog)
        #    if got != expected:
        #        break
        #else:
        watch_id = -1
        revdb.watch_restore_state(any_watch_point)
        if watch_id != -1:
            revdb.breakpoint(watch_id)
    revdb.stop_point()


def load_metavar(index):
    assert index >= 0
    space = dbstate.space
    metavars = dbstate.metavars
    w_var = metavars[index] if index < len(metavars) else None
    if w_var is None:
        raise oefmt(space.w_NameError, "no constant object '$%d'",
                    index)
    if w_var is dbstate.w_future:
        raise oefmt(space.w_RuntimeError,
                    "'$%d' refers to an object created later in time",
                    index)
    return w_var

def set_metavar(index, w_obj):
    assert index >= 0
    if index >= len(dbstate.metavars):
        missing = index + 1 - len(dbstate.metavars)
        dbstate.metavars = dbstate.metavars + [None] * missing
    dbstate.metavars[index] = w_obj


def fetch_cur_frame():
    ec = dbstate.space.getexecutioncontext()
    frame = ec.topframeref()
    if frame is None:
        revdb.send_output("No stack.\n")
    return frame

def compile(source, mode):
    space = dbstate.space
    compiler = space.createcompiler()
    dbstate.extend_syntax_with_dollar_num = True
    try:
        code = compiler.compile(source, '<revdb>', mode, 0,
                                hidden_applevel=True)
    finally:
        dbstate.extend_syntax_with_dollar_num = False
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

def descr_get_softspace(space, revdb):
    return space.wrap(revdb.softspace)
def descr_set_softspace(space, revdb, w_newvalue):
    revdb.softspace = space.int_w(w_newvalue)

W_RevDBOutput.typedef = typedef.TypeDef(
    "revdb_output",
    write = gateway.interp2app(W_RevDBOutput.descr_write),
    softspace = typedef.GetSetProperty(descr_get_softspace,
                                       descr_set_softspace,
                                       cls=W_RevDBOutput),
    )

def revdb_displayhook(space, w_obj):
    """Modified sys.displayhook() that also outputs '$NUM = ',
    for non-prebuilt objects.  Such objects are then recorded in
    'printed_objects'.
    """
    if space.is_w(w_obj, space.w_None):
        return
    uid = revdb.get_unique_id(w_obj)
    if uid > 0:
        dbstate.printed_objects[uid] = w_obj
        revdb.send_nextnid(uid)   # outputs '$NUM = '
    space.setitem(space.builtin.w_dict, space.wrap('_'), w_obj)
    # do str_w(repr()) only now: if w_obj was produced successfully,
    # but its repr crashes because it tries to do I/O, then we already
    # have it recorded in '_' and in '$NUM ='.
    s = space.str_w(space.repr(w_obj))
    revdb.send_output(s)
    revdb.send_output("\n")

@specialize.memo()
def get_revdb_displayhook(space):
    return space.wrap(gateway.interp2app(revdb_displayhook))


def prepare_print_environment(space):
    w_revdb_output = space.wrap(W_RevDBOutput(space))
    w_displayhook = get_revdb_displayhook(space)
    space.sys.setdictvalue(space, 'stdout', w_revdb_output)
    space.sys.setdictvalue(space, 'stderr', w_revdb_output)
    space.sys.setdictvalue(space, 'displayhook', w_displayhook)

def command_print(cmd, expression):
    frame = fetch_cur_frame()
    if frame is None:
        return
    space = dbstate.space
    try:
        prepare_print_environment(space)
        code = compile(expression, 'single')
        try:
            code.exec_code(space,
                           frame.get_w_globals(),
                           frame.getdictscope())

        except OperationError as operationerr:
            # can't use sys.excepthook: it will likely try to do 'import
            # traceback', which might not be doable without using I/O
            tb = operationerr.get_traceback()
            if tb is not None:
                revdb.send_output("Traceback (most recent call last):\n")
                while tb is not None:
                    if not isinstance(tb, pytraceback.PyTraceback):
                        revdb.send_output("  ??? %s\n" % tb)
                        break
                    show_frame(tb.frame, tb.get_lineno(), indent='  ')
                    tb = tb.next

            # set the sys.last_xxx attributes
            w_type = operationerr.w_type
            w_value = operationerr.get_w_value(space)
            w_tb = space.wrap(operationerr.get_traceback())
            space.setitem(space.sys.w_dict, space.wrap('last_type'), w_type)
            space.setitem(space.sys.w_dict, space.wrap('last_value'), w_value)
            space.setitem(space.sys.w_dict, space.wrap('last_traceback'), w_tb)

            # re-raise, catch me in the outside "except OperationError"
            raise

    except OperationError as e:
        revdb.send_output('%s\n' % e.errorstr(space, use_repr=True))
lambda_print = lambda: command_print


def file_and_lineno(frame, lineno):
    code = frame.getcode()
    return 'File "%s", line %d in %s' % (
        code.co_filename, lineno, code.co_name)

def show_frame(frame, lineno=0, indent=''):
    if lineno == 0:
        lineno = frame.get_last_lineno()
    revdb.send_output("%s%s\n%s  " % (
        indent,
        file_and_lineno(frame, lineno),
        indent))
    revdb.send_linecache(frame.getcode().co_filename, lineno)

def display_function_part(frame, max_lines_before, max_lines_after):
    code = frame.getcode()
    if code.co_filename.startswith('<builtin>'):
        return
    first_lineno = code.co_firstlineno
    current_lineno = frame.get_last_lineno()
    final_lineno = get_final_lineno(code)
    #
    ellipsis_after = False
    if first_lineno < current_lineno - max_lines_before - 1:
        first_lineno = current_lineno - max_lines_before
        revdb.send_output("...\n")
    if final_lineno > current_lineno + max_lines_after + 1:
        final_lineno = current_lineno + max_lines_after
        ellipsis_after = True
    #
    for i in range(first_lineno, final_lineno + 1):
        if i == current_lineno:
            revdb.send_output("> ")
        else:
            revdb.send_output("  ")
        revdb.send_linecache(code.co_filename, i, strip=False)
    #
    if ellipsis_after:
        revdb.send_output("...\n")

def command_backtrace(cmd, extra):
    frame = fetch_cur_frame()
    if frame is None:
        return
    if cmd.c_arg1 == 0:
        revdb.send_output("%s:\n" % (
            file_and_lineno(frame, frame.get_last_lineno()),))
        display_function_part(frame, max_lines_before=8, max_lines_after=5)
    elif cmd.c_arg1 == 2:
        display_function_part(frame, max_lines_before=1000,max_lines_after=1000)
    else:
        revdb.send_output("Current call stack (most recent call last):\n")
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


def command_locals(cmd, extra):
    frame = fetch_cur_frame()
    if frame is None:
        return
    space = dbstate.space
    try:
        prepare_print_environment(space)
        space.appexec([space.wrap(space.sys),
                       frame.getdictscope()], """(sys, locals):
            lst = locals.keys()
            lst.sort()
            print 'Locals:'
            for key in lst:
                try:
                    print '    %s =' % key,
                    s = '%r' % locals[key]
                    if len(s) > 140:
                        s = s[:100] + '...' + s[-30:]
                    print s
                except:
                    exc, val, tb = sys.exc_info()
                    print '!<%s: %r>' % (exc, val)
        """)
    except OperationError as e:
        revdb.send_output('%s\n' % e.errorstr(space, use_repr=True))
lambda_locals = lambda: command_locals


def command_breakpoints(cmd, extra):
    dbstate.breakpoint_stack_id = cmd.c_arg1
    funcnames = None
    for i, name in enumerate(extra.split('\x00')):
        if name:
            if name[0] == 'B':
                if funcnames is None:
                    funcnames = {}
                funcnames[name[1:]] = i
            elif name[0] == 'W':
                pass
                ## try:
                ##     prog = compiler.parse(dbstate.space, name[1:])
                ## except DuhtonError, e:
                ##     revdb.send_output('compiling "%s": %s\n' %
                ##                       (name[1:], e.msg))
                ## else:
                ##     watch_progs.append((prog, i, ''))
    dbstate.breakpoint_funcnames = funcnames
lambda_breakpoints = lambda: command_breakpoints

def command_stackid(cmd, extra):
    frame = fetch_cur_frame()
    if frame is not None and cmd.c_arg1 != 0:     # parent_flag
        frame = dbstate.space.getexecutioncontext().getnextframe_nohidden(frame)
    if frame is None:
        uid = 0
    else:
        uid = revdb.get_unique_id(frame)
    revdb.send_answer(revdb.ANSWER_STACKID, uid)
lambda_stackid = lambda: command_stackid


def command_allocating(uid, gcref):
    w_obj = cast_gcref_to_instance(W_Root, gcref)
    dbstate.printed_objects[uid] = w_obj
    try:
        index_metavar = dbstate.watch_futures.pop(uid)
    except KeyError:
        pass
    else:
        set_metavar(index_metavar, w_obj)
lambda_allocating = lambda: command_allocating


def command_attachid(cmd, extra):
    space = dbstate.space
    index_metavar = cmd.c_arg1
    uid = cmd.c_arg2
    try:
        w_obj = dbstate.printed_objects[uid]
    except KeyError:
        # uid not found, probably a future object
        dbstate.watch_futures[uid] = index_metavar
        w_obj = dbstate.w_future
    set_metavar(index_metavar, w_obj)
lambda_attachid = lambda: command_attachid
