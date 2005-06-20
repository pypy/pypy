from pypy.rpython.lltype import *


class SymbolTable:
    """For debugging purposes only.  This collects the information
    needed to know the byte-layout of the data structures generated in
    a C source.
    """

    def __init__(self):
        self.next_number = 0
        self.next_pointer = 0
        self.lltypes = {}
        self.globals = {}
        self.module = None

    def attach(self, module):
        self.module = module
        module.__symboltable__ = self

    def generate_type_info(self, db, defnode):
        self.lltypes[defnode.LLTYPE] = self.next_number
        for number_expr in defnode.debug_offsets():
            self.next_number += 1
            yield number_expr

    def generate_global_info(self, db, node):
        self.globals[node.name] = self.next_pointer, node.T
        self.next_pointer += 1
        return node.ptrname

    # __________ public interface (mapping-like) __________

    def keys(self):
        return self.globals.keys()

    def __getitem__(self, globalname_or_address):
        if isinstance(globalname_or_address, str):
            ptrindex, T = self.globals[globalname]
            address = self.module.debuginfo_global(ptrindex)
        else:
            for ptrindex, T in self.globals.values():
                address = self.module.debuginfo_global(ptrindex)
                if address == globalname_or_address:
                    break
            else:
                raise KeyError("no global object at 0x%x" %
                               (globalname_or_address,))
        return debugptr(Ptr(T), address, self)

    def __iter__(self):
        return self.globals.iterkeys()

def getsymboltable(module):
    if isinstance(module, str):
        module = __import__(module)
    return module.__symboltable__

# ____________________________________________________________

import struct

PrimitiveTag = {
    Signed:    'l',
    Unsigned:  'L',
    Float:     'd',
    Char:      'c',
    Bool:      'b',
    }
ptr_size = struct.calcsize('P')


class debugptr:

    def __init__(self, PTRTYPE, address, symtable):
        self._TYPE = PTRTYPE
        self._address = address
        self._symtable = symtable

    def __eq__(self, other):
        return self._address == other._address

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        raise TypeError("pointer objects are not hashable")

    def __repr__(self):
        addr = self._address
        if addr < 0:
            addr += 256 ** ptr_size
        return '<debugptr %s to 0x%x>' % (self._TYPE.TO, addr)

    def __nonzero__(self):
        return self._address != 0

    def _nth_offset(self, n):
        index = self._symtable.lltypes[self._TYPE.TO]
        return self._symtable.module.debuginfo_offset(index + n)

    def _read(self, FIELD_TYPE, offset):
        if not self:   # NULL
            raise ValueError, 'dereferencing NULL pointer'
        module = self._symtable.module
        address = self._address + offset
        if isinstance(FIELD_TYPE, ContainerType):
            return debugptr(Ptr(FIELD_TYPE), address, self._symtable)
        elif isinstance(FIELD_TYPE, Primitive):
            if FIELD_TYPE == Void:
                return None
            tag = PrimitiveTag[FIELD_TYPE]
            size = struct.calcsize(tag)
            data = module.debuginfo_peek(address, size)
            result, = struct.unpack(tag, data)
            return result
        elif isinstance(FIELD_TYPE, Ptr):
            data = module.debuginfo_peek(address, ptr_size)
            result, = struct.unpack('P', data)
            return debugptr(FIELD_TYPE, result, self._symtable)
        else:
            raise TypeError("unknown type %r" % (FIELD_TYPE,))

    def __getattr__(self, name):
        STRUCT = self._TYPE.TO
        if not name.startswith('_') and isinstance(STRUCT, Struct):
            try:
                field_index = list(STRUCT._names).index(name)
            except ValueError:
                raise AttributeError, name
            FIELD_TYPE = STRUCT._flds[name]
            offset = self._nth_offset(field_index)
            return self._read(FIELD_TYPE, offset)
        raise AttributeError, name

    def __len__(self):
        ARRAY = self._TYPE.TO
        if isinstance(ARRAY, Array):
            length_offset = self._nth_offset(0)
            return self._read(Signed, length_offset)
        raise TypeError, "not an array: %r" % (ARRAY,)

    def __getitem__(self, index):
        ARRAY = self._TYPE.TO
        if isinstance(ARRAY, Array):
            if not (0 <= index < len(self)):
                raise IndexError("array index out of bounds")
            item0_offset = self._nth_offset(1)
            item1_offset = self._nth_offset(2)
            offset = item0_offset + (item1_offset-item0_offset) * index
            return self._read(ARRAY.OF, offset)
        raise TypeError, "not an array: %r" % (ARRAY,)
