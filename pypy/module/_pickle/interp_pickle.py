from rpython.rlib.rstring import StringBuilder

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef, make_weakref_descr
from pypy.interpreter.error import oefmt, OperationError

from pypy.interpreter.gateway import interp2app

class Opcodes(object):
    MARK           = b'('   # push special markobject on stack
    STOP           = b'.'   # every pickle ends with STOP
    POP            = b'0'   # discard topmost stack item
    POP_MARK       = b'1'   # discard stack top through topmost markobject
    DUP            = b'2'   # duplicate top stack item
    FLOAT          = b'F'   # push float object; decimal string argument
    INT            = b'I'   # push integer or bool; decimal string argument
    BININT         = b'J'   # push four-byte signed int
    BININT1        = b'K'   # push 1-byte unsigned int
    LONG           = b'L'   # push long; decimal string argument
    BININT2        = b'M'   # push 2-byte unsigned int
    NONE           = b'N'   # push None
    PERSID         = b'P'   # push persistent object; id is taken from string arg
    BINPERSID      = b'Q'   #  "       "         "  ;  "  "   "     "  stack
    REDUCE         = b'R'   # apply callable to argtuple, both on stack
    STRING         = b'S'   # push string; NL-terminated string argument
    BINSTRING      = b'T'   # push string; counted binary string argument
    SHORT_BINSTRING= b'U'   #  "     "   ;    "      "       "      " < 256 bytes
    UNICODE        = b'V'   # push Unicode string; raw-unicode-escaped'd argument
    BINUNICODE     = b'X'   #   "     "       "  ; counted UTF-8 string argument
    APPEND         = b'a'   # append stack top to list below it
    BUILD          = b'b'   # call __setstate__ or __dict__.update()
    GLOBAL         = b'c'   # push self.find_class(modname, name); 2 string args
    DICT           = b'd'   # build a dict from stack items
    EMPTY_DICT     = b'}'   # push empty dict
    APPENDS        = b'e'   # extend list on stack by topmost stack slice
    GET            = b'g'   # push item from memo on stack; index is string arg
    BINGET         = b'h'   #   "    "    "    "   "   "  ;   "    " 1-byte arg
    INST           = b'i'   # build & push class instance
    LONG_BINGET    = b'j'   # push item from memo on stack; index is 4-byte arg
    LIST           = b'l'   # build list from topmost stack items
    EMPTY_LIST     = b']'   # push empty list
    OBJ            = b'o'   # build & push class instance
    PUT            = b'p'   # store stack top in memo; index is string arg
    BINPUT         = b'q'   #   "     "    "   "   " ;   "    " 1-byte arg
    LONG_BINPUT    = b'r'   #   "     "    "   "   " ;   "    " 4-byte arg
    SETITEM        = b's'   # add key+value pair to dict
    TUPLE          = b't'   # build tuple from topmost stack items
    EMPTY_TUPLE    = b')'   # push empty tuple
    SETITEMS       = b'u'   # modify dict by adding topmost key+value pairs
    BINFLOAT       = b'G'   # push float; arg is 8-byte float encoding

    TRUE           = b'I01\n'  # not an opcode; see INT docs in pickletools.py
    FALSE          = b'I00\n'  # not an opcode; see INT docs in pickletools.py

    # Protocol 2

    PROTO          = b'\x80'  # identify pickle protocol
    NEWOBJ         = b'\x81'  # build object by applying cls.__new__ to argtuple
    EXT1           = b'\x82'  # push object from extension registry; 1-byte index
    EXT2           = b'\x83'  # ditto, but 2-byte index
    EXT4           = b'\x84'  # ditto, but 4-byte index
    TUPLE1         = b'\x85'  # build 1-tuple from stack top
    TUPLE2         = b'\x86'  # build 2-tuple from two topmost stack items
    TUPLE3         = b'\x87'  # build 3-tuple from three topmost stack items
    NEWTRUE        = b'\x88'  # push True
    NEWFALSE       = b'\x89'  # push False
    LONG1          = b'\x8a'  # push long from < 256 bytes
    LONG4          = b'\x8b'  # push really big long

    _tuplesize2code = [EMPTY_TUPLE, TUPLE1, TUPLE2, TUPLE3]

    # Protocol 3 (Python 3.x)

    BINBYTES       = b'B'   # push bytes; counted binary string argument
    SHORT_BINBYTES = b'C'   #  "     "   ;    "      "       "      " < 256 bytes

    # Protocol 4

    SHORT_BINUNICODE = b'\x8c'  # push short string; UTF-8 length < 256 bytes
    BINUNICODE8      = b'\x8d'  # push very long string
    BINBYTES8        = b'\x8e'  # push very long bytes string
    EMPTY_SET        = b'\x8f'  # push empty set on the stack
    ADDITEMS         = b'\x90'  # modify set by adding topmost stack items
    FROZENSET        = b'\x91'  # build frozenset from topmost stack items
    NEWOBJ_EX        = b'\x92'  # like NEWOBJ but work with keyword only arguments
    STACK_GLOBAL     = b'\x93'  # same as GLOBAL but using names on the stacks
    MEMOIZE          = b'\x94'  # store top of the stack in memo
    FRAME            = b'\x95'  # indicate the beginning of a new frame

    # Protocol 5

    BYTEARRAY8       = b'\x96'  # push bytearray
    NEXT_BUFFER      = b'\x97'  # push next out-of-band buffer
    READONLY_BUFFER  = b'\x98'  # make top of stack readonly

op = Opcodes()

def packQ(opcode, val):
    res = StringBuilder(9)
    res.append(opcode)
    for i in range(8):
        res.append(chr(val & 0xff))
        val >>= 8
    return res.build()

def packH(opcode, val):
    res = StringBuilder(3)
    res.append(opcode)
    for i in range(2):
        res.append(chr(val & 0xff))
        val >>= 8
    return res.build()

def packi(opcode, val):
    res = StringBuilder(5)
    res.append(opcode)
    for i in range(4):
        res.append(chr(val & 0xff))
        val >>= 8
    return res.build()

def packB(opcode, val):
    return opcode + chr(val)

class _Framer(object):

    _FRAME_SIZE_MIN = 4
    _FRAME_SIZE_TARGET = 64 * 1024

    def __init__(self, space, w_file):
        self.w_file = w_file
        self.space = space
        self.current_frame = None

    def start_framing(self):
        self.current_frame = StringBuilder()

    def end_framing(self):
        if self.current_frame and self.current_frame.getlength() > 0:
            self.commit_frame(force=True)
            self.current_frame = None

    def file_write(self, data):
        self.space.call_method(self.w_file, 'write', self.space.newbytes(data))

    def commit_frame(self, force=False):
        if self.current_frame is not None:
            f = self.current_frame
            if f.getlength() >= self._FRAME_SIZE_TARGET or force:
                data = f.build()
                write = self.file_write
                if len(data) >= self._FRAME_SIZE_MIN:
                    # Issue a single call to the write method of the underlying
                    # file object for the frame opcode with the size of the
                    # frame. The concatenation is expected to be less expensive
                    # than issuing an additional call to write.
                    write(packQ(op.FRAME, len(data)))

                # Issue a separate call to write to append the frame
                # contents without concatenation to the above to avoid a
                # memory copy.
                write(data)

                self.current_frame = StringBuilder()

    def write(self, data):
        if self.current_frame is not None:
            self.current_frame.append(data)
            return len(data)
        else:
            return self.file_write(data)

    def write_large_bytes(self, header, payload):
        write = self.file_write
        if self.current_frame:
            # Terminate the current frame and flush it to the file.
            self.commit_frame(force=True)

        # Perform direct write of the header and payload of the large binary
        # object. Be careful not to concatenate the header and the payload
        # prior to calling 'write' as we do not want to allocate a large
        # temporary bytes object.
        # We intentionally do not insert a protocol 4 frame opcode to make
        # it possible to optimize file.read calls in the loader.
        write(header)
        write(payload)


class W_Pickler(W_Root):
    """
    This takes a binary file for writing a pickle data stream.

    The optional *protocol* argument tells the pickler to use the given
    protocol; supported protocols are 0, 1, 2, 3, 4 and 5.  The default
    protocol is 4. It was introduced in Python 3.4, and is incompatible
    with previous versions.

    Specifying a negative protocol version selects the highest protocol
    version supported.  The higher the protocol used, the more recent the
    version of Python needed to read the pickle produced.

    The *file* argument must have a write() method that accepts a single
    bytes argument. It can thus be a file object opened for binary
    writing, an io.BytesIO instance, or any other custom object that meets
    this interface.

    If *fix_imports* is True and protocol is less than 3, pickle will try
    to map the new Python 3 names to the old module names used in Python
    2, so that the pickle data stream is readable with Python 2.

    If *buffer_callback* is None (the default), buffer views are
    serialized into *file* as part of the pickle stream.

    If *buffer_callback* is not None, then it can be called any number
    of times with a buffer view.  If the callback returns a false value
    (such as None), the given buffer is out-of-band; otherwise the
    buffer is serialized in-band, i.e. inside the pickle stream.

    It is an error if *buffer_callback* is not None and *protocol*
    is None or smaller than 5.
    """

    def __init__(self, space, w_file, protocol=4, fix_imports=True,
                 buffer_callback=None):
        assert protocol == 4
        self.space = space
        self.w_file = w_file
        self.protocol = protocol
        self.fix_imports = fix_imports
        self.buffer_callback = buffer_callback
        self.framer = _Framer(space, w_file)
        self.memo = {}
        self.proto = protocol
        self.bin = protocol >= 1
        assert self.bin
        self.fast = 0
        self.fix_imports = fix_imports and protocol < 3
        self.pers_func = None

    def write(self, data):
        self.space.call_method(self.w_file, 'write', self.space.newbytes(data))

    def dump(self, w_obj):
        """Write a pickled representation of obj to the open file."""
        if self.proto >= 2:
            self.write(packB(op.PROTO, self.proto))
        if self.proto >= 4:
            self.framer.start_framing()
        self.save(w_obj)
        self.write(op.STOP)
        self.framer.end_framing()

    def save(self, w_obj, save_persistent_id=True):
        space = self.space
        self.framer.commit_frame()

        # Check for persistent id (defined by a subclass)
        if save_persistent_id and self.pers_func is not None:
            import pdb;pdb.set_trace()
            pid = self.persistent_id(w_obj)
            if pid is not None:
                self.save_pers(pid)
                return
        if space.is_w(space.w_None, w_obj):
            self.save_none(w_obj)
            return
        if space.is_w(space.w_True, w_obj) or space.is_w(space.w_False, w_obj):
            self.save_bool(w_obj)
            return
        w_type = space.type(w_obj)
        if space.is_w(space.w_int, w_type):
            self.save_long(w_obj)
            return
        if space.is_w(space.w_float, w_type):
            self.save_float(w_obj)

        # Check the memo
        x = self.memo.get(w_obj)
        if x is not None:
            self.write(self.get(x[0]))
            return

        rv = NotImplemented
        reduce = getattr(self, "reducer_override", None)
        if reduce is not None:
            rv = reduce(w_obj)

        if rv is NotImplemented:
            # Check the type dispatch table
            t = type(w_obj)
            f = self.dispatch.get(t)
            if f is not None:
                f(self, w_obj)  # Call unbound method with explicit self
                return

            # Check private dispatch table if any, or else
            # copyreg.dispatch_table
            reduce = getattr(self, 'dispatch_table', dispatch_table).get(t)
            if reduce is not None:
                rv = reduce(w_obj)
            else:
                # Check for a class with a custom metaclass; treat as regular
                # class
                if issubclass(t, type):
                    self.save_global(w_obj)
                    return

                # Check for a __reduce_ex__ method, fall back to __reduce__
                reduce = getattr(w_obj, "__reduce_ex__", None)
                if reduce is not None:
                    rv = reduce(self.proto)
                else:
                    reduce = getattr(w_obj, "__reduce__", None)
                    if reduce is not None:
                        rv = reduce()
                    else:
                        raise PicklingError("Can't pickle %r object: %r" %
                                            (t.__name__, w_obj))

        # Check for string returned by reduce(), meaning "save as global"
        if isinstance(rv, str):
            self.save_global(w_obj, rv)
            return

        # Assert that reduce() returned a tuple
        if not isinstance(rv, tuple):
            raise PicklingError("%s must return string or tuple" % reduce)

        # Assert that it returned an appropriately sized tuple
        l = len(rv)
        if not (2 <= l <= 6):
            raise PicklingError("Tuple returned by %s must have "
                                "two to six elements" % reduce)

        # Save the reduce() output and finally memoize the object
        self.save_reduce(w_obj=w_obj, *rv)

    def save_long(self, w_obj):
        # If the int is small enough to fit in a signed 4-byte 2's-comp
        # format, we can store it more efficiently than the general
        # case.
        # First one- and two-byte unsigned ints:
        space = self.space
        try:
            obj = space.int_w(w_obj)
        except OperationError as e:
            if not e.match(space.w_TypeError):
                raise
        else:
            if obj >= 0:
                if obj <= 0xff:
                    self.write(packB(op.BININT1, obj))
                    return
                if obj <= 0xffff:
                    self.write(packH(op.BININT2 , obj))
                    return
            # Next check for 4-byte signed ints:
            # XXX 32 bit systems?
            if -0x80000000 <= obj <= 0x7fffffff:
                self.write(packi(op.BININT, obj))
                return
        encoded = encode_long(space, w_obj)
        n = len(encoded)
        if n < 256:
            self.write(packB(op.LONG1, n) + encoded)
        else:
            self.write(packB(op.LONG4, i) + encoded)
        return


def encode_long(space, w_x):
    r"""Encode a long to a two's complement little-endian binary string.
    Note that 0 is a special case, returning an empty string, to save a
    byte in the LONG1 pickling context.

    >>> encode_long(0)
    b''
    >>> encode_long(255)
    b'\xff\x00'
    >>> encode_long(32767)
    b'\xff\x7f'
    >>> encode_long(-256)
    b'\x00\xff'
    >>> encode_long(-32768)
    b'\x00\x80'
    >>> encode_long(-128)
    b'\x80'
    >>> encode_long(127)
    b'\x7f'
    >>>
    """
    from pypy.objspace.std import intobject
    assert isinstance(w_x, intobject.W_AbstractIntObject)
    if not space.is_true(w_x):
        return b''
    import pdb;pdb.set_trace()
    nbytes = (space.int_w(w_x.descr_bit_length(space)) >> 3) + 1
    result = space.bytes_w(w_x.descr_to_bytes(space, nbytes, byteorder='little', signed=True))
    if space.is_true(space.lt(w_x, space.newint(0))) and nbytes > 1:
        if result[-1] == b'\xff' and (result[-2] & '\x80') != 0:
            result = result[:-1]
    return result

def descr__new__(space, w_subtype, w_file):
    w_self = space.allocate_instance(W_Pickler, w_subtype)
    W_Pickler.__init__(w_self, space, w_file)
    return w_self

W_Pickler.typedef = TypeDef("_pickle.Pickler",
    __new__ = interp2app(descr__new__),
    dump = interp2app(W_Pickler.dump),
)

