"""
Graph-to-low-level transformer for C/Assembler code generators.
"""

from __future__ import generators
from pypy.objspace.flow.model import Variable, Block, Link, traverse
from pypy.translator.simplify import remove_direct_loops


class LLVar:
    "A variable in the low-level language."
    def __init__(self, type, name):
        self.type = type   # low-level type in any format, e.g. a C type name
        self.name = name

class LLConst(LLVar):
    "A global, constant, preinitialized variable."
    def __init__(self, type, name, initexpr=None, to_declare=False):
        LLVar.__init__(self, type, name)
        self.initexpr = initexpr
        self.to_declare = to_declare

class LLOp(object):
    "A low-level operation.  Must be subclassed, one subclass per operation."
    can_fail = False  # boolean attribute: should an errtarget be generated?

    def __init__(self, args, errtarget=None):
        self.args = args            # list of LLVars
        self.errtarget = errtarget  # label to jump to in case of error

    def optimize(self, typer):
        """If the operation can be statically optimized, this method can
        return a list [new-llvars-for-result] and optionally generate
        replacement operations by calling typer.operation() or
        typer.convert()."""
        return None

class TypingError(Exception):
    pass

class CannotConvert(Exception):
    pass


# ____________________________________________________________
#
# below, a 'typeset' is an object with the following methods/attributes:
#
#   def gethltype(self, var_or_const)
#       Return the high-level type of a var or const.
#
#   def represent(self, hltype)
#       Return a list of LLTypes that together implement the high-level type.
#
#   lloperations = {
#       'opname': {
#           (tuple-of-hltypes): subclass-of-LLOp,
#           ... },
#       ...}
#       This dict contains the known signatures of each space operation.
#       Special opnames:
#         'caseXXX'    v : fails (i.e. jump to errlabel) if v is not XXX
#
#   rawoperations = {
#       'opname': subclass-of-LLOp,
#       ...}
#       Low-level-only operations on raw LLVars (as opposed to lloperations,
#       which are on flow.model.Variables as found in SpaceOperations):
#         'goto'          : fails unconditionally (i.e. jump to errlabel)
#         'move'    x y   : raw copy of the LLVar x to the LLVar y
#         'copy' x1 x2.. y1 y2...: raw copy x1 to y1, x2 to y2, etc. and incref
#         'incref'  x y...: raw incref of the LLVars x, y, etc.
#         'decref'  x y...: raw decref of the LLVars x, y, etc.
#         'xdecref' x y...: raw xdecref of the LLVars x, y, etc.
#         'comment'       : comment (text is in errtarget)
#         'return'  x y...: return the value stored in the LLVars
#
#   def getconvertion(self, hltype1, hltype2):
#       If it is possible to convert from 'hltype1' to 'hltype2', this
#       function should return the conversion operation (as a subclass of
#       LLOp).  Otherwise, it should raise CannotConvert.
#
#   def typemismatch(self, opname, hltypes):
#       Called when no exact match is found in lloperations.  This function
#       can extend lloperations[opname] to provide a better match for hltypes.
#       Partial matches (i.e. ones requiring conversions) are only considered
#       after this function returns.
# ____________________________________________________________


class LLTyper:
    "Base class for type-oriented low-level generators."

    def __init__(self, typeset):
        self.gethltype    = typeset.gethltype
        self.represent    = typeset.represent
        self.lloperations = typeset.lloperations
        self.rawoperations= typeset.rawoperations
        self.getconversion= typeset.getconversion
        self.typemismatch = typeset.typemismatch
        self.hltypes = {}
        self.llreprs = {}

    def makevar(self, v, hltype=None):
        "Record v in self.hltypes and self.llreprs."
        if v in self.llreprs:
            return
        if hltype is None:
            hltype = self.gethltype(v)
        llrepr = []
        lltypes = self.represent(hltype)
        for i, lltype in zip(range(len(lltypes)), lltypes):
            if i:
                suffix = '_%d' % i
            else:
                suffix = ''
            llrepr.append(LLVar(lltype, v.name + suffix))
        self.hltypes[v] = hltype
        self.llreprs[v] = llrepr

# ____________________________________________________________

class LLFunction(LLTyper):
    "A low-level version of a function from a control flow graph."

    def __init__(self, typeset, name, graph):
        LLTyper.__init__(self, typeset)
        remove_direct_loops(graph)
        self.name = name
        self.graph = graph

    def hl_header(self):
        """
        Get the high-level signature (argument types and return type).
        """
        result = []
        for v in self.graph.getargs():
            self.makevar(v)
            result.append(self.hltypes[v])
        v = self.graph.getreturnvar()
        self.makevar(v)
        result.append(self.hltypes[v])
        return result

    def ll_header(self):
        """
        Get the low-level representation of the header.
        """
        llrepr = []
        for v in self.graph.getargs():
            self.makevar(v)
            llrepr += self.llreprs[v]
        v = self.graph.getreturnvar()
        self.makevar(v)
        llret = self.llreprs[v]
        return llrepr, llret

    def ll_body(self, error_retvals):
        """
        Get the body by flattening and low-level-izing the flow graph.
        Enumerates low-level operations: LLOps with labels inbetween (strings).
        """
        self.blockname = {}
        llreturn = self.rawoperations['return']
        assert not llreturn.can_fail
        self.release_root = ReleaseNode(None, llreturn(error_retvals), None)
        allblocks = []
        
        # collect all blocks
        def visit(block):
            if isinstance(block, Block):
                allblocks.append(block)
                self.blockname[block] = 'block%d' % len(self.blockname)
                for v in block.inputargs:
                    self.makevar(v)
        traverse(visit, self.graph)

        # generate an incref for each input argument
        for v in self.graph.getargs():
            yield self.rawoperations['incref'](self.llreprs[v])

        # generate the body of each block
        for block in allblocks:
            for op in self.generate_block(block):
                yield op
            yield ''   # empty line

        # generate the code to handle errors
        for op in self.release_root.error_code(self.rawoperations):
            yield op

    def generate_block(self, block):
        "Generate the operations for one basic block."
        self.to_release = self.release_root
        for v in block.inputargs:
            self.mark_release(v)
        # entry point
        self.blockops = [self.blockname[block]]   # label
        # basic block operations
        for op in block.operations:
            self.operation('OP_' + op.opname.upper(), list(op.args), op.result)
        # exits
        if block.exits:
            for exit in block.exits[:-1]:
                # generate | caseXXX v elselabel
                #          |   copy output vars to next block's input vars
                #          |   jump to next block
                #          | elselabel:
                elselabel = '%s_not%s' % (self.blockname[block], exit.exitcase)
                self.operation('case%s' % exit.exitcase,
                               [block.exitswitch],
                               errlabel = elselabel)
                self.goto(exit)
                self.blockops.append(elselabel)
            # for the last exit, generate only the jump to next block
            exit = block.exits[-1]
            self.goto(exit)

        elif hasattr(block, 'exc_type'):
            XXX("to do")
        else:
            llreturn = self.rawoperations['return']
            assert not llreturn.can_fail
            llrepr = self.llreprs[block.inputargs[0]]
            self.blockops.append(llreturn(llrepr))
        return self.blockops

    # __________ Type checking and conversion routines __________

    def mark_release(self, v):
        llop = self.rawoperations['decref'](self.llreprs[v])
        # make a new node for the release tree
        self.to_release = ReleaseNode(v, llop, self.to_release)

    def find_best_match(self, opname, args_t, directions):
        # look for an exact match first
        llsigs = self.lloperations.setdefault(opname, {})
        sig = tuple(args_t)
        if sig in llsigs:
            return sig, llsigs[sig]
        # no exact match, give the typeset a chance to provide an
        # accurate version
        self.typemismatch(opname, tuple(args_t))
        if sig in llsigs:
            return sig, llsigs[sig]
        # enumerate the existing operation signatures and their costs
        choices = []
        for sig, llopcls in llsigs.items():
            if len(sig) != len(args_t):
                continue   # wrong number of arguments
            try:
                cost = llopcls.cost
                for hltype1, hltype2, reverse in zip(args_t, sig,
                                                     directions):
                    if hltype1 != hltype2:
                        if reverse:
                            hltype1, hltype2 = hltype2, hltype1
                        convop = self.getconversion(hltype1, hltype2)
                        cost += convop.cost
                choices.append((cost, sig, llopcls))
            except CannotConvert:
                continue   # non-matching signature
        if choices:
            cost, sig, llopcls = min(choices)
            # for performance, cache the approximate match
            # back into self.lloperations
            llsigs[sig] = llopcls
            return sig, llopcls
        raise TypingError([opname] + list(args_t))

    def operation(self, opname, args, result=None, errlabel=None):
        "Helper to build the LLOps for a single high-level operation."
        # get the hltypes of the input arguments
        for v in args:
            self.makevar(v)
        args_t = [self.hltypes[v] for v in args]
        directions = [False] * len(args)
        # append the hltype of the result
        if result:
            self.makevar(result)
            args_t.append(self.hltypes[result])
            directions.append(True)
        # look for the low-level operation class that implements these types
        sig, llopcls = self.find_best_match(opname, args_t, directions)
        # convert input args to temporary variables, if needed
        llargs = []
        for v, v_t, s_t in zip(args, args_t, sig):
            if v_t != s_t:
                llargs += self.convert(v_t, self.llreprs[v], s_t)
            else:
                llargs += self.llreprs[v]
        # case-by-case analysis of the result variable
        if result:
            if args_t[-1] == sig[-1]:
                # the result has the correct type
                if self.writeoperation(llopcls, llargs,
                                       self.llreprs[result], errlabel):
                    self.mark_release(result)
            else:
                # the result has to be converted
                tmp = Variable()
                self.makevar(tmp, hltype=sig[-1])
                if self.writeoperation(llopcls, llargs,
                                       self.llreprs[tmp], errlabel):
                    self.mark_release(tmp)
                self.convert_variable(tmp, result)
        else:
            # no result variable
            self.writeoperation(llopcls, llargs, [], errlabel)

    def writeoperation(self, llopcls, llargs, llresult, errlabel=None):
        # generate an error label if the operation can fail
        if llopcls.can_fail and errlabel is None:
            errlabel = self.to_release.getlabel()
        # create the LLOp instance
        llop = llopcls(llargs + llresult, errlabel)
        constantllreprs = llop.optimize(self)
        if constantllreprs is not None:
            # the result is a constant: patch llresult, i.e. replace its
            # LLVars with the given constants which will be used by the
            # following operations.
            assert len(constantllreprs) == len(llresult)
            llresult[:] = constantllreprs
            return False   # operation skipped
        else:
            # common case: emit the LLOp.
            self.blockops.append(llop)
            return True

    def convert(self, inputtype, inputrepr, outputtype, outputrepr=None):
        convop = self.getconversion(inputtype, outputtype)
        if outputrepr is None:
            tmp = Variable()
            self.makevar(tmp, hltype=outputtype)
            outputrepr = self.llreprs[tmp]
            if self.writeoperation(convop, inputrepr, outputrepr):
                self.mark_release(tmp)
        else:
            if self.writeoperation(convop, inputrepr, outputrepr):
                tmp = Variable()
                self.hltypes[tmp] = outputtype
                self.llreprs[tmp] = outputrepr
                self.mark_release(tmp)
        return outputrepr

    def convert_variable(self, v1, v2):
        self.makevar(v1)
        self.makevar(v2)
        convop = self.getconversion(self.hltypes[v1], self.hltypes[v2])
        if self.writeoperation(convop, self.llreprs[v1], self.llreprs[v2]):
            self.mark_release(v2)

    def goto(self, exit):
        # generate the exit.args -> target.inputargs copying operations
        to_release_copy = self.to_release
        try:
            # convert the exit.args to the type expected by the target.inputargs
            exitargs = []
            for v, w in zip(exit.args, exit.target.inputargs):
                self.makevar(v)
                if self.hltypes[v] != self.hltypes[w]:
                    tmp = Variable()
                    self.makevar(tmp, hltype=self.hltypes[w])
                    self.convert_variable(v, tmp)
                    v = tmp
                exitargs.append(v)
            # move the data from exit.args to target.inputargs
            # See also remove_direct_loops() for why we don't worry about
            # the order of the move operations
            current_refcnt = {}
            needed_refcnt = {}
            llmove = self.rawoperations['move']
            for v, w in zip(exitargs, exit.target.inputargs):
                for x, y in zip(self.llreprs[v], self.llreprs[w]):
                    self.blockops.append(llmove([x, y]))
                    needed_refcnt.setdefault(x, 0)
                    needed_refcnt[x] += 1
            # list all variables that go out of scope: by default
            # they need no reference, but have one reference.
            for node in self.to_release.getbranch():
                for x in self.llreprs[node.var]:
                    current_refcnt[x] = 1
                    needed_refcnt.setdefault(x, 0)
            # now adjust all reference counters: first increfs, then decrefs
            # (in case a variable to decref points to the same objects than
            #  another variable to incref).
            llincref = self.rawoperations['incref']
            for x, needed in needed_refcnt.items():
                current_refcnt.setdefault(x, 0)
                while current_refcnt[x] < needed:
                    self.blockops.append(llincref([x]))
                    current_refcnt[x] += 1
            lldecref = self.rawoperations['decref']
            for x, needed in needed_refcnt.items():
                while current_refcnt[x] > needed:
                    self.blockops.append(lldecref([x]))
                    current_refcnt[x] -= 1
            # finally jump to the target block
            llgoto = self.rawoperations['goto']
            self.blockops.append(llgoto([], self.blockname[exit.target]))
        finally:
            self.to_release = to_release_copy
            # after a call to goto() we are back to generating ops for
            # other cases, so we restore the previous self.to_release.

# ____________________________________________________________

# In a function, all the variables that have to released can be organized
# in a tree in which each node is a variable: whenever this variable has
# to be released, its parent in the tree has to be release too, and its
# parent's parent and so on up to the root.
class ReleaseNode:
    accessible = False
    label = None
    counter = 0
    
    def __init__(self, var, release_operation, parent):
        self.var = var
        self.release_operation = release_operation
        self.parent = parent
        self.accessible_children = []

    def mark_accessible(self):
        if not self.accessible:
            self.accessible = True
            if self.parent:
                self.parent.accessible_children.append(self)
                self.parent.mark_accessible()

    def nextlabel(self):
        while self.parent:
            self = self.parent
        self.counter += 1
        return 'err%d' % self.counter

    def getlabel(self):
        if self.label is None:
            self.mark_accessible()
            self.label = self.nextlabel()
        return self.label

    def getbranch(self):
        while self.parent:
            yield self
            self = self.parent

    def error_code(self, rawoperations):
        N = len(self.accessible_children)
        for i in range(N):
            if i > 0:
                llgoto = rawoperations['goto']
                yield llgoto([], self.getlabel())
            node = self.accessible_children[~i]
            for op in node.error_code(rawoperations):
                yield op
        if self.label:
            yield self.label
        elif not N:
            return
        yield self.release_operation
