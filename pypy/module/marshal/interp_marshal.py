from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import WrappedDefault, unwrap_spec
from rpython.rlib.rarithmetic import intmask
from rpython.rlib import rstackovf
from pypy.module._file.interp_file import W_File
from pypy.objspace.std.marshal_impl import marshal, get_unmarshallers


Py_MARSHAL_VERSION = 2

@unwrap_spec(w_version=WrappedDefault(Py_MARSHAL_VERSION))
def dump(space, w_data, w_f, w_version):
    """Write the 'data' object into the open file 'f'."""
    # special case real files for performance
    if isinstance(w_f, W_File):
        writer = DirectStreamWriter(space, w_f)
    else:
        writer = FileWriter(space, w_f)
    try:
        # note: bound methods are currently not supported,
        # so we have to pass the instance in, instead.
        ##m = Marshaller(space, writer.write, space.int_w(w_version))
        m = Marshaller(space, writer, space.int_w(w_version))
        m.dump_w_obj(w_data)
    finally:
        writer.finished()

@unwrap_spec(w_version=WrappedDefault(Py_MARSHAL_VERSION))
def dumps(space, w_data, w_version):
    """Return the string that would have been written to a file
by dump(data, file)."""
    m = StringMarshaller(space, space.int_w(w_version))
    m.dump_w_obj(w_data)
    return space.wrap(m.get_value())

def load(space, w_f):
    """Read one value from the file 'f' and return it."""
    # special case real files for performance
    if isinstance(w_f, W_File):
        reader = DirectStreamReader(space, w_f)
    else:
        reader = FileReader(space, w_f)
    try:
        u = Unmarshaller(space, reader)
        return u.load_w_obj()
    finally:
        reader.finished()

def loads(space, w_str):
    """Convert a string back to a value.  Extra characters in the string are
ignored."""
    u = StringUnmarshaller(space, w_str)
    obj = u.load_w_obj()
    return obj


class AbstractReaderWriter(object):
    def __init__(self, space):
        self.space = space

    def raise_eof(self):
        space = self.space
        raise oefmt(space.w_EOFError, "EOF read where object expected")

    def finished(self):
        pass

    def read(self, n):
        raise NotImplementedError("Purely abstract method")

    def write(self, data):
        raise NotImplementedError("Purely abstract method")

class FileWriter(AbstractReaderWriter):
    def __init__(self, space, w_f):
        AbstractReaderWriter.__init__(self, space)
        try:
            self.func = space.getattr(w_f, space.wrap('write'))
            # XXX how to check if it is callable?
        except OperationError as e:
            if not e.match(space, space.w_AttributeError):
                raise
            raise oefmt(space.w_TypeError,
                        "marshal.dump() 2nd arg must be file-like object")

    def write(self, data):
        space = self.space
        space.call_function(self.func, space.wrap(data))


class FileReader(AbstractReaderWriter):
    def __init__(self, space, w_f):
        AbstractReaderWriter.__init__(self, space)
        try:
            self.func = space.getattr(w_f, space.wrap('read'))
            # XXX how to check if it is callable?
        except OperationError as e:
            if not e.match(space, space.w_AttributeError):
                raise
            raise oefmt(space.w_TypeError,
                        "marshal.load() arg must be file-like object")

    def read(self, n):
        space = self.space
        w_ret = space.call_function(self.func, space.wrap(n))
        ret = space.str_w(w_ret)
        if len(ret) != n:
            self.raise_eof()
        return ret


class StreamReaderWriter(AbstractReaderWriter):
    def __init__(self, space, file):
        AbstractReaderWriter.__init__(self, space)
        self.file = file
        file.lock()

    def finished(self):
        self.file.unlock()

class DirectStreamWriter(StreamReaderWriter):
    def write(self, data):
        self.file.direct_write_str(data)

class DirectStreamReader(StreamReaderWriter):
    def read(self, n):
        data = self.file.direct_read(n)
        if len(data) < n:
            self.raise_eof()
        return data


class _Base(object):
    def raise_exc(self, msg):
        space = self.space
        raise OperationError(space.w_ValueError, space.wrap(msg))

class Marshaller(_Base):
    """
    atomic types including typecode:

    atom(tc)                    puts single typecode
    atom_int(tc, int)           puts code and int
    atom_int64(tc, int64)       puts code and int64
    atom_str(tc, str)           puts code, len and string

    building blocks for compound types:

    start(typecode)             sets the type character
    put(s)                      puts a string with fixed length
    put_short(int)              puts a short integer
    put_int(int)                puts an integer
    put_pascal(s)               puts a short string
    put_w_obj(w_obj)            puts a wrapped object
    put_tuple_w(TYPE, tuple_w)  puts tuple_w, an unwrapped list of wrapped objects
    """

    def __init__(self, space, writer, version):
        self.space = space
        ## self.put = putfunc
        self.writer = writer
        self.version = version
        self.stringtable = {}

    ## currently we cannot use a put that is a bound method
    ## from outside. Same holds for get.
    def put(self, s):
        self.writer.write(s)

    def put1(self, c):
        self.writer.write(c)

    def atom(self, typecode):
        #assert type(typecode) is str and len(typecode) == 1
        # type(char) not supported
        self.put1(typecode)

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

    def start(self, typecode):
        # type(char) not supported
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

    def put_w_obj(self, w_obj):
        marshal(self.space, w_obj, self)

    def dump_w_obj(self, w_obj):
        space = self.space
        try:
            self.put_w_obj(w_obj)
        except rstackovf.StackOverflow:
            rstackovf.check_stack_overflow()
            self._overflow()

    def put_tuple_w(self, typecode, lst_w):
        self.start(typecode)
        lng = len(lst_w)
        self.put_int(lng)
        idx = 0
        while idx < lng:
            w_obj = lst_w[idx]
            marshal(self.space, w_obj, self)
            idx += 1

    def _overflow(self):
        self.raise_exc('object too deeply nested to marshal')


class StringMarshaller(Marshaller):
    def __init__(self, space, version):
        Marshaller.__init__(self, space, None, version)
        self.buflis = [chr(0)] * 128
        self.bufpos = 0

    def put(self, s):
        pos = self.bufpos
        lng = len(s)
        newpos = pos + lng
        while len(self.buflis) < newpos:
            self.buflis *= 2
        idx = 0
        while idx < lng:
            self.buflis[pos + idx] = s[idx]
            idx += 1
        self.bufpos = newpos

    def put1(self, c):
        pos = self.bufpos
        newpos = pos + 1
        if len(self.buflis) < newpos:
            self.buflis *= 2
        self.buflis[pos] = c
        self.bufpos = newpos

    def atom_int(self, typecode, x):
        a = chr(x & 0xff)
        x >>= 8
        b = chr(x & 0xff)
        x >>= 8
        c = chr(x & 0xff)
        x >>= 8
        d = chr(x & 0xff)
        pos = self.bufpos
        newpos = pos + 5
        if len(self.buflis) < newpos:
            self.buflis *= 2
        self.buflis[pos] = typecode
        self.buflis[pos+1] = a
        self.buflis[pos+2] = b
        self.buflis[pos+3] = c
        self.buflis[pos+4] = d
        self.bufpos = newpos

    def put_short(self, x):
        a = chr(x & 0xff)
        x >>= 8
        b = chr(x & 0xff)
        pos = self.bufpos
        newpos = pos + 2
        if len(self.buflis) < newpos:
            self.buflis *= 2
        self.buflis[pos]   = a
        self.buflis[pos+1] = b
        self.bufpos = newpos

    def put_int(self, x):
        a = chr(x & 0xff)
        x >>= 8
        b = chr(x & 0xff)
        x >>= 8
        c = chr(x & 0xff)
        x >>= 8
        d = chr(x & 0xff)
        pos = self.bufpos
        newpos = pos + 4
        if len(self.buflis) < newpos:
            self.buflis *= 2
        self.buflis[pos]   = a
        self.buflis[pos+1] = b
        self.buflis[pos+2] = c
        self.buflis[pos+3] = d
        self.bufpos = newpos

    def get_value(self):
        return ''.join(self.buflis[:self.bufpos])


def invalid_typecode(space, u, tc):
    u.raise_exc("bad marshal data (unknown type code)")



class Unmarshaller(_Base):
    _dispatch = [invalid_typecode] * 256
    for tc, func in get_unmarshallers():
        _dispatch[ord(tc)] = func

    def __init__(self, space, reader):
        self.space = space
        self.reader = reader
        self.stringtable_w = []

    def get(self, n):
        assert n >= 0
        return self.reader.read(n)

    def get1(self):
        # the [0] is used to convince the annotator to return a char
        return self.get(1)[0]

    def atom_str(self, typecode):
        self.start(typecode)
        lng = self.get_lng()
        return self.get(lng)

    def atom_lng(self, typecode):
        self.start(typecode)
        return self.get_lng()

    def start(self, typecode):
        tc = self.get1()
        if tc != typecode:
            self.raise_exc('invalid marshal data')

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
        if d & 0x80:
            d -= 0x100
        x = a | (b<<8) | (c<<16) | (d<<24)
        return intmask(x)

    def get_lng(self):
        s = self.get(4)
        a = ord(s[0])
        b = ord(s[1])
        c = ord(s[2])
        d = ord(s[3])
        x = a | (b<<8) | (c<<16) | (d<<24)
        if x >= 0:
            return x
        else:
            self.raise_exc('bad marshal data')

    def get_pascal(self):
        lng = ord(self.get1())
        return self.get(lng)

    def get_str(self):
        lng = self.get_lng()
        return self.get(lng)

    def get_w_obj(self, allow_null=False):
        space = self.space
        tc = self.get1()
        w_ret = self._dispatch[ord(tc)](space, self, tc)
        if w_ret is None and not allow_null:
            raise oefmt(space.w_TypeError, "NULL object in marshal data")
        return w_ret

    def load_w_obj(self):
        try:
            return self.get_w_obj()
        except rstackovf.StackOverflow:
            rstackovf.check_stack_overflow()
            self._overflow()

    # inlined version to save a recursion level
    def get_tuple_w(self):
        lng = self.get_lng()
        res_w = [None] * lng
        idx = 0
        space = self.space
        w_ret = space.w_None # something not
        while idx < lng:
            tc = self.get1()
            w_ret = self._dispatch[ord(tc)](space, self, tc)
            if w_ret is None:
                break
            res_w[idx] = w_ret
            idx += 1
        if w_ret is None:
            raise oefmt(space.w_TypeError, "NULL object in marshal data")
        return res_w

    def get_list_w(self):
        return self.get_tuple_w()[:]

    def _overflow(self):
        self.raise_exc('object too deeply nested to unmarshal')


class StringUnmarshaller(Unmarshaller):
    # Unmarshaller with inlined buffer string
    def __init__(self, space, w_str):
        Unmarshaller.__init__(self, space, None)
        self.bufstr = space.getarg_w('s#', w_str)
        self.bufpos = 0
        self.limit = len(self.bufstr)

    def raise_eof(self):
        space = self.space
        raise oefmt(space.w_EOFError, "EOF read where object expected")

    def get(self, n):
        pos = self.bufpos
        newpos = pos + n
        if newpos > self.limit:
            self.raise_eof()
        self.bufpos = newpos
        return self.bufstr[pos : newpos]

    def get1(self):
        pos = self.bufpos
        if pos >= self.limit:
            self.raise_eof()
        self.bufpos = pos + 1
        return self.bufstr[pos]

    def get_int(self):
        pos = self.bufpos
        newpos = pos + 4
        if newpos > self.limit:
            self.raise_eof()
        self.bufpos = newpos
        a = ord(self.bufstr[pos])
        b = ord(self.bufstr[pos+1])
        c = ord(self.bufstr[pos+2])
        d = ord(self.bufstr[pos+3])
        if d & 0x80:
            d -= 0x100
        x = a | (b<<8) | (c<<16) | (d<<24)
        return intmask(x)

    def get_lng(self):
        pos = self.bufpos
        newpos = pos + 4
        if newpos > self.limit:
            self.raise_eof()
        self.bufpos = newpos
        a = ord(self.bufstr[pos])
        b = ord(self.bufstr[pos+1])
        c = ord(self.bufstr[pos+2])
        d = ord(self.bufstr[pos+3])
        x = a | (b<<8) | (c<<16) | (d<<24)
        if x >= 0:
            return x
        else:
            self.raise_exc('bad marshal data')
