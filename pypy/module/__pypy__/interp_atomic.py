from pypy.interpreter.error import OperationError
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

def last_abort_info(space):
    from rpython.rlib.rstm import charp_inspect_abort_info
    p = charp_inspect_abort_info()
    if not p:
        return space.w_None
    assert p[0] == 'l'
    w_obj, p = bdecode(space, p)
    assert p[0] == '\0'
    return w_obj

def discard_last_abort_info(space):
    from rpython.rlib.rstm import charp_inspect_abort_info
    charp_inspect_abort_info()

def bdecode(space, p):
    return decoder[p[0]](space, p)

def bdecodeint(space, p):
    p = rffi.ptradd(p, 1)
    n = 0
    while p[n] != 'e':
        n += 1
    return (space.call_function(space.w_int,
               space.wrap(rffi.charpsize2str(p, n))),
            rffi.ptradd(p, n + 1))

def bdecodelist(space, p):
    p = rffi.ptradd(p, 1)
    objects_w = []
    while p[0] != 'e':
        w_obj, p = bdecode(space, p)
        objects_w.append(w_obj)
    return (space.newlist(objects_w), rffi.ptradd(p, 1))

def bdecodestr(space, p):
    length = 0
    n = 0
    while p[n] != ':':
        c = p[n]
        n += 1
        assert '0' <= c <= '9'
        length = length * 10 + (ord(c) - ord('0'))
    n += 1
    p = rffi.ptradd(p, n)
    return (space.wrap(rffi.charpsize2str(p, length)),
            rffi.ptradd(p, length))

decoder = {'i': bdecodeint,
           'l': bdecodelist,
           #'d': bdecodedict,
           }
for c in '0123456789':
    decoder[c] = bdecodestr
