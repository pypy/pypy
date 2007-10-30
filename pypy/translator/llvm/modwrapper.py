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

TO_CTYPES = {lltype.Bool: "ctypes.c_int",
             lltype.SingleFloat: "ctypes.c_float",
             lltype.Float: "ctypes.c_double",
             lltype.Char: "ctypes.c_char",
             lltype.Signed: "ctypes.c_int",
             lltype.Unsigned: "ctypes.c_uint",
             lltype.SignedLongLong: "ctypes.c_longlong",
             lltype.UnsignedLongLong: "ctypes.c_ulonglong",
             lltype.Void: None
             }

def to_ctype(T):
    if isinstance(T, lltype.Ptr):
        return "ctypes.c_void_p"
    else:
        return TO_CTYPES[T]

def build_lltype_to_ctypes_to_res(T):
    identity = """
def tores(res):
    return res
    """

    to_bool = """
def tores(res):
    return bool(res)
    """

    to_str = """

class Chars(ctypes.Structure):
    _fields_ = [("size", ctypes.c_int),
                ("data", ctypes.c_char * 1)]

class STR(ctypes.Structure):
    _fields_ = [("hash", ctypes.c_int),
                ("array", Chars)]

def tores(res):
    if res:
        s = ctypes.cast(res, ctypes.POINTER(STR)).contents
        return ctypes.string_at(res + (STR.array.offset + Chars.data.offset), s.array.size)
    else:
        return None
    """

    to_tuple = """
def tores(res):
    if res:
        t = ctypes.cast(res, ctypes.POINTER(%s * %s)).contents
        return tuple(t)
    else:
        return None
    """

    to_list = """

def tores(res):
    if res:
        size = ctypes.cast(res, ctypes.POINTER(ctypes.c_int)).contents.value
        class Array(ctypes.Structure):
            _fields_ = [("size", ctypes.c_int),
                        ("data", %s * size)]
        array = ctypes.cast(res, ctypes.POINTER(Array)).contents
        return list(array.data)
    else:
        return None
    """

    from pypy.rpython.lltypesystem.rstr import STR

    if T is lltype.Bool:
        return to_bool
    elif isinstance(T, lltype.Ptr) and T.TO is STR:
        return to_str
    elif isinstance(T, lltype.Ptr) and isinstance(T.TO, lltype.Struct):
        fields = [getattr(T.TO, name) for name in T.TO._names_without_voids()]
        if fields:
            F0 = fields[0]
            for F in fields[1:]:
                if F0 is not F:
                    raise Exception("struct must be of same kind")
            if F0 not in TO_CTYPES:
                raise Exception("struct must be of primitve type")
            
            return to_tuple % (len(fields), TO_CTYPES[F0])
        
    elif isinstance(T, lltype.Ptr) and isinstance(T.TO, lltype.Array):
        OF = T.TO.OF
        if OF not in TO_CTYPES:
            raise Exception("struct must be of primitve type")
            
        return to_list % TO_CTYPES[OF]
    else:
        return identity

def write_ctypes_module(genllvm, dllname):
    """ use ctypes to create a temporary module """

    template = """
import ctypes
from os.path import join, dirname, realpath
_c = ctypes.CDLL(join(dirname(realpath(__file__)), "%(dllname)s"))

_setup = False

class LLVMException(Exception):
    pass

%(name)s = _c.__entrypoint__%(name)s
%(name)s.argtypes = %(args)s
%(name)s.restype = %(returntype)s

%(name)s_raised = _c.__entrypoint__raised_LLVMException
%(name)s_raised.argtypes = []
%(name)s_raised.restype = ctypes.c_int

GC_get_heap_size_wrapper = _c.GC_get_heap_size
GC_get_heap_size_wrapper.argtypes = []
GC_get_heap_size_wrapper.restype = ctypes.c_int

startup_code = _c.ctypes_RPython_StartupCode
startup_code.argtypes = []
startup_code.restype = ctypes.c_int

def %(name)s_wrapper(*args):
    global _setup
    if not _setup:
        if not startup_code():
            raise LLVMException("Failed to startup")
        _setup = True
    result = %(name)s(*args)
    if %(name)s_raised():
        raise LLVMException("Exception raised")
    return tores(result)
"""

    basename = genllvm.filename.purebasename + '_wrapper.py'
    modfilename = genllvm.filename.new(basename = basename)
    name = genllvm.entrynode.ref.strip("%")
    
    g = genllvm.entrynode.graph  
    rt = g.returnblock.inputargs[0].concretetype
    returntype = to_ctype(rt)
    inputargtypes = [TO_CTYPES[a.concretetype] for a in g.startblock.inputargs]
    args = '[%s]' % ", ".join(inputargtypes)

    modfilename.write(template % locals() + build_lltype_to_ctypes_to_res(rt))

    return modfilename.purebasename
