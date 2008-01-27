import py
from pypy.jit.codegen.llvm.genvarorconst import Var, BoolConst, CharConst,\
    IntConst, UIntConst, FloatConst, AddrConst
from pypy.jit.codegen.llvm.compatibility import icmp, scmp, ucmp, fcmp, inttoptr,\
    trunc, zext, bitcast, inttoptr, shr_prefix, define, i1, i8, i16, i32, f64
    
def cast(osrc, dst):
    print src, '->', dst
