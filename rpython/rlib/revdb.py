import sys
from rpython.rlib.objectmodel import we_are_translated, fetch_translated_config
from rpython.rlib.objectmodel import specialize
from rpython.rtyper.lltypesystem import lltype, rstr
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rtyper.extregistry import ExtRegistryEntry
from rpython.rtyper.annlowlevel import llhelper, hlstr


def stop_point(n):
    """Indicates a point in the execution of the RPython program where
    the reverse-debugger can stop.  When reverse-debugging, we see
    the "time" as the index of the stop-point that happened.
    """
    if we_are_translated():
        if fetch_translated_config().translation.reverse_debugger:
            llop.revdb_stop_point(lltype.Void, n)

def register_debug_command(command, lambda_func):
    """Register the extra RPython-implemented debug command."""

def send_output(string):
    """For RPython debug commands: writes the string to stdout."""
    llop.revdb_send_output(lltype.Void, string)

def current_time():
    """For RPython debug commands: returns the current time."""
    return llop.revdb_get_value(lltype.Signed, 'c')

def most_recent_fork():
    """For RPython debug commands: returns the time of the most
    recent fork.  Going back to that time is fast; going back to a time
    just before is slow."""
    return llop.revdb_get_value(lltype.Signed, 'm')

def total_time():
    """For RPython debug commands: returns the total time (measured
    as the total number of stop-points)."""
    return llop.revdb_get_value(lltype.Signed, 't')

@specialize.arg(1)
def go_forward(time_delta, callback, arg_string):
    """For RPython debug commands: tells that after this function finishes,
    the debugger should run the 'forward <time_delta>' command and then
    invoke the 'callback' with no argument.
    """
    _change_time('f', time_delta, callback, arg_string)

@specialize.arg(1)
def jump_in_time(target_time, callback, arg_string):
    """For RPython debug commands: the debugger should run the
    'go <target_time>' command.  This will reset the memory and fork again,
    so you can't save any RPython state and read it back.  You can only
    encode the state you want to save into a string.  In the reloaded
    process, 'callback(arg_string)' is called.
    """
    _change_time('g', target_time, callback, arg_string)


# ____________________________________________________________


@specialize.arg(2)
def _change_time(mode, time, callback, arg_string):
    callback_wrapper = _make_callback(callback)
    ll_callback = llhelper(_CALLBACK_ARG_FNPTR, callback_wrapper)
    llop.revdb_change_time(lltype.Void, mode, time, ll_callback, arg_string)

@specialize.memo()
def _make_callback(callback):
    def callback_wrapper(ll_string):
        callback(hlstr(ll_string))
    return callback_wrapper
_CALLBACK_ARG_FNPTR = lltype.Ptr(lltype.FuncType([lltype.Ptr(rstr.STR)],
                                                 lltype.Void))


class RegisterDebugCommand(ExtRegistryEntry):
    _about_ = register_debug_command

    def compute_result_annotation(self, s_command, s_lambda_func):
        from rpython.annotator import model as annmodel
        command = s_command.const
        lambda_func = s_lambda_func.const
        assert isinstance(command, str)
        t = self.bookkeeper.annotator.translator
        if t.config.translation.reverse_debugger:
            func = lambda_func()
            try:
                cmds = t.revdb_commands
            except AttributeError:
                cmds = t.revdb_commands = {}
            cmds[command] = func
            s_func = self.bookkeeper.immutablevalue(func)
            self.bookkeeper.emulate_pbc_call(self.bookkeeper.position_key,
                                             s_func, [annmodel.s_Str0])

    def specialize_call(self, hop):
        hop.exception_cannot_occur()
