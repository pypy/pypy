from pypy.rlib import _rffi_stacklet as _c
from pypy.rpython.lltypesystem import lltype, rffi


class StackletThread(object):

    def __init__(self, config):
        self._gcrootfinder = _getgcrootfinder(config)
        self._thrd = _c.newthread()
        if not self._thrd:
            raise MemoryError

    def __del__(self):
        thrd = self._thrd
        if thrd:
            self._thrd = lltype.nullptr(_c.thread_handle.TO)
            _c.deletethread(thrd)

    def new(self, callback, arg=lltype.nullptr(rffi.VOIDP.TO)):
        return self._gcrootfinder.new(self._thrd, callback, arg)
    new._annspecialcase_ = 'specialize:arg(1)'

    def switch(self, stacklet):
        return self._gcrootfinder.switch(self._thrd, stacklet)

    def destroy(self, stacklet):
        self._gcrootfinder.destroy(self._thrd, stacklet)

    def is_empty_handle(self, stacklet):
        return self._gcrootfinder.is_empty_handle(stacklet)

    def get_null_handle(self):
        return self._gcrootfinder.get_null_handle()

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
