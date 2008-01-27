#! /usr/bin/env python
"""
A demo using the ri386 module to assemble instructions.
"""

from pypy.jit.codegen.i386.ri386 import *

class CodeBuilder(I386CodeBuilder):
    def __init__(self):
        self.buffer = []

    def write(self, data):
        for c in data:
            self.buffer.append(c)    # extend the list of characters

    def tell(self):
        return len(self.buffer)

    def getvalue(self):
        return ''.join(self.buffer)

    def as_string(self):
        lst = []
        for c in self.buffer:
            lst.append('%02x' % ord(c))
        return ' '.join(lst)

    def dump(self):
        print self.as_string()
        del self.buffer[:]


def do(insn, *args):
    s = CodeBuilder()
    getattr(s, insn)(*args)
    print '%24s   ' % (s.as_string(),),
    print insn,
    for a in args:
        print a,
    print


do('PUSH', ebp)
do('MOV', ebp, esp)
do('MOV', ecx, mem(ebp, 12))

do('LEA', eax, memSIB(None, ecx, 2, 4))

do('SUB', esp, eax)
do('ADD', esp, eax)

do('LEA', ecx, memSIB(edx, ecx, 2, 0))

do('CALL', mem(ebp, 8))

do('MOV', esp, ebp)

