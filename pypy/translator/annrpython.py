from __future__ import generators

from types import FunctionType
from pypy.annotation.model import SomeValue, ANN, blackholevalue
from pypy.annotation.model import intvalue, boolvalue, slicevalue
from pypy.annotation.annset import AnnotationSet, QUERYARG, IDontKnow
from pypy.objspace.flow.model import Variable, Constant, UndefinedConstant
from pypy.objspace.flow.model import SpaceOperation


class AnnotatorError(Exception):
    pass


class RPythonAnnotator:
    """Block annotator for RPython.
    See description in doc/transation/annotation.txt."""

    def __init__(self, translator=None):
        self.heap = AnnotationSet()
        self.pendingblocks = []  # list of (block, list-of-SomeValues-args)
        self.delayedblocks = []  # list of blocked blocks
        self.bindings = self.heap.getbindings()  # map Variables/Constants
                                                 # to SomeValues
        self.annotated = {}      # set of blocks already seen
        self.translator = translator


    #___ convenience high-level interface __________________

    def build_types(self, flowgraph, input_arg_types):
        """Recursively build annotations about the specific entry point."""
        # make input arguments and set their type
        inputcells = [SomeValue() for arg in flowgraph.getargs()]
        for cell, arg_type in zip(inputcells, input_arg_types):
            self.heap.settype(cell, arg_type)
        
        # register the entry point
        self.addpendingblock(flowgraph.startblock, inputcells)
        # recursively proceed until no more pending block is left
        self.complete()


    #___ medium-level interface ____________________________

    def addpendingblock(self, block, cells):
        """Register an entry point into block with the given input cells."""
        self.pendingblocks.append((block, cells))

    def complete(self):
        """Process pending blocks until none is left."""
        while self.pendingblocks:
            # XXX don't know if it is better to pop from the head or the tail.
            # let's do it breadth-first and pop from the head (oldest first).
            # that's more stacklessy.
            block, cells = self.pendingblocks.pop(0)
            self.processblock(block, cells)
        if self.delayedblocks:
            raise AnnotatorError('%d block(s) are still blocked' %
                                 len(delayed))

    def binding(self, arg):
        "Gives the SomeValue corresponding to the given Variable or Constant."
        try:
            return self.bindings[arg]
        except KeyError:
            if not isinstance(arg, Constant):
                raise   # propagate missing bindings for Variables
            if isinstance(arg, UndefinedConstant):
                result = blackholevalue  # undefined local variables
            else:
                result = self.consider_const(arg.value)
            self.bindings[arg] = result
            return result

    def constant(self, value):
        "Turn a value into a SomeValue with the proper annotations."
        return self.binding(Constant(value))


    #___ simplification (should be moved elsewhere?) _______

    # it should be!
    # now simplify_calls is moved to transform.py.
    # i kept reverse_binding here for future(?) purposes though. --sanxiyn

    def reverse_binding(self, known_variables, cell):
        """This is a hack."""
        # In simplify_calls, when we are trying to create the new
        # SpaceOperation, all we have are SomeValues.  But SpaceOperations take
        # Variables, not SomeValues.  Trouble is, we don't always have a
        # Variable that just happens to be bound to the given SomeValue.
        # A typical example would be if the tuple of arguments was created
        # from another basic block or even another function.  Well I guess
        # there is no clean solution.
        vlist = self.heap.queryconstant(cell)
        if len(vlist) == 1:
            return Constant(vlist[0])
        else:
            cell = self.heap.normalized(cell)
            for v in known_variables:
                if self.bindings[v] == cell:
                    return v
            else:
                raise IDontKnow, cell

    def simplify(self):
        # Generic simpliciations
        from pypy.translator import transform
        transform.transform_simple_call(self)


    #___ flowing annotations in blocks _____________________

    def processblock(self, block, cells):
        # Important: this is not called recursively.
        # self.flowin() can only issue calls to self.addpendingblock().
        # The analysis of a block can be in three states:
        #  * block not in self.annotated:
        #      never seen the block.
        #  * self.annotated[block] == False:
        #      the input variables of the block are in self.bindings but we
        #      still have to consider all the operations in the block.
        #  * self.annotated[block] == True:
        #      analysis done (at least until we find we must generalize the
        #      input variables).

        #print '* processblock', block, cells
        if block not in self.annotated:
            self.bindinputargs(block, cells)
        elif cells is not None:
            self.mergeinputargs(block, cells)
        if not self.annotated[block]:
            try:
                self.flowin(block)
            except DelayAnnotation:
                self.delayedblocks.append(block) # failed, hopefully temporarily
            else:
                self.annotated[block] = True
                # When flowin succeeds, i.e. when the analysis progress,
                # we can tentatively re-schedlue the delayed blocks.
                for block in self.delayedblocks:
                    self.pendingblocks.append((block, None))
                del self.delayedblocks[:]

    def bindinputargs(self, block, inputcells):
        # Create the initial bindings for the input args of a block.
        for a, cell in zip(block.inputargs, inputcells):
            self.bindings[a] = self.heap.normalized(cell)
        self.annotated[block] = False  # must flowin.

    def mergeinputargs(self, block, inputcells):
        # Merge the new 'cells' with each of the block's existing input
        # variables.
        oldcells = []
        newcells = []
        for a, cell2 in zip(block.inputargs, inputcells):
            cell1 = self.bindings[a]   # old binding
            oldcells.append(cell1)
            newcells.append(self.heap.merge(cell1, cell2))
        # if the merged cells changed, we must redo the analysis
        oldcells = [self.heap.normalized(c) for c in oldcells]
        newcells = [self.heap.normalized(c) for c in newcells]
        #print '** oldcells = ', oldcells
        #print '** newcells = ', newcells
        if newcells != oldcells:
            self.bindinputargs(block, newcells)

    def flowin(self, block):
        for op in block.operations:
            self.consider_op(op)
        for link in block.exits:
            cells = [self.binding(a) for a in link.args]
            self.addpendingblock(link.target, cells)


    #___ creating the annotations based on operations ______

    def consider_op(self,op):
        argcells = [self.binding(a) for a in op.args]
        consider_meth = getattr(self,'consider_op_'+op.opname,
                                self.default_consider_op)
        try:
            resultcell = consider_meth(*argcells)
        except IDontKnow:
            resultcell = SomeValue()
        if resultcell is blackholevalue:
            raise DelayAnnotation  # the operation cannot succeed
        assert isinstance(resultcell, SomeValue)
        assert isinstance(op.result, Variable)
        self.bindings[op.result] = resultcell   # bind resultcell to op.result

    def default_consider_op(self, *args):
        return SomeValue()

    def consider_op_add(self, arg1, arg2):
        result = SomeValue()
        tp = self.heap.checktype
        if tp(arg1, int) and tp(arg2, int):
            self.heap.settype(result, int)
        elif tp(arg1, (int, long)) and tp(arg2, (int, long)):
            self.heap.settype(result, long)
        if tp(arg1, str) and tp(arg2, str):
            self.heap.settype(result, str)
        if tp(arg1, list) and tp(arg2, list):
            self.heap.settype(result, list)
            # XXX propagate information about the type of the elements
        return result

    def consider_op_mul(self, arg1, arg2):
        result = SomeValue()
        tp = self.heap.checktype
        if tp(arg1, int) and tp(arg2, int):
            self.heap.settype(result, int)
        elif tp(arg1, (int, long)) and tp(arg2, (int, long)):
            self.heap.settype(result, long)
        return result

    def consider_op_inplace_add(self, arg1, arg2):
        tp = self.heap.checktype
        if tp(arg1, list) and tp(arg2, list):
            # Annotations about the items of arg2 are merged with the ones about
            # the items of arg1.  arg2 is not modified during this operation.
            # result is arg1.
            self.heap.delete(ANN.len[arg1, ...])
            item1 = self.heap.get_del(ANN.getitem[arg1, intvalue, QUERYARG])
            if item1:
                item2 = self.heap.get(ANN.getitem[arg2, intvalue, QUERYARG])
                item2 = item2 or SomeValue()  # defaults to "can be anything"
                item3 = self.heap.merge(item1, item2)
                self.heap.set(ANN.getitem[arg1, intvalue, item3])
            return arg1
        else:
            return self.consider_op_add(arg1, arg2)

    def consider_op_sub(self, arg1, arg2):
        result = SomeValue()
        tp = self.heap.checktype
        if tp(arg1, int) and tp(arg2, int):
            self.heap.settype(result, int)
        elif tp(arg1, (int, long)) and tp(arg2, (int, long)):
            self.heap.settype(result, long)
        return result

    consider_op_and_ = consider_op_sub # trailing underline
    consider_op_inplace_lshift = consider_op_sub

    def consider_op_is_true(self, arg):
        return boolvalue

    consider_op_not_ = consider_op_is_true

    def consider_op_lt(self, arg1, arg2):
        return boolvalue

    consider_op_le = consider_op_lt
    consider_op_eq = consider_op_lt
    consider_op_ne = consider_op_lt
    consider_op_gt = consider_op_lt
    consider_op_ge = consider_op_lt

    def consider_op_newtuple(self, *args):
        result = SomeValue()
        self.heap.settype(result, tuple)
        self.heap.set(ANN.len[result, self.constant(len(args))])
        for i in range(len(args)):
            self.heap.set(ANN.getitem[result, self.constant(i), args[i]])
        return result

    def consider_op_newlist(self, *args):
        result = SomeValue()
        self.heap.settype(result, list)
        self.heap.set(ANN.len[result, self.constant(len(args))])
        item_cell = blackholevalue
        for a in args:
            item_cell = self.heap.merge(item_cell, a)
        self.heap.set(ANN.getitem[result, intvalue, item_cell])
        return result

    def consider_op_newslice(self, *args):
        return slicevalue

    def consider_op_newdict(self, *args):
        result = SomeValue()
        self.heap.settype(result, dict)
        if not args:
            self.heap.set(ANN.len[result, self.constant(0)])
        return result

    def consider_op_getitem(self, arg1, arg2):
        tp = self.heap.checktype
        result = self.heap.get(ANN.getitem[arg1, arg2, QUERYARG])
        if result:
            return result
        if tp(arg2, int):  # not too nice, but needed for lists
            result = self.heap.get(ANN.getitem[arg1, intvalue, QUERYARG])
            if result:
                return result
        result = SomeValue()
        if tp(arg2, slice):
            self.heap.copytype(arg1, result)
        return result

    def decode_simple_call(self, varargs_cell, varkwds_cell):
        len_cell = self.heap.get(ANN.len[varargs_cell, QUERYARG])
        nbargs = self.heap.getconstant(len_cell)
        arg_cells = [self.heap.get(ANN.getitem[varargs_cell,
                                               self.constant(j), QUERYARG])
                     for j in range(nbargs)]
        if None in arg_cells:
            raise IDontKnow
        len_cell = self.heap.get(ANN.len[varkwds_cell, QUERYARG])
        nbkwds = self.heap.getconstant(len_cell)
        if nbkwds != 0:
            raise IDontKnow
        return arg_cells

    def consider_op_call(self, func, varargs, kwargs):
        func = self.heap.getconstant(func)
        if isinstance(func, FunctionType) and self.translator:
            args = self.decode_simple_call(varargs, kwargs)
            return self.translator.consider_call(self, func, args)

        # XXX: generalize this later
        tp = self.heap.checktype
        result = SomeValue()
        if func is range:
            self.heap.settype(result, list)
        if func is pow:
            args = self.decode_simple_call(varargs, kwargs)
            if len(args) == 2:
                if tp(args[0], int) and tp(args[1], int):
                    self.heap.settype(result, int)
        return result

    def consider_const(self, constvalue):
        result = self.heap.newconstant(constvalue)
        self.heap.set(ANN.immutable[result])
        self.heap.settype(result, type(constvalue))
        if isinstance(constvalue, tuple):
            pass # XXX say something about the elements
        return result


class DelayAnnotation(Exception):
    pass
