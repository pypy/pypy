"""
This file contains various snippets of my attemts
to create a stackless marshal version. Finally,
I postponed this effort, because the recursive
solution gets quite far, already, and I wanted to
deliver a clean solution, after all. Explicit
stackless-ness is not very nice, after all.
"""

"""

Stackless extension:
--------------------
I used marshal as an example of making recursive
algorithms iterative. At some point in the future,
we will try to automate such transformations. For the
time being, the approach used here is quite nice
and shows, how much superior RPython is over C.
Especially the simple inheritance makes writing
the necessary callbacks a pleasure.
I believe that the recursive version is always more
efficient (to be tested). The strategy used here is
to use recursion up to a small stack depth and to switch
to iteration at some point.

"""

class TupleEmitter(Emitter):
    def init(self):
        self.limit = len(self.w_obj.wrappeditems)
        self.items_w = self.w_obj.wrappeditems
        self.idx = 0
    def emit(self):
        idx = self.idx
        if idx < self.limit:
            self.idx = idx + 1
            return self.items_w[idx]


class TupleCollector(Collector):
    def init(self):
        pass
    def collect(self, w_obj):
        idx = self.idx
        if idx < self.limit:
            self.idx = idx + 1
            self.items_w[idx] = w_obj
            return True
        return False
    def fini(self):
        return W_TupleObject(self.space, self.items_w)


class xxx(object):
    def _run_stackless(self):
        self.stackless = True
        tc = self.get(1)
        w_obj = unmarshal_dispatch[ord(tc)](self.space, self, tc)
        while 1:
            collector = self._stack
            if not collector:
                break
            w_obj = emitter.emit()
            if w_obj:
                self.space.marshal_w(w_obj, self)
            else:
                emitter._teardown()
        self.stackless = False

    def deferred_call(self, collector):
        collector._setup()

# stackless helper class

class Collector(_Base):
    def __init__(self, typecode, unmarshaller):
        self.space = unmarshaller.space
        self.typecode = typecode

    def _setup(self):
        unmarshaller = self.unmarshaller
        self.f_back = unmarshaller._stack
        unmarshaller._stack = self
        self.init()

    def collect(self, w_obj):
        return False # to be overridden

    def _teardown(self):
        self.unmarshaller._stack = self.f_back
        return self.fini()


class ListCollector(Collector):
    def __init__(self, space, typecode, count, finalizer):
        Collector.__init__(self, space, typecode)
        self.limit = count
        self.finalizer = finalizer
        self.items_w = [space.w_None] * count
        self.idx = 0

    def accumulate(self, w_data):
        idx = self.idx
        limit = self.limit
        assert idx < limit
        self.items_w[idx] = w_data
        idx += 1
        self.idx = idx
        return idx < limit

class DictCollector(Collector):
    def __init__(self, space, typecode, finalizer):
        Collector.__init__(self, space, typecode)
        self.finalizer = finalizer
        self.items_w = []
        self.first = False
        self.w_hold = None

    def accumulate(self, w_data):
        first = not self.first
        if w_data is None:
            if not first:
                self.raise_exc('bad marshal data')
            return False
        if first:
            self.w_hold = w_data
        else:
            self.items_w.append( (self.w_hold, w_data) )
        self.first = first
        return True

class yyy(object):
    def _run_stackless(self, w_obj):
        self.stackless = True
        self.space.marshal_w(w_obj, self)
        while 1:
            emitter = self._stack
            if not emitter:
                break
            w_obj = emitter.emit()
            if w_obj:
                self.space.marshal_w(w_obj, self)
            else:
                emitter._teardown()
        self.stackless = False

    def deferred_call(self, emitter):
        emitter._setup()

"""
Protocol:
Functions which write objects check the marshaller's stackless flag.
If set, they call the deferred_call() method with an instance of
an Emitter subclass.
"""

class Emitter(_Base):
    def __init__(self, w_obj, marshaller):
        self.space = marshaller.space
        self.marshaller = marshaller
        self.w_obj = w_obj

    def _setup(self):
        # from now on, we must keep track of recursive objects
        marshaller = self.marshaller
        iddict = marshaller._iddict
        objid = id(self.w_obj)
        if objid in iddict:
            self.raise_exc('recursive objects cannot be marshalled')
        self.f_back = marshaller._stack
        marshaller._stack = self
        iddict[objid] = 1

    def _teardown(self):
        del self.marshaller._iddict[id(self.w_obj)]
        self.marshaller._stack = self.f_back

    def emit(self):
        return None # to be overridden

