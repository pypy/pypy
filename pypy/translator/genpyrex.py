"""
generate Pyrex files from the flowmodel. 

"""
from pypy.interpreter.baseobjspace import ObjSpace
from pypy.translator.flowmodel import *
from pypy.translator.annotation import Annotator, set_type, get_type

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


    def generic_op(self): 
        """Generic handler for all operators, which I don't handle explicitly"""

        return "%s = %s(%s)" % (self.resultname, self.op.opname, ", ".join(self.argnames)) 
    
    def op_next_and_flag(self):
        lines = []
        args = self.argnames
        lines.append("try:")
        lines.append("    _nextval = %s.next()" % args[0])
        lines.append("except StopIteration:")
        lines.append("    %s = None, 0" % self.resultname)
        lines.append("else:")
        lines.append("    %s = _nextval, 1" % self.resultname)
        return "\n".join(lines)

    def op_getitem(self):
        return "%s = %s[%s]" % ((self.resultname,) + tuple(self.argnames))

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

    def op_call(self):
        a = self.argnames
        return "%s = %s(*%s, **%s)" % (self.resultname, a[0], a[1], a[2])

    def op_simple_call(self):
        a = self.argnames
        return "%s = %s(%s)" % (self.resultname, a[0], ", ".join(a[1:]))

    def op_getattr(self):
        args = self.argnames
        attr = self.op.args[1]
        if isinstance(attr, Constant):  ###don't we have only the strings here?
            return "%s = %s.%s" % (self.resultname, args[0], attr.value)
        else: 
            return "%s = getattr(%s)" % (self.resultname, ", ".join(args))

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
        self.annotations = {}

    def annotate(self, input_arg_types):
        a = Annotator(self.functiongraph)
        self.annotations = a.build_types(input_arg_types)
        a.simplify_calls()

    def emitcode(self):
        self.blockids = {}
        self.variablelocations = {}
        self.lines = []
        self.indent = 0
        self.gen_Graph()
        return "\n".join(self.lines)

    def putline(self, line):
        for l in line.split('\n'):
            self.lines.append("  " * self.indent + l)

    def gen_Graph(self):
        fun = self.functiongraph
        self.entrymap = fun.mkentrymap()
        currentlines = self.lines
        self.lines = []
        self.indent += 1 
        self.gen_BasicBlock(fun.startblock)
        self.indent -= 1
        # emit the header after the body
        functionbodylines = self.lines
        self.lines = currentlines
        inputargnames = [ " ".join(self._paramvardecl(var)) for var in fun.startblock.input_args ]
        params = ", ".join(inputargnames)
        self.putline("def %s(%s):" % (fun.functionname, params))
        self.indent += 1
        #self.putline("# %r" % self.annotations)
        for var in self.variablelocations:
            if var not in fun.startblock.input_args:
                self.putline(self._vardecl(var))
        self.indent -= 1
        self.lines.extend(functionbodylines)

    def get_type(self, var):
        block = self.variablelocations.get(var)
        ann = self.annotations.get(block, [])
        return get_type(var, ann)

    def get_varname(self, var):
        if self.get_type(var) == int:
            prefix = "i_"
        else:
            prefix = ""
        return prefix + var.pseudoname

    def _paramvardecl(self, var):
        vartype = self.get_type(var)
        if vartype == int:
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
            self.variablelocations[obj] = block
            return self.get_varname(obj)
        elif isinstance(obj, Constant):
            try:
                name = obj.value.__name__
            except AttributeError:
                pass
            else:
                if __builtins__.get(name) is obj.value:
                    return name    # built-in functions represented as their name only
            return repr(obj.value)
        else:
            raise TypeError("Unknown class: %s" % obj.__class__)

    def gen_BasicBlock(self, block):
        if self.blockids.has_key(block):
            self.putline('cinline "goto Label%s;"' % self.blockids[block])
            return 

        blockids = self.blockids
        blockids.setdefault(block, len(blockids))

        #the label is only, if there are more, then are multiple references to the block
        if len(self.entrymap[block]) > 1:
            self.putline('cinline "Label%s:"' % blockids[block])
        for op in block.operations:
            opg = Op(op, self, block)
            self.putline(opg())

        self.dispatchBranch(block, block.branch)

    def dispatchBranch(self, prevblock, branch):
        method = getattr(self, "gen_" + branch.__class__.__name__)
        method(prevblock, branch)

    def gen_Branch(self, prevblock, branch):
        _str = self._str
        block = branch.target
        sourceargs = [_str(arg, prevblock) for arg in branch.args]       
        targetargs = [_str(arg, branch.target) for arg in block.input_args]
        assert(len(sourceargs) == len(targetargs))
        # get rid of identity-assignments 
        sargs, targs = [], []
        for s,t in zip(sourceargs, targetargs):
            if s != t:
                sargs.append(s) 
                targs.append(t)
        if sargs:
            self.putline("%s = %s" % (", ".join(targs), ", ".join(sargs)))

        self.gen_BasicBlock(block)    

    def gen_EndBranch(self, prevblock, branch):
        self.putline("return %s" % self._str(branch.returnvalue, prevblock))
 
    def gen_ConditionalBranch(self, prevblock, branch):
        self.putline("if %s:" % self._str(branch.condition, prevblock))
        self.indent += 1
        self.dispatchBranch(prevblock, branch.ifbranch)
        self.indent -= 1
        self.putline("else:")
        self.indent += 1
        self.dispatchBranch(prevblock, branch.elsebranch)
        self.indent -= 1

