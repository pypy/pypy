from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef, GetSetProperty

INVALID_HANDLE_VALUE = -1
READABLE = 1
WRITABLE = 2


class W_BaseConnection(Wrappable):
    def __init__(self, handle, flags):
        self.handle = handle
        self.flags = flags

    def descr_repr(self, space):
        conn_type = ["read-only", "write-only", "read-write"][self.flags]

        return space.wrap("<%s %s, handle %zd>" % (
            conn_type, space.type(self).getname(space, '?'), self.handle))

    def close(self):
        if self.handle != INVALID_HANDLE_VALUE:
            self.do_close()
            self.handle = INVALID_HANDLE_VALUE

    def __del__(self):
        self.close()

    def closed_get(space, self):
        return space.w_bool(self.handle == INVALID_HANDLE_VALUE)
    def readable_get(space, self):
        return space.w_bool(self.flags & READABLE)
    def writable_get(space, self):
        return space.w_bool(self.flags & WRITABLE)

class W_SocketConnection(W_BaseConnection):
    pass

W_SocketConnection.typedef = TypeDef(
    'Connection',
    closed = GetSetProperty(W_BaseConnection.closed_get),
    readable = GetSetProperty(W_BaseConnection.readable_get),
    writable = GetSetProperty(W_BaseConnection.writable_get),
)
