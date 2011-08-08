from pypy.rlib import _rffi_stacklet as _c
from pypy.rpython.lltypesystem import lltype, llmemory


class StackletThread(object):

    def __init__(self, config):
        self._gcrootfinder = _getgcrootfinder(config)
        self._thrd = _c.newthread()
        if not self._thrd:
            raise MemoryError
        self._thrd_deleter = StackletThreadDeleter(self._thrd)

    def new(self, callback, arg=llmemory.NULL):
        return self._gcrootfinder.new(self, callback, arg)
    new._annspecialcase_ = 'specialize:arg(1)'

    def switch(self, stacklet):
        return self._gcrootfinder.switch(self, stacklet)

    def destroy(self, stacklet):
        self._gcrootfinder.destroy(self, stacklet)

    def is_empty_handle(self, stacklet):
        return self._gcrootfinder.is_empty_handle(stacklet)

    def get_null_handle(self):
        return self._gcrootfinder.get_null_handle()


class StackletThreadDeleter(object):
    # quick hack: the __del__ is on another object, so that
    # if the main StackletThread ends up in random circular
    # references, on pypy deletethread() is only called
    # when all that circular reference mess is gone.
    def __init__(self, thrd):
        self._thrd = thrd
    def __del__(self):
        thrd = self._thrd
        if thrd:
            self._thrd = lltype.nullptr(_c.thread_handle.TO)
            _c.deletethread(thrd)

# ____________________________________________________________

def _getgcrootfinder(config):
    if (config is None or
        config.translation.gc in ('ref', 'boehm', 'none')):   # for tests
        gcrootfinder = 'n/a'
    else:
        gcrootfinder = config.translation.gcrootfinder
    gcrootfinder = gcrootfinder.replace('/', '_')
    module = __import__('pypy.rlib._stacklet_%s' % gcrootfinder,
                        None, None, ['__doc__'])
    return module.gcrootfinder
_getgcrootfinder._annspecialcase_ = 'specialize:memo'
