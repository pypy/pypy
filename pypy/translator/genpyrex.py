"""
generate Pyrex files from the flowmodel. 

"""
from pypy.interpreter.baseobjspace import ObjSpace
from pypy.objspace.flow.model import Variable, Constant, UndefinedConstant
from pypy.objspace.flow.model import mkentrymap, last_exception
from pypy.translator.annrpython import RPythonAnnotator
from pypy.annotation.model import SomeCallable
from pypy.annotation.factory import isclassdef
import inspect

class Op:
    def __init__(self, operation, gen, block):
        self._str = gen._str
        self.gen = gen
        self.argnames = [self._str(arg, block) for arg in operation.args]
        self.resultname = self._str(operation.result, block)
        self.op = operation
        #op.opname

    def __call__(self):
        operator = self.gen.ops.get(self.op.opname, self.op.opname)
        args = self.argnames
        if not (operator[0] >= "a" and operator[0] <= "z"):
            if len(args) == 1:
                return "%s = %s %s" % (self.resultname, operator) + args
            elif len(args) == 2:
                #Inplace operators
                inp=['+=','-=','*=','/=','%=','&=','|=','^=','//=',
                     '<<=','>>=','**=']
                if operator in inp:
                    return "%s = %s; %s %s %s" % (self.resultname, args[0],
                                        self.resultname, operator, args[1])
                else:
                    return "%s = %s %s %s" % (self.resultname, args[0], operator, args[1])
            elif len(args) == 3 and operator == "**": #special case, have to handle it manually
                return "%s = pow(%s, %s, %s)" % (self.resultname,) + args
            else:
                raise NotImplementedError, "I don't know to handle the operator %s (arity %s)" \
                      % (operator, len(args))
        else:
            method = getattr(self, "op_%s" % operator, self.generic_op)
            return method() 

    def ispythonident(self, s):
        if s[0] not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_":
            return False
        for c in s[1:]:
            if (c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_"
                         "0123456789"):
                return False
        return True


    def generic_op(self): 
        """Generic handler for all operators, which I don't handle explicitly"""

        return "%s = %s(%s)" % (self.resultname, self.op.opname, ", ".join(self.argnames)) 
    
    def op_next(self):
        args = self.argnames
        return "%s = %s.next()" % (self.resultname, args[0])

    def op_getitem(self):
        direct = "%s = %s[%s]" % ((self.resultname,) + tuple(self.argnames))
        w_sequence, w_index = self.op.args
        tp = self.gen.get_type(w_index)
        if tp is int:
            return direct
        else:
            # the index could be a slice
            indexname = self.argnames[1]
            lines = []
            if tp is slice:  # XXX do this better
                lines.append('if 1:')
            else:
                lines.append('from types import SliceType')
                lines.append('if isinstance(%s, SliceType):' % indexname)
            lines.append('    assert %s.step is None' % indexname)
            lines.append('    %s = %s[%s.start:%s.stop]' % (self.resultname,
                                                            self.argnames[0],
                                                            indexname,
                                                            indexname))
            lines.append('else:')
            lines.append('    ' + direct)
            return "\n".join(lines)

    def op_newtuple(self):
        if self.argnames:
            return "%s = (%s,)" % (self.resultname, ", ".join(self.argnames))
        else:
            return "%s = ()" % self.resultname

    def op_newlist(self):  
        if self.argnames: 
            return "%s = [%s,]" % (self.resultname, ", ".join(self.argnames))
        else:
            return "%s = []" % self.resultname

    def op_newdict(self):
        pairs = []
        for i in range(0, len(self.argnames), 2):
            pairs.append("%s: %s, " % (self.argnames[i], self.argnames[i+1]))
        return "%s = {%s}" % (self.resultname, "".join(pairs))

    def op_newslice(self):
        a = self.argnames
        return "%s = slice(%s, %s, %s)" % (self.resultname, a[0], a[1], a[2])

    def op_call(self):
        a = self.argnames
        return "%s = %s(*%s, **%s)" % (self.resultname, a[0], a[1], a[2])

    def op_simple_call(self):
        a = self.argnames
        return "%s = %s(%s)" % (self.resultname, a[0], ", ".join(a[1:]))

    def op_setitem(self):
        a = self.argnames
        return "%s[%s] = %s" % (a[0], a[1], a[2])

    def op_getattr(self):
        args = self.argnames
        attr = self.op.args[1]
        if isinstance(attr, Constant) and self.ispythonident(attr.value):
            return "%s = %s.%s" % (self.resultname, args[0], attr.value)
        else: 
            return "%s = getattr(%s)" % (self.resultname, ", ".join(args))

    def op_setattr(self):
        args = self.argnames
        attr = self.op.args[1]
        if isinstance(attr, Constant) and self.ispythonident(attr.value):
            return "%s.%s = %s" % (args[0], attr.value, args[2])
        else:
            return "setattr(%s, %s, %s)" % args

    def op_not(self):
        return "%s = not %s" % (self.resultname, self.argnames[0])

    def op_is_true(self):
        return "%s = not not %s" % (self.resultname, self.argnames[0])

class GenPyrex:
    def __init__(self, functiongraph):
        self.functiongraph = functiongraph
        ops = {}
        oparity = {}
        for (opname, opsymbol, arity, _) in ObjSpace.MethodTable:
            ops[opname] = opsymbol
            oparity[opname] = arity
        self.ops = ops  
        self.oparity = oparity
        self.annotator = None
        self.namecache = {}

    def annotate(self, input_arg_types):
        a = RPythonAnnotator()
        a.build_types(self.functiongraph, input_arg_types)
        self.setannotator(a)

    def setannotator(self, annotator):
        self.annotator = annotator

    def emitcode(self, public=True):
        self.blockids = {}
        #self.variablelocations = {}
        self.lines = []
        self.indent = 0
        self.gen_graph(public)
        return "\n".join(self.lines)

    def putline(self, line):
        for l in line.split('\n'):
            self.lines.append("  " * self.indent + l)

    def gen_graph(self, public=True):
        fun = self.functiongraph
        self.entrymap = mkentrymap(fun)
        currentlines = self.lines
        self.lines = []
        self.indent += 1 
        self.gen_block(fun.startblock)
        self.indent -= 1
        # emit the header after the body
        functionbodylines = self.lines
        self.lines = currentlines
        inputargnames = [ " ".join(self._paramvardecl(var)) for var in fun.getargs() ]
        params = ", ".join(inputargnames)
        returntype = self.get_type(fun.getreturnvar())
        returntypename = self._gettypename(returntype)
        try:
            function_object = self.by_the_way_the_function_was   # XXX!
        except AttributeError:
            def function_object(): pass   # XXX!!!
        if public:
            # make the function visible from the outside
            # under its original name
            args = ', '.join([var.name for var in fun.getargs()])
            self.putline("def %s(%s):" % (fun.name, args))
            self.indent += 1
            self.putline("return %s(%s)" % (
                self.getfunctionname(function_object), args))
            self.indent -= 1
        # go ahead with the mandled header and body of the function
        self.putline("cdef %s %s(%s):" % (
            returntypename,
            self.getfunctionname(function_object),
            params))
        self.indent += 1
        #self.putline("# %r" % self.annotations)
        decllines = []
        missing_decl = []
        funargs = fun.getargs()
        for block in self.blockids:
            for var in block.getvariables():
                if var not in funargs:
                    decl = self._vardecl(var)
                    if decl:
                        decllines.append(decl)
                    else:
                        missing_decl.append(self.get_varname(var))
        if missing_decl:
            missing_decl.sort()
            decllines.append('# untyped variables: ' + ' '.join(missing_decl))
        decllines.sort()
        for decl in decllines:
            self.putline(decl)
        self.indent -= 1
        self.lines.extend(functionbodylines)

    def get_type(self, var):
        if isinstance(var, Constant):
            return type(var.value)
        elif self.annotator:
            return self.annotator.gettype(var)
        else:
            return None

    def get_varname(self, var):
        vartype = self.get_type(var)
        if vartype in (int, bool):
            prefix = "i_"
        elif self.annotator and vartype in self.annotator.getuserclasses():
            prefix = "p_"
        else:
            prefix = ""
        return prefix + var.name

    def _paramvardecl(self, var):
        vartype = self.get_type(var)
        ctype=self._gettypename(vartype)
        return (ctype, self.get_varname(var))

    def _gettypename(self, vartype):
        if vartype in (int, bool):
            ctype = "int"
        elif self.annotator and vartype in self.annotator.getuserclasses():
            ctype = self.getclassname(vartype)
        else:
            ctype = "object"
        return ctype

    def _vardecl(self, var):
            vartype, varname = self._paramvardecl(var)
            if vartype != "object":
                return "cdef %s %s" % (vartype, varname)
            else:
                return ""

    def getclassname(self,cls):
        assert inspect.isclass(cls)
        name = cls.__name__
        if issubclass(cls,Exception):
            return name
        return '%s__%x' % (name, id(cls))#self._hackname(cls)
    
    def getfunctionname(self,func):
        # NB. the purpose of the cache is not performance, but to ensure that
        # two methods that compare equal get the same name.
        if inspect.ismethod(func) and func.im_self is None:
            func = func.im_func  # consider unbound methods as plain functions
        try:
            return self.namecache[func]
        except KeyError:
            assert inspect.isfunction(func) or inspect.ismethod(func)
            name = '%s__%x' % (func.__name__, id(func))#self._hackname(func)
            self.namecache[func] = name
            return name
    
    def getvarname(self,var):
        assert inspect.isclass(var)
        return self._hackname(var)

    def _str(self, obj, block):
        if isinstance(obj, Variable):
            #self.variablelocations[obj] = block
            return self.get_varname(obj)
        elif isinstance(obj, Constant):
            import types
            if isinstance(obj.value,(types.ClassType,type)):
                fff=self.getclassname(obj.value)
            elif isinstance(obj.value,(types.FunctionType,
                                       types.MethodType,
                                       type)):
                fff=self.getfunctionname(obj.value)
            elif isinstance(obj.value, types.BuiltinFunctionType):
                fff=str(obj.value.__name__)
            else:
                #fff=self._hackname(obj.value)
                fff=repr(obj.value)
                if isinstance(obj.value,( int,long)):
                    fff = repr(int(obj.value))
            return fff
        else:
            raise TypeError("Unknown class: %s" % obj.__class__)

    def gen_block(self, block):
        if self.blockids.has_key(block):
            self.putline('cinline "goto Label%s;"' % self.blockids[block])
            return 

        blockids = self.blockids
        blockids.setdefault(block, len(blockids))

        #the label is only written if there are multiple refs to the block
        if len(self.entrymap[block]) > 1:
            self.putline('cinline "Label%s:"' % blockids[block])

        if block.exitswitch == Constant(last_exception):
            catch_exc = len(block.operations)-1
        else:
            catch_exc = None

        for i, op in zip(range(len(block.operations)), block.operations):
            if i == catch_exc:
                self.putline("try:")
                self.indent += 1
            opg = Op(op, self, block)
            self.putline(opg())
            if i == catch_exc:
                # generate all exception handlers
                self.indent -= 1
                exits = block.exits
                for exit in exits[1:]:
                    self.putline("except %s, last_exc_value:" %
                                 exit.exitcase.__name__)
                    self.indent += 1
                    self.putline("last_exception = last_exc_value.__class__")
                    self.gen_link(block, exit)
                    self.indent -= 1
                self.putline("else:")   # no-exception case
                self.indent += 1
                assert exits[0].exitcase is None
                self.gen_link(block, exits[0])
                self.indent -= 1
                break

        else:
            exits = block.exits
            if len(exits) == 1:
                self.gen_link(block, exits[0])
            elif len(exits) > 1:
                varname = self._str(block.exitswitch, block)
                for i in range(len(exits)):
                    exit = exits[-i-1]  # reverse order
                    cond = self._str(Constant(exit.exitcase), block)
                    if i == 0:
                        self.putline("if %s == %s:" % (varname, cond))
                    elif i < len(exits) - 1:
                        self.putline("elif %s == %s:" % (varname, cond))
                    else:
                        self.putline("else: # %s == %s" % (varname, cond))
                    self.indent += 1
                    self.gen_link(block, exit)
                    self.indent -= 1
            elif len(block.inputargs) == 2:   # exc_cls, exc_value
                exc_cls   = self._str(block.inputargs[0], block)
                exc_value = self._str(block.inputargs[1], block)
                self.putline("raise %s, %s" % (exc_cls, exc_value))
            else:
                self.putline("return %s" % self._str(block.inputargs[0], block))

    def gen_link(self, prevblock, link):
        _str = self._str
        block = link.target
        sourceargs = link.args
        targetargs = block.inputargs
        assert len(sourceargs) == len(targetargs)
        # get rid of identity-assignments and assignments of UndefinedConstant
        sargs, targs = [], []
        for s,t in zip(sourceargs, targetargs):
            if s != t and not isinstance(s, UndefinedConstant):
                sargs.append(s)
                targs.append(t)
        if sargs:
            sargs = [_str(arg, prevblock) for arg in sargs]
            targs = [_str(arg, block) for arg in targs]
            self.putline("%s = %s" % (", ".join(targs), ", ".join(sargs)))

        self.gen_block(block)

    def globaldeclarations(self,):
        """Generate the global class declaration for a group of functions."""
        if self.annotator:
            self.lines = []
            self.indent = 0
            delay_methods={}
            for cls in self.annotator.getuserclassdefinitions():
                if cls.basedef:
                    bdef="(%s)" % (self.getclassname(cls.basedef.cls))
                else:
                    bdef=""
                self.putline("cdef class %s%s:" % (self.getclassname(cls.cls),bdef))
                self.indent += 1
                empty = True
                for attr,s_value in cls.attrs.items():
                    if isinstance(s_value, SomeCallable):
                        for py_fun,fun_class in s_value.callables.items():
                            assert isclassdef(fun_class), (
                                "%r must have a classdef" % py_fun)
                            delay_methods.setdefault(fun_class,[]).append(py_fun)                          
                    else:
                        vartype=self._gettypename(s_value.knowntype)
                        self.putline("cdef public %s %s" % (vartype, attr))
                        empty = False
                list_methods=delay_methods.get(cls,[])
                for py_fun in list_methods:
                    # XXX!
                    try:
                        fun = self.annotator.translator.flowgraphs[py_fun]
                    except KeyError:
                        continue  # method present in class but never called
                    hackedargs = ', '.join([var.name for var in fun.getargs()])
                    self.putline("def %s(%s):" % (py_fun.__name__, hackedargs))
                    self.indent += 1
                    # XXX special case hack: cannot use 'return' in __init__
                    if py_fun.__name__ == "__init__":
                        statement = ""
                    else:
                        statement = "return "
                    self.putline("%s%s(%s)" % (statement,
                                               self.getfunctionname(py_fun),
                                               hackedargs))
                    self.indent -= 1
                    empty = False
                if empty:
                    self.putline("pass")
                self.indent -= 1
                self.putline("")
            return '\n'.join(self.lines)
        else:
            return ''

