
import autopath


class BasicBlock:
    def __init__(self, input_args, locals, operations, branch=None):
        self.input_args = input_args
        self.locals = locals
        self.operations = operations
        self.branch = branch
    def closeblock(self, branch):
        self.operations = tuple(self.operations)  # should no longer change
        self.branch = branch

class Variable:
    def __init__(self, pseudoname):
        self.pseudoname = pseudoname
    def __repr__(self):
        return "<%s>" % self.pseudoname

class Constant:
    def __init__(self, value):
        self.value = value
    
    def __repr__(self):
        return str(self.value)

class SpaceOperation:
    def __init__(self, opname, args, result):
        self.opname = opname
        self.args = args # list of variables
        self.result = result # <Variable/Constant instance>
    def __eq__(self, other):
        return (self.__class__ is other.__class__ and
                self.opname == other.opname and
                self.args == other.args and
                self.result == other.result)

    def __repr__(self):
        return "%s(%s) -> %s" % (self.opname, ", ".join(map(str, self.args)), self.result)

class Branch:
    def __init__(self, args=None, target=None):
        self.set(args, target)

    def set(self, args, target):
        self.args = args     # list of variables
        self.target = target # basic block instance

class ConditionalBranch:
    def __init__(self, condition=None, ifbranch=None, elsebranch=None):
        self.set(condition, ifbranch, elsebranch)

    def set(self, condition, ifbranch, elsebranch):
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

