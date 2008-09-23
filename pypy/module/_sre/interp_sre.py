from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import GetSetProperty, TypeDef
from pypy.interpreter.typedef import interp_attrproperty, interp_attrproperty_w
from pypy.interpreter.gateway import interp2app, ObjSpace, W_Root
from pypy.interpreter.error import OperationError
from pypy.rlib.rarithmetic import intmask

# This can be compiled in two ways:
#
# * THREE_VERSIONS_OF_CORE=True: you get three copies of the whole
#   regexp searching and matching code: for strings, for unicode strings,
#   and for generic buffer objects (like mmap.mmap or array.array).
#
# * THREE_VERSIONS_OF_CORE=False: there is only one copy of the code,
#   at the cost of an indirect method call to fetch each character.

THREE_VERSIONS_OF_CORE = False


#### Constants and exposed functions

from pypy.rlib.rsre import rsre
from pypy.rlib.rsre.rsre_char import MAGIC, CODESIZE, getlower
copyright = "_sre.py 2.4 Copyright 2005 by Nik Haldimann"

def w_getlower(space, char_ord, flags):
    return space.wrap(getlower(char_ord, flags))
w_getlower.unwrap_spec = [ObjSpace, int, int]

def w_getcodesize(space):
    return space.wrap(CODESIZE)

# use the same version of unicodedb as the standard objspace
from pypy.objspace.std.unicodeobject import unicodedb
rsre.set_unicode_db(unicodedb)

#### State classes

def make_state(space, w_string, start, end, flags):
    # XXX maybe turn this into a __new__ method of W_State
    if space.is_true(space.isinstance(w_string, space.w_str)):
        cls = W_StringState
    elif space.is_true(space.isinstance(w_string, space.w_unicode)):
        cls = W_UnicodeState
    else:
        cls = W_GenericState
    return space.wrap(cls(space, w_string, start, end, flags))
make_state.unwrap_spec = [ObjSpace, W_Root, int, int, int]


class W_State(Wrappable):
    if not THREE_VERSIONS_OF_CORE:
        rsre.insert_sre_methods(locals(), 'all')

    def __init__(self, space, w_string, start, end, flags):
        self.space = space
        self.w_string = w_string
        length = self.unwrap_object()
        if start < 0:
            start = 0
        if end > length:
            end = length
        self.start = start
        self.pos   = start     # records the original start position
        self.end   = end
        self.flags = flags
        self.reset()

    def lower(self, char_ord):
        return getlower(char_ord, self.flags)

    # methods overridden by subclasses

    def unwrap_object(self):
        raise NotImplementedError

    if 'reset' not in locals():
        def reset(self):
            raise NotImplementedError

    if 'search' not in locals():
        def search(self, pattern_codes):
            raise NotImplementedError

    if 'match' not in locals():
        def match(self, pattern_codes):
            raise NotImplementedError

    # Accessors for the typedef

    def w_reset(self):
        self.reset()

    def w_create_regs(self, group_count):
        """Creates a tuple of index pairs representing matched groups, a format
        that's convenient for SRE_Match."""
        space = self.space
        return space.newtuple([
            space.newtuple([space.wrap(value1),
                            space.wrap(value2)])
            for value1, value2 in self.create_regs(group_count)])
    w_create_regs.unwrap_spec = ['self', int]

    def fget_start(space, self):
        return space.wrap(self.start)

    def fset_start(space, self, w_value):
        self.start = space.int_w(w_value)

    def fget_string_position(space, self):
        return space.wrap(self.string_position)

    def fset_string_position(space, self, w_value):
        self.start = space.int_w(w_value)

    def get_char_ord(self, p):
        raise NotImplementedError

getset_start = GetSetProperty(W_State.fget_start, W_State.fset_start, cls=W_State)
getset_string_position = GetSetProperty(W_State.fget_string_position,
                                     W_State.fset_string_position, cls=W_State)

W_State.typedef = TypeDef("W_State",
    string = interp_attrproperty_w("w_string", W_State),
    start = getset_start,
    end = interp_attrproperty("end", W_State),
    string_position = getset_string_position,
    pos = interp_attrproperty("pos", W_State),
    lastindex = interp_attrproperty("lastindex", W_State),
    reset = interp2app(W_State.w_reset),
    create_regs = interp2app(W_State.w_create_regs),
)


class W_StringState(W_State):
    if THREE_VERSIONS_OF_CORE:
        rsre.insert_sre_methods(locals(), 'str')

    def unwrap_object(self):
        self.string = self.space.str_w(self.w_string)
        return len(self.string)

    def get_char_ord(self, p):
        return ord(self.string[p])


class W_UnicodeState(W_State):
    if THREE_VERSIONS_OF_CORE:
        rsre.insert_sre_methods(locals(), 'unicode')

    def unwrap_object(self):
        self.unicode = self.space.unicode_w(self.w_string)
        return len(self.unicode)

    def get_char_ord(self, p):
        return ord(self.unicode[p])


class W_GenericState(W_State):
    if THREE_VERSIONS_OF_CORE:
        rsre.insert_sre_methods(locals(), 'generic')

    def unwrap_object(self):
        self.buffer = self.space.buffer_w(self.w_string)
        return self.buffer.getlength()

    def get_char_ord(self, p):
        return ord(self.buffer.getitem(p))


def w_search(space, w_state, w_pattern_codes):
    state = space.interp_w(W_State, w_state)
    pattern_codes = [intmask(space.uint_w(code)) for code
                                    in space.unpackiterable(w_pattern_codes)]
    return space.newbool(state.search(pattern_codes))

def w_match(space, w_state, w_pattern_codes):
    state = space.interp_w(W_State, w_state)
    pattern_codes = [intmask(space.uint_w(code)) for code
                                    in space.unpackiterable(w_pattern_codes)]
    return space.newbool(state.match(pattern_codes))
