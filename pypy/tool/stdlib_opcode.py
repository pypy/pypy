# load opcode.py as pythonopcode from our own lib

__all__ = ['opmap', 'opname', 'HAVE_ARGUMENT',
           'hasconst', 'hasname', 'hasjrel', 'hasjabs',
           'haslocal', 'hascompare', 'hasfree', 'cmp_op']

def load_opcode():
    import py
    opcode_path = py.path.local(__file__).dirpath().dirpath().dirpath('lib-python/modified-2.4.1/opcode.py')
    d = {}
    execfile(str(opcode_path), d)
    return d

opcode_dict = load_opcode()
del load_opcode

# copy some stuff from opcode.py directly into our globals
for name in __all__:
    if name in opcode_dict:
        globals()[name] = opcode_dict[name]

opcode_method_names = ['MISSING_OPCODE'] * 256
for name, index in opmap.items():
    opcode_method_names[index] = name.replace('+', '_')

# ____________________________________________________________
# RPython-friendly helpers and structures

from pypy.rlib.unroll import unrolling_iterable


class OpcodeDesc(object):
    def __init__(self, name, index):
        self.name = name
        self.methodname = opcode_method_names[index]
        self.index = index
        self.hasarg = index >= HAVE_ARGUMENT

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
        return cmp(self.sortkey(), other.sortkey())


opdescmap = {}

class opcodedesc:
    """A namespace mapping OPCODE_NAME to OpcodeDescs."""

for name, index in opmap.items():
    desc = OpcodeDesc(name, index)
    setattr(opcodedesc, name, desc)
    opdescmap[index] = desc

lst = opdescmap.values()
lst.sort()
unrolling_opcode_descs = unrolling_iterable(lst)

del name, index, desc, lst
