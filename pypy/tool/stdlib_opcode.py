"""
Opcodes PyPy compiles Python source to.
Also gives access to opcodes of the host Python PyPy was bootstrapped with
(module attributes with the `host_` prefix).
"""

# load opcode.py as pythonopcode from our own lib

__all__ = ['opmap', 'opname', 'HAVE_ARGUMENT',
           'hasconst', 'hasname', 'hasjrel', 'hasjabs',
           'haslocal', 'hascompare', 'hasfree', 'cmp_op']

# ____________________________________________________________
# RPython-friendly helpers and structures

class _BaseOpcodeDesc(object):
    def __init__(self, bytecode_spec, name, index, methodname):
        self.bytecode_spec = bytecode_spec
        self.name = name
        self.methodname = methodname
        self.index = index
        self.hasarg = index >= self.HAVE_ARGUMENT

    def _freeze_(self):
        return True

    def is_enabled(self, space):
        """Check if the opcode should be enabled in the space's configuration.
        (Returns True for all standard opcodes.)"""
        opt = space.config.objspace.opcodes
        return getattr(opt, self.name, True)
    is_enabled._annspecialcase_ = 'specialize:memo'

    # for predictable results, we try to order opcodes most-used-first
    opcodeorder = [124, 125, 100, 105, 1, 131, 116, 111, 106, 83, 23, 93, 113, 25, 95, 64, 112, 66, 102, 110, 60, 92, 62, 120, 68, 87, 32, 136, 4, 103, 24, 63, 18, 65, 15, 55, 121, 3, 101, 22, 12, 80, 86, 135, 126, 90, 140, 104, 2, 33, 20, 108, 107, 31, 134, 132, 88, 30, 133, 130, 137, 141, 61, 122, 11, 40, 74, 73, 51, 96, 21, 42, 56, 85, 82, 89, 142, 77, 78, 79, 91, 76, 97, 57, 19, 43, 84, 50, 41, 99, 53, 26]

    def sortkey(self):
        try:
            i = self.opcodeorder.index(self.index)
        except ValueError:
            i = 1000000
        return i, self.index

    def __cmp__(self, other):
        return (cmp(self.__class__, other.__class__) or
                cmp(self.sortkey(), other.sortkey()))

    def __str__(self):
        return "<OpcodeDesc code=%d name=%s at %x>" % (self.index, self.name, id(self))
    
    __repr__ = __str__

class _baseopcodedesc:
    """A namespace mapping OPCODE_NAME to _BaseOpcodeDescs."""
    pass


class BytecodeSpec(object):
    """A bunch of mappings describing a bytecode instruction set."""

    def __init__(self, name, opmap, HAVE_ARGUMENT):
        """NOT_RPYTHON."""
        class OpcodeDesc(_BaseOpcodeDesc):
            HAVE_ARGUMENT = HAVE_ARGUMENT
        class opcodedesc(_baseopcodedesc):
            """A namespace mapping OPCODE_NAME to OpcodeDescs."""
        
        self.name = name
        self.OpcodeDesc = OpcodeDesc
        self.opcodedesc = opcodedesc
        self.HAVE_ARGUMENT = HAVE_ARGUMENT
        # opname -> opcode
        self.opmap = opmap
        # opcode -> method name
        self.method_names = tbl = ['MISSING_OPCODE'] * 256
        # opcode -> opdesc
        self.opdescmap = {}
        for name, index in opmap.items():
            tbl[index] = methodname = name.replace('+', '_')
            desc = OpcodeDesc(self, name, index, methodname)
            setattr(self.opcodedesc, name, desc)
            self.opdescmap[index] = desc
        # fill the ordered opdesc list
        self.ordered_opdescs = lst = self.opdescmap.values() 
        lst.sort()
    
    def to_globals(self):
        """NOT_RPYTHON. Add individual opcodes to the module constants."""
        g = globals()
        g.update(self.opmap)
        g['SLICE'] = self.opmap["SLICE+0"]
        g['STORE_SLICE'] = self.opmap["STORE_SLICE+0"]
        g['DELETE_SLICE'] = self.opmap["DELETE_SLICE+0"]

    def __str__(self):
        return "<%s bytecode>" % (self.name,)
    
    __repr__ = __str__


# Initialization

from pypy.rlib.unroll import unrolling_iterable

from opcode import (
    opmap as host_opmap, HAVE_ARGUMENT as host_HAVE_ARGUMENT)

def load_pypy_opcode():
    from pypy.tool.lib_pypy import LIB_PYTHON
    opcode_path = LIB_PYTHON.join('opcode.py')
    d = {}
    execfile(str(opcode_path), d)
    for name in __all__:
        if name in d:
            globals()[name] = d[name]
    return d

load_pypy_opcode()
del load_pypy_opcode

bytecode_spec = BytecodeSpec('pypy', opmap, HAVE_ARGUMENT)
host_bytecode_spec = BytecodeSpec('host', host_opmap, host_HAVE_ARGUMENT)
bytecode_spec.to_globals()

opcode_method_names = bytecode_spec.method_names
opcodedesc = bytecode_spec.opcodedesc

unrolling_all_opcode_descs = unrolling_iterable(
    bytecode_spec.ordered_opdescs + host_bytecode_spec.ordered_opdescs)
unrolling_opcode_descs = unrolling_iterable(
    bytecode_spec.ordered_opdescs)
