
import autopath


class BasicBlock:
    def __init__(self, input_args, locals, operations, branch):
        self.input_args = input_args
        self.locals = locals
        self.operations = operations
        self.branch = branch

class Variable:
    def __init__(self, pseudoname):
        self.pseudoname = pseudoname

class Constant:
    def __init__(self, value):
        self.value = value

class SpaceOperation:
    def __init__(self, opname, args, result, branch):
        self.opname = opname
        self.args = args # list of variables
        self.result = result # <Variable/Constant instance>
        self.branch = branch # branch

class Branch:
    def __init__(self, args, target):
        self.args = args     # list of variables
        self.target = target # basic block instance

class ConditionalBranch:
    def __init__(self, condition, ifbranch, elsebranch):
        self.condition = condition
        self.ifbranch = ifbranch
        self.elsebranch = elsebranch

class EndBranch:
    def __init__(self, returnvalue):
        self.returnvalue = returnvalue

class FunctionGraph:
    def __init__(self, startblock, functionname):
        self.startblock = startblock
        self.functionname = functionname

