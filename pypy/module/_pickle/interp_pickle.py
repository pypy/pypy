from rpython.rlib.rstring import StringBuilder
from rpython.rlib.mutbuffer import MutableStringBuffer
from rpython.rlib.rstruct import ieee
from rpython.rlib import objectmodel

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.argument import Arguments
from pypy.interpreter.typedef import TypeDef, make_weakref_descr, GetSetProperty
from pypy.interpreter.error import oefmt, oefmt_attribute_error, OperationError
from pypy.interpreter.unicodehelper import decode_utf8sp

from pypy.interpreter.gateway import interp2app, applevel, unwrap_spec, WrappedDefault
from pypy.module._pickle.state import State
from pypy.module.__pypy__.interp_buffer import W_PickleBuffer

import sys
maxsize = sys.maxint

HIGHEST_PROTOCOL = 5
DEFAULT_PROTOCOL = 4

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

def unpacki(s, index=0):
    val = 0
    for i in range(4):
        x = ord(s[index])
        if i == 3 and x >= 128:
            x -= 256
        val += x * (1 << 8 * i)
        index += 1
    return val

def unpackI(s, index=0):
    val = 0
    for i in range(4):
        x = ord(s[index])
        val += x * (1 << 8 * i)
        index += 1
    return val

def unpackQ(s, index=0):
    val = 0
    for i in range(8):
        x = ord(s[index])
        val += x * (1 << 8 * i)
        index += 1
    return val


def packI(opcode, val):
    assert val >= 0
    return packi(opcode, val)

def packB(opcode, val):
    return opcode + chr(val)

def pack_float(f):
    # like marshal, but bigendian, marshal uses littlendian
    buf = MutableStringBuffer(8)
    ieee.pack_float(buf, 0, f, 8, True)
    return buf.finish()

def unpack_float(s):
    return ieee.unpack_float(s, True)

def pickling_error(space):
    w_module = space.getbuiltinmodule('_pickle')
    return space.getattr(w_module, space.newtext('PicklingError'))

def unpickling_error(space):
    w_module = space.getbuiltinmodule('_pickle')
    return space.getattr(w_module, space.newtext('UnpicklingError'))

def data_pop(space, stack):
    if len(stack) >= 1:
        return stack.pop()
    raise oefmt(unpickling_error(space),
        "unexpected MARK found")

# An instance of _Stop is raised by Unpickler.load_stop() in response to
# the STOP opcode, passing the object that is the result of unpickling.
class _Stop(Exception):
    def __init__(self, value):
        self.value = value

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
        w_ret = self.space.call_method(self.w_file, 'write', self.space.newbytes(data))
        return self.space.int_w(w_ret)

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
    def __init__(self, space, w_file, protocol=4, fix_imports=1,
                 buffer_callback=None):
        self.space = space
        self.w_file = w_file
        self.protocol = protocol
        self.fix_imports = fix_imports
        self.buffer_callback = buffer_callback
        self.framer = _Framer(space, w_file)
        self.memo = {}
        self.proto = protocol
        self.bin = protocol >= 1
        self.fast = 0
        self.pers_func = None
        self.w_dispatch_table = None
        self.w_reducer_override = None
        self.dispatch = {}
        self.dispatch[space.w_NoneType] = save_none
        self.dispatch[space.w_bool]   = save_bool
        self.dispatch[space.w_int]    = save_long
        self.dispatch[space.w_float]  = save_float
        self.dispatch[space.w_unicode] = save_str
        self.dispatch[space.w_bytes]  = save_bytes
        self.dispatch[space.w_tuple]  = save_tuple
        self.dispatch[space.w_list]   = save_list
        self.dispatch[space.w_dict]   = save_dict
        if self.proto >= 4:
            self.dispatch[space.w_frozenset] = save_frozenset
        if self.proto >= 5:
            self.dispatch[space.w_bytearray]   = save_bytearray
        self.w_function = space.type(space.getattr(space.w_text, space.newtext("count")))
        self.dispatch[self.w_function]     = save_global

    def write(self, data):
        return self.framer.write(data)

    def _write_large_bytes(self, arg0, arg1):
        return self.framer.write_large_bytes(arg0, arg1)

    def dump(self, w_obj):
        """Write a pickled representation of obj to the open file."""
        space = self.space
        if space.findattr(self, space.newtext("reducer_override")):
            self.w_reducer_override = space.getattr(self, space.newtext("reducer_override"))
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
            pid = self.persistent_id(w_obj)
            if pid is not None:
                self.save_pers(pid)
                return

        w_type = space.type(w_obj)
        # Atom types: these are not memoized
        if w_type is space.w_None:
            return save_none(self, w_obj)
        elif w_type is space.w_bool:
            return save_bool(self, w_obj)
        elif w_type is space.w_int:
            return save_long(self, w_obj) 
        elif w_type is space.w_float:
            return save_float(self, w_obj) 

        # Check the memo
        x = self.memo.get(w_obj, -1)
        if x >= 0:
            self.write(self.get(x))
            return

        if w_type is space.w_bytes:
            return save_bytes(self, w_obj)
        elif w_type is space.w_text:
            return save_str(self, w_obj)

        # XXX check recursive call
        if w_type is space.w_dict:
            return save_dict(self, w_obj)
        elif w_type is space.w_set:
            return save_set(self, w_obj)
        elif w_type is space.w_frozenset and self.proto >= 4:
            return save_frozenset(self, w_obj)
        elif w_type is space.w_list:
            return save_list(self, w_obj)
        elif w_type is space.w_tuple:
            return save_tuple(self, w_obj)
        elif w_type is space.w_bytearray and self.proto >= 5:
            return save_bytearray(self, w_obj)
        elif isinstance(w_obj, W_PickleBuffer):
            return save_picklebuffer(self, w_obj)

        w_reduce = space.w_None
        w_rv = space.w_NotImplemented
        if self.w_reducer_override:
            w_reduce = self.w_reducer_override
            w_rv = space.call(w_reduce, w_obj)

        if w_rv is space.w_NotImplemented:
            # Check private dispatch table if any, or else
            f = self.dispatch.get(w_type)
            if f is not None:
                # This should never happen, we should have checked all cases above!
                f(self, w_obj)
                return
            # copyreg.dispatch_table
            w_dispatch_table = self.w_dispatch_table
            if not w_dispatch_table:
                w_dispatch_table = space.fromcache(State).w_dispatch_table
            w_reduce = space.finditem(w_dispatch_table, w_type)
            if w_reduce:
                w_rv = space.call_function(w_reduce, w_obj)
            else:
                # Check for a class with a custom metaclass; treat as regular
                # class
                if space.issubtype_w(w_type, space.w_type):
                    self.save_global2(w_obj, None)
                    return

                # Check for a __reduce_ex__ method, fall back to __reduce__
                w_reduce = space.lookup(w_obj, "__reduce_ex__")
                if w_reduce is not None:
                    w_rv = space.call_function(w_reduce, w_obj, space.newint(self.proto))
                else:
                    w_reduce = space.lookup(w_obj, "__reduce__")
                    if w_reduce is not None:
                        w_rv = space.call_function(w_reduce, w_obj)
                    else:
                        raise oefmt(pickling_error(space), "Can't pickle %T object: %R", w_obj, w_obj)
        else:
            if w_type is self.w_function:
                save_global(self, w_obj)
                return
        # Check for string returned by reduce(), meaning "save as global"
        if space.isinstance_w(w_rv, space.w_unicode):
            self.save_global2(w_obj, w_rv)
            return

        # Assert that reduce() returned a tuple
        if not space.isinstance_w(w_rv, space.w_tuple):
            raise oefmt(pickling_error(space), "%S must return string or tuple", w_reduce)

        # Assert that it returned an appropriately sized tuple
        rv_w = space.fixedview(w_rv)
        length = len(rv_w)
        if not (2 <= length <= 6):
            raise oefmt(pickling_error(space), "Tuple returned by %S must have "
                                "two to six elements", w_reduce)
        # Save the reduce() output and finally memoize the object

        # this does not translate...
        # self.save_reduce(*rv_w, w_obj=w_obj)
        if length == 2:
            self.save_reduce(rv_w[0], rv_w[1], w_obj=w_obj)
        if length == 3:
            self.save_reduce(rv_w[0], rv_w[1], rv_w[2], w_obj=w_obj)
        if length == 4:
            self.save_reduce(rv_w[0], rv_w[1], rv_w[2], rv_w[3], w_obj=w_obj)
        if length == 5:
            self.save_reduce(rv_w[0], rv_w[1], rv_w[2], rv_w[3], rv_w[4], w_obj=w_obj)
        if length == 6:
            self.save_reduce(rv_w[0], rv_w[1], rv_w[2], rv_w[3], rv_w[4], rv_w[5], w_obj=w_obj)

    _BATCHSIZE = 1000
    def _batch_appends(self, w_list):
        space = self.space
        # Helper to batch up APPENDS sequences
        save = self.save
        write = self.write

        if not self.bin:
            for w_x in space.listview(w_list):
                save(w_x)
                write(op.APPEND)
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

    def _batch_setitems(self, w_items):
        def savetup2(self, w_tup):
            space = self.space
            w_k, w_v = space.unpackiterable(w_tup, 2)
            self.save(w_k)
            self.save(w_v)

        # Helper to batch up SETITEMS sequences; proto >= 1 only
        space = self.space
        save = self.save
        write = self.write

        w_it = space.iter(w_items)
        if not self.bin:
            w_item = spacenext(space, w_it)
            if w_item is None:
                return
            while True:
                w_k, w_v = space.unpackiterable(w_item, 2)
                save(w_k)
                save(w_v)
                write(op.SETITEM)
                w_item = spacenext(space, w_it)
                if not w_item:
                    break
            return

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

    def save_reduce(self, w_func, w_args, w_state=None, w_listitems=None,
                    w_dictitems=None, w_state_setter=None, __kwargs__=None, w_obj=None):
        space = self.space
        #func, args, state=None, listitems=None,
        #            dictitems=None, state_setter=None, *, obj=None):
        # This API is called by some subclasses
        if not space.isinstance_w(w_args, space.w_tuple):
            raise oefmt(pickling_error(space), "args from save_reduce() must be a tuple")
        if not space.callable_w(w_func):
            raise oefmt(pickling_error(space), "func from save_reduce() must be callable")

        save = self.save
        write = self.write

        w_func_name = space.findattr(w_func, space.newtext("__name__"))
        if self.proto >= 2 and space.eq_w(w_func_name, space.newtext("__newobj_ex__")):
            w_cls, w_args, w_kwargs = space.unpackiterable(w_args, 3)
            w_new = space.findattr(w_cls, space.newtext("__new__"))
            if not w_new:
                raise oefmt(pickling_error(space), "args[0] from %S args has no __new__", w_func_name)
            if w_obj is not None and not space.is_w(w_cls, space.getattr(w_obj, space.newtext('__class__'))):
                raise oefmt(pickling_error(space), "args[0] from %S args has the wrong class", w_func_name)
            if self.proto >= 4:
                save(w_cls)
                save(w_args)
                save(w_kwargs)
                write(op.NEWOBJ_EX)
            else:
                args_w = space.listview(w_args)
                w_partial_args = space.newlist([w_new, w_cls] + args_w)
                w_partial = space.fromcache(State).w_partial
                w_func = space.call(w_partial, w_partial_args, w_kwargs)
                save(w_func)
                save(space.newtext("()"))
                write(op.REDUCE)
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
            w_new = space.findattr(w_cls, space.newtext("__new__"))
            if not w_new:
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
            save(w_func)
            save(w_args)
            write(op.REDUCE)

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

    def save_global2(self, w_obj, w_name):
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
                    "Can't pickle %R: it's not the same object as %S.%S",
                    w_obj, w_module_name, w_name)

        if self.proto >= 2:
            w_mod_and_name = space.newtuple([w_module_name, w_name])
            state = space.fromcache(State)
            w_code = space.finditem(state.w_extension_registry, w_mod_and_name)
            if not space.is_none(w_code):
                code = space.int_w(w_code)
                assert code > 0
                if code <= 0xff:
                    write(packB(op.EXT1, code))
                elif code <= 0xffff:
                    write(packH(op.EXT2, code))
                else:
                    write(packi(op.EXT4, code))
                return
        name = space.utf8_w(w_name)
        lastname = name.split('.')[-1]
        if space.is_w(w_parent, w_module):
            w_name = space.newtext(lastname)
            name = lastname
        # Non-ASCII identifiers are supported only with protocols >= 3.
        if self.proto >= 4:
            self.save(w_module_name)
            self.save(w_name)
            write(op.STACK_GLOBAL)
        elif not space.is_w(w_parent, w_module):
            self.save_reduce(space.getattr(space.builtin, space.newtext('getattr')),
                             space.newtuple2(w_parent, space.newtext(lastname)))
        elif self.proto >= 3:
            module_name = space.utf8_w(w_module_name)
            write(op.GLOBAL + module_name + b'\n' +
                  name + b'\n')
        else:
            if self.fix_imports:
                w_modname_and_name = space.newtuple([w_module_name, w_name])
                w_r_NAME_MAPPING = space.fromcache(State).w_REVERSE_NAME_MAPPING
                w_r_IMPORT_MAPPING = space.fromcache(State).w_REVERSE_IMPORT_MAPPING
                w_1 = space.finditem(w_r_NAME_MAPPING, w_modname_and_name)
                w_2 = space.finditem(w_r_IMPORT_MAPPING, w_module_name)
                if w_1:
                    w_module_name, w_name = space.listview(w_1)
                elif w_2:
                    w_module_name = w_2
            try:
                module_name = space.utf8_w(w_module_name)
                name = space.utf8_w(w_name)
                write(op.GLOBAL + module_name + b'\n' +
                      name + b'\n')
            except UnicodeEncodeError:
                raise oefmt(pickling_error(space),
                    "can't pickle global identifier '%S.%S' using "
                    "pickle protocol %d", w_module, w_name, self.proto)
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
            return "%s%d\n" %(op.PUT, idx)

    # Return a GET (BINGET, LONG_BINGET) opcode string, with argument i.
    def get(self, idx):
        if self.bin:
            if idx < 256:
                return packB(op.BINGET, idx)
            else:
                return packI(op.LONG_BINGET, idx)

        return "%s%d\n" %(op.GET, idx)

    def set_dispatch_table_w(self, space, w_obj):
        self.w_dispatch_table = w_obj

    def get_dispatch_table_w(self, space):
        if self.w_dispatch_table:
            return self.w_dispatch_table
        raise oefmt_attribute_error(self, space.newtext('dispatch_table'), 
           "'%T' object has no attribute %R")

    def set_fast_w(self, space, w_val):
        self.fast = space.int_w(w_val)

    def get_fast_w(self, space):
        return space.newint(self.fast)

def save_global(self, w_obj):
    return self.save_global2(w_obj, None)

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
        if self.bin:
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
        if self.proto < 2:
            as_ascii = space.utf8_w(space.repr(w_obj))
            if -0x80000000 <= obj <= 0x7fffffff:
                self.write(op.INT + as_ascii + b'\n')
            else:
                self.write(op.LONG + as_ascii + b'L\n')
            return
    encoded = encode_long(space, w_obj)
    n = len(encoded)
    if n < 256:
        self.write(packB(op.LONG1, n) + encoded)
    else:
        self.write(packi(op.LONG4, n) + encoded)

def save_float(self, w_obj):
    space = self.space
    if self.bin:
        obj = space.float_w(w_obj)
        self.write(op.BINFLOAT + pack_float(obj))
    else:
        as_ascii = space.utf8_w(space.repr(w_obj)) # .encode("ascii")
        self.write(op.FLOAT + as_ascii + '\n')

def save_bytes(self, w_obj):
    space = self.space
    n = space.len_w(w_obj)
    if self.proto < 3:
        if n < 1:
            self.save_reduce(space.w_bytes, space.newtuple([]), w_obj=w_obj)
        else:
            w_import = space.getattr(space.builtin, space.newtext("__import__"))
            w_codecs = space.call_function(w_import, space.newtext('codecs'))
            w_encode = space.getattr(w_codecs, space.newtext('encode'))
            self.save_reduce(w_encode, space.newtuple([space.newtext(space.bytes_w(w_obj)), space.newtext('latin1')]), w_obj=w_obj)
        return
    obj = space.bytes_w(w_obj)
    save_raw_bytes(self, n, obj)
    self.memoize(w_obj)

def save_raw_bytes(self, n, obj):
    if n <= 0xff:
        self.write(packB(op.SHORT_BINBYTES, n) + obj)
    elif n > 0xffffffff and self.proto >= 4:
        self._write_large_bytes(packQ(op.BINBYTES8, n), obj)
    elif n >= self.framer._FRAME_SIZE_TARGET:
        self._write_large_bytes(packI(op.BINBYTES, n), obj)
    else:
        self.write(packI(op.BINBYTES, n) + obj)

def save_str(self, w_obj):
    space = self.space
    if self.bin:
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
    else:
        # Escape what raw-unicode-escape doesn't, but memoize the original.
        w_tmp = space.call_method(w_obj, "replace", space.newtext("\\"), space.newtext("\\u005c"))
        tmp = space.call_method(w_obj, "replace", space.newtext("\0"), space.newtext("\\u0000"))
        tmp = space.call_method(w_obj, "replace", space.newtext("\n"), space.newtext("\\u000a"))
        tmp = space.call_method(w_obj, "replace", space.newtext("\r"), space.newtext("\\u000d"))
        # EOF on DOS
        tmp = space.call_method(w_obj, "replace", space.newtext("\x1a"), space.newtext("\\u001a"))
        w_encoded = space.call_method(w_obj, "encode", space.newtext('utf-8'), space.newtext('raw-unicode-escape'))
        encoded = space.bytes_w(w_encoded)
        self.write(op.UNICODE + encoded + b'\n')

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
            get = self.get(memo[w_obj])
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

def save_dict(self, w_obj):
    if self.bin:
        self.write(op.EMPTY_DICT)
    else:   # proto 0 -- can't use EMPTY_DICT
        self.write(op.MARK + op.DICT)

    self.memoize(w_obj)
    w_items = self.space.call_method(w_obj, 'items')
    self._batch_setitems(w_items)

def save_set(self, w_obj):
        save = self.save
        write = self.write
        space = self.space

        if self.proto < 4:
            self.save_reduce(space.w_set, space.newtuple([space.newlist([w_obj])]), w_obj=w_obj)
            return

        write(op.EMPTY_SET)
        self.memoize(w_obj)
        w_iter = space.iter(w_obj)
        write(op.MARK)
        length = space.len_w(w_obj)
        if length == 0:
            return
        w_item = space.next(w_iter)
        save(w_item)
        for i in range(1, length - 1):
            if i % self._BATCHSIZE == 0:
                write(op.ADDITEMS)
                write(op.MARK)
            w_item = space.next(w_iter)
            save(w_item)
        if length > 1:
            w_item = space.next(w_iter)
            save(w_item)
        write(op.ADDITEMS)

def save_frozenset(self, w_obj):
    self.write(op.MARK)
    space = self.space
    save = self.save
    memo = self.memo
    for element in space.unpackiterable(w_obj):
        save(element)
    # Subtle.  Avoids recursive writing
    if w_obj in memo:
        get = self.get(memo[w_obj])
        self.write(op.POP + get)
    else:
        self.write(op.FROZENSET)
        self.memoize(w_obj)

def save_bytearray(self, w_obj):
    space = self.space
    n = space.len_w(w_obj)
    obj = space.buffer_w(w_obj, 0).as_str()
    save_raw_bytearray(self, n, obj)

def save_raw_bytearray(self, n, obj):
    if n >= self.framer._FRAME_SIZE_TARGET:
        self._write_large_bytes(packQ(op.BYTEARRAY8, n), obj)
    else:
        self.write(packQ(op.BYTEARRAY8, n))
        self.write(obj)

def iscontiguous(buf):
    # taken from objspace.std.memoryobject._IsCContiguous
    ndim = buf.getndim()
    shape = buf.getshape()
    strides = buf.getstrides()
    itemsize = buf.getitemsize()
    if ndim == 0:
        return 1
    if not strides:
        return ndim == 1
    if ndim == 1:
        return shape[0] == 1 or itemsize == strides[0]
    sd = itemsize
    for i in range(ndim -1, -1 -1):
        # C order
        dim = shape[i]
        if dim == 0:
            return 1
        if strides[i] != sd:
            # Could be Fortran order?
            break
        sd *= dim
    sd = itemsize
    for i in range(ndim):
        dim = shape[i]
        if dim == 0:
            return 1
        if strides[i] != sd:
            return 0
        sd *= dim
    return 1
 
def save_picklebuffer(self, w_obj):
    space = self.space
    if self.proto < 5:
        raise oefmt(pickling_error(space),
            "PickleBuffer can only pickled with protocol >= 5")
    buf = w_obj.buf
    if not iscontiguous(buf):
        raise oefmt(pickling_error(space),
            "PickleBuffer can not be pickled when "
            "pointing to a non-contiguous buffer")
    in_band = 1
    if self.buffer_callback:
        w_ret = space.call_function(self.buffer_callback, w_obj)
        in_band = space.bool_w(w_ret)
    if in_band:
        # write data in-band
        raw = buf.as_str()
        n = len(raw)
        if buf.readonly:
            save_raw_bytes(self, n, raw)
        else:
            save_raw_bytearray(self, n, raw)
    else:
        # Write data out-of-band
        self.write(op.NEXT_BUFFER)
        if buf.readonly:
            self.write(op.READONLY_BUFFER)


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
    import sys
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
        if result[-1] == b'\xff' and (ord(result[-2]) & 0x080 != 0):
            result = result[:-1]
    return result

def decode_long(space, data):
    from rpython.rlib.rbigint import rbigint
    bigint = rbigint.frombytes(data, byteorder="little",
                               signed=True)
    try:
        as_int = bigint.toint()
    except OverflowError:
        w_obj = space.newlong_from_rbigint(bigint)
    else:
        w_obj = space.newint(as_int)
    return w_obj


@unwrap_spec(protocol=int, fix_imports=int)
def descr__new__(space, w_subtype, w_file, protocol=DEFAULT_PROTOCOL, fix_imports=1, w_buffer_callback=None):
    w_self = space.allocate_instance(W_Pickler, w_subtype)
    if protocol < 0:
        protocol = HIGHEST_PROTOCOL
    elif not 0 <= protocol <= HIGHEST_PROTOCOL:
        raise oefmt(space.w_ValueError, "pickle protocol must be <= %d", HIGHEST_PROTOCOL)
    if w_buffer_callback is not None and protocol < 5:
        raise oefmt(space.w_ValueError, "buffer_callback needs protocol < 5")
    W_Pickler.__init__(w_self, space, w_file, protocol, fix_imports, w_buffer_callback)
    return w_self

W_Pickler.typedef = TypeDef("_pickle.Pickler",
    __new__ = interp2app(descr__new__),
    dump = interp2app(W_Pickler.dump),
    dispatch_table = GetSetProperty(W_Pickler.get_dispatch_table_w, W_Pickler.set_dispatch_table_w),
    fast = GetSetProperty(W_Pickler.get_fast_w, W_Pickler.set_fast_w),
)


class _Unframer(object):
    def __init__(self, space, w_file_read, w_file_readline):
        self.space = space
        self.w_file_read = w_file_read
        self.w_file_readline = w_file_readline
        self.current_frame = None
        self.index = 0

    def read(self, n):
        assert isinstance(n, int)
        assert n >= 0
        space = self.space
        if self.current_frame:
            data = self.current_frame
            if self.index + n > len(data) and n > 0:
                self.current_frame = None
                self.index = 0
                w_ret = space.call_function(self.w_file_read, space.newint(n))
                ret = space.bytes_w(w_ret)
                if len(ret) < n:
                    raise oefmt(space.w_EOFError, "Ran out of input 1")
                return ret
            if len(data) - self.index < n:
                raise oefmt(unpickling_error(space),
                    "pickle exhausted before end of frame")
            result = data[self.index:self.index + n]
            self.index += n
            return result
        else:
            w_ret = space.call_function(self.w_file_read, space.newint(n))
            ret = space.bytes_w(w_ret)
            if len(ret) < n:
                if n == 1:
                    w_err = space.w_EOFError
                else:
                    w_err = unpickling_error(space)
                raise oefmt(w_err, "pickle data was truncated, wanted %d got %d", n, len(ret))
            return ret

    def read1(self):
        if self.current_frame is not None and self.index < len(self.current_frame):
            res = self.current_frame[self.index]
            self.index += 1
            return res
        return self.read(1)[0]

    @objectmodel.always_inline
    def read_with_offset(self, n):
        # returns a string, offset tuple. the resulting values are in string[offset:offset+n]
        if self.current_frame is not None and self.index + n <= len(self.current_frame):
            data = self.current_frame
            index = self.index
            self.index += n
        else:
            data = self.read(n)
            index = 0
        return data, index

    def readline(self):
        space = self.space
        if self.current_frame:
            data = self.current_frame
            if not data:
                self.current_frame = None
                self.index = 0
                w_ret = space.call_function(self.w_file_readline)
                data = space.bytes_w(w_ret)
                if len(data) < 2:
                    raise oefmt(space.w_EOFError, "Ran out of input 3")
            # XXX this looks wrong. we need to find the first '\n'
            if data[-1] != b'\n'[0]:
                raise oefmt(unpickling_error(space),
                    "pickle exhausted before end of frame readline")
            return data[self.index:]
        else:
            w_ret = space.call_function(self.w_file_readline)
            data = space.bytes_w(w_ret)
            if len(data) < 2:
                raise oefmt(unpickling_error(space),
                    "pickle data was truncated 2")
            if data[-1] != b'\n'[0]:
                raise oefmt(unpickling_error(space),
                    "pickle exhausted before end of frame")
            return data

    def load_frame(self, frame_size):
        if self.current_frame and len(self.current_frame) > 0:
            raise oefmt(unpickling_error(self.space),
                "beginning of a new frame before end of current frame")
        w_ret = self.space.call_function(self.w_file_read, self.space.newint(frame_size))
        ret = self.space.bytes_w(w_ret)
        if len(ret) < frame_size:
            raise oefmt(self.space.w_EOFError, "Ran out of input 5")
        self.current_frame = ret
        self.index = 0


class W_Unpickler(W_Root):
    """This takes a binary file for reading a pickle data stream.

    The protocol version of the pickle is detected automatically, so
    no proto argument is needed.

    The argument *file* must have two methods, a read() method that
    takes an integer argument, and a readline() method that requires
    no arguments.  Both methods should return bytes.  Thus *file*
    can be a binary file object opened for reading, an io.BytesIO
    object, or any other custom object that meets this interface.

    The file-like object must have two methods, a read() method
    that takes an integer argument, and a readline() method that
    requires no arguments.  Both methods should return bytes.
    Thus file-like object can be a binary file object opened for
    reading, a BytesIO object, or any other custom object that
    meets this interface.

    If *buffers* is not None, it should be an iterable of buffer-enabled
    objects that is consumed each time the pickle stream references
    an out-of-band buffer view.  Such buffers have been given in order
    to the *buffer_callback* of a Pickler object.

    If *buffers* is None (the default), then the buffers are taken
    from the pickle stream, assuming they are serialized there.
    It is an error for *buffers* to be None if the pickle stream
    was produced with a non-None *buffer_callback*.

    Other optional arguments are *fix_imports*, *encoding* and
    *errors*, which are used to control compatibility support for
    pickle stream generated by Python 2.  If *fix_imports* is True,
    pickle will try to map the old Python 2 names to the new names
    used in Python 3.  The *encoding* and *errors* tell pickle how
    to decode 8-bit string instances pickled by Python 2; these
    default to 'ASCII' and 'strict', respectively. *encoding* can be
    'bytes' to read these 8-bit string instances as bytes objects.
    """

    dispatch = {}

    def __init__(self, space, w_file, fix_imports, encoding, errors, w_buffers=None):
        self.w_buffers = w_buffers
        self.w_file_readline = space.getattr(w_file, space.newtext("readline"))
        self.w_file_read = space.getattr(w_file, space.newtext("read"))
        self.memo = {}
        self.encoding = encoding
        self.errors = errors
        self.proto = 0
        self.fix_imports = fix_imports
        self.space = space

    def load(self):
        # if not hasattr(self, "w_file_read"):
        #     raise oefmt(unpickling_error(self.space),
        #         "Unpickler.__init__() was not called by %T", self)
        self._unframer = _Unframer(self.space, self.w_file_read, self.w_file_readline)
        self.read = self._unframer.read
        self.readline = self._unframer.readline
        self.metastack = []
        self.stack = []
        self.append = self.stack.append
        self.proto = 0
        read = self.read
        while True:
            key = self.read(1)
            if key[0] == op.STOP[0]:
                return data_pop(self.space, self.stack)
            try:
                self.dispatch[ord(key[0])](self)
            except KeyError:
                raise oefmt(unpickling_error(self.space),
                    "unkown mark %s", key[0])
            # print "self.stack", self.stack

    def read1(self):
        return self._unframer.read1()

    def read_unpackI(self):
        d, index = self._unframer.read_with_offset(4)
        return unpackI(d, index)

    def read_unpacki(self):
        d, index = self._unframer.read_with_offset(4)
        return unpacki(d, index)

    # Return a list of items pushed in the stack after last MARK instruction.
    def pop_mark(self):
        items = self.stack
        if len(self.metastack) < 1:
            raise oefmt(unpickling_error(self.space),
                "no items on stack")
        self.stack = self.metastack.pop()
        self.append = self.stack.append
        return items

    def load_proto(self):
        proto = ord(self.read(1)[0])
        if not 0 <= proto <= HIGHEST_PROTOCOL:
            raise oefmt(self.space.w_ValueError,
                "unsupported pickle protocol: %d", proto)
        self.proto = proto
    dispatch[op.PROTO[0]] = load_proto

    def load_frame(self):
        try:
            frame_size = unpackQ(self.read(8))
        except IndexError:
            raise oefmt(unpickling_error(self.space),
                'truncated data in FRAME')
        if frame_size > maxsize:
            raise oefmt(self.space.w_ValueError,
                "frame size > maxsize: %d", frame_size)
        self._unframer.load_frame(frame_size)
    dispatch[op.FRAME[0]] = load_frame

    if 0:
        def persistent_load(self, w_pid):
            raise oefmt(unpickling_error(self.space),
                "unsupported persistent id encountered")

        def load_persid(self):
            try:
                pid = self.readline()[:-1]
            except UnicodeDecodeError:
                raise oefmt(unpickling_error(self.space),
                    "persistent IDs in protocol 0 must be ASCII strings")
            self.append(self.persistent_load(pid))
        dispatch[op.PERSID[0]] = load_persid

        def load_binpersid(self):
            w_pid = data_pop(self.space, self.stack)
            self.append(self.persistent_load(w_pid))
        dispatch[op.BINPERSID[0]] = load_binpersid

    def load_none(self):
        self.append(self.space.w_None)
    dispatch[op.NONE[0]] = load_none

    def load_false(self):
        self.append(self.space.w_False)
    dispatch[op.NEWFALSE[0]] = load_false

    def load_true(self):
        self.append(self.space.w_True)
    dispatch[op.NEWTRUE[0]] = load_true

    def load_int(self):
        space = self.space
        data = self.readline()[:-1]
        if data == op.FALSE[1:]:
            w_val = space.w_False
        elif data == op.TRUE[1:]:
            w_val = space.w_True
        else:
            try:
                w_val = space.newint(int(data))
            except ValueError:
                raise oefmt(space.w_ValueError, "could not convert string to int")
        self.append(w_val)
    dispatch[op.INT[0]] = load_int

    def load_binint(self):
        val = self.read_unpacki()
        self.append(self.space.newint(val))
    dispatch[op.BININT[0]] = load_binint

    def load_binint1(self):
        self.append(self.space.newint(ord(self.read1()[0])))
    dispatch[op.BININT1[0]] = load_binint1

    def load_binint2(self):
        data = self.read(2)
        # val = unpack('<H', data)[0]
        val = 256 * ord(data[1]) + ord(data[0])
        self.append(self.space.newint(val))
    dispatch[op.BININT2[0]] = load_binint2

    def load_long(self):
        data = self.readline()[:-1]
        if data and data[-1] == 'L':
            data = data[:-1]
        val = int(data)
        self.append(self.space.newint(val))
    dispatch[op.LONG[0]] = load_long

    def load_long1(self):
        n = ord(self.read1()[0])
        data = self.read(n)
        self.append(decode_long(self.space, data))
    dispatch[op.LONG1[0]] = load_long1

    def load_long4(self):
        n = self.read_unpacki()
        if n < 0:
            # Corrupt or hostile pickle -- we never write one like this
            raise oefmt(unpickling_error(self.space),
                "LONG pickle has negative byte count")
        data = self.read(n)
        self.append(decode_long(self.space, data))
    dispatch[op.LONG4[0]] = load_long4

    def load_float(self):
        f = float(self.readline()[:-1])
        self.append(self.space.newfloat(f))
    dispatch[op.FLOAT[0]] = load_float

    def load_binfloat(self):
        f = unpack_float(self.read(8))
        self.append(self.space.newfloat(f))
    dispatch[op.BINFLOAT[0]] = load_binfloat

    if 0:
        def _decode_string(self, value):
            # Used to allow strings from Python 2 to be decoded either as
            # bytes or Unicode strings.  This should be used only with the
            # STRING, BINSTRING and SHORT_BINSTRING opcodes.
            if self.encoding == "bytes":
                return value
            else:
                return value.decode(self.encoding, self.errors)

        def load_string(self):
            raise oefmt(self.space.w_NotImplementedError,
                "cannot unpickle python2 STRING pickled data")
            data = self.readline()[:-1]
            # Strip outermost quotes
            if len(data) >= 2 and data[0] == data[-1] and data[0] in b'"\'':
                data = data[1:-1]
            else:
                raise oefmt(unpickling_error(self.space),
                    "the STRING opcode argument must be quoted")
            decoded = self._decode_string(codecs.escape_decode(data)[0])
            self.append(decoded)
        dispatch[op.STRING[0]] = load_string

        def load_binstring(self):
            # Deprecated BINSTRING uses signed 32-bit length
            length = self.read_unpacki()
            if length < 0:
                raise oefmt(unpickling_error(self.space),
                    "BINSTRING pickle has negative byte count")
            data = self.read(length)
            if len(data) < length:
                raise oefmt(unpickling_error(self.space),
                    "trucated data in BINSTRING")
            self.append(self._decode_string(data))
        dispatch[op.BINSTRING[0]] = load_binstring

    def load_binbytes(self):
        length = self.read_unpackI()
        if length > maxsize:
            raise oefmt(unpickling_error(self.space),
                "BINBYTES exceeds system's maximum size "
                                  "of %d bytes", maxsize)
        data = self.read(length)
        if len(data) < length:
            raise oefmt(unpickling_error(self.space),
                "trucated data in BINBYTES")
        self.append(self.space.newbytes(data))
    dispatch[op.BINBYTES[0]] = load_binbytes

    def load_unicode(self):
        data = self.readline()[:-1]
        self.append(self.space.newtext(*decode_utf8sp(self.space, data)))
    dispatch[op.UNICODE[0]] = load_unicode

    def load_binunicode(self):
        length = self.read_unpackI()
        if length > maxsize:
            raise oefmt(unpickling_error(self.space),
                "BINUNICODE exceeds system's maximum size "
                                  "of %d bytes", maxsize)
        data = self.read(length)
        if len(data) < length:
            raise oefmt(unpickling_error(self.space),
                "trucated data in BINUNICODE")
        self.append(self.space.newtext(*decode_utf8sp(self.space, data)))
    dispatch[op.BINUNICODE[0]] = load_binunicode

    def load_binunicode8(self):
        try:
            length = unpackQ(self.read(8))
        except IndexError:
            raise oefmt(unpickling_error(self.space),
                "trucated data in BINUNICODE8")
        if length > maxsize:
            raise oefmt(unpickling_error(self.space),
                "BINUNICODE8 exceeds system's maximum size "
                                  "of %d bytes", maxsize)
        data = self.read(length)
        if len(data) < length:
            raise oefmt(unpickling_error(self.space),
                "trucated data in BINUNICODE8")
        self.append(self.space.newtext(*decode_utf8sp(self.space, data)))
    dispatch[op.BINUNICODE8[0]] = load_binunicode8

    def load_binbytes8(self):
        try:
            length = unpackQ(self.read(8))
        except IndexError:
            raise oefmt(unpickling_error(self.space),
                "trucated data in BINBYTES8")
        if length > maxsize:
            raise oefmt(unpickling_error(self.space),
                "BINBYTES8 exceeds system's maximum size "
                                  "of %d bytes", maxsize)
        data = self.read(length)
        if len(data) < length:
            raise oefmt(unpickling_error(self.space),
                "trucated data in BINBYTES8")
        self.append(self.space.newbytes(data))
    dispatch[op.BINBYTES8[0]] = load_binbytes8

    def load_bytearray8(self):
        try:
            length = unpackQ(self.read(8))
        except IndexError:
            raise oefmt(unpickling_error(self.space),
                "trucated data in BYTEARRAY8")
        if length > maxsize:
            raise oefmt(unpickling_error(self.space),
                "BYTEARRAY8 exceeds system's maximum size "
                                  "of %d bytes", maxsize)
        data = self.read(length)
        if len(data) < length:
            raise oefmt(unpickling_error(self.space),
                "trucated data in BYTEARRAY8")
        self.append(self.space.newbytearray([c for c in data]))
    dispatch[op.BYTEARRAY8[0]] = load_bytearray8

    def load_next_buffer(self):
        space = self.space
        if space.is_none(self.w_buffers):
            raise oefmt(unpickling_error(space),
                "pickle stream refers to out-of-band data "
                                  "but no *buffers* argument was given")
        try:
            w_buf = space.next(self.w_buffers)
        except StopIteration:
            raise oefmt(unpickling_error(space),
                "not enough out-of-band buffers")
        self.append(w_buf)
    dispatch[op.NEXT_BUFFER[0]] = load_next_buffer

    if 0:
        def load_readonly_buffer(self):
            buf = self.stack[-1]
            with memoryview(buf) as m:
                if not m.readonly:
                    self.stack[-1] = m.toreadonly()
        dispatch[op.READONLY_BUFFER[0]] = load_readonly_buffer

        def load_short_binstring(self):
            length = ord(self.read1()[0])
            data = self.read(length)
            if len(data) < length:
                raise oefmt(unpickling_error(self.space),
                    "trucated data in SHORT_BINSTRING")
            self.append(self._decode_string(data))
        dispatch[op.SHORT_BINSTRING[0]] = load_short_binstring

    def load_short_binbytes(self):
        length = ord(self.read1()[0])
        data = self.read(length)
        if len(data) < length:
            raise oefmt(unpickling_error(self.space),
                "trucated data in SHORT_BINBYTES")
        self.append(self.space.newbytes(data))
    dispatch[op.SHORT_BINBYTES[0]] = load_short_binbytes

    def load_short_binunicode(self):
        length = ord(self.read1()[0])
        data = self.read(length)
        if len(data) < length:
            raise oefmt(unpickling_error(self.space),
                "trucated data in SHORT_BINUNICODE")
        self.append(self.space.newtext(data))
    dispatch[op.SHORT_BINUNICODE[0]] = load_short_binunicode

    def load_tuple(self):
        items = self.pop_mark()
        items_w = [w_obj for w_obj in items]
        self.append(self.space.newtuple(items_w))
    dispatch[op.TUPLE[0]] = load_tuple

    def load_empty_tuple(self):
        self.append(self.space.newtuple([]))
    dispatch[op.EMPTY_TUPLE[0]] = load_empty_tuple

    def load_tuple1(self):
        n1 = len(self.stack) - 1
        if n1 < 0:
            raise oefmt(unpickling_error(self.space),
                "stack empty in TUPLE")
        self.stack[n1] = self.space.newtuple([self.stack[n1]])
    dispatch[op.TUPLE1[0]] = load_tuple1

    def load_tuple2(self):
        n = len(self.stack)
        n2 = n - 2
        if n2 < 0:
            raise oefmt(unpickling_error(self.space),
                "stack empty in TUPLE2")
        self.stack[n2:n] = [self.space.newtuple([self.stack[n2], self.stack[n2+1]])]
    dispatch[op.TUPLE2[0]] = load_tuple2

    def load_tuple3(self):
        n = len(self.stack)
        n3 = n - 3
        if n3 < 0:
            raise oefmt(unpickling_error(self.space),
                "stack empty in TUPLE3")
        self.stack[n3:n] = [self.space.newtuple([self.stack[n3], self.stack[n3+1], self.stack[n3+2]])]
    dispatch[op.TUPLE3[0]] = load_tuple3

    def load_empty_list(self):
        self.append(self.space.newlist([]))
    dispatch[op.EMPTY_LIST[0]] = load_empty_list

    def load_empty_dictionary(self):
        self.append(self.space.newdict())
    dispatch[op.EMPTY_DICT[0]] = load_empty_dictionary

    def load_empty_set(self):
        self.append(self.space.newset([]))
    dispatch[op.EMPTY_SET[0]] = load_empty_set

    def load_frozenset(self):
        items = self.pop_mark()
        items_copy_w = [w_item for w_item in items]
        w_frozenset = self.space.newfrozenset(items_copy_w)
        self.append(w_frozenset)
    dispatch[op.FROZENSET[0]] = load_frozenset

    def load_list(self):
        items = self.pop_mark()
        self.append(self.space.newlist(items))
    dispatch[op.LIST[0]] = load_list

    def load_dict(self):
        space = self.space
        items = self.pop_mark()
        if (len(items) % 2) != 0:
            raise oefmt(unpickling_error(space),
                "odd number of items for DICT")
        w_d = space.newdict()
        for i in range(0, len(items), 2):
            space.setitem(w_d, items[i], items[i+1])
        self.append(w_d)
    dispatch[op.DICT[0]] = load_dict

    if 0:  # Python2 residue?
        # INST and OBJ differ only in how they get a class object.  It's not
        # only sensible to do the rest in a common routine, the two routines
        # previously diverged and grew different bugs.
        # klass is the class to instantiate, and k points to the topmost mark
        # object, following which are the arguments for klass.__init__.
        def _instantiate(self, klass, args):
            if (args or not isinstance(klass, type) or
                hasattr(klass, "__getinitargs__")):
                try:
                    value = klass(*args)
                except TypeError as err:
                    raise oefmt(self.space.w_TypeError("in constructor for %s: %s",
                                    klass.__name__, str(err)))
            else:
                value = klass.__new__(klass)
            self.append(value)

        def load_inst(self):
            raise oefmt(self.space.w_NotImplementedError, "INST opcode not implemented")
            w_module = self.readline()[:-1].decode("ascii")
            w_name = self.readline()[:-1].decode("ascii")
            klass = self.find_class(w_module, w_name)
            self._instantiate(klass, self.pop_mark())
        dispatch[op.INST[0]] = load_inst

        def load_obj(self):
            raise oefmt(self.space.w_NotImplementedError, "OBJ opcode not implemented")
            # Stack is ... markobject classobject arg1 arg2 ...
            args = self.pop_mark()
            cls = args.pop(0)
        self._instantiate(cls, args)
        dispatch[op.OBJ[0]] = load_obj

    def load_newobj(self):
        space = self.space
        w_args = data_pop(self.space, self.stack)
        w_cls = data_pop(self.space, self.stack)
        w_new = space.getattr(w_cls, space.newtext("__new__"))
        if space.len_w(w_args) > 0:
            w_arguments = Arguments(space, [w_cls], w_stararg = w_args)
            w_obj = space.call_args(w_new, w_arguments)
        else:
            w_obj = space.call_function(w_new, w_cls)
        self.append(w_obj)
    dispatch[op.NEWOBJ[0]] = load_newobj

    def load_newobj_ex(self):
        space = self.space
        w_kwargs = data_pop(self.space, self.stack)
        w_args = data_pop(self.space, self.stack)
        w_cls = data_pop(self.space, self.stack)
        w_new = space.getattr(w_cls, space.newtext("__new__"))
        w_arguments = Arguments(self.space, [w_cls], w_stararg = w_args, w_starstararg=w_kwargs)
        w_obj = self.space.call_args(w_new, w_arguments)
        self.append(w_obj)
    dispatch[op.NEWOBJ_EX[0]] = load_newobj_ex

    def load_global(self):
            w_module = self.space.newtext(self.readline()[:-1])
            w_name = self.space.newtext(self.readline()[:-1])
            w_klass = self.find_class(w_module, w_name)
            self.append(w_klass)
    dispatch[op.GLOBAL[0]] = load_global

    def load_stack_global(self):
        space = self.space
        w_name = data_pop(self.space, self.stack)
        w_module = data_pop(self.space, self.stack)
        if space.isinstance_w(w_name, space.w_text) and space.isinstance_w(w_module, space.w_text):
            self.append(self.find_class(w_module, w_name))
        else:
            raise oefmt(unpickling_error(self.space),
                "STACK_GLOBAL requires str")
    dispatch[op.STACK_GLOBAL[0]] = load_stack_global

    def load_ext1(self):
        code = int(self.read1())
        self.get_extension(code)
    dispatch[op.EXT1[0]] = load_ext1

    def load_ext2(self):
        data = self.read(2)
        # code, = unpack('<H', self.read(2))
        if len(data) < 2:
            raise oefmt(unpickling_error(self.space),
                'truncated data in EXT4')
        code = 256 * ord(data[1]) + ord(data[0])
        self.get_extension(code)
    dispatch[op.EXT2[0]] = load_ext2

    def load_ext4(self):
        code = self.read_unpacki()
        self.get_extension(code)
    dispatch[op.EXT4[0]] = load_ext4

    def get_extension(self, code):
        space = self.space
        w_code = space.newint(code)
        state = space.fromcache(State)
        w_obj = space.finditem(state.w_extension_cache, w_code)
        if not space.is_none(w_obj):
            self.append(w_obj)
            return
        w_key = space.finditem(state.w_inverted_registry, w_code)
        if space.is_none(w_key):
            if code <= 0: # note that 0 is forbidden
                # Corrupt or hostile pickle.
                raise oefmt(unpickling_error(self.space), "EXT specifies code <= 0")
            raise oefmt(self.space.w_ValueError, "unregistered extension code %d", code)
        w_module_name, w_name = space.listview(w_key)
        w_obj = self.find_class(w_module_name, w_name)
        space.setitem(state.w_extension_cache, w_code, w_obj)
        self.append(w_obj)

    def find_class(self, w_module_name, w_name):
        # Subclasses may override this.
        space = self.space
        space.audit('pickle.find_class', [w_module_name, w_name])
        if self.proto < 3 and self.fix_imports:
            w_modname_and_name = space.newtuple([w_module_name, w_name])
            w_NAME_MAPPING = space.fromcache(State).w_NAME_MAPPING
            w_IMPORT_MAPPING = space.fromcache(State).w_IMPORT_MAPPING
            w_1 = space.finditem(w_NAME_MAPPING, w_modname_and_name)
            w_2 = space.finditem(w_IMPORT_MAPPING, w_module_name)
            if w_1:
                w_module_name, w_name = space.listview(w_1)
            elif w_2:
                w_module_name = w_2
        w_import = space.getattr(space.builtin, space.newtext("__import__"))
        space.call_function(w_import, w_module_name)
        w_module = space.getitem(space.getattr(space.sys, space.newtext('modules')), w_module_name)
        if self.proto >= 4:
            retval = _getattribute(space, w_module, w_name)
            return space.listview(retval)[0]
        else:
            return space.getattr(w_module, w_name)

    def load_reduce(self):
        stack = self.stack
        w_args = data_pop(self.space, stack)
        if len(self.stack) < 1:
            raise oefmt(unpickling_error(self.space),
                "unexpected MARK found")
        w_func = stack[-1]
        w_arguments = Arguments(self.space, [], w_stararg = w_args)
        w_obj = self.space.call_args(w_func, w_arguments)
        stack[-1] = w_obj
    dispatch[op.REDUCE[0]] = load_reduce

    def load_pop(self):
        if self.stack:
            del self.stack[-1]
        else:
            self.pop_mark()
    dispatch[op.POP[0]] = load_pop

    def load_pop_mark(self):
        self.pop_mark()
    dispatch[op.POP_MARK[0]] = load_pop_mark

    def load_dup(self):
        if len(self.stack) < 1:
            raise oefmt(unpickling_error(self.space),
                "unexpected MARK found")
        self.append(self.stack[-1])
    dispatch[op.DUP[0]] = load_dup

    def load_get(self):
        i = int(self.readline()[:-1])
        try:
            self.append(self.memo[i])
        except KeyError:
            raise oefmt(unpickling_error(self.space),
                'Memo value not found at index %d', i)
    dispatch[op.GET[0]] = load_get

    def load_binget(self):
        i = ord(self.read1()[0])
        try:
            self.append(self.memo[i])
        except KeyError as exc:
            raise oefmt(unpickling_error(self.space),
                'Memo value not found at index %d', i)
    dispatch[op.BINGET[0]] = load_binget

    def load_long_binget(self):
        i = self.read_unpackI()
        try:
            self.append(self.memo[i])
        except KeyError as exc:
            raise oefmt(unpickling_error(self.space),
                'Memo value not found at index %d', i)
    dispatch[op.LONG_BINGET[0]] = load_long_binget

    def load_put(self):
        data = self.readline()
        i = int(data[:-1])
        if i < 0:
            raise oefmt(self.space.w_ValueError, "negative PUT argument")
        if len(self.stack) < 1:
            raise oefmt(unpickling_error(self.space),
                'stack underflow in PUT')
        self.memo[i] = self.stack[-1]
    dispatch[op.PUT[0]] = load_put

    def load_binput(self):
        i = ord(self.read1()[0])
        if i < 0:
            raise oefmt(self.space.w_ValueError, "negative BINPUT argument")
        if len(self.stack) < 1:
            raise oefmt(unpickling_error(self.space),
                'stack underflow in BINPUT')
        self.memo[i] = self.stack[-1]
    dispatch[op.BINPUT[0]] = load_binput

    def load_long_binput(self):
        i = self.read_unpackI()
        if i > maxsize:
            raise oefmt(self.space.w_ValueError, "negative LONG_BINPUT argument")
        if len(self.stack) < 1:
            raise oefmt(unpickling_error(self.space),
                'stack underflow in LONG_BINPUT')
        self.memo[i] = self.stack[-1]
    dispatch[op.LONG_BINPUT[0]] = load_long_binput

    def load_memoize(self):
        memo = self.memo
        if len(self.stack) < 1:
            raise oefmt(unpickling_error(self.space),
                'stack underflow in MEMOIZE')
        memo[len(memo)] = self.stack[-1]
    dispatch[op.MEMOIZE[0]] = load_memoize

    def load_append(self):
        stack = self.stack
        w_value = data_pop(self.space, stack)
        if len(self.stack) < 1:
            raise oefmt(unpickling_error(self.space),
                "unexpected MARK found")
        w_list = stack[-1]
        self.space.call_method(w_list, "append", w_value)
    dispatch[op.APPEND[0]] = load_append

    def load_appends(self):
        space = self.space
        w_items = self.pop_mark()
        if len(self.stack) < 1:
            raise oefmt(unpickling_error(self.space),
                "unexpected MARK found")
        w_list_obj = self.stack[-1]
        w_extend = space.lookup(w_list_obj, "extend")
        if w_extend:
            space.call_method(w_list_obj, "extend", space.newlist(w_items))
            return
        # Even if the PEP 307 requires extend() and append() methods,
        # fall back on append() if the object has no extend() method
        # for backward compatibility.
        for w_item in w_items:
            space.call_method(w_list_obj, "append", w_item)
    dispatch[op.APPENDS[0]] = load_appends

    def load_setitem(self):
        stack = self.stack
        w_value = data_pop(self.space, stack)
        w_key = data_pop(self.space, stack)
        if len(self.stack) < 1:
            raise oefmt(unpickling_error(self.space),
                "unexpected MARK found")
        w_dict = stack[-1]
        self.space.setitem(w_dict, w_key, w_value)
    dispatch[op.SETITEM[0]] = load_setitem

    def load_setitems(self):
        items_w = self.pop_mark()
        if len(self.stack) < 1:
            raise oefmt(unpickling_error(self.space),
                "unexpected MARK found")
        w_dict = self.stack[-1]
        for i in range(0, len(items_w), 2):
            self.space.setitem(w_dict, items_w[i], items_w[i + 1])
    dispatch[op.SETITEMS[0]] = load_setitems

    def load_additems(self):
        space = self.space
        items = self.pop_mark()
        if len(self.stack) < 1:
            raise oefmt(unpickling_error(self.space),
                "unexpected MARK found")
        w_set_obj = self.stack[-1]
        if space.isinstance_w(w_set_obj, space.w_set):
            w_items = space.newtuple([w_i for w_i in items])
            space.call_method(w_set_obj,"update", w_items)
        else:
            for w_item in items:
                space.call_method(w_set_obj,"add", w_item)
    dispatch[op.ADDITEMS[0]] = load_additems

    def load_build(self):
        space = self.space
        stack = self.stack
        w_state = data_pop(self.space, stack)
        if len(self.stack) < 1:
            raise oefmt(unpickling_error(self.space),
                "unexpected MARK found")
        w_inst = stack[-1]
        w_setstate = space.findattr(w_inst, space.newtext("__setstate__"))
        if not space.is_none(w_setstate):
            space.call_function(w_setstate , w_state)
            return
        w_slotstate = space.w_None
        if space.isinstance_w(w_state, space.w_tuple) and space.len_w(w_state) == 2:
            w_state, w_slotstate = space.listview(w_state)
        if not space.is_none(w_state):
            w_inst_dict = w_inst.getdict(space)
            space.call_method(w_inst_dict, "update", w_state)
        if not space.is_none(w_slotstate):
            w_iter = space.iter(space.call_method(w_slotstate, "items"))
            while True:
                try:
                    w_item = space.next(w_iter)
                except OperationError as e:
                    if not e.match(space, space.w_StopIteration):
                        raise
                    break
                w_key, w_value = space.unpackiterable(w_item, 2)
                space.setattr(w_inst, w_key, w_value)
    dispatch[op.BUILD[0]] = load_build

    def load_mark(self):
        self.metastack.append(self.stack)
        self.stack = []
        self.append = self.stack.append
    dispatch[op.MARK[0]] = load_mark

W_Unpickler.dispatch = [W_Unpickler.dispatch.get(chr(i), None) for i in range(256)]


@unwrap_spec(fix_imports=bool, encoding="text", errors="text", w_buffers=WrappedDefault(None))
def descr__new__unpickler(space, w_subtype, w_file, __kwonly__, fix_imports=True, encoding="ASCII", errors="stricts", w_buffers=None):
    w_self = space.allocate_instance(W_Unpickler, w_subtype)
    W_Unpickler.__init__(w_self, space, w_file, fix_imports, encoding, errors, w_buffers)
    return w_self

W_Unpickler.typedef = TypeDef("_pickle.Unpickler",
    __new__ = interp2app(descr__new__unpickler),
    load = interp2app(W_Unpickler.load),
)


