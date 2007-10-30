import py
import ctypes
from pypy.rpython.lltypesystem import lltype 

def _noresult(returntype):
    r = returntype.strip()
    if r == 'void':
        return 'void'
    elif r == 'bool':
        return 'bool false'
    elif r in 'float double'.split():
        return r + ' 0.0'
    elif r in 'ubyte sbyte ushort short uint int ulong long'.split():
        return r + ' 0'
    return r + ' null'

def llvm_implcode(entrynode):
    from pypy.translator.llvm.codewriter import DEFAULT_CCONV as cconv
    from pypy.translator.llvm.module.excsupport import entrycode, voidentrycode, raisedcode 
    returntype, entrypointname = entrynode.getdecl().split(' %', 1)
    noresult = _noresult(returntype)

    code = raisedcode % locals()
    if returntype == "void":
        code += voidentrycode % locals()
    else:
        code += entrycode % locals()

    print 'XXXXXXXXXXXXXXX'
    print returntype
    print entrypointname
    print noresult
    print entrynode.graph.returnblock.inputargs[0].concretetype
    print code
    print 'XXXXXXXXXXXXXXX'

    return code


class CtypesModule:
    """ use ctypes to create a temporary module """

    prolog = """
import ctypes
from os.path import join, dirname, realpath

_c = ctypes.CDLL(join(dirname(realpath(__file__)), "%s"))

raised = _c.__entrypoint__raised_LLVMException
raised.argtypes = []
raised.restype = ctypes.c_int

GC_get_heap_size_wrapper = _c.GC_get_heap_size
GC_get_heap_size_wrapper.argtypes = []
GC_get_heap_size_wrapper.restype = ctypes.c_int

startup_code = _c.ctypes_RPython_StartupCode
startup_code.argtypes = []
startup_code.restype = ctypes.c_int

_setup = False

class LLVMException(Exception):
    pass

def entrypoint(*args):
    global _setup
    if not _setup:
        if not startup_code():
            raise LLVMException("Failed to startup")
        _setup = True
    args = to_llargs(args)
    result = __entrypoint__(*args)
    if raised():
        raise LLVMException("Exception raised")
    return ll_to_res(result)

def identity(res):
    return res

def to_bool(res):
    return bool(res)

class Chars(ctypes.Structure):
    _fields_ = [("size", ctypes.c_int),
                ("data", ctypes.c_char * 1)]

class STR(ctypes.Structure):
    _fields_ = [("hash", ctypes.c_int),
                ("array", Chars)]

def to_str(res):
    if res:
        s = ctypes.cast(res, ctypes.POINTER(STR)).contents
        return ctypes.string_at(res + (STR.array.offset + Chars.data.offset), s.array.size)
    else:
        return None

def to_tuple(res, size, C_TYPE, action):
    if res:
        t = ctypes.cast(res, ctypes.POINTER(C_TYPE * size)).contents
        return tuple([action(ii) for ii in t])
    else:
        return None

def to_list(res, C_TYPE, action):
    if res:
        size = ctypes.cast(res, ctypes.POINTER(ctypes.c_int)).contents.value
        class Array(ctypes.Structure):
            _fields_ = [("size", ctypes.c_int),
                        ("data", C_TYPE * size)]
        array = ctypes.cast(res, ctypes.POINTER(Array)).contents
        return [action(array.data[ii]) for ii in range(size)]
    else:
        return None
"""

    epilog = """
to_llargs = %(to_llargs)s
ll_to_res = %(ll_to_res)s
__entrypoint__ = _c.__entrypoint__%(name)s
__entrypoint__.argtypes = %(args)s
__entrypoint__.restype = %(returntype)s
    """
    def __init__(self, genllvm, dllname):
        self.genllvm = genllvm
        self.dllname = dllname
        basename = self.genllvm.filename.purebasename + '_wrapper.py'
        self.modfilename = genllvm.filename.new(basename=basename)
        self.count = 0

    def create(self):
        self.file = open(str(self.modfilename), 'w')
        self.file.write(self.prolog % self.dllname)
        
        g = self.genllvm.entrynode.graph  
        name = "pypy_" + g.name

        inputargtypes = [self.to_ctype(a.concretetype) for a in g.startblock.inputargs]
        to_llargs = 'identity'
        args = '[%s]' % ', '.join(inputargtypes)

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

    def build_lltype_to_ctypes_to_res(self, T):
        from pypy.rpython.lltypesystem.rstr import STR

        if T is lltype.Bool:
            action = 'to_bool'

        elif isinstance(T, lltype.Ptr) and T.TO is STR:
            action = 'to_str'

        elif isinstance(T, lltype.Ptr) and isinstance(T.TO, lltype.Struct):
            fields = [getattr(T.TO, name) for name in T.TO._names_without_voids()]
            if fields:
                F0 = fields[0]
                _c_type, _action = self.build_lltype_to_ctypes_to_res(F0)
                action = self.create_simple_closure('res', 'to_tuple(res, %s, %s, %s)' % (len(fields), 
                                                                                          _c_type, 
                                                                                          _action))

        elif isinstance(T, lltype.Ptr) and isinstance(T.TO, lltype.Array):
            OF = T.TO.OF
            _c_type, _action = self.build_lltype_to_ctypes_to_res(OF)
            action = self.create_simple_closure('res', 'to_list(res, %s, %s)' % (_c_type, _action))

        else:
            assert not isinstance(T, lltype.Ptr)
            action = 'identity'

        c_type = self.to_ctype(T)
        return c_type, action

    def to_ctype(self, T):
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
                     }

        if isinstance(T, lltype.Ptr):
            return 'ctypes.c_void_p'
        else:
            return TO_CTYPES[T]
 
