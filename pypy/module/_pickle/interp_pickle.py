from rpython.rlib.rstring import StringBuilder

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef, make_weakref_descr
from pypy.interpreter.error import oefmt, OperationError

from pypy.interpreter.gateway import interp2app, applevel

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

def packI(opcode, val):
    assert val >= 0
    return packi(opcode, val)

def packB(opcode, val):
    return opcode + chr(val)

def pickling_error(space):
    w_module = space.getbuiltinmodule('_pickle')
    return space.getattr(w_module, space.newtext('PicklingError'))

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

def spacenext(space, w_it):
    try:
        return space.next(w_it)
    except OperationError as e:
        if not e.match(space, space.w_StopIteration):
            raise
        return None


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

    def _write_large_bytes(self, arg0, arg1):
        return self.framer.write_large_bytes(arg0, arg1)

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
        x = self.memo.get(w_obj, -1)
        if x >= 0:
            self.write(self.get(x))
            return

        if space.is_w(space.w_bytes, w_type):
            self.save_bytes(w_obj)
            return

        if space.is_w(space.w_unicode, w_type):
            self.save_str(w_obj)
            return

        if space.is_w(space.w_tuple, w_type):
            self.save_tuple(w_obj)
            return

        if space.is_w(space.w_list, w_type):
            self.save_list(w_obj)
            return

        if space.is_w(space.w_dict, w_type):
            self.save_dict(w_obj)
            return

        rv = NotImplemented
        reduce = getattr(self, "reducer_override", None)
        if reduce is not None:
            rv = reduce(w_obj)

        if rv is NotImplemented:
            # Check private dispatch table if any, or else
            # copyreg.dispatch_table
            #reduce = getattr(self, 'dispatch_table', dispatch_table).get(t)
            if 0: # reduce is not None:
                rv = reduce(w_obj)
            else:
                # Check for a class with a custom metaclass; treat as regular
                # class
                if space.issubtype_w(w_type, space.w_type):
                    self.save_global(w_obj)
                    return

                # Check for a __reduce_ex__ method, fall back to __reduce__
                w_reduce = space.lookup(w_obj, "__reduce_ex__")
                if w_reduce is not None:
                    w_rv = space.get_and_call_function(w_reduce, w_obj, space.newint(self.proto))
                else:
                    w_reduce = space.lookup(w_obj, "__reduce__")
                    if w_reduce is not None:
                        w_rv = space.get_and_call_function(w_reduce, w_obj)
                    else:
                        raise oefmt(pickling_error(space), "Can't pickle %T object: %R", w_obj, w_obj)

        # Check for string returned by reduce(), meaning "save as global"
        if space.isinstance_w(w_rv, space.w_unicode):
            self.save_global(w_obj, w_rv)
            return

        # Assert that reduce() returned a tuple
        if not space.isinstance_w(w_rv, space.w_tuple):
            import pdb;pdb.set_trace()
            raise oefmt(pickling_error(space), "%S must return string or tuple", w_reduce)

        # Assert that it returned an appropriately sized tuple
        l = space.len_w(w_rv)
        if not (2 <= l <= 6):
            raise oefmt(pickling_error(space), "Tuple returned by %S must have "
                                "two to six elements", w_reduce)

        # Save the reduce() output and finally memoize the object
        self.save_reduce(w_obj, w_rv)

    def save_none(self, w_obj):
        self.write(op.NONE)

    def save_bool(self, w_obj):
        space = self.space
        if self.proto >= 2:
            self.write(op.NEWTRUE if space.is_w(space.w_True, w_obj) else op.NEWFALSE)
        else:
            self.write(op.TRUE if space.is_w(space.w_True, w_obj) else op.FALSE)


    def save_long(self, w_obj):
        # If the int is small enough to fit in a signed 4-byte 2's-comp
        # format, we can store it more efficiently than the general
        # case.
        # First one- and two-byte unsigned ints:
        space = self.space
        try:
            obj = space.int_w(w_obj)
        except OperationError as e:
            if not e.match(space, space.w_OverflowError):
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
            self.write(packi(op.LONG4, n) + encoded)
        return

    def save_bytes(self, w_obj):
        space = self.space
        if self.proto < 3:
            assert 0
        n = space.len_w(w_obj)
        obj = space.bytes_w(w_obj)
        if n <= 0xff:
            self.write(packB(op.SHORT_BINBYTES, n) + obj)
        elif n > 0xffffffff and self.proto >= 4:
            self._write_large_bytes(packQ(op.BINBYTES8, n), obj)
        elif n >= self.framer._FRAME_SIZE_TARGET:
            self._write_large_bytes(packI(op.BINBYTES, n), obj)
        else:
            self.write(packI(op.BINBYTES, n) + obj)
        self.memoize(w_obj)

    def save_str(self, w_obj):
        space = self.space
        w_encoded = space.call_method(w_obj, "encode", space.newtext('utf-8'), space.newtext('surrogatepass'))
        encoded = space.bytes_w(w_encoded)
        n = len(encoded)
        if n <= 0xff and self.proto >= 4:
            self.write(packB(op.SHORT_BINUNICODE, n) + encoded)
        elif n > 0xffffffff and self.proto >= 4:
            self._write_large_bytes(packQ(op.BINUNICODE8, n), encoded)
        elif n >= self.framer._FRAME_SIZE_TARGET:
            self._write_large_bytes(packI(op.BINUNICODE, n), encoded)
        else:
            self.write(packI(op.BINUNICODE, n) + encoded)
        self.memoize(w_obj)

    def save_tuple(self, w_obj):
        space = self.space
        n = space.len_w(w_obj)
        if not n: # tuple is empty
            if self.bin:
                self.write(op.EMPTY_TUPLE)
            else:
                self.write(op.MARK + op.TUPLE)
            return

        save = self.save
        memo = self.memo
        if n <= 3 and self.proto >= 2:
            for element in space.unpackiterable(w_obj):
                save(element)
            # Subtle.  Same as in the big comment below.
            if w_obj in memo:
                get = self.get(memo[w_obj][0])
                self.write(op.POP * n + get)
            else:
                self.write(op._tuplesize2code[n])
                self.memoize(w_obj)
            return

        # proto 0 or proto 1 and tuple isn't empty, or proto > 1 and tuple
        # has more than 3 elements.
        write = self.write
        write(op.MARK)
        for element in space.unpackiterable(w_obj):
            save(element)

        if w_obj in memo:
            # Subtle.  d was not in memo when we entered save_tuple(), so
            # the process of saving the tuple's elements must have saved
            # the tuple itself:  the tuple is recursive.  The proper action
            # now is to throw away everything we put on the stack, and
            # simply GET the tuple (it's already constructed).  This check
            # could have been done in the "for element" loop instead, but
            # recursive tuples are a rare thing.
            get = self.get(memo[w_obj])
            if self.bin:
                write(op.POP_MARK + get)
            else:   # proto 0 -- POP_MARK not available
                write(op.POP * (n+1) + get)
            return

        # No recursion.
        write(op.TUPLE)
        self.memoize(w_obj)

    def save_list(self, w_obj):
        if self.bin:
            self.write(op.EMPTY_LIST)
        else:   # proto 0 -- can't use EMPTY_LIST
            self.write(op.MARK + op.LIST)

        self.memoize(w_obj)
        self._batch_appends(w_obj)


    _BATCHSIZE = 1000
    def _batch_appends(self, w_list):
        space = self.space
        # Helper to batch up APPENDS sequences
        save = self.save
        write = self.write

        if not self.bin:
            for x in space.listview(w_list):
                save(x)
                write(APPEND)
            return

        w_it = space.iter(w_list)
        while True:
            w_firstitem = spacenext(space, w_it)
            if w_firstitem is None:
                return
            w_item = spacenext(space, w_it)
            if w_item is None:
                # only one item
                self.save(w_firstitem)
                self.write(op.APPEND)
                return

            # more than two items, batch them
            self.write(op.MARK)
            n = 1
            self.save(w_firstitem)
            while 1:
                self.save(w_item)
                n += 1
                if n == self._BATCHSIZE:
                    break
                w_item = spacenext(space, w_it)
                if not w_item:
                    break
            self.write(op.APPENDS)

    def save_dict(self, w_obj):
        if self.bin:
            self.write(op.EMPTY_DICT)
        else:   # proto 0 -- can't use EMPTY_DICT
            self.write(op.MARK + op.DICT)

        self.memoize(w_obj)
        self._batch_setitems(w_obj)

    def _batch_setitems(self, w_dict):
        def savetup2(self, w_tup):
            space = self.space
            w_k, w_v = space.unpackiterable(w_tup, 2)
            self.save(w_k)
            self.save(w_v)

        # Helper to batch up SETITEMS sequences; proto >= 1 only
        space = self.space
        save = self.save
        write = self.write

        if not self.bin:
            import pdb;pdb.set_trace()
            for k, v in items:
                save(k)
                save(v)
                write(SETITEM)
            return

        w_it = space.iter(space.call_method(w_dict, 'items'))
        while True:
            w_firstitem = spacenext(space, w_it)
            if w_firstitem is None:
                return
            w_item = spacenext(space, w_it)
            if w_item is None:
                savetup2(self, w_firstitem)
                self.write(op.SETITEM)
                return

            # more than two items, batch them
            self.write(op.MARK)
            n = 1
            savetup2(self, w_firstitem)
            while 1:
                savetup2(self, w_item)
                n += 1
                if n == self._BATCHSIZE:
                    break
                w_item = spacenext(space, w_it)
                if not w_item:
                    break
            self.write(op.SETITEMS)

    def save_reduce(self, w_obj, w_rv):
        space = self.space
        #func, args, state=None, listitems=None,
        #            dictitems=None, state_setter=None, *, obj=None):
        # This API is called by some subclasses
        values_w = space.unpackiterable(w_rv)
        w_func = values_w[0]
        w_args = values_w[1]
        if len(values_w) >= 3:
            w_state = values_w[2]
            if len(values_w) >= 4:
                w_listitems = values_w[3]
                if len(values_w) >= 5:
                    w_dictitems = values_w[4]
                    if len(values_w) == 6:
                        w_state_setter = values_w[5]
                    else:
                        w_state_setter = None
                else:
                    w_dictitems = None
            else:
                w_listitems = None
        else:
            w_state = None

        if not space.isinstance_w(w_args, space.w_tuple):
            raise oefmt(pickling_error(space), "args from save_reduce() must be a tuple")
        if not space.callable_w(w_func):
            raise oefmt(pickling_error(space), "func from save_reduce() must be callable")

        save = self.save
        write = self.write

        w_func_name = space.findattr(w_func, space.newtext("__name__"))
        if self.proto >= 2 and space.eq_w(w_func_name, space.newtext("__newobj_ex__")):
            w_cls, w_args, w_kwargs = space.unpackiterable(w_args, 3)
            if space.findattr(w_cls, space.newtext("__new__")):
                raise oefmt(pickling_error(space), "args[0] from %S args has no __new__", w_func_name)
            if w_obj is not None and not space.is_w(w_cls, space.getattr(obj, space.newtext('__class__'))):
                raise oefmt(pickling_error(space), "args[0] from %S args has the wrong class", w_func_name)
            if self.proto >= 4:
                save(w_cls)
                save(w_args)
                save(w_kwargs)
                write(NEWOBJ_EX)
            else:
                import pdb;pdb.set_trace()
                func = partial(cls.__new__, cls, *args, **kwargs)
                save(func)
                save(())
                write(REDUCE)
        elif self.proto >= 2 and space.eq_w(w_func_name, space.newtext("__newobj__")):
            # A __reduce__ implementation can direct protocol 2 or newer to
            # use the more efficient NEWOBJ opcode, while still
            # allowing protocol 0 and 1 to work normally.  For this to
            # work, the function returned by __reduce__ should be
            # called __newobj__, and its first argument should be a
            # class.  The implementation for __newobj__
            # should be as follows, although pickle has no way to
            # verify this:
            #
            # def __newobj__(cls, *args):
            #     return cls.__new__(cls, *args)
            #
            # Protocols 0 and 1 will pickle a reference to __newobj__,
            # while protocol 2 (and above) will pickle a reference to
            # cls, the remaining args tuple, and the NEWOBJ code,
            # which calls cls.__new__(cls, *args) at unpickling time
            # (see load_newobj below).  If __reduce__ returns a
            # three-tuple, the state from the third tuple item will be
            # pickled regardless of the protocol, calling __setstate__
            # at unpickling time (see load_build below).
            #
            # Note that no standard __newobj__ implementation exists;
            # you have to provide your own.  This is to enforce
            # compatibility with Python 2.2 (pickles written using
            # protocol 0 or 1 in Python 2.3 should be unpicklable by
            # Python 2.2).
            w_cls = space.getitem(w_args, space.newint(0))
            if not space.findattr(w_cls, space.newtext("__new__")):
                raise oefmt(pickling_error(space),
                    "args[0] from __newobj__ args has no __new__")
            if w_obj is not None and not space.is_w(w_cls, space.getattr(w_obj, space.newtext('__class__'))):
                raise oefmt(pickling_error(space),
                    "args[0] from __newobj__ args has the wrong class")
            w_args = space.getitem(w_args, space.newslice(space.newint(1), space.w_None, space.w_None))
            self.save(w_cls)
            self.save(w_args)
            self.write(op.NEWOBJ)
        else:
            save(func)
            save(args)
            write(REDUCE)

        if w_obj is not None:
            # If the object is already in the memo, this means it is
            # recursive. In this case, throw away everything we put on the
            # stack, and fetch the object back from the memo.
            if w_obj in self.memo:
                write(op.POP + self.get(self.memo[w_obj]))
            else:
                self.memoize(w_obj)

        # More new special cases (that work with older protocols as
        # well): when __reduce__ returns a tuple with 4 or 5 items,
        # the 4th and 5th item should be iterators that provide list
        # items and dict items (as (key, value) tuples), or None.

        if not space.is_none(w_listitems):
            self._batch_appends(w_listitems)

        if not space.is_none(w_dictitems):
            self._batch_setitems(w_dictitems)

        if not space.is_none(w_state):
            if w_state_setter is None:
                save(w_state)
                write(op.BUILD)
            else:
                # If a state_setter is specified, call it instead of load_build
                # to update obj's with its previous state.
                # First, push state_setter and its tuple of expected arguments
                # (obj, state) onto the stack.
                save(w_state_setter)
                save(w_obj)  # simple BINGET opcode as obj is already memoized.
                save(w_state)
                write(op.TUPLE2)
                # Trigger a state_setter(obj, state) function call.
                write(op.REDUCE)
                # The purpose of state_setter is to carry-out an
                # inplace modification of obj. We do not care about what the
                # method might return, so its output is eventually removed from
                # the stack.
                write(op.POP)

    def save_global(self, w_obj, w_name=None):
        space = self.space
        write = self.write
        memo = self.memo

        if space.is_none(w_name):
            w_name = space.findattr(w_obj, space.newtext('__qualname__'))
        if space.is_none(w_name):
            w_name = space.getattr(w_obj, space.newtext('__name__'))

        w_module_name = whichmodule(space, w_obj, w_name)
        try:
            w_import = space.getattr(space.builtin, space.newtext("__import__"))
            space.call_function(w_import, w_module_name)
            w_module = space.getitem(space.getattr(space.sys, space.newtext('modules')), w_module_name)
            w_obj2, w_parent = space.unpackiterable(_getattribute(space, w_module, w_name), 2)
        except OperationError as e:
            if (not e.match(space, space.w_ImportError) and
                    not e.match(space, space.w_KeyError) and
                    e.match(space, space.w_AttributeError)):
                raise
            raise oefmt(pickling_error(space),
                "Can't pickle %R: it's not found as %S.%S",
                w_obj, w_module_name, w_name)
        else:
            if not space.is_w(w_obj2, w_obj):
                raise oefmt(pickling_error(space),
                    "Can't pickle %R: it's not the same object as %S.%S" %
                    w_obj, w_module_name, w_name)

        if self.proto >= 2:
            #code = _extension_registry.get((module_name, name))
            if 0: #code:
                assert code > 0
                if code <= 0xff:
                    write(EXT1 + pack("<B", code))
                elif code <= 0xffff:
                    write(EXT2 + pack("<H", code))
                else:
                    write(EXT4 + pack("<i", code))
                return
        name = space.text_w(w_name)
        lastname = name.split('.')[-1]
        if space.is_w(w_parent, w_module):
            w_name = space.newtext(lastname)
        # Non-ASCII identifiers are supported only with protocols >= 3.
        if self.proto >= 4:
            self.save(w_module_name)
            self.save(w_name)
            write(op.STACK_GLOBAL)
        elif not space.is_w(w_parent, w_module):
            self.save_reduce(space.getattr(space.builtin, 'getattr'), space.newtuple2(w_parent, w_lastname))
        elif self.proto >= 3:
            write(op.GLOBAL + bytes(module_name, "utf-8") + b'\n' +
                  bytes(name, "utf-8") + b'\n')
        else:
            if self.fix_imports:
                r_name_mapping = _compat_pickle.REVERSE_NAME_MAPPING
                r_import_mapping = _compat_pickle.REVERSE_IMPORT_MAPPING
                if (module_name, name) in r_name_mapping:
                    module_name, name = r_name_mapping[(module_name, name)]
                elif module_name in r_import_mapping:
                    module_name = r_import_mapping[module_name]
            try:
                write(GLOBAL + bytes(module_name, "ascii") + b'\n' +
                      bytes(name, "ascii") + b'\n')
            except UnicodeEncodeError:
                raise oefmt(pickling_error(space),
                    "can't pickle global identifier '%S.%S' using "
                    "pickle protocol %d" % (w_module, w_name, self.proto))
        self.memoize(w_obj)

    def memoize(self, w_obj):
        """Store an object in the memo."""

        # The Pickler memo is a dictionary mapping objects to the
        # Unpickler memo key.

        # The use of the Unpickler memo length as the memo key is just a
        # convention.  The only requirement is that the memo values be unique.
        # But there appears no advantage to any other scheme, and this
        # scheme allows the Unpickler memo to be implemented as a plain (but
        # growable) array, indexed by memo key.
        if self.fast:
            return
        assert w_obj not in self.memo
        idx = len(self.memo)
        self.write(self.put(idx))
        self.memo[w_obj] = idx

    # Return a PUT (BINPUT, LONG_BINPUT) opcode string, with argument i.
    def put(self, idx):
        if self.proto >= 4:
            return op.MEMOIZE
        elif self.bin:
            if idx < 256:
                return packB(op.BINPUT, idx)
            else:
                return packI(op.LONG_BINPUT, idx)
        else:
            return op.PUT + repr(idx) + b'\n'

    # Return a GET (BINGET, LONG_BINGET) opcode string, with argument i.
    def get(self, i):
        if self.bin:
            if i < 256:
                return packB(op.BINGET, i)
            else:
                return packI(op.LONG_BINGET, i)

        return op.GET + repr(i) + b'\n'

app = applevel('''
def _getattribute(obj, name):
    for subpath in name.split('.'):
        if subpath == '<locals>':
            raise AttributeError("Can't get local attribute {!r} on {!r}"
                                 .format(name, obj))
        try:
            parent = obj
            obj = getattr(obj, subpath)
        except AttributeError:
            raise AttributeError("Can't get attribute {!r} on {!r}"
                                 .format(name, obj)) from None
    return obj, parent

def whichmodule(obj, name):
    """Find the module an object belong to."""
    module_name = getattr(obj, '__module__', None)
    if module_name is not None:
        return module_name
    # Protect the iteration by using a list copy of sys.modules against dynamic
    # modules that trigger imports of other modules upon calls to getattr.
    for module_name, module in sys.modules.copy().items():
        if (module_name == '__main__'
            or module_name == '__mp_main__'  # bpo-42406
            or module is None):
            continue
        try:
            if _getattribute(module, name)[0] is obj:
                return module_name
        except AttributeError:
            pass
    return '__main__'
''', filename=__file__)

_getattribute = app.interphook('_getattribute')
whichmodule = app.interphook('whichmodule')

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

