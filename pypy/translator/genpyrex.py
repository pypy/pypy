"""
generate Pyrex files from the flowmodel. 

"""
from pypy.interpreter.baseobjspace import ObjSpace
from pypy.objspace.flow.model import Variable, Constant, UndefinedConstant
from pypy.objspace.flow.model import mkentrymap
from pypy.translator.annrpython import RPythonAnnotator

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
        #print "operator, ", self.op.opname, operator, self.gen.ops

        args = self.argnames
        if not (operator[0] >= "a" and operator[0] <= "z"):
            if len(args) == 1:
                return "%s = %s %s" % (self.resultname, operator) + args
            elif len(args) == 2:
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
        lines = []
        args = self.argnames
        lines.append("try:")
        lines.append("  %s = %s.next()" % (self.resultname, args[0]))
        lines.append("except StopIteration:")
        lines.append("  last_exc = StopIteration")
        lines.append("else:")
        lines.append("  last_exc = None")
        return "\n".join(lines)

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

    def op_not(self):
        return "%s = not %s" % (self.resultname, self.argnames[0])

    def op_is_true(self):
        return "%s = not not %s" % (self.resultname, self.argnames[0])

    def op_exception(self):
        return "%s, last_exc = last_exc, None" % (self.resultname,)

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
        self.bindings = {}

    def annotate(self, input_arg_types):
        a = RPythonAnnotator()
        a.build_types(self.functiongraph, input_arg_types)
        self.setannotator(a)

    def setannotator(self, annotator):
        self.bindings = annotator.bindings
        self.transaction = annotator.transaction()

    def emitcode(self):
        self.blockids = {}
        #self.variablelocations = {}
        self.lines = []
        self.indent = 0
        self.gen_graph()
        return "\n".join(self.lines)

    def putline(self, line):
        for l in line.split('\n'):
            self.lines.append("  " * self.indent + l)

    def gen_graph(self):
        fun = self.functiongraph
        self.entrymap = mkentrymap(fun)
        currentlines = self.lines
        self.lines = []
        self.indent += 1 
        self.putline("last_exc = None")
        self.gen_block(fun.startblock)
        self.indent -= 1
        # emit the header after the body
        functionbodylines = self.lines
        self.lines = currentlines
        inputargnames = [ " ".join(self._paramvardecl(var)) for var in fun.getargs() ]
        params = ", ".join(inputargnames)
        self.putline("def %s(%s):" % (fun.name, params))
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
        elif var in self.bindings:
            cell = self.bindings[var]
            return self.transaction.get_type(cell)
        else:
            return None

    def get_varname(self, var):
        if self.get_type(var) in (int, bool):
            prefix = "i_"
        else:
            prefix = ""
        return prefix + var.name

    def _paramvardecl(self, var):
        vartype = self.get_type(var)
        if vartype in (int, bool):
            ctype = "int"
        else:
            ctype = "object"

        return (ctype, self.get_varname(var))

    def _vardecl(self, var):
            vartype, varname = self._paramvardecl(var)
            if vartype != "object":
                return "cdef %s %s" % (vartype, varname)
            else:
                return ""

    def _str(self, obj, block):
        if isinstance(obj, Variable):
            #self.variablelocations[obj] = block
            return self.get_varname(obj)
        elif isinstance(obj, Constant):
            value = obj.value
            try:
                name = value.__name__
            except AttributeError:
                pass
            else:
                if __builtins__.get(name) is value:
                    return name    # built-in functions represented as their name only
            if isinstance(value, int):
                value = int(value)  # cast subclasses of int (i.e. bools) to ints
            return repr(value)
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
        for op in block.operations:
            opg = Op(op, self, block)
            self.putline(opg())

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
        elif hasattr(block, 'exc_type'):
            self.putline("raise %s" % block.exc_type.__name__)
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
