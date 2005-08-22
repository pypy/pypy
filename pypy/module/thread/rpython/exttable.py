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

declare(thread.start_new_thread, int,            '%s/start_new_thread' % module)
declare(thread.get_ident,        int,            '%s/get_ident'        % module)
declare(thread.allocate_lock,   thread.LockType, '%s/allocate_lock'    % module)

# ____________________________________________________________
# thread.error can be raised by the above

# XXX a bit hackish
standardexceptions[thread.error] = True
