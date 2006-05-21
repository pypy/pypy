
""" backend generator routines
"""

from pypy.translator.js2.log import log

from pypy.rpython.lltypesystem.lltype import Signed, Unsigned, Void, Bool, Float
from pypy.rpython.lltypesystem.lltype import SignedLongLong, UnsignedLongLong

from StringIO import StringIO

class CodeGenerator(object):
    def __init__(self, out, indentstep = 4, startblock = '{', endblock = '}'):
        self._out = out
        self._indent = 0
        self._bol = True # begin of line
        self._indentstep = indentstep
        self._startblock = startblock
        self._endblock = endblock
    
    def write(self, s, indent = 0):
        indent = self._indent + (indent * self._indentstep)
        
        if self._bol:
            self._out.write(' ' * indent)

        self._out.write(s)
        self._bol = (s and s[-1] == '\n')

    def writeline(self, s=''):
        self.write(s)
        self.write('\n')

    def openblock(self):
        self.writeline(self._startblock)
        self._indent += self._indentstep

    def closeblock(self):
        self._indent -= self._indentstep
        self.writeline(self._endblock)

class Queue(object):
    def __init__(self, l, subst_table):
        self.l = l[:]
        self.subst_table = subst_table
    
    def pop(self):
        el = self.l.pop()
        return self.subst_table.get(el, el)
    
    def __getattr__(self,attr):
        return getattr(self.l, attr)
    
    def __len__(self):
        return len(self.l)

class AsmGen(object):
    """ JS 'assembler' generator routines
    """
    def __init__(self, outfile, name):
        self.outfile = outfile
        self.name = name
        self.subst_table = {}
        self.right_hand = Queue([], self.subst_table)
        self.codegenerator = CodeGenerator(outfile)
    
    def show_const(self):
        return False

    def begin_function(self, name, arglist, returntype, is_entrypoint = False, *args):
        args = ",".join([i[1] for i in arglist])
        self.codegenerator.write("function %s (%s) "%(name, args))
        self.codegenerator.openblock()
    
    def end_function(self):
        self.codegenerator.closeblock()
    
    def locals(self, loc):
        self.codegenerator.writeline("var "+",".join([i[1] for i in loc])+";")
    
    def load_arg(self, v):
        self.right_hand.append(v.name)
    
    def store_local(self, v):
        name = self.subst_table.get(v.name, v.name)
        element = self.right_hand.pop()
        if element != name:
            self.codegenerator.writeline("%s = %s;"%(name, element))
    
    def load_local(self, v):
        self.right_hand.append(v.name)
    
    def load_const(self, _type, v):
        if _type is Bool:
            if v == False:
                val = 'false'
            else:
                val = 'true'
        else:
            val = str(v)
        self.right_hand.append(val)
    
    def ret(self):
        self.codegenerator.writeline("return ( %s );"%self.right_hand.pop())
    
    def begin_namespace(self,namespace):
        pass
    
    def end_namespace(self):
        pass
    
    def begin_class(self,cl):
        raise NotImplementedError("Class support")
    
    def end_class(self):
        raise NotImplementedError("Class support")

    def emit(self, opcode, *args):
        v1 = self.right_hand.pop()
        v2 = self.right_hand.pop()
        self.right_hand.append("(%s%s%s)"%(v2, opcode, v1))

    def call(self, func):
        func_name, args = func
        real_args = ",".join([self.right_hand.pop() for i in xrange(len(args))] )
        self.right_hand.append("%s ( %s )"%(func_name, real_args))

    def branch_if(self, arg, exitcase):
        arg_name = self.subst_table.get(arg.name, arg.name)
        self.codegenerator.write("if ( %s == %s )"%(arg_name, str(exitcase).lower()))
        self.codegenerator.openblock()
    
    def branch_while(self, arg, exitcase):
        arg_name = self.subst_table.get(arg.name, arg.name)
        self.codegenerator.write("while ( %s == %s )"%(arg_name, str(exitcase).lower()))
        self.codegenerator.openblock()
    
    def branch_else(self):
        self.codegenerator.closeblock()
        self.codegenerator.write("else")
        self.codegenerator.openblock()
    
    def close_branch(self):
        self.codegenerator.closeblock()

    def label(self, *args):
        self.codegenerator.openblock()

    def branch(self, *args):
        #self . codegenerator . closeblock ()
        pass
    
    def change_name(self, from_name, to_name):
        self.subst_table[from_name.name] = to_name.name
        #pass
    
    def cast_floor(self):
        self.right_hand.append("Math.floor ( %s )"%self.right_hand.pop())
    
    #def finish ( self ):
    #    self . outfile . write ( "%r" % self . right_hand )
