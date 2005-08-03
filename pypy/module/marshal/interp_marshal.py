from pypy.interpreter.baseobjspace import ObjSpace
from pypy.interpreter.error import OperationError
from pypy.rpython.rarithmetic import intmask
import sys

# Py_MARSHAL_VERSION = 2
# this is from Python 2.5
# already implemented, but for compatibility,
# we default to version 1. Version 2 can be
# tested, anyway, by using the optional parameter.
# XXX auto-configure this by inspecting the
# Python version we emulate. How to do this?
Py_MARSHAL_VERSION = 1

def dump(space, w_data, w_f, w_version=Py_MARSHAL_VERSION):
    writer = FileWriter(space, w_f)
    # note: bound methods are currently not supported,
    # so we have to pass the instance in, instead.
    ##m = Marshaller(space, writer.write, space.int_w(w_version))
    m = Marshaller(space, writer, space.int_w(w_version))
    m.put_w_obj(w_data)

def dumps(space, w_data, w_version=Py_MARSHAL_VERSION):
    # using a list's append directly does not work,
    # it leads to someobjectness.
    writer = StringWriter()
    m = Marshaller(space, writer, space.int_w(w_version))
    m.put_w_obj(w_data)
    return space.wrap(writer.get_value())

def load(space, w_f):
    reader = FileReader(space, w_f)
    u = Unmarshaller(space, reader)
    return u.get_w_obj(False)

def loads(space, w_str):
    reader = StringReader(space, w_str)
    u = Unmarshaller(space, reader)
    return u.get_w_obj(False)


class _BaseWriter(object):
    pass


class _BaseReader(object):
    def raise_eof(self):
        space = self.space
        raise OperationError(space.w_EOFError, space.wrap(
            'EOF read where object expected'))


class FileWriter(_BaseWriter):
    def __init__(self, space, w_f):
        self.space = space
        try:
            self.func = space.getattr(w_f, space.wrap('write'))
            # XXX how to check if it is callable?
        except OperationError:
            raise OperationError(space.w_TypeError, space.wrap(
            'marshal.dump() 2nd arg must be file-like object'))

    def raise_eof(self):
        space = self.space
        raise OperationError(space.w_EOFError, space.wrap(
            'EOF read where object expected'))

    def write(self, data):
        space = self.space
        space.call_function(self.func, space.wrap(data))


class FileReader(_BaseReader):
    def __init__(self, space, w_f):
        self.space = space
        try:
            self.func = space.getattr(w_f, space.wrap('read'))
            # XXX how to check if it is callable?
        except OperationError:
            raise OperationError(space.w_TypeError, space.wrap(
            'marshal.load() arg must be file-like object'))

    def read(self, n):
        space = self.space
        w_ret = space.call_function(self.func, space.wrap(n))
        ret = space.str_w(w_ret)
        if len(ret) != n:
            self.raise_eof()
        return ret


class StringWriter(_BaseWriter):
    # actually we are writing to a stringlist
    def __init__(self):
        self.buflis = []

    def write(self, data):
        self.buflis.append(data)

    def get_value(self):
        return ''.join(self.buflis)


class StringReader(_BaseReader):
    def __init__(self, space, w_str):
        self.space = space
        try:
            self.bufstr = space.str_w(w_str)
        except OperationError:
            raise OperationError(space.w_TypeError, space.wrap(
                'marshal.loads() arg must be string'))
        self.bufpos = 0
        self.limit = len(self.bufstr)

    def read(self, n):
        pos = self.bufpos
        newpos = pos + n
        if newpos > self.limit:
            self.raise_eof()
        self.bufpos = newpos
        return self.bufstr[pos : newpos]


MAX_MARSHAL_DEPTH = 5000

# the above is unfortunately necessary because CPython
# relies on it without run-time checking.
# PyPy is currently in much bigger trouble, because the
# multimethod dispatches cause deeper stack nesting.

# we try to do a true stack limit estimate, assuming that
# one applevel call costs at most APPLEVEL_STACK_COST
# nested calls.

nesting_limit = sys.getrecursionlimit()
APPLEVEL_STACK_COST = 25    # XXX check if this is true

CPYTHON_COMPATIBLE = True

TEST_CONST = 10

class _Base(object):
    def raise_exc(self, msg):
        space = self.space
        raise OperationError(space.w_ValueError, space.wrap(msg))

DONT_USE_MM_HACK = False

class Marshaller(_Base):
    # _annspecialcase_ = "specialize:ctr_location" # polymorphic
    # does not work with subclassing
    
    def __init__(self, space, writer, version):
        self.space = space
        ## self.put = putfunc
        self.writer = writer
        self.version = version
        # account for the applevel that we will call by one more.
        self.nesting = ((space.getexecutioncontext().framestack.depth() + 1)
                        * APPLEVEL_STACK_COST + TEST_CONST)
        self.cpy_nesting = 0    # contribution to compatibility
        self.stringtable = {}
        self.stackless = False
        self._stack = None
        self._iddict = {}

    ## currently we cannot use a put that is a bound method
    ## from outside. Same holds for get.
    def put(self, s):
        self.writer.write(s)

    def atom(self, typecode):
        assert type(typecode) is str and len(typecode) == 1
        self.put(typecode)

    def atom_int(self, typecode, x):
        a = chr(x & 0xff)
        x >>= 8
        b = chr(x & 0xff)
        x >>= 8
        c = chr(x & 0xff)
        x >>= 8
        d = chr(x & 0xff)
        self.put(typecode + a + b + c + d)

    def atom_int64(self, typecode, x):
        self.atom_int(typecode, x)
        self.put_int(x>>32)

    def atom_str(self, typecode, x):
        self.atom_int(typecode, len(x))
        self.put(x)

    def atom_strlist(self, typecode, tc2, x):
        self.atom_int(typecode, len(x))
        for item in x:
            if type(item) is not str:
                self.raise_exc('object with wrong type in strlist')
            self.atom_str(tc2, item)

    def start(self, typecode):
        assert type(typecode) is str and len(typecode) == 1
        self.put(typecode)

    def put_short(self, x):
        a = chr(x & 0xff)
        x >>= 8
        b = chr(x & 0xff)
        self.put(a + b)

    def put_int(self, x):
        a = chr(x & 0xff)
        x >>= 8
        b = chr(x & 0xff)
        x >>= 8
        c = chr(x & 0xff)
        x >>= 8
        d = chr(x & 0xff)
        self.put(a + b + c + d)

    def put_pascal(self, x):
        lng = len(x)
        if lng > 255:
            self.raise_exc('not a pascal string')
        self.put(chr(lng))
        self.put(x)

    # HACK!ing a bit to loose some recursion depth and gain some speed.
    # XXX it would be nicer to have a clean interface for this.
    # remove this hack when we have optimization
    # YYY we can drop the chain of mm dispatchers and save code if a method
    # does not use NotImplemented at all.
    def _get_mm_marshal(self, w_obj):
        mm = getattr(w_obj, '__mm_marshal_w')
        mm_func = mm.im_func
        name = mm_func.func_code.co_names[0]
        assert name.startswith('marshal_w_')
        return mm_func.func_globals[name]

    def put_w_obj(self, w_obj):
        self.nesting += 2
        do_nested = self.nesting < nesting_limit
        if CPYTHON_COMPATIBLE:
            self.cpy_nesting += 1
            do_nested = do_nested and self.cpy_nesting < MAX_MARSHAL_DEPTH
        if do_nested:
            if DONT_USE_MM_HACK:
                self.nesting += 2
                self.space.marshal_w(w_obj, self)
                self.nesting -= 2
            else:
                self._get_mm_marshal(w_obj)(self.space, w_obj, self)
        else:
            self._run_stackless(w_obj)
        self.nesting -= 2
        if CPYTHON_COMPATIBLE:
            self.cpy_nesting -= 1

    # this function is inlined below
    def put_list_w(self, list_w, lng):
        self.nesting += 1
        self.put_int(lng)
        idx = 0
        while idx < lng:
            self.put_w_obj(list_w[idx])
            idx += 1
        self.nesting -= 1

    def put_list_w(self, list_w, lng):
        if DONT_USE_MM_HACK:
            # inlining makes no sense without the hack
            self.nesting += 1
            self.put_int(lng)
            idx = 0
            while idx < lng:
                self.put_w_obj(list_w[idx])
                idx += 1
            self.nesting -= 1
            return

        # inlined version, two stack levels, only!
        self.nesting += 2
        self.put_int(lng)
        idx = 0
        space = self.space
        do_nested = self.nesting < nesting_limit
        if CPYTHON_COMPATIBLE:
            self.cpy_nesting += 1
            do_nested = do_nested and self.cpy_nesting < MAX_MARSHAL_DEPTH
        if do_nested:
            while idx < lng:
                w_obj = list_w[idx]
                self._get_mm_marshal(w_obj)(space, w_obj, self)
                idx += 1
        else:
            while idx < lng:
                w_obj = list_w[idx]
                self._run_stackless(w_obj)
                idx += 1
        self.nesting -= 2
        if CPYTHON_COMPATIBLE:
            self.cpy_nesting -= 1

    def _run_stackless(self, w_obj):
        self.raise_exc('object too deeply nested to marshal')


def invalid_typecode(space, u, tc):
    u.raise_exc('invalid typecode in unmarshal: %r' % tc)

def register(codes, func):
    """NOT_RPYTHON"""
    for code in codes:
        Unmarshaller._dispatch[ord(code)] = func


class Unmarshaller(_Base):
    _dispatch = [invalid_typecode] * 256

    def __init__(self, space, reader):
        self.space = space
        ## self.get = getfunc
        self.reader = reader
        # account for the applevel that we will call by one more.
        self.nesting = ((space.getexecutioncontext().framestack.depth() + 1)
                        * APPLEVEL_STACK_COST)
        self.stringtable_w = []

    def get(self, n):
        assert n >= 0
        return self.reader.read(n)

    def atom_str(self, typecode):
        self.start(typecode)
        lng = self.get_lng()
        return self.get(lng)

    def atom_strlist(self, typecode, tc2):
        self.start(typecode)
        lng = self.get_lng()
        res = [None] * lng
        idx = 0
        while idx < lng:
            res[idx] = self.atom_str(tc2)
            idx += 1
        return res

    def start(self, typecode):
        tc = self.get(1)
        if tc != typecode:
            self.raise_exc('invalid marshal data')
        self.typecode = tc

    def get_short(self):
        s = self.get(2)
        a = ord(s[0])
        b = ord(s[1])
        x = a | (b << 8)
        if x & 0x8000:
            x = x - 0x10000
        return x

    def get_int(self):
        s = self.get(4)
        a = ord(s[0])
        b = ord(s[1])
        c = ord(s[2])
        d = ord(s[3])
        x = a | (b<<8) | (c<<16) | (d<<24)
        return intmask(x)

    def get_lng(self):
        s = self.get(4)
        a = ord(s[0])
        b = ord(s[1])
        c = ord(s[2])
        d = ord(s[3])
        if d & 0x80:
            self.raise_exc('bad marshal data')
        x = a | (b<<8) | (c<<16) | (d<<24)
        return x

    def get_pascal(self):
        lng = ord(self.get(1))
        return self.get(lng)

    def get_str(self):
        lng = self.get_lng()
        return self.get(lng)

    # this function is inlined below
    def get_list_w(self):
        self.nesting += 1
        lng = self.get_lng()
        res_w = [None] * lng
        idx = 0
        while idx < lng:
            res_w[idx] = self.get_w_obj(False)
            idx += 1
        self.nesting -= 1
        return res_w

    def get_w_obj(self, allow_null):
        self.nesting += 2
        if self.nesting < nesting_limit:
            tc = self.get(1)
            w_ret = self._dispatch[ord(tc)](self.space, self, tc)
            if w_ret is None and not allow_null:
                space = self.space
                raise OperationError(space.w_TypeError, space.wrap(
                    'NULL object in marshal data'))
        else:
            w_ret = self._run_stackless()
        self.nesting -= 2
        return w_ret

    # inlined version to save a nesting level
    def get_list_w(self):
        self.nesting += 2
        lng = self.get_lng()
        res_w = [None] * lng
        idx = 0
        space = self.space
        w_ret = space.w_None # something not None
        if self.nesting < nesting_limit:
            while idx < lng:
                tc = self.get(1)
                w_ret = self._dispatch[ord(tc)](space, self, tc)
                if w_ret is None:
                    break
                res_w[idx] = w_ret
                idx += 1
        else:
            while idx < lng:
                w_ret = self._run_stackless()
                if w_ret is None:
                    break
                res_w[idx] = w_ret
                idx += 1
        if w_ret is None:
            raise OperationError(space.w_TypeError, space.wrap(
                'NULL object in marshal data'))
        self.nesting -= 2
        return res_w

    def _run_stackless(self):
        self.raise_exc('object too deeply nested to unmarshal')
