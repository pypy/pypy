"""
Graph-to-low-level transformer for C/Assembler code generators.
"""

from __future__ import generators
from pypy.objspace.flow.model import Constant, Variable, Block, Link, traverse
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

class LLOp:
    "A low-level operation."
    def __init__(self, name, args, errtarget=None):
        self.name = name    # low-level operation name
        self.args = args    # list of LLVars
        self.errtarget = errtarget  # label to jump to in case of error

class TypingError(Exception):
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
#           (tuple-of-hltypes): (low-level-name, flag-can-fail),
#           ... },
#       ...}
#       This dict contains the known signatures of each space operation.
#       Special opnames:
#         'convert' x y : convert some x to y
#         'caseXXX'   z : fails (i.e. jump to errlabel) if z is not XXX
#         'return'    z : z is the return value of the function
#         'returnerr' z : same, but return an error code instead of z's content
#
#       Low-level-only operation names:
#         'goto'          : fails unconditionally (i.e. jump to errlabel)
#         'move'    x y   : raw copy of the LLVar x to the LLVar y
#         'copy' x1 x2.. y1 y2...: raw copy x1 to y1, x2 to y2, etc. and incref
#         'incref'  x y...: raw incref of the LLVars x, y, etc.
#         'decref'  x y...: raw decref of the LLVars x, y, etc.
#         'xdecref' x y...: raw xdecref of the LLVars x, y, etc.
#
#   def typingerror(self, opname, hltypes):
#       Called when no match is found in lloperations.  This function must
#       either extend lloperations and return True to retry, or return
#       False to fail.
#
#   def knownanswer(self, llname):
#       Optionally returns a list of LLVars that give the well-known, constant
#       answer to the low-level operation name 'llname'; else return None.
# ____________________________________________________________


class LLTyper:
    "Base class for type-oriented low-level generators."

    def __init__(self, typeset):
        self.gethltype    = typeset.gethltype
        self.represent    = typeset.represent
        self.lloperations = typeset.lloperations
        self.typingerror  = typeset.typingerror
        self.knownanswer  = typeset.knownanswer
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
        if len(llret) == 0:
            retlltype = None
        elif len(llret) == 1:
            retlltype = llret[0].type
        else:
            XXX("to do")
        return llrepr, retlltype

    def ll_body(self):
        """
        Get the body by flattening and low-level-izing the flow graph.
        Enumerates low-level operations: LLOps with labels inbetween (strings).
        """
        self.blockname = {}
        v = self.graph.getreturnvar()
        self.makevar(v)
        sig = (self.hltypes[v],)
        llname, can_fail = self.lloperations['returnerr'][sig]
        assert not can_fail
        self.release_root = ReleaseNode(None, LLOp(llname, []), None)
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
            yield LLOp('incref', self.llreprs[v])

        # generate the body of each block
        for block in allblocks:
            for op in self.generate_block(block):
                yield op
            yield ''   # empty line

        # generate the code to handle errors
        for op in self.release_root.error_code():
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
            self.operation('return', block.inputargs)
        return self.blockops

    # __________ Type checking and conversion routines __________

    def mark_release(self, v):
        llop = LLOp('decref', self.llreprs[v])
        # make a new node for the release tree
        self.to_release = ReleaseNode(v, llop, self.to_release)

    def convert_from(self, hltype):
        # enumerate all types that hltype can be converted to
        for frm, to in self.lloperations['convert']:
            if frm == hltype:
                yield to

    def convert_to(self, hltype):
        # enumerate all types that can be converted to hltype
        for frm, to in self.lloperations['convert']:
            if to == hltype:
                yield frm

    def operation(self, opname, args, result=None, errlabel=None):
        "Helper to build the LLOps for a single high-level operation."
        # get the hltypes of the input arguments
        for v in args:
            self.makevar(v)
        args_t = [self.hltypes[v] for v in args]
        directions = [self.convert_from] * len(args)
        # append the hltype of the result
        if result:
            self.makevar(result)
            args_t.append(self.hltypes[result])
            directions.append(self.convert_to)
        # enumerate possible signatures until we get a match
        llsigs = self.lloperations.get(opname, {})
        for sig in variants(tuple(args_t), directions):
            if sig in llsigs:
                llname, can_fail = llsigs[sig]
                break
        else:
            retry = self.typingerror(opname, tuple(args_t))
            # if 'typingerror' did not raise an exception, try again.
            # infinite recursion here means that 'typingerror' did not
            # correctly extend 'lloperations'.
            if retry:
                try:
                    self.operation(opname, args, result, errlabel)
                    return
                except RuntimeError:   # infinite recursion
                    pass
            raise TypingError([opname] + args_t)
        # check for some operations that have an existing well-known answer
        # that doesn't involve side-effects, so that we can just provide
        # this answer and not generate any LLOp.
        if result:
            if llname == 'copy':
                # patch self.llreprs and we're done
                llrepr = []
                for v in args:
                    llrepr += self.llreprs[v]
                self.llreprs[result] = llrepr
                return
            llrepr = self.knownanswer(llname)
            if llrepr is not None:
                # patch self.llreprs and we're done
                self.llreprs[result] = llrepr
                return
        # convert input args to temporary variables
        llargs = []
        for v, v_t, s_t in zip(args, args_t, sig):
            if v_t != s_t:
                tmp = Variable()
                self.makevar(tmp, hltype=s_t)
                self.operation('convert', [v], tmp)
                v = tmp
            llargs += self.llreprs[v]
        # generate an error label if the operation can fail
        if can_fail and errlabel is None:
            errlabel = self.to_release.getlabel()
        # case-by-case analysis of the result variable
        if result:
            if args_t[-1] == sig[-1]:
                # the result has the correct type
                llargs += self.llreprs[result]
                self.blockops.append(LLOp(llname, llargs, errlabel))
                self.mark_release(result)
            else:
                # the result has to be converted
                tmp = Variable()
                self.makevar(tmp, hltype=sig[-1])
                llargs += self.llreprs[tmp]
                self.blockops.append(LLOp(llname, llargs, errlabel))
                self.mark_release(tmp)
                self.operation('convert', [tmp], result)
        else:
            # no result variable
            self.blockops.append(LLOp(llname, llargs, errlabel))

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
                    self.operation('convert', [v], tmp)
                    v = tmp
                exitargs.append(v)
            # move the data from exit.args to target.inputargs
            # See also remove_direct_loops() for why we don't worry about
            # the order of the move operations
            current_refcnt = {}
            needed_refcnt = {}
            for v, w in zip(exitargs, exit.target.inputargs):
                for x, y in zip(self.llreprs[v], self.llreprs[w]):
                    self.blockops.append(LLOp('move', [x, y]))
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
            for x, needed in needed_refcnt.items():
                current_refcnt.setdefault(x, 0)
                while current_refcnt[x] < needed:
                    self.blockops.append(LLOp('incref', [x]))
                    current_refcnt[x] += 1
            for x, needed in needed_refcnt.items():
                while current_refcnt[x] > needed:
                    self.blockops.append(LLOp('decref', [x]))
                    current_refcnt[x] -= 1
            # finally jump to the target block
            self.blockops.append(LLOp('goto', [], self.blockname[exit.target]))
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

    def error_code(self):
        N = len(self.accessible_children)
        for i in range(N):
            if i > 0:
                yield LLOp('goto', [], self.getlabel())
            node = self.accessible_children[~i]
            for op in node.error_code():
                yield op
        if self.label:
            yield self.label
        elif not N:
            return
        yield self.release_operation


def variants(args_t, directions):
    # enumerate all variants of the given signature of hltypes
    # XXX this can become quadratically slow for large programs because
    # XXX it enumerates all conversions of the result from a constant value
    if len(args_t):
        for sig in variants(args_t[:-1], directions[:-1]):
            yield sig + args_t[-1:]
        choices_for_last_arg = list(directions[-1](args_t[-1]))
        for sig in variants(args_t[:-1], directions[:-1]):
            for last_arg in choices_for_last_arg:
                yield sig + (last_arg,)
    else:
        yield ()
