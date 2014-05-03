from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import unwrap_spec
from pypy.module.thread.error import wrap_thread_error
from rpython.rtyper.lltypesystem import rffi



def exclusive_atomic_enter(space):
    if space.config.translation.stm:
        from rpython.rlib.rstm import is_atomic
        count = is_atomic()
    else:
        giltl = space.threadlocals
        count = giltl.is_atomic
    if count:
        raise wrap_thread_error(space,
            "exclusive_atomic block can't be entered inside another atomic block")

    atomic_enter(space)

def atomic_enter(space):
    if space.config.translation.stm:
        from rpython.rlib.rstm import increment_atomic
        increment_atomic()
    else:
        giltl = space.threadlocals
        giltl.is_atomic += 1
        space.threadlocals.set_gil_releasing_calls()

def atomic_exit(space, w_ignored1=None, w_ignored2=None, w_ignored3=None):
    if space.config.translation.stm:
        from rpython.rlib.rstm import decrement_atomic, is_atomic
        if is_atomic():
            decrement_atomic()
            return
    else:
        giltl = space.threadlocals
        if giltl.is_atomic > 0:
            giltl.is_atomic -= 1
            space.threadlocals.set_gil_releasing_calls()
            return
    raise wrap_thread_error(space,
        "atomic.__exit__(): more exits than enters")

def getsegmentlimit(space):
    '''Return the number of "segments" this PyPy is running with.

With STM, multithreaded Python code executes on multiple segments in
parallel.  This function gives the limit above which more threads will not
be able to execute on more cores.  In a non-STM PyPy, this limit is 1.

XXX This limit is so far a compile time option (STM_NB_SEGMENTS in
rpython/translator/stm/src_stm/stmgc.h), but this should instead be
based on the machine found at run-time.  We should also be able to
change the limit (or at least lower it) with setsegmentlimit().
'''
    if space.config.translation.stm:
        from rpython.rlib.rstm import stm_nb_segments
        return space.wrap(stm_nb_segments + 0)  # :-( annotation hack
    else:
        return space.wrap(1)

@unwrap_spec(mintime=float)
def longest_abort_info(space, mintime=0.0):
    if space.config.translation.stm:
        from rpython.rlib import rstm
        if rstm.longest_marker_time() <= mintime:
            return space.w_None
        a, b, c, d = rstm.longest_abort_info()
        return space.newtuple([space.wrap(a), space.wrap(b),
                               space.wrap(c), space.wrap(d)])
    else:
        return space.w_None

def reset_longest_abort_info(space):
    if space.config.translation.stm:
        from rpython.rlib.rstm import reset_longest_abort_info
        reset_longest_abort_info()
