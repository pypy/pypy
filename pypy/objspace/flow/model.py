# The model produced by the flowobjspace
# this is to be used by the translator mainly.
# 
# the below object/attribute model evolved from
# a discussion in Berlin, 4th of october 2003

class FunctionGraph:
    def __init__(self, name, startblock, return_var=None):
        self.name        = name    # function name (possibly mangled already)
        self.startblock  = startblock
        # build default returnblock
        self.returnblock = Block([return_var or Variable()])
        self.returnblock.operations = ()
        self.returnblock.exits      = ()
    def getargs(self):
        return self.startblock.inputargs

class Link:
    def __init__(self, args, target, exitcase=None):
        assert len(args) == len(target.inputargs), "output args mismatch"
        self.args = args           # mixed list of var/const
        self.target = target       # block
        self.exitcase = exitcase   # this is a concrete value

class Block:

    def __init__(self, inputargs):
        self.inputargs = inputargs    # mixed list of variable/const 
        self.operations = []          # list of SpaceOperation(s)
        self.exitswitch = None        # variable
        self.exits      = []          # list of Link(s)

    def getvariables(self):
        "Return all variables mentionned in this Block."
        result = self.inputargs[:]
        for op in self.operations:
            result += op.args
            result.append(op.result)
        return uniqueitems([w for w in result if isinstance(w, Variable)])

    def closeblock(self, *exits):
        assert self.exits == [], "block already closed"
        self.exits = exits

class Variable:
    counter = 0
    def __init__(self, name=None):
        if name is None:
            name = 'v%d' % Variable.counter
            Variable.counter += 1
        self.name = name
    def __repr__(self):
        return '<%s>' % self.name

class Constant:
    def __init__(self, value):
        self.value = value     # a concrete value
    def __eq__(self, other):
        return isinstance(other, Constant) and self.value == other.value
    def __ne__(self, other):
        return not (self == other)
    def __hash__(self):
        return hash(self.value)
    def __repr__(self):
        return '<%r>' % (self.value,)

class SpaceOperation:
    def __init__(self, opname, args, result): 
        self.opname = opname      # operation name
        self.args   = list(args)  # mixed list of var/const
        self.result = result      # either Variable or Constant instance
    def __eq__(self, other):
        return (self.__class__ is other.__class__ and 
                self.opname == other.opname and
                self.args == other.args and
                self.result == other.result)
    def __ne__(self, other):
        return not (self == other)
    def __hash__(self):
        return hash((self.opname,tuple(self.args),self.result))
    def __repr__(self):
        return "%r <- %s(%s)" % (self.result, self.opname, ", ".join(map(repr, self.args)))

def uniqueitems(lst):
    "Returns a list with duplicate elements removed."
    result = []
    seen = {}
    for item in lst:
        if item not in seen:
            result.append(item)
            seen[item] = True
    return result

