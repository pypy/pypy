# The model produced by the flowobjspace
# this is to be used by the translator mainly.
# 
# the below object/attribute model evolved from
# a discussion in Berlin, 4th of october 2003
from __future__ import generators

class FunctionGraph:
    def __init__(self, name, startblock, return_var=None):
        self.name        = name    # function name (possibly mangled already)
        self.startblock  = startblock
        # build default returnblock
        self.returnblock = Block([return_var or Variable()])
        self.returnblock.operations = ()
        self.returnblock.exits      = ()
        self.exceptblocks = {}  # Blocks corresponding to exception results

    def getargs(self):
        return self.startblock.inputargs

    def getreturnvar(self):
        return self.returnblock.inputargs[0]

    def getexceptblock(self, exc_type):
        try:
            block = self.exceptblocks[exc_type]
        except KeyError:
            block = self.exceptblocks[exc_type] = Block([Variable()])
            block.exc_type = exc_type
            block.operations = ()
            block.exits      = ()
        return block

class Link:
    def __init__(self, args, target, exitcase=None):
        assert len(args) == len(target.inputargs), "output args mismatch"
        self.args = args           # mixed list of var/const
        self.target = target       # block
        self.exitcase = exitcase   # this is a concrete value
        self.prevblock = None      # the block this Link is an exit of

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

    def renamevariables(self, mapping):
        self.inputargs = [mapping.get(a, a) for a in self.inputargs]
        for op in self.operations:
            op.args = [mapping.get(a, a) for a in op.args]
            op.result = mapping.get(op.result, op.result)
        for link in self.exits:
            link.args = [mapping.get(a, a) for a in link.args]

    def closeblock(self, *exits):
        assert self.exits == [], "block already closed"
        self.recloseblock(*exits)
        
    def recloseblock(self, *exits):
        for exit in exits:
            exit.prevblock = self
        self.exits = exits


class Variable:
    counter = 0
    def __init__(self, name=None):
        if name is None:
            name = 'v%d' % Variable.counter
            Variable.counter += 1
        self.name = name
    def __repr__(self):
        return '%s' % self.name

class Constant:
    def __init__(self, value):
        self.value = value     # a concrete value

    def __eq__(self, other):
        return self.__class__ is other.__class__ and self.value == other.value

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash(self.value)

    def __repr__(self):
        return '(%r)' % (self.value,)

class UndefinedConstant(Constant):
    # for local variables not defined yet.
    def __init__(self):
        Constant.__init__(self, None)

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
        return "%r = %s(%s)" % (self.result, self.opname, ", ".join(map(repr, self.args)))

def uniqueitems(lst):
    "Returns a list with duplicate elements removed."
    result = []
    seen = {}
    for item in lst:
        if item not in seen:
            result.append(item)
            seen[item] = True
    return result


#_________________________________________________________
# a visitor for easy traversal of the above model

import inspect   # for getmro

class traverse:
    edgedef = {
        FunctionGraph : ('startblock',),
        Block : ('exits',),
        Link : ('target',),
        }

    def __init__(self, visitor, functiongraph):
        """ send the visitor over all (reachable) nodes. 
            the visitor needs to have either callable attributes 'visit_typename'
            or otherwise is callable itself.  
        """
        self.visitor = visitor
        self.seen = {}
        self.visit(functiongraph)

    def visit(self, node):
        if id(node) in self.seen:
            return

        # do the visit
        cls = node.__class__
        for subclass in inspect.getmro(cls):
            consume = getattr(self.visitor, "visit_" + subclass.__name__, None)
            if consume:
                break
        else:
            consume = getattr(self.visitor, 'visit', self.visitor)

        assert callable(consume), "visitor not found for %r on %r" % (cls, self.visitor)
        self.seen[id(node)] = consume(node)

        # recurse
        for dispclass, attrs in self.edgedef.items():
            for subclass in inspect.getmro(cls):
                if subclass == dispclass:
                    for attr in attrs:
                        for obj in flattenobj(getattr(node, attr)):
                            self.visit(obj)
                    return

        raise ValueError, "could not dispatch %r" % cls

def flatten(funcgraph):
    l = []
    traverse(l.append, funcgraph)
    return l

def flattenobj(*args):
    for arg in args:
        try:
            for atom in flattenobj(*arg):
                yield atom
        except: yield arg

def mkentrymap(funcgraph):
    "Returns a dict mapping Blocks to lists of Links."
    startlink = Link(funcgraph.getargs(), funcgraph.startblock)
    result = {funcgraph.startblock: [startlink]}
    def visit(link):
        if isinstance(link, Link):
            lst = result.setdefault(link.target, [])
            lst.append(link)
    traverse(visit, funcgraph)
    return result
