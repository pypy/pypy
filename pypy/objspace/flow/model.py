# The model produced by the flowobjspace
# this is to be used by the translator mainly.
# 
# the below object/attribute model evolved from
# a discussion in Berlin, 4th of october 2003
from __future__ import generators
from pypy.tool.uid import Hashable

"""
    memory size before and after introduction of __slots__
    using targetpypymain with -no-c

    slottified          annotation  ann+genc
    -------------------------------------------
    nothing             321 MB      442 MB
    Var/Const/SpaceOp   205 MB      325 MB
    + Link              189 MB      311 MB
    + Block             185 MB      304 MB
    
    Dropping Variable.instances and using
    just an instancenames dict brought
    annotation down to 160 MB.
    Computing the Variable.renamed attribute
    and dropping Variable.instancenames
    got annotation down to 109 MB.
    Probably an effect of less fragmentation.
"""

COUNTOBJECTS = False

__metaclass__ = type

class Missing:
    pass

class Slotted:
    __slots__ = []
    from copy_reg import _slotnames
    _slotnames = classmethod(_slotnames)
    def __getstate__(self):
        names = self._slotnames()
        return tuple([getattr(self, name, Missing) for name in names])
    def __setstate__(self, args):
        names = self._slotnames()
        [setattr(self, name, value) for name, value in zip(names, args)
         if value is not Missing]
        
class FunctionGraph(Slotted):
    __slots__ = """func source name startblock returnblock exceptblock""".split()
    
    def __init__(self, name, startblock, return_var=None):
        self.name        = name    # function name (possibly mangled already)
        self.startblock  = startblock
        self.startblock.isstartblock = True
        # build default returnblock
        self.returnblock = Block([return_var or Variable()])
        self.returnblock.operations = ()
        self.returnblock.exits      = ()
        # block corresponding to exception results
        self.exceptblock = Block([Variable('etype'),   # exception class
                                  Variable('evalue')])  # exception value
        self.exceptblock.operations = ()
        self.exceptblock.exits      = ()

    def getargs(self):
        return self.startblock.inputargs

    def getreturnvar(self):
        return self.returnblock.inputargs[0]

##    def hasonlyexceptionreturns(self):
##        try:
##            return self._onlyex
##        except AttributeError: 
##            def visit(link):
##                if isinstance(link, Link):
##                    if link.target == self.returnblock: 
##                        raise ValueError(link) 
##            try:
##                traverse(visit, self)
##            except ValueError:
##                self._onlyex = False 
##            else:
##                self._onlyex = True
##            return self._onlyex 

    def show(self):
        from pypy.translator.tool.graphpage import SingleGraphPage
        SingleGraphPage(self).display()

class Link(Slotted):

    __slots__ = """args target exitcase prevblock
                last_exception last_exc_value""".split()

    def __init__(self, args, target, exitcase=None):
        assert len(args) == len(target.inputargs), "output args mismatch"
        self.args = list(args)     # mixed list of var/const
        self.target = target       # block
        self.exitcase = exitcase   # this is a concrete value
        self.prevblock = None      # the block this Link is an exit of

        # exception passing vars
        self.last_exception = None
        self.last_exc_value = None

    # right now only exception handling needs to introduce new variables on the links
    def extravars(self, last_exception=None, last_exc_value=None):
        self.last_exception = last_exception
        self.last_exc_value = last_exc_value

    def getextravars(self):
        "Return the extra vars created by this Link."
        result = []
        if isinstance(self.last_exception, Variable):
            result.append(self.last_exception)
        if isinstance(self.last_exc_value, Variable):
            result.append(self.last_exc_value)
        return result

    def copy(self, rename=lambda x: x):
        newargs = [rename(a) for a in self.args]
        newlink = Link(newargs, self.target, self.exitcase)
        newlink.prevblock = self.prevblock
        newlink.last_exception = rename(self.last_exception)
        newlink.last_exc_value = rename(self.last_exc_value)
        return newlink

    def __repr__(self):
        return "link from %s to %s" % (str(self.prevblock), str(self.target))

class Block(Slotted):
    __slots__ = """isstartblock inputargs operations exitswitch
                exits exc_handler""".split()
    
    def __init__(self, inputargs):
        self.isstartblock = False
        self.inputargs = list(inputargs)  # mixed list of variable/const 
        self.operations = []              # list of SpaceOperation(s)
        self.exitswitch = None            # a variable or
                                          #  Constant(last_exception), see below
        self.exits      = []              # list of Link(s)

        self.exc_handler = False          # block at the start of exception handling code

    def at(self):
        if self.operations:
            return "@%d" % self.operations[0].offset
        else:
            return ""

    def __str__(self):
        if self.operations:
            txt = "block@%d" % self.operations[0].offset
        else:
            txt = "codeless block"
        if self.exc_handler:
            txt = txt +" EH"
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


class Variable(Slotted):
    __slots__ = ["_name", "concretetype"]

    countall = 0
    if COUNTOBJECTS:
        countmax = 0
        countcurr = 0

    def name(self):
        name = self._name
        if type(name) is int:
            name = 'v%d' % name
        return name
    name = property(name)

    def renamed(self):
        return isinstance(self._name, str)
    renamed = property(renamed)
    
    def __init__(self, name=None):
        self._name = Variable.countall
        Variable.countall += 1
        if COUNTOBJECTS:
            Variable.countcurr += 1
            Variable.countmax = max(Variable.countmax, Variable.countcurr)
        if name is not None:
            self.rename(name)

    if COUNTOBJECTS:
        def __del__(self):
            Variable.countcurr -= 1

    def __repr__(self):
        return '%s' % self.name

    def rename(self, name):
        if self.renamed:
            return
        if isinstance(name, Variable):
            if not name.renamed:
                return
            name = name.name[:name.name.rfind('_')]
        # remove strange characters in the name
        name = ''.join([c for c in name if c.isalnum() or c == '_'])
        if not name:
            return
        if '0' <= name[0] <= '9':
            name = '_' + name
        self._name = name + '_' + self.name[1:]


class Constant(Hashable, Slotted):
    __slots__ = ["concretetype"]


class SpaceOperation(Slotted):
    __slots__ = "opname args result offset".split()

    def __init__(self, opname, args, result, offset=-1):
        self.opname = opname      # operation name
        self.args   = list(args)  # mixed list of var/const
        self.result = result      # either Variable or Constant instance
        self.offset = offset      # offset in code string

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
    def __init__(self, name):
        self.name = name
    def __repr__(self):
        return self.name

last_exception = Atom('last_exception')
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

                def definevar(v, only_in_link=None):
                    assert isinstance(v, Variable)
                    assert v not in vars, "duplicate variable %r" % (v,)
                    assert v not in vars_previous_blocks, (
                        "variable %r used in more than one block" % (v,))
                    vars[v] = only_in_link

                def usevar(v, in_link=None):
                    assert v in vars
                    if in_link is not None:
                        assert vars[v] is None or vars[v] is in_link

                for v in block.inputargs:
                    definevar(v)

                for op in block.operations:
                    for v in op.args:
                        assert isinstance(v, (Constant, Variable))
                        if isinstance(v, Variable):
                            usevar(v)
                        else:
                            assert v.value is not last_exception
                            #assert v.value != last_exc_value
                    definevar(op.result)

                exc_links = {}
                if block.exitswitch is None:
                    assert len(block.exits) <= 1
                    if block.exits:
                        assert block.exits[0].exitcase is None
                elif block.exitswitch == Constant(last_exception):
                    assert len(block.operations) >= 1
                    assert len(block.exits) >= 2
                    assert block.exits[0].exitcase is None
                    for link in block.exits[1:]:
                        assert issubclass(link.exitcase, Exception)
                        exc_links[link] = True
                else:
                    assert isinstance(block.exitswitch, Variable)
                    assert block.exitswitch in vars

                for link in block.exits:
                    assert len(link.args) == len(link.target.inputargs)
                    assert link.prevblock is block
                    exc_link = link in exc_links
                    if exc_link:
                        for v in [link.last_exception, link.last_exc_value]:
                            assert isinstance(v, (Variable, Constant))
                            if isinstance(v, Variable):
                                definevar(v, only_in_link=link)
                    else:
                        assert link.last_exception is None
                        assert link.last_exc_value is None
                    for v in link.args:
                        assert isinstance(v, (Constant, Variable))
                        if isinstance(v, Variable):
                            usevar(v, in_link=link)
                            if exc_link:
                                assert v != block.operations[-1].result
                        #else:
                        #    if not exc_link:
                        #        assert v.value is not last_exception
                        #        #assert v.value != last_exc_value
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
            #graph.show()  # <== ENABLE THIS TO SEE THE BROKEN GRAPH
            if this_block[0] and not hasattr(e, '__annotator_block'):
                setattr(e, '__annotator_block', this_block[0])
            raise
