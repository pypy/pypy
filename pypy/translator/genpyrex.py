"""
generate Pyrex files from the flowmodel. 

"""
import autopath
from pypy.tool import test
from pypy.interpreter.baseobjspace import ObjSpace
from pypy.translator.flowmodel import *
from pypy.translator.annotation import Annotator, set_type, get_type

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
        input_ann = []
        for arg, arg_type in zip(self.functiongraph.get_args(),
                                 input_arg_types):
            set_type(arg, arg_type, input_ann)
        self.annotations = a.build_annotations(input_ann)

    def emitcode(self):
        self.blockids = {}
        self.variablelocations = {}
        self.lines = []
        self.indent = 0
        self.gen_Graph()
        return "\n".join(self.lines)

    def putline(self, line):
        self.lines.append("  " * self.indent + line)

    def gen_Graph(self):
        fun = self.functiongraph
        currentlines = self.lines
        self.lines = []
        self.indent += 1 
        self.gen_BasicBlock(fun.startblock)
        self.indent -= 1
        # emit the header after the body
        functionbodylines = self.lines
        self.lines = currentlines
        inputargnames = [ self._declvar(var) for var in fun.startblock.input_args ]
        params = ", ".join(inputargnames)
        self.putline("def %s(%s):" % (fun.functionname, params))
        self.indent += 1
        #self.putline("# %r" % self.annotations)
        for var in self.variablelocations:
            if var not in fun.startblock.input_args:
                self.putline("cdef %s" % self._declvar(var))
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

    def _declvar(self, var):
        vartype = self.get_type(var)
        if vartype == int:
            ctype = "int "
        else:
            ctype = "object "
        return ctype + self.get_varname(var)

    def _str(self, obj, block):
        if isinstance(obj, Variable):
            self.variablelocations[obj] = block
            return self.get_varname(obj)
        elif isinstance(obj, Constant):
            return repr(obj.value)
        else:
            raise ValueError("Unknow class: %s" % obj.__class__)

    def gen_BasicBlock(self, block):
        if self.blockids.has_key(block):
            self.putline('cinline "goto Label%s;"' % self.blockids[block])
            return 

        blockids = self.blockids
        blockids.setdefault(block, len(blockids))

        
        self.putline('cinline "Label%s:"' % blockids[block])
        for op in block.operations:
            argnames = [self._str(arg, block) for arg in op.args]
            resultname = self._str(op.result, block)
            # XXX refactor me
            if op.opname == 'next_and_flag':
                self.putline("try:")
                self.putline("    _nextval = %s.next()" % argnames[0])
                self.putline("except StopIteration:")
                self.putline("    %s = None, 0" % resultname)
                self.putline("else:")
                self.putline("    %s = _nextval, 1" % resultname)
            elif op.opname == 'getitem':
                self.putline("%s = %s[%s]" % (resultname, argnames[0],
                                              argnames[1]))
            elif op.opname == 'newtuple':
                self.putline("%s = (%s)" % (
                    resultname, "".join([s+", " for s in argnames])))
            elif op.opname == 'newlist':
                self.putline("%s = [%s]" % (
                    resultname, "".join([s+", " for s in argnames])))
            elif op.opname == 'newdict':
                pairs = []
                for i in range(0, len(argnames), 2):
                    pairs.append("%s: %s, " % (argnames[i], argnames[i+1]))
                self.putline("%s = {%s}" % (resultname, "".join(pairs)))
            elif op.opname == 'call':
                self.putline("%s = %s(*%s, **%s)" % (resultname, argnames[0],
                                                     argnames[1], argnames[2]))
            else:
                opsymbol = self.ops[op.opname]
                arity = self.oparity[op.opname]
                assert(arity == len(op.args))
                if arity == 1 or arity == 3 or "a" <= opsymbol[0] <= "z":
                    self.putline("%s = %s(%s)" % (resultname, opsymbol,
                                                  ", ".join(argnames)))
                elif opsymbol[-1] == '=':
                    # in-place operator
                    self.putline("%s = %s; %s += %s" % (
                        resultname, argnames[0],
                        resultname, argnames[1]))
                else:
                    # infix operator
                    self.putline("%s = %s %s %s" % (resultname, argnames[0],
                                                    opsymbol, argnames[1]))

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
        if sourceargs and sourceargs != targetargs: 
            self.putline("%s = %s" % (", ".join(targetargs), ", ".join(sourceargs)))

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

