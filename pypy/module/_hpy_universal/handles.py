from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib.objectmodel import specialize, always_inline, we_are_translated
from rpython.rlib.unroll import unrolling_iterable

CONSTANTS = [
    ('NULL', lambda space: None),
    ('None', lambda space: space.w_None),
    ('False', lambda space: space.w_False),
    ('True', lambda space: space.w_True),
    ('Exception', lambda space: space.w_Exception),
    ('ValueError', lambda space: space.w_ValueError),
    ('TypeError', lambda space: space.w_TypeError),
    ('IndexError', lambda space: space.w_IndexError),
    ('BaseObjectType', lambda space: space.w_object),
    ('TypeType', lambda space: space.w_type),
    ('LongType', lambda space: space.w_int),
    ('UnicodeType', lambda space: space.w_unicode),
    ('TupleType', lambda space: space.w_tuple),
    ('ListType', lambda space: space.w_list),
    ]


class HandleManager:

    def __init__(self, space):
        self.handles_w = [build_value(space) for name, build_value in CONSTANTS]
        self.release_callbacks = [None] * len(self.handles_w)
        self.free_list = []

    def new(self, w_object):
        if len(self.free_list) == 0:
            index = len(self.handles_w)
            self.handles_w.append(w_object)
            self.release_callbacks.append(None)
        else:
            index = self.free_list.pop()
            self.handles_w[index] = w_object
            # releasers[index] is already set to None by close()
        return index

    def close(self, index):
        assert index > 0
        if self.release_callbacks[index] is not None:
            w_obj = self.deref(index)
            for f in self.release_callbacks[index]:
                f.release(index, w_obj)
            self.release_callbacks[index] = None
        self.handles_w[index] = None
        self.free_list.append(index)

    def deref(self, index):
        assert index > 0
        return self.handles_w[index]

    def consume(self, index):
        """
        Like close, but also return the w_object which was pointed by the handled
        """
        assert index > 0
        w_object = self.handles_w[index]
        self.close(index)
        return w_object

    def dup(self, index):
        w_object = self.handles_w[index]
        return self.new(w_object)

    def attach_release_callback(self, index, cb):
        if self.release_callbacks[index] is None:
            self.release_callbacks[index] = [cb]
        else:
            self.release_callbacks[index].append(cb)


class HandleReleaseCallback(object):

    def release(self, h, w_obj):
        raise NotImplementedError


class FreeNonMovingBuffer(HandleReleaseCallback):
    """
    Callback to call rffi.free_nonmovingbuffer_ll
    """

    def __init__(self, llbuf, llstring, flag):
        self.llbuf = llbuf
        self.llstring = llstring
        self.flag = flag

    def release(self, h, w_obj):
        rffi.free_nonmovingbuffer_ll(self.llbuf, self.llstring, self.flag)



# =========================
# high level user interface
# =========================

def new(space, w_object):
    mgr = space.fromcache(HandleManager)
    return mgr.new(w_object)

def close(space, index):
    mgr = space.fromcache(HandleManager)
    mgr.close(index)

def deref(space, index):
    mgr = space.fromcache(HandleManager)
    return mgr.deref(index)

def consume(space, index):
    mgr = space.fromcache(HandleManager)
    return mgr.consume(index)

def dup(space, index):
    mgr = space.fromcache(HandleManager)
    return mgr.dup(index)

def attach_release_callback(space, index, cb):
    mgr = space.fromcache(HandleManager)
    return mgr.attach_release_callback(index, cb)

# ~~~ context manager ~~~

@specialize.argtype(1)
def using(space, *w_objs):
    """
    context-manager to new/close one or more handles
    """
    # Here we are using some RPython trickery to create different classes
    # depending on the number of w_objs. The idea is that the whole class is
    # optimized away and what's left is a series of calls to handles.new() and
    # handles.close()
    UsingContextManager = make_UsingContextManager(len(w_objs))
    return UsingContextManager(space, w_objs)

@specialize.memo()
def make_UsingContextManager(N):
    INDICES = unrolling_iterable(range(N))
    class UsingContextManager(object):

        @always_inline
        def __init__(self, space, w_objects):
            self.space = space
            self.w_objects = w_objects
            self.handles = (0,) * N

        @always_inline
        def __enter__(self):
            handles = ()
            for i in INDICES:
                h = new(self.space, self.w_objects[i])
                handles += (h,)
            self.handles = handles

            # if we have only one handle, return it directly. This makes it
            # possible to write this:
            #     with handles.using(space, w1) as h1:
            #         ...
            # AND this
            #     with handles.using(space, w1, w2) as (h1, h2):
            #         ...
            if N == 1:
                return self.handles[0]
            else:
                return handles

        @always_inline
        def __exit__(self, etype, evalue, tb):
            for i in INDICES:
                close(self.space, self.handles[i])

    return UsingContextManager
