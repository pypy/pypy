
import autopath
from pypy.tool import test
from pypy.interpreter.baseobjspace import ObjSpace
from pypy.translator.controlflow import *

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

    def emitcode(self):
        self.blockids = {}
        self.lines = []
        self.indent = 0
        self.createCodeFromGraph()
        return "\n".join(self.lines)

    def putline(self, line):
        self.lines.append("  " * self.indent + line)

    def createCodeFromGraph(self):
        fun = self.functiongraph
        inputargnames = [ var.pseudoname for var in fun.startblock.input_args ]
        params = ", ".join(inputargnames)
        self.putline("def %s(%s):" % (fun.functionname, params))
        self.indent += 1 
        self.createCodeFromBasicBlock(fun.startblock)
        self.indent -= 1

    def _str(self, obj):
        if isinstance(obj, Variable):
            return obj.pseudoname
        elif isinstance(obj, Constant):
            return repr(obj.value)
        else:
            raise ValueError("Unknow class: %s" % obj.__class__)

    def createCodeFromBasicBlock(self, block):
        if self.blockids.has_key(block):
            self.putline('cinline "goto Label%s;"' % self.blockids[block])
            return 

        blockids = self.blockids
        blockids.setdefault(block, len(blockids))
        
        self.putline('cinline "Label%s:"' % blockids[block])
        for op in block.operations:
            opsymbol = self.ops[op.opname] 
            arity = self.oparity[op.opname]
            assert(arity == len(op.args))
            argnames = [self._str(arg) for arg in op.args]
            if arity == 1 or arity == 3 or "a" <= opsymbol[0] <= "z":
                
                self.putline("%s = %s(%s)" % (op.result.pseudoname, opsymbol, ", ".join([argnames])))
            else:
                self.putline("%s = %s %s %s" % (op.result.pseudoname, argnames[0], opsymbol, argnames[1]))

        self.dispatchBranch(block.branch)

    def dispatchBranch(self, branch):
        method = getattr(self, "createCodeFrom" + branch.__class__.__name__)
        method(branch)

    def createCodeFromBranch(self, branch):
        _str = self._str
        block = branch.target
        sourceargs = [_str(arg) for arg in branch.args]       
        targetargs = [arg.pseudoname for arg in block.input_args]
        assert(len(sourceargs) == len(targetargs))
        if sourceargs: 
            self.putline("%s = %s" % (", ".join(targetargs), ", ".join(sourceargs)))

        self.createCodeFromBasicBlock(block)    

    def createCodeFromEndBranch(self, branch):
        self.putline("return %s" % self._str(branch.returnvalue))
   
 
    def createCodeFromConditionalBranch(self, branch):
        self.putline("if %s:" % self._str(branch.condition))
        self.indent += 1
        self.dispatchBranch(branch.ifbranch)
        self.indent -= 1
        self.putline("else:")
        self.indent += 1
        self.dispatchBranch(branch.elsebranch)
        self.indent -= 1

