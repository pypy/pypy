"""
Annotation support for interp-level lock objects.
"""

import thread
from pypy.rpython.extfunctable import declare, declaretype, standardexceptions

module = 'pypy.module.thread.rpython.ll_thread'

# ____________________________________________________________
# The external type thread.LockType

locktypeinfo = declaretype(thread.LockType,
                           "ThreadLock",
                           acquire = (bool,       '%s/acquire_lock' % module),
                           release = (type(None), '%s/release_lock' % module),
                           )

# ____________________________________________________________
# Built-in functions needed in the rtyper

def ann_startthr(s_bootstrap_function, s_argument_tuple):
    from pypy.annotation import model as annmodel
    from pypy.annotation.bookkeeper import getbookkeeper
    bookkeeper = getbookkeeper()
    assert (isinstance(s_argument_tuple, annmodel.SomeTuple) and
            len(s_argument_tuple.items) == 1), (
        """thread.start_new_thread(f, arg) is only supported with a tuple of
           length 1 for arg""")
    s_arg, = s_argument_tuple.items
    # XXX hack hack hack: emulate a call to s_bootstrap_function
    s_result = bookkeeper.emulate_pbc_call(bookkeeper.position_key, s_bootstrap_function, [s_arg])
    assert bookkeeper.getpbc(None).contains(s_result), (
        """thread.start_new_thread(f, arg): f() should return None""")
    return annmodel.SomeInteger()

declare(thread.start_new_thread, ann_startthr,   '%s/start_new_thread' % module)
declare(thread.get_ident,        int,            '%s/get_ident'        % module)
declare(thread.allocate_lock,    thread.LockType,'%s/allocate_lock'    % module)

# ____________________________________________________________
# thread.error can be raised by the above

# XXX a bit hackish
standardexceptions[thread.error] = True
