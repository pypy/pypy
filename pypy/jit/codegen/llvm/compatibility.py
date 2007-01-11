'''
Use this file to hide differences between llvm 1.x and 2.x .
'''
from pypy.jit.codegen.llvm.llvmjit import llvm_version


if llvm_version() < 2.0:
    icmp = scmp = ucmp = fcmp = 'set'
    inttoptr = trunc = zext = bitcast = 'cast'
    shr_prefix = ('', '')
    i8  = 'ubyte'
    i16 = 'short'
    i32 = 'int'
    i64 = 'long'
    define = ''
else:   # >= 2.0
    icmp = 'icmp '
    scmp = 'icmp s'
    ucmp = 'icmp u'
    fcmp = 'fcmp o'
    inttoptr = 'inttoptr'
    trunc = 'trunc'
    zext = 'zext'
    bitcast = 'bitcast'
    shr_prefix = ('l', 'a')
    define = 'define'
    i8  = 'i8'
    i16 = 'i16'
    i32 = 'i32'
    i64 = 'i64'

f64 = 'double'
