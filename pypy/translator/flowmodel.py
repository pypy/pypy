"""
the objectmodel on which the FlowObjSpace and the translator 
interoperate. While the FlowObjSpace may (and does) use subclasses
of the classes in this module the translator parts will only look 
into the attributes defined here. 
"""
class FlowNode:
    def getedges(self):
        raise NotImplementedError, "Abstract base class"

    def flatten(self):
        nodedict = self.visit(lambda x: None)
        return nodedict.keys()

    def visit(self, fn, _visited = None):
        if _visited is None:
            _visited = {}
        _visited[self] = fn(self)
        for targetnode in self.getedges():
            if not _visited.has_key(targetnode):
                targetnode.visit(fn, _visited)
        return _visited

class BasicBlock(FlowNode):
    def __init__(self, input_args, locals, operations, branch=None):
        self.input_args = input_args
        self.locals = locals
        self.operations = operations
        self.branch = branch

    def getedges(self):
        return [self.branch]

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

    def __eq__(self, other):
        return type(other) is type(self) and self.value == other.value

    def __hash__(self):
        return hash(self.value)

    def __repr__(self):
        return str(self.value)

class SpaceOperation:
    def __init__(self, opname, args, result):
        self.opname = opname
        self.args = args     # list of variables
        self.result = result # <Variable/Constant instance>

    def __eq__(self, other):
        return (self.__class__ is other.__class__ and
                self.opname == other.opname and
                self.args == other.args and
                self.result == other.result)

    def __hash__(self):
        return hash((self.opname,tuple(self.args),self.result))
        

    def __repr__(self):
        return "%s(%s) -> %s" % (self.opname, ", ".join(map(str, self.args)), self.result)

class Branch(FlowNode):
    def __init__(self, args=None, target=None):
        self.set(args, target)

    def getedges(self):
        return [self.target]

    def set(self, args, target):
        self.args = args     # list of variables
        self.target = target # basic block instance

class ConditionalBranch(FlowNode):
    def __init__(self, condition=None, ifbranch=None, elsebranch=None):
        self.set(condition, ifbranch, elsebranch)

    def getedges(self):
        return [self.ifbranch, self.elsebranch]

    def set(self, condition, ifbranch, elsebranch):
        self.condition = condition
        self.ifbranch = ifbranch
        self.elsebranch = elsebranch

class EndBranch(FlowNode):
    def __init__(self, returnvalue):
        self.returnvalue = returnvalue

    def getedges(self):
        return []

class FunctionGraph:
    def __init__(self, startblock, functionname):
        self.startblock = startblock
        self.functionname = functionname

    def get_args(self):
        return self.startblock.input_args

    def flatten(self):
        return self.startblock.flatten()

    def mkentrymap(self):
        """Create a map from nodes in the graph to back edge lists"""
        entrymap = { self.startblock: []}
        for node in self.flatten():
            for edge in node.getedges():
                entrymap.setdefault(edge, []).append(node)
        return entrymap
