"""disassembler of Python byte code into mnemonics.

XXX this only works for python-2.3 because of the linenumber 
    optimization 

"""

import autopath
import sys
import types

from pypy.tool.opcode import *
from pypy.tool.opcode import __all__ as _opcodes_all

__all__ = ["dis","pydisassemble","distb","disco"] + _opcodes_all
del _opcodes_all

class Bytecode:
    def __init__(self, disresult, bytecodeindex, oparg, lineno):
        self.disresult = disresult 
        self.index = bytecodeindex
        self.op = ord(disresult.code.co_code[self.index])
        self.name = opname[self.op]
        self.oparg = oparg
        self.lineno = lineno

    def reprargstring(self):
        """ return a string representation of any arguments. (empty for no args)"""
        oparg = self.oparg
        if oparg is None:
            return ''
        co = self.disresult.code
        op = self.op
        
        s = repr(oparg).rjust(5) + " "
        if op in hasconst:
            s += '(' + `co.co_consts[oparg]` + ')'
        elif op in hasname:
            s +=  '(' + co.co_names[oparg] + ')'
        elif op in hasjrel:
            s +=  '(to ' + repr(self.index + oparg) + ')'
        elif op in haslocal:
            s +=  '(' + co.co_varnames[oparg] + ')'
        elif op in hascompare:
            s +=  '(' + cmp_op[oparg] + ')'
        elif op in hasfree:
            if free is None:
                free = co.co_cellvars + co.co_freevars
            s +=  '(' + free[oparg] + ')'
        return s 

class DisResult:
    """ an instance of this class gets returned for disassembling 
        objects/functions/code objects whatever.    
    """
    def __init__(self, code):
        self.code = code
        self._bytecodes = []
   
    def append(self,  bytecodeindex, oparg, lineno):
        """ append bytecode anaylsis information ..."""
        bc = Bytecode(self, bytecodeindex, oparg, lineno)
        self._bytecodes.append(bc)

    def format(self):
        lastlineno = -1
        labels = findlabels(self.code.co_code)
        lines = []
        for bc in self._bytecodes:
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

def pydis(x=None):
    """pydisassemble classes, methods, functions, or code.

    With no argument, pydisassemble the last traceback.

    """
    if x is None:
        distb()
        return
    if type(x) is types.InstanceType:
        x = x.__class__
    if hasattr(x, 'im_func'):
        x = x.im_func
    if hasattr(x, 'func_code'):
        x = x.func_code
    if hasattr(x, '__dict__'):
        items = x.__dict__.items()
        items.sort()
        for name, x1 in items:
            if type(x1) in (types.MethodType,
                            types.FunctionType,
                            types.CodeType,
                            types.ClassType):
                print "Disassembly of %s:" % name
                try:
                    dis(x1)
                except TypeError, msg:
                    print "Sorry:", msg
                print
    elif hasattr(x, 'co_code'):
        return pydisassemble(x)
    #elif isinstance(x, str):
    #    return pydisassemble_string(x)
    else:
        raise TypeError, \
              "don't know how to pydisassemble %s objects" % \
              type(x).__name__

def distb(tb=None):
    """pydisassemble a traceback (default: last traceback)."""
    if tb is None:
        try:
            tb = sys.last_traceback
        except AttributeError:
            raise RuntimeError, "no last traceback to pydisassemble"
        while tb.tb_next: tb = tb.tb_next
    pydisassemble(tb.tb_frame.f_code, tb.tb_lasti)

def pydisassemble(co): 
    """return result of dissassembling a code object. """

    disresult = DisResult(co)
    code = co.co_code

    byte_increments = [ord(c) for c in co.co_lnotab[0::2]]
    line_increments = [ord(c) for c in co.co_lnotab[1::2]]
    table_length = len(byte_increments) # == len(line_increments)

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
