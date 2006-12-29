'''
Use this file to hide differences between llvm 1.x and 2.x .
'''
from pypy.jit.codegen.llvm.llvmjit import llvm_version


if llvm_version() < 2.0:
    icmp = scmp = ucmp = fcmp = 'set'
    inttoptr = trunc = zext = bitcast = 'cast'
    shr_prefix = ('', '')
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
