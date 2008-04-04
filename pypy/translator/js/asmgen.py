
""" backend generator routines
"""

from pypy.translator.js.log import log

from pypy.objspace.flow.model import Variable

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

    def __nonzero__(self):
        return len(self.l) > 0

    def empty(self):
        self.l = []

    def __repr__(self):
        return "<Queue %s>" % (repr(self.l),)

class AsmGen(object):
    """ JS 'assembler' generator routines
    """
    def __init__(self, outfile, name):
        self.outfile = outfile
        self.name = name
        self.subst_table = {}
        self.right_hand = Queue([], self.subst_table)
        self.codegenerator = CodeGenerator(outfile)

    def close(self):
        self.outfile.close()
    
    def begin_function(self, name, arglist):
        args = ",".join([i[1] for i in arglist])
        self.codegenerator.write("function %s (%s) "%(name, args))
        self.codegenerator.openblock()
    
    def begin_method(self, name, _class, arglist):
        args = ",".join(arglist)
        self.codegenerator.write("%s.prototype.%s = function (%s)"%(_class, name, args))
        self.codegenerator.openblock()
    
    def end_function(self):
        self.codegenerator.closeblock()
        self.codegenerator.writeline("")
    
    def load_arg(self, v):
        self.right_hand.append(v.name)
    
    def store_local(self, v):
        self.store_name(v.name)
    
    def store_name(self, name):
        name = self.subst_table.get(name, name)
        element = self.right_hand.pop()
        if element != name:
            self.codegenerator.writeline("%s = %s;"%(name, element))
    
    def load_local(self, v):
        self.right_hand.append(v.name)
    
    def load_const(self, v):
        self.right_hand.append(v)

    def ret(self):
        self.codegenerator.writeline("return ( %s );"%self.right_hand.pop())
    
    def emit(self, opcode, *args):
        v1 = self.right_hand.pop()
        v2 = self.right_hand.pop()
        self.right_hand.append("(%s%s%s)"%(v2, opcode, v1))

    def call(self, func):
        func_name, args = func
        l = [self.right_hand.pop() for i in xrange(len(args))]
        l.reverse()
        real_args = ",".join(l)
        self.right_hand.append("%s ( %s )" % (func_name, real_args))

    def branch_if(self, exitcase):
        def mapping(exitc):
            if exitc in ['True', 'False']:
                return exitc.lower()
            return exitc

        arg = self.right_hand.pop()
        if hasattr(arg,'name'):
            arg_name = self.subst_table.get(arg.name, arg.name)
        else:
            arg_name = arg
        self.branch_if_string("%s == %s"%(arg_name, mapping(str(exitcase))))
        
    def branch_if_string(self, arg):
        self.codegenerator.writeline("if (%s)"%arg)
        self.codegenerator.openblock()
    
    def branch_elsif_string(self, arg):
        self.codegenerator.closeblock()
        self.codegenerator.writeline("else if (%s)"%arg)
        self.codegenerator.openblock()
    
    def branch_elsif(self, arg, exitcase):
        self.codegenerator.closeblock()
        self.branch_if(arg, exitcase, "else if")
    
    def branch_while(self, arg, exitcase):
        def mapping(exitc):
            if exitc in ['True', 'False']:
                return exitc.lower()
            return exitc
        
        arg_name = self.subst_table.get(arg.name, arg.name)
        self.codegenerator.write("while ( %s == %s )"%(arg_name, mapping(str(exitcase))))
        self.codegenerator.openblock()
    
    def branch_while_true(self):
        self.codegenerator.write("while (true)")
        self.codegenerator.openblock()
    
    def branch_else(self):
        self.right_hand.pop()
        self.codegenerator.closeblock()
        self.codegenerator.write("else")
        self.codegenerator.openblock()
    
    def close_branch(self):
        self.codegenerator.closeblock()

    def label(self, *args):
        self.codegenerator.openblock()

    def change_name(self, from_name, to_name):
        if isinstance(from_name,Variable) and isinstance(to_name,Variable):
            self.subst_table[from_name.name] = to_name.name
    
    def cast_function(self, name, num):
        # FIXME: redundancy with call
        args = [self.right_hand.pop() for i in xrange(num)]
        args.reverse()
        arg_list = ",".join(args)
        self.right_hand.append("%s ( %s )"%(name, arg_list))
    
    def prefix_op(self, st):
        self.right_hand.append("%s%s"%(st, self.right_hand.pop()))
    
    #def field(self, f_name, cts_type):
    #    pass

    def set_locals(self, loc_string):
        if loc_string != '':
            self.codegenerator.writeline("var %s;"%loc_string)

    def set_static_field(self, _type, namespace, _class, varname):
        self.codegenerator.writeline("%s.prototype.%s = %s;"%(_class, varname, self.right_hand.pop()))
    
    def set_field(self, useless_parameter, name):
        v = self.right_hand.pop()
        self.codegenerator.writeline("%s.%s = %s;"%(self.right_hand.pop(), name, v))
        #self.right_hand.append(None)
    
    def call_method(self, obj, name, signature):
        l = [self.right_hand.pop() for i in signature]
        l.reverse()
        args = ",".join(l)
        self.right_hand.append("%s.%s(%s)"%(self.right_hand.pop(), name, args))
    
    def get_field(self, name):
        self.right_hand.append("%s.%s"%(self.right_hand.pop(), name))
    
    def new(self, obj):
        #log("New: %r"%obj)
        self.right_hand.append("new %s()"%obj)
    
    def runtimenew(self):
        self.right_hand.append("new %s()" % self.right_hand.pop())
    
    def oonewarray(self, obj, length):
        self.right_hand.append("new %s(%s)" % (obj, length))

    def load_self(self):
        self.right_hand.append("this")
    
    def store_void(self):
        if not len(self.right_hand):
            return
        v = self.right_hand.pop()
        if v is not None and v.find('('):
            self.codegenerator.writeline(v+";")
    
    def begin_consts(self, name):
        # load consts, maybe more try to use stack-based features?
        self.codegenerator.writeline("%s = {};"%name)

    def new_obj(self):
        self.right_hand.append("{}")
    
    def new_list(self):
        self.right_hand.append("[]")
    
    # FIXME: will refactor later
    load_str = load_const
    
    def list_setitem(self):
        item = self.right_hand.pop()
        value = self.right_hand.pop()
        lst = self.right_hand.pop()
        self.right_hand.append("%s[%s]=%s"%(lst, item, value))
    
    def list_getitem(self):
        item = self.right_hand.pop()
        lst = self.right_hand.pop()
        self.right_hand.append("%s[%s]"%(lst, item))
    
    def load_void(self):
        self.right_hand.append("undefined")

    def load_void_obj(self):
        self.right_hand.append("{}")
    
    def begin_try(self):
        self.codegenerator.write("try ")
        self.codegenerator.openblock()
    
    def catch(self):
        self.codegenerator.closeblock()
        self.codegenerator.write("catch (exc)")
        self.codegenerator.openblock()
    
    def begin_for(self):
        self.codegenerator.writeline("var block = 0;")
        self.codegenerator.write("for(;;)")
        self.codegenerator.openblock()
        self.codegenerator.write("switch(block)")
        self.codegenerator.openblock()
    
    def write_case(self, num):
        self.codegenerator.writeline("case %d:"%num)
    
    def jump_block(self, num):
        self.codegenerator.writeline("block = %d;"%num)
        self.codegenerator.writeline("break;")
    
    def end_for(self):
        self.codegenerator.closeblock()
        self.codegenerator.closeblock()
    
    def inherits(self, subclass_name, parent_name):
        self.codegenerator.writeline("inherits(%s,%s);"%(subclass_name, parent_name))
    
    def throw(self, var):
        self.throw_real(var.name)
    
    def throw_real(self, s):
        self.codegenerator.writeline("throw(%s);"%s)

    def clean_stack(self):
        self.right_hand.empty()
