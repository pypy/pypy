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
        self.startblock.isstartblock = True
        # build default returnblock
        self.returnblock = Block([return_var or Variable()])
        self.returnblock.operations = ()
        self.returnblock.exits      = ()
        # block corresponding to exception results
        self.exceptblock = Block([Variable(),   # exception class
                                  Variable()])  # exception value
        self.exceptblock.operations = ()
        self.exceptblock.exits      = ()

    def getargs(self):
        return self.startblock.inputargs

    def getreturnvar(self):
        return self.returnblock.inputargs[0]

    def hasonlyexceptionreturns(self):
        try:
            return self._onlyex
        except AttributeError: 
            def visit(link):
                if isinstance(link, Link):
                    if link.target == self.returnblock: 
                        raise ValueError(link) 
            try:
                traverse(visit, self)
            except ValueError:
                self._onlyex = False 
            else:
                self._onlyex = True
            return self._onlyex 

    def show(self):
        from pypy.translator.tool.pygame.flowviewer import SingleGraphLayout
        SingleGraphLayout(self).display()

class Link:
    def __init__(self, args, target, exitcase=None):
        assert len(args) == len(target.inputargs), "output args mismatch"
        self.args = list(args)     # mixed list of var/const
        self.target = target       # block
        self.exitcase = exitcase   # this is a concrete value
        self.prevblock = None      # the block this Link is an exit of

    def __repr__(self):
        return "link from %s to %s" % (str(self.prevblock), str(self.target))

class Block:
    isstartblock = False
    
    def __init__(self, inputargs):
        self.inputargs = list(inputargs)  # mixed list of variable/const 
        self.operations = []              # list of SpaceOperation(s)
        self.exitswitch = None            # a variable or
                                          #  Constant(last_exception), see below
        self.exits      = []              # list of Link(s)

    def __str__(self):
        if self.operations:
            txt = "block@%d" % self.operations[0].offset
        else:
            txt = "codeless block"
        return txt
    
    def __repr__(self):
        txt = "%s with %d exits" % (str(self), len(self.exits))
        if self.exitswitch:
            txt = "%s(%s)" % (txt, self.exitswitch)
        return txt

    def getvariables(self):
        "Return all variables mentioned in this Block."
        result = self.inputargs[:]
        for op in self.operations:
            result += op.args
            result.append(op.result)
        return uniqueitems([w for w in result if isinstance(w, Variable)])

    def getconstants(self):
        "Return all constants mentioned in this Block."
        result = self.inputargs[:]
        for op in self.operations:
            result += op.args
        return uniqueitems([w for w in result if isinstance(w, Constant)])

    def renamevariables(self, mapping):
        for a in mapping:
            assert isinstance(a, Variable), a
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
    instances = {}
    def __init__(self, name=None):
        if name is None:
            name = 'v%d' % Variable.counter
            Variable.counter += 1
        self.name = name
        Variable.instances[name] = self
    def __repr__(self):
        return '%s' % self.name

class Constant:
    def __init__(self, value):
        self.value = value     # a concrete value
        # try to be smart about constant mutable or immutable values
        key = type(self.value), self.value  # to avoid confusing e.g. 0 and 0.0
        try:
            hash(key)
        except TypeError:
            key = id(self.value)
        self.key = key

    def __eq__(self, other):
        return self.__class__ is other.__class__ and self.key == other.key

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash(self.key)

    def __repr__(self):
        # try to limit the size of the repr to make it more readable
        r = repr(self.value)
        if (r.startswith('<') and r.endswith('>') and
            hasattr(self.value, '__name__')):
            r = '%s %s' % (type(self.value).__name__, self.value.__name__)
        elif len(r) > 30:
            r = r[:20] + '...' + r[-8:]
        return '(%s)' % r

# hack! it is useful to have UNDEFINED be an instance of Constant too.
# PyFrame then automatically uses this Constant as a marker for
# non-initialized variables.
from pypy.interpreter.eval import UNDEFINED
UndefinedConstant = UNDEFINED.__class__
UndefinedConstant.__bases__ += (Constant,)
Constant.__init__(UNDEFINED, None)

class SpaceOperation:
    def __init__(self, opname, args, result):
        self.opname = opname      # operation name
        self.args   = list(args)  # mixed list of var/const
        self.result = result      # either Variable or Constant instance
        self.offset = -1          # offset in code string, to be added later

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

class Atom:
    "NOT_RPYTHON"
    def __init__(self, name):
        self.name = name
    def __repr__(self):
        return self.name
last_exception = Atom('last_exception')
last_exc_value = Atom('last_exc_value')
# if Block().exitswitch == Constant(last_exception), it means that we are
# interested in catching the exception that the *last operation* of the
# block could raise.  The exitcases of the links are None for no exception
# or XxxError classes to catch the matching exceptions.

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

def checkgraph(graph):
    "Check the consistency of a flow graph."
    if __debug__:
        this_block = [None]
        exitblocks = {graph.returnblock: 1,   # retval
                      graph.exceptblock: 2}   # exc_cls, exc_value
        
        def visit(block):
            if isinstance(block, Block):
                this_block[0] = block
                assert bool(block.isstartblock) == (block is graph.startblock)
                if not block.exits:
                    assert block in exitblocks
                vars = {}
                resultvars = [op.result for op in block.operations]
                for v in block.inputargs + resultvars:
                    assert isinstance(v, Variable)
                    assert v not in vars, "duplicate variable %r" % (v,)
                    assert v not in vars_previous_blocks, (
                        "variable %r used in more than one block" % (v,))
                    vars[v] = True
                for op in block.operations:
                    for v in op.args:
                        assert isinstance(v, (Constant, Variable))
                        if isinstance(v, Variable):
                            assert v in vars
                if block.exitswitch is None:
                    assert len(block.exits) <= 1
                    if block.exits:
                        assert block.exits[0].exitcase is None
                elif block.exitswitch == Constant(last_exception):
                    assert len(block.operations) >= 1
                    assert len(block.exits) >= 1
                    assert block.exits[0].exitcase is None
                    for link in block.exits[1:]:
                        assert issubclass(link.exitcase, Exception)
                else:
                    assert isinstance(block.exitswitch, Variable)
                    assert block.exitswitch in vars
                for link in block.exits:
                    assert len(link.args) == len(link.target.inputargs)
                    assert link.prevblock is block
                    for v in link.args:
                        assert isinstance(v, (Constant, Variable))
                        if isinstance(v, Variable):
                            assert v in vars
                vars_previous_blocks.update(vars)

        try:
            for block, nbargs in exitblocks.items():
                this_block[0] = block
                assert len(block.inputargs) == nbargs
                assert not block.operations
                assert not block.exits

            vars_previous_blocks = {}

            traverse(visit, graph)

        except AssertionError, e:
            # hack for debug tools only
            if this_block[0] and not hasattr(e, '__annotator_block'):
                setattr(e, '__annotator_block', this_block[0])
            raise
