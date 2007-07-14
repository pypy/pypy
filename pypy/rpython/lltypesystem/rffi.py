
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.lltypesystem import ll2ctypes
from pypy.annotation.model import lltype_to_annotation
from pypy.rlib.objectmodel import Symbolic, CDefinedIntSymbolic
from pypy.rlib import rarithmetic

class CConstant(Symbolic):
    """ A C-level constant, maybe #define, rendered directly.
    """
    def __init__(self, c_name, TP):
        self.c_name = c_name
        self.TP = TP

    def annotation(self):
        return lltype_to_annotation(self.TP)

    def lltype(self):
        return self.TP

def llexternal(name, args, result, _callable=None, sources=[], includes=[],
               libraries=[], include_dirs=[]):
    ext_type = lltype.FuncType(args, result)
    funcptr = lltype.functionptr(ext_type, name, external='C',
                                 sources=tuple(sources),
                                 includes=tuple(includes),
                                 libraries=tuple(libraries),
                                 include_dirs=tuple(include_dirs),
                                 _callable=_callable)
    if _callable is None:
        ll2ctypes.make_callable_via_ctypes(funcptr)
    return funcptr

def setup():
    """ creates necessary c-level types
    """
    from pypy.rpython.lltypesystem.rfficache import platform
    for name, bits in platform.items():
        if name.startswith('unsigned'):
            name = 'u' + name[9:]
            signed = False
        else:
            signed = True
        name = name.replace(' ', '')
        llname = name.upper()
        inttype = rarithmetic.build_int('r_' + name, signed, bits)
        globals()['r_' + name] = inttype
        globals()[llname] = lltype.build_number(llname, inttype)

setup()

def CStruct(name, *fields, **kwds):
    """ A small helper to create external C structure, not the
    pypy one
    """
    hints = kwds.get('hints', {})
    hints = hints.copy()
    kwds['hints'] = hints
    hints['external'] = 'C'
    hints['c_name'] = name
    # Hack: prefix all attribute names with 'c_' to cope with names starting
    # with '_'.  The genc backend removes the 'c_' prefixes...
    c_fields = [('c_' + key, value) for key, value in fields]
    return lltype.Ptr(lltype.Struct(name, *c_fields, **kwds))

c_errno = CConstant('errno', lltype.Signed)

# void *   - for now, represented as char *
VOIDP = lltype.Ptr(lltype.Array(lltype.Char, hints={'nolength': True}))

# char *
CCHARP = lltype.Ptr(lltype.Array(lltype.Char, hints={'nolength': True}))

# int *
INTP = lltype.Ptr(lltype.Array(lltype.Signed, hints={'nolength': True}))

# various type mapping
# str -> char*
def str2charp(s):
    """ str -> char*
    """
    array = lltype.malloc(CCHARP.TO, len(s) + 1, flavor='raw')
    for i in range(len(s)):
        array[i] = s[i]
    array[len(s)] = '\x00'
    return array

def free_charp(cp):
    lltype.free(cp, flavor='raw')

# char* -> str
# doesn't free char*
def charp2str(cp):
    l = []
    i = 0
    while cp[i] != '\x00':
        l.append(cp[i])
        i += 1
    return "".join(l)

# char**
CCHARPP = lltype.Ptr(lltype.Array(CCHARP, hints={'nolength': True}))

def liststr2charpp(l):
    """ list[str] -> char**, NULL terminated
    """
    array = lltype.malloc(CCHARPP.TO, len(l) + 1, flavor='raw')
    for i in range(len(l)):
        array[i] = str2charp(l[i])
    array[len(l)] = lltype.nullptr(CCHARP.TO)
    return array

def free_charpp(ref):
    """ frees list of char**, NULL terminated
    """
    i = 0
    while ref[i]:
        free_charp(ref[i])
        i += 1
    lltype.free(ref, flavor='raw')

force_cast = ll2ctypes.force_cast     # cast a ptr to another with no typecheck
