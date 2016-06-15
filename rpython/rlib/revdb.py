import sys
from rpython.rlib.objectmodel import we_are_translated, fetch_translated_config
from rpython.rlib.objectmodel import specialize
from rpython.rtyper.lltypesystem import lltype, llmemory, rstr
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rtyper.extregistry import ExtRegistryEntry
from rpython.rtyper.annlowlevel import llhelper, hlstr
from rpython.rtyper.annlowlevel import cast_gcref_to_instance


def stop_point():
    """Indicates a point in the execution of the RPython program where
    the reverse-debugger can stop.  When reverse-debugging, we see
    the "time" as the index of the stop-point that happened.
    """
    if we_are_translated():
        if fetch_translated_config().translation.reverse_debugger:
            llop.revdb_stop_point(lltype.Void)

def register_debug_command(command, lambda_func):
    """Register the extra RPython-implemented debug command."""

def send_output(string):
    """For RPython debug commands: writes the string to stdout."""
    llop.revdb_send_output(lltype.Void, string)

def current_time():
    """For RPython debug commands: returns the current time."""
    return llop.revdb_get_value(lltype.SignedLongLong, 'c')

def current_break_time():
    """Returns the time configured for the next break.  When going forward,
    this is the target time at which we'll stop going forward."""
    return llop.revdb_get_value(lltype.SignedLongLong, 'b')

def most_recent_fork():
    """For RPython debug commands: returns the time of the most
    recent fork.  Going back to that time is fast; going back to a time
    just before is slow."""
    return llop.revdb_get_value(lltype.SignedLongLong, 'f')

def total_time():
    """For RPython debug commands: returns the total time (measured
    as the total number of stop-points)."""
    return llop.revdb_get_value(lltype.SignedLongLong, 't')

@specialize.arg(1)
def go_forward(time_delta, callback, arg_string):
    """For RPython debug commands: tells that after this function finishes,
    the debugger should run the 'forward <time_delta>' command and then
    invoke the 'callback' with no argument.
    """
    _change_time('f', time_delta, callback, arg_string)

@specialize.arg(1)
def jump_in_time(target_time, callback, arg_string, exact=True):
    """For RPython debug commands: the debugger should run the
    'go <target_time>' command.  This will reset the memory and fork again,
    so you can't save any RPython state and read it back.  You can only
    encode the state you want to save into a string.  In the reloaded
    process, 'callback(arg_string)' is called.  If 'exact' is False, go to
    the fork point before target_time but don't go_forward to exactly
    target_time afterwards.
    """
    _change_time('g' if exact else 'b', target_time, callback, arg_string)

def currently_created_objects():
    """For RPython debug commands: returns the current value of
    the object creation counter.  All objects created so far have
    a lower unique id; all objects created afterwards will have a
    unique id greater or equal."""
    return llop.revdb_get_value(lltype.SignedLongLong, 'u')

def first_created_object_uid():
    """Returns the creation number of the first object dynamically created
    by the program.  Older objects are either prebuilt or created before
    the first stop point."""
    return llop.revdb_get_value(lltype.SignedLongLong, '1')

@specialize.argtype(0)
def get_unique_id(x):
    """Returns the creation number of the object 'x'.  For objects created
    by the program, it is globally unique, monotonic, and reproducible
    among multiple processes.  For objects created by a debug command,
    this returns a (random) negative number.  Right now, this returns 0
    for all prebuilt objects.
    """
    return llop.revdb_get_unique_id(lltype.SignedLongLong, x)

def track_object(unique_id):
    """Track the creation of the object given by its unique_id, which must
    be in the future (i.e. >= currently_created_objects()).  Call this
    before go_forward().  If go_forward() goes over the creation of this
    object, then afterwards, get_tracked_object() returns the object.
    Going forward is also interrupted at the following stop point.
    Object tracking is lost by jump_in_time(), like everything else.
    """
    llop.revdb_track_object(lltype.Void, unique_id)

@specialize.arg(0)
def get_tracked_object(Class=llmemory.GCREF):   # or an RPython class
    """Get the tracked object if it was created during the last go_forward().
    Otherwise, returns None.  (Note: this API is minimal: to get an
    object from its unique id, you need first to search backward for a
    time where currently_created_objects() is lower than the unique_id,
    then use track_object() and go_forward() to come back.  You can't
    really track several objects, only one.)
    """
    x = llop.revdb_get_tracked_object(llmemory.GCREF)
    if Class is llmemory.GCREF:
        return x
    return cast_gcref_to_instance(Class, x)


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
                cmds = t.revdb_commands = []
            cmds.append((command, func))
            s_func = self.bookkeeper.immutablevalue(func)
            self.bookkeeper.emulate_pbc_call(self.bookkeeper.position_key,
                                             s_func, [annmodel.s_Str0])

    def specialize_call(self, hop):
        hop.exception_cannot_occur()
