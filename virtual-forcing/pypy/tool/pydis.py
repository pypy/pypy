"""disassembler of Python byte code into mnemonics.

XXX this only works for python-2.3 because of the linenumber 
    optimization 

"""

import autopath
import sys

from pypy.tool import stdlib_opcode
from pypy.tool.stdlib_opcode import *

__all__ = ["dis","pydisassemble","distb","disco"] + stdlib_opcode.__all__

EXTENDED_ARG = stdlib_opcode.opcodedesc.EXTENDED_ARG.index


class Bytecode:
    def __init__(self, disresult, bytecodeindex, oparg, lineno):
        self.disresult = disresult 
        self.index = bytecodeindex
        self.op = ord(disresult.code.co_code[self.index])
        self.name = opname[self.op]
        self.oparg = oparg
        self.lineno = lineno

    def __eq__(self, other):
        return (self.__class__ == other.__class__ and 
                self.index == other.index and
                self.op == other.op and
                self.name == other.name and
                self.oparg == other.oparg)

    def __ne__(self, other):
        return not (self == other)

    def reprargstring(self, space = None):
        """ return a string representation of any arguments. (empty for no args)"""
        oparg = self.oparg
        if oparg is None:
            return ''
        co = self.disresult.code
        op = self.op
        
        s = repr(oparg).rjust(5) + " "
        if op in hasconst:
            consts = self.get_consts(space)
            s += '(' + consts[oparg] + ')'
        elif op in hasname:
            s +=  '(' + co.co_names[oparg] + ')'
        elif op in hasjrel:
            s +=  '(to ' + repr(self.index + oparg) + ')'
        elif op in haslocal:
            s +=  '(' + co.co_varnames[oparg] + ')'
        elif op in hascompare:
            s +=  '(' + cmp_op[oparg] + ')'
        elif op in hasfree:
            #if free is None:
            free = co.co_cellvars + co.co_freevars
            s +=  '(' + free[oparg] + ')'
        return s 

    def get_consts(self, space=None):
        # support both real code objects and PyCode objects
        co = self.disresult.code
        if hasattr(co, "co_consts"):
            return [repr(c) for c in co.co_consts]

        if space is None:
            return [repr(c) for c in co.co_consts_w]
        
        r = lambda x: space.str_w(space.repr(x))
        return [r(c) for c in co.co_consts_w]

    def repr_with_space(self, space):
        return self.name + self.reprargstring(space)

    def __repr__(self):
        return self.name + self.reprargstring()

class DisResult:
    """ an instance of this class gets returned for disassembling 
        objects/functions/code objects whatever.    
    """
    def __init__(self, code):
        self.code = code
        self.bytecodes = []
   
    def append(self,  bytecodeindex, oparg, lineno):
        """ append bytecode anaylsis information ..."""
        bc = Bytecode(self, bytecodeindex, oparg, lineno)
        self.bytecodes.append(bc)

    def getbytecode(self, index):
        """ return bytecode instance matching the given index. """
        for bytecode in self.bytecodes:
            if bytecode.index == index:
                return bytecode
        raise ValueError, "no bytecode found on index %s in code \n%s" % (
                index, pydis(self.code))

    def format(self):
        lastlineno = -1
        labels = findlabels(self.code.co_code)
        lines = []
        for bc in self.bytecodes:
            l = []
            if bc.lineno != lastlineno:
                lastlineno = bc.lineno
                l.append("%3d" % bc.lineno)
            else:
                l.append("   ")
            l.append(bc.index in labels and ">>" or "  ")
            l.append(repr(bc.index).rjust(4)) 
            l.append(bc.name.ljust(20))
            l.append(bc.reprargstring())
            lines.append(" ".join(l))
        return "\n".join(lines)

    __repr__ = format

def pydis(co): 
    """return result of dissassembling a code object. """

    if hasattr(co, 'func_code'):
        co = co.func_code 

    if hasattr(co, 'code'):
        co = co.code 

    disresult = DisResult(co)
    code = co.co_code

    byte_increments = [ord(c) for c in co.co_lnotab[0::2]]
    line_increments = [ord(c) for c in co.co_lnotab[1::2]]
    table_length = len(byte_increments)

    lineno = co.co_firstlineno
    table_index = 0
    while (table_index < table_length
           and byte_increments[table_index] == 0):
        lineno += line_increments[table_index]
        table_index += 1
    addr = 0
    line_incr = 0

    n = len(code)
    i = 0
    extended_arg = 0
    free = None
    while i < n:
        c = code[i]
        op = ord(c)

        if i >= addr:
            lineno += line_incr
            while table_index < table_length:
                addr += byte_increments[table_index]
                line_incr = line_increments[table_index]
                table_index += 1
                if line_incr:
                    break
            else:
                addr = sys.maxint
        current_bytecodeindex = i
        i = i+1
        oparg = None
        if op >= HAVE_ARGUMENT:
            oparg = ord(code[i]) + ord(code[i+1])*256 + extended_arg
            extended_arg = 0
            i = i+2
            if op == EXTENDED_ARG:
                extended_arg = oparg*65536L
        
        disresult.append(current_bytecodeindex, oparg, lineno)
    assert disresult is not None
    return disresult

def findlabels(code):
    """Detect all offsets in a byte code which are jump targets.

    Return the list of offsets.

    """
    labels = []
    n = len(code)
    i = 0
    while i < n:
        c = code[i]
        op = ord(c)
        i = i+1
        if op >= HAVE_ARGUMENT:
            oparg = ord(code[i]) + ord(code[i+1])*256
            i = i+2
            label = -1
            if op in hasjrel:
                label = i+oparg
            elif op in hasjabs:
                label = oparg
            if label >= 0:
                if label not in labels:
                    labels.append(label)
    return labels
