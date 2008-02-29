" THIS IS ONLY FOR TESTING "

import py
import ctypes
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rpython.lltypesystem.rstr import STR

class CtypesModule:
    """ use ctypes to create a temporary module """

    prolog = """
import ctypes
from os.path import join, dirname, realpath

_c = ctypes.CDLL(join(dirname(realpath(__file__)), "%s"))

rpyexc_occured = _c.pypy_rpyexc_occured
rpyexc_occured.argtypes = []
rpyexc_occured.restype = ctypes.c_byte

rpyexc_clear = _c.pypy_rpyexc_clear
rpyexc_clear.argtypes = []
rpyexc_clear.restype = None

rpyexc_fetch_type = _c.pypy_rpyexc_fetch_type
rpyexc_fetch_type.argtypes = []
rpyexc_fetch_type.restype = ctypes.c_void_p

if hasattr(_c, 'GC_get_heap_size'):
    GC_get_heap_size_wrapper = _c.GC_get_heap_size
    GC_get_heap_size_wrapper.argtypes = []
    GC_get_heap_size_wrapper.restype = ctypes.c_int

startup_code = _c.ctypes_RPython_StartupCode
startup_code.argtypes = []
startup_code.restype = ctypes.c_int

_setup = False

def entrypoint(*args):
    global _setup
    if not _setup:
        if not startup_code():
            raise Exception("Failed to startup")
        _setup = True
    else:
        rpyexc_clear()
    args = [f(a) for a, f in zip(args, to_llargs)]
    result = __entrypoint__(*args)
    if rpyexc_occured():
        exc = rpyexc_fetch_type()
        return {'value':to_exception_type(exc), 'type':'exceptiontypename'} 
    return ll_to_res(result)

def identity(res):
    return res

def from_str(arg):
    class Chars(ctypes.Structure):
        _fields_ = [("size", ctypes.c_int),
                    ("data", ctypes.c_byte * len(arg))]
    class STR(ctypes.Structure):
        _fields_ = [("hash", ctypes.c_int),
                    ("chars", Chars)]
    s = STR()
    s.hash = 0
    s.chars.size = len(arg)
    for ii in range(len(arg)):
        s.chars.data[ii] = ord(arg[ii])
    return ctypes.addressof(s)

def to_r_uint(res):
    return {'type':'r_uint', 'value':long(res)}

def to_r_longlong(res):
    return {'type':'r_longlong', 'value':long(res)}

def to_r_ulonglong(res):
    return {'type':'r_ulonglong', 'value':long(res)}

def to_str(res):
    class Chars(ctypes.Structure):
        _fields_ = [("size", ctypes.c_int),
                    ("data", ctypes.c_char * 1)]

    class STR(ctypes.Structure):
        _fields_ = [("hash", ctypes.c_int),
                    ("array", Chars)]

    if res:
        s = ctypes.cast(res, ctypes.POINTER(STR)).contents
        return ctypes.string_at(res + (STR.array.offset + Chars.data.offset), s.array.size)
    else:
        return None

def struct_to_tuple(res, C_TYPE_actions):
    if res:
        class S(ctypes.Structure):
            _fields_ = [("item%%s" %% ii, C_TYPE) for ii, (C_TYPE, _) in enumerate(C_TYPE_actions)]        
        s = ctypes.cast(res, ctypes.POINTER(S)).contents
        items = [action(getattr(s, 'item%%s' %% ii)) for ii, (_, action) in enumerate(C_TYPE_actions)]
        return {'type':'tuple', 'value':tuple(items)}
    else:
        return None

def list_to_array(res, action):
    if res:
        class List(ctypes.Structure):
            _fields_ = [("length", ctypes.c_int),
                        ("items", ctypes.c_void_p)]
        list = ctypes.cast(res, ctypes.POINTER(List)).contents
        size = list.length
        return action(list.items, size)
    else:
        return None

def array_to_list(res, C_TYPE, action, size=-1):
    if res:
        if size == -1:
            size = ctypes.cast(res, ctypes.POINTER(ctypes.c_int)).contents.value
        class Array(ctypes.Structure):
            _fields_ = [("size", ctypes.c_int),
                        ("data", C_TYPE * size)]
        array = ctypes.cast(res, ctypes.POINTER(Array)).contents
        return [action(array.data[ii]) for ii in range(size)]
    else:
        return None

def to_exception_type(addr):
    addr_str = ctypes.cast(addr+12, ctypes.POINTER(ctypes.c_int)).contents.value
    size = ctypes.cast(addr_str, ctypes.POINTER(ctypes.c_int)).contents.value - 1
    name = ctypes.string_at(addr_str+4, size)
    return name
"""

    epilog = """
__entrypoint__ = _c.pypy_%(name)s

# %(RT)r
to_llargs = %(to_llargs)s
__entrypoint__.argtypes = %(args)s

# %(ARGS)r
ll_to_res = %(ll_to_res)s
__entrypoint__.restype = %(returntype)s
    """
    
    TO_CTYPES = {lltype.Bool: "ctypes.c_byte",
                 lltype.SingleFloat: "ctypes.c_float",
                 lltype.Float: "ctypes.c_double",
                 lltype.Char: "ctypes.c_char",
                 lltype.Signed: "ctypes.c_int",
                 lltype.Unsigned: "ctypes.c_uint",
                 lltype.SignedLongLong: "ctypes.c_longlong",
                 lltype.UnsignedLongLong: "ctypes.c_ulonglong",
                 lltype.Void: None,
                 lltype.UniChar: "ctypes.c_uint",
                 rffi.SIGNEDCHAR: "ctypes.c_char",
                 rffi.UCHAR: "ctypes.c_ubyte"
                 }

    def __init__(self, genllvm, dllname):
        self.genllvm = genllvm
        self.dllname = dllname
        basename = self.genllvm.entry_name + '_wrapper.py'
        self.modfilename = genllvm.filename.new(basename=basename)
        self.count = 0

    def create(self):
        self.file = open(str(self.modfilename), 'w')
        self.file.write(self.prolog % self.dllname)
        
        g = self.genllvm.entrynode.graph  
        name = self.genllvm.entry_name

        ARGS = [a.concretetype for a in g.startblock.inputargs]
        inputargtypes, to_llargs = self.build_args_to_ctypes_to_lltype(ARGS)

        args = '[%s]' % ', '.join(inputargtypes)
        to_llargs = '[%s]' % ', '.join(to_llargs)

        RT = g.returnblock.inputargs[0].concretetype
        returntype, ll_to_res = self.build_lltype_to_ctypes_to_res(RT)
        
        self.file.write(self.epilog % locals())
        self.file.close()
        return self.modfilename.purebasename

    def create_simple_closure(self, args, code):
        name = 'tmpfunction_%s' % self.count
        self.count += 1
        self.file.write('\n')
        self.file.write('def %s(%s): return %s' % (name, args, code))
        self.file.write('\n')
        return name

    def build_args_to_ctypes_to_lltype(self, ARGS):
        ctype_s = []
        actions = []

        for A in ARGS:
            ctype_s.append(self.to_ctype(A))

            if A is lltype.UniChar:
                action = 'ord'

            elif A is lltype.Float:
                action = 'ctypes.c_double'

            elif isinstance(A, lltype.Ptr) and A.TO is STR:
                action = 'from_str'
            else:
                assert A in self.TO_CTYPES
                action = 'identity'

            actions.append(action)

        return ctype_s, actions

    def build_lltype_to_ctypes_to_res(self, T):
        if T is lltype.Bool:
            action = 'bool'

        elif T is rffi.UCHAR:
            action = "chr"
        elif T is lltype.UniChar:
            action = 'unichr'

        elif T is lltype.Unsigned:
            action = 'to_r_uint'

        elif T is lltype.SignedLongLong:
            action = 'to_r_longlong'

        elif T is lltype.UnsignedLongLong:
            action = 'to_r_ulonglong'

        elif isinstance(T, lltype.Ptr) and T.TO is STR:
            action = 'to_str'

        elif isinstance(T, lltype.Ptr) and isinstance(T.TO, lltype.Struct):
            S = T.TO
            fields = [(getattr(S, name), name) for name in S._names_without_voids()]
            if fields:
                F0, name = fields[0]
                if name.startswith("item"):
                    ctype_actions = "%s" % [self.build_lltype_to_ctypes_to_res(f[0]) for f in fields]
                    ctype_actions = ctype_actions.replace("'", "")
                    action = self.create_simple_closure('res', 'struct_to_tuple(res, %s)' % (ctype_actions))
                elif name == "length" and fields[1][1] == "items":
                    _c_type, _action = self.build_lltype_to_ctypes_to_res(fields[1][0])
                    action = self.create_simple_closure('res', 'list_to_array(res, %s)' % (_action))
                else:
                    py.test.skip("unspported struct %r" % S)

        elif isinstance(T, lltype.Ptr) and isinstance(T.TO, lltype.Array):
            OF = T.TO.OF
            _c_type, _action = self.build_lltype_to_ctypes_to_res(OF)
            action = self.create_simple_closure('res, size=-1', 'array_to_list(res, %s, %s, size=size)' % (_c_type, _action))

        else:
            assert not isinstance(T, lltype.Ptr)
            action = 'identity'

        c_type = self.to_ctype(T)
        return c_type, action

    def to_ctype(self, T):
        if isinstance(T, lltype.Ptr):
            return 'ctypes.c_void_p'
        else:
            return self.TO_CTYPES[T]
 
