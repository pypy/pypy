from __future__ import generators

from types import FunctionType
from pypy.translator.annheap import AnnotationHeap, Transaction
from pypy.translator.annotation import XCell, XConstant, nothingyet
from pypy.translator.annotation import Annotation
from pypy.objspace.flow.model import Variable, Constant, UndefinedConstant
from pypy.objspace.flow.model import SpaceOperation


class AnnotatorError(Exception):
    pass


class RPythonAnnotator:
    """Block annotator for RPython.
    See description in doc/transation/annotation.txt."""

    def __init__(self, translator=None):
        self.heap = AnnotationHeap()
        self.pendingblocks = []  # list of (block, list-of-XCells)
        self.delayedblocks = []  # list of blocked blocks
        self.bindings = {}       # map Variables/Constants to XCells/XConstants
        self.annotated = {}      # set of blocks already seen
        self.translator = translator
        # build default annotations
        t = self.transaction()
        self.any_immutable = XCell()
        t.set('immutable', [], self.any_immutable)
        self.any_int = XCell()
        t.set_type(self.any_int, int)


    #___ convenience high-level interface __________________

    def build_types(self, flowgraph, input_arg_types):
        """Recursively build annotations about the specific entry point."""
        # make input arguments and set their type
        inputcells = [XCell() for arg in flowgraph.getargs()]
        t = self.transaction()
        for cell, arg_type in zip(inputcells, input_arg_types):
            t.set_type(cell, arg_type)
        # register the entry point
        self.addpendingblock(flowgraph.startblock, inputcells)
        # recursively proceed until no more pending block is left
        self.complete()


    #___ medium-level interface ____________________________

    def addpendingblock(self, block, cells):
        """Register an entry point into block with the given input cells."""
        self.pendingblocks.append((block, cells))

    def transaction(self):
        """Start a Transaction.  Each new Annotation is marked as depending
        on the Annotations queried for during the same Transation."""
        return Transaction(self.heap)

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
        "XCell or XConstant corresponding to the given Variable or Constant."
        try:
            return self.bindings[arg]
        except KeyError:
            if not isinstance(arg, Constant):
                raise   # propagate missing bindings for Variables
            if isinstance(arg, UndefinedConstant):
                result = nothingyet  # undefined local variables
            else:
                result = XConstant(arg.value)
                self.consider_const(result, arg)
            self.bindings[arg] = result
            return result

    def bindnew(self, arg):
        "Force the creation of a new binding for the given Variable."
        assert isinstance(arg, Variable)
        self.bindings[arg] = result = XCell()
        return result

    def constant(self, value):
        "Turn a value into an XConstant with the proper annotations."
        return self.binding(Constant(value))


    #___ simplification (should be moved elsewhere?) _______

    # it should be!
    # now simplify_calls is moved to transform.py.
    # i kept reverse_binding here for future(?) purposes though. --sanxiyn

    def reverse_binding(self, known_variables, cell):
        """This is a hack."""
        # In simplify_calls, when we are trying to create the new
        # SpaceOperation, all we have are XCells.  But SpaceOperations take
        # Variables, not XCells.  Trouble is, we don't always have a Variable
        # that just happens to be bound to the given XCells.  A typical
        # example would be if the tuple of arguments was created from another
        # basic block or even another function.  Well I guess there is no
        # clean solution.
        if isinstance(cell, XConstant):
            return Constant(cell.value)
        else:
            for v in known_variables:
                if self.bindings[v] == cell:
                    return v
            else:
                raise CannotSimplify

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
            self.bindings[a] = cell
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
        #print '** oldcells = ', oldcells
        #print '** newcells = ', newcells
        # if the merged cells changed, we must redo the analysis
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
        resultcell = self.bindnew(op.result)
        consider_meth = getattr(self,'consider_op_'+op.opname,None)
        if consider_meth is not None:
            consider_meth(argcells, resultcell, self.transaction())

    def consider_op_add(self, (arg1,arg2), result, t):
        type1 = t.get_type(arg1)
        type2 = t.get_type(arg2)
        if type1 is int and type2 is int:
            t.set_type(result, int)
        elif type1 in (int, long) and type2 in (int, long):
            t.set_type(result, long)
        if type1 is str and type2 is str:
            t.set_type(result, str)
        if type1 is list and type2 is list:
            t.set_type(result, list)
            # XXX propagate information about the type of the elements

    def consider_op_mul(self, (arg1,arg2), result, t):
        type1 = t.get_type(arg1)
        type2 = t.get_type(arg2)
        if type1 is int and type2 is int:
            t.set_type(result, int)
        elif type1 in (int, long) and type2 in (int, long):
            t.set_type(result, long)

    def consider_op_inplace_add(self, (arg1,arg2), result, t):
        type1 = t.get_type(arg1)
        type2 = t.get_type(arg1)
        if type1 is list and type2 is list:
            # Annotations about the items of arg2 are merged with the ones about
            # the items of arg1.  arg2 is not modified during this operation.
            # result is arg1.
            result.share(arg1)
            t.delete('len', [arg1])
            item1 = t.get('getitem', [arg1, None])
            if item1 is not None:
                item2 = t.get('getitem', [arg2, None])
                if item2 is None:
                    item2 = XCell()   # anything at all
                item3 = self.heap.merge(item1, item2)
                if item3 != item1:
                    t.delete('getitem', [arg1, None])
                    t.set('getitem', [arg1, self.any_int], item3)
        else:
            self.consider_op_add((arg1,arg2), result, t)

    def consider_op_sub(self, (arg1,arg2), result, t):
        type1 = t.get_type(arg1)
        type2 = t.get_type(arg2)
        if type1 is int and type2 is int:
            t.set_type(result, int)
        elif type1 in (int, long) and type2 in (int, long):
            t.set_type(result, long)

    consider_op_and_ = consider_op_sub # trailing underline
    consider_op_inplace_lshift = consider_op_sub

    def consider_op_is_true(self, (arg,), result, t):
        t.set_type(result, bool)

    consider_op_not_ = consider_op_is_true

    def consider_op_lt(self, (arg1,arg2), result, t):
        t.set_type(result, bool)

    consider_op_le = consider_op_lt
    consider_op_eq = consider_op_lt
    consider_op_ne = consider_op_lt
    consider_op_gt = consider_op_lt
    consider_op_ge = consider_op_lt

    def consider_op_newtuple(self, args, result, t):
        t.set_type(result,tuple)
        t.set("len", [result], self.constant(len(args)))
        for i in range(len(args)):
            t.set("getitem", [result, self.constant(i)], args[i])

    def consider_op_newlist(self, args, result, t):
        t.set_type(result, list)
        t.set("len", [result], self.constant(len(args)))
        item_cell = nothingyet
        for a in args:
            item_cell = self.heap.merge(item_cell, a)
        t.set("getitem", [result, self.any_int], item_cell)

    def consider_op_newslice(self, args, result, t):
        t.set_type(result, slice)

    def consider_op_newdict(self, args, result, t):
        t.set_type(result, dict)
        if not args:
            t.set("len", [result], self.constant(0))

    def consider_op_getitem(self, (arg1,arg2), result, t):
        type1 = t.get_type(arg1)
        type2 = t.get_type(arg2)
        if type1 in (list, tuple) and type2 is slice:
            t.set_type(result, type1)

    def decode_simple_call(self, varargs_cell, varkwds_cell, t):
        len_cell = t.get('len', [varargs_cell])
        if not isinstance(len_cell, XConstant):
            return None
        nbargs = len_cell.value
        arg_cells = [t.get('getitem', [varargs_cell, self.constant(j)])
                     for j in range(nbargs)]
        if None in arg_cells:
            return None
        len_cell = t.get('len', [varkwds_cell])
        if not isinstance(len_cell, XConstant):
            return None
        nbkwds = len_cell.value
        if nbkwds != 0:
            return None
        return arg_cells

    def consider_op_call(self, (func,varargs,kwargs), result, t):
        if not isinstance(func, XConstant):
            return
        func = func.value
        if isinstance(func, FunctionType) and self.translator:
            args = self.decode_simple_call(varargs, kwargs, t)
            if args is not None:
                result_cell = self.translator.consider_call(self, func, args)
                if result_cell is nothingyet:
                    raise DelayAnnotation
                # 'result' is made shared with 'result_cell'.  This has the
                # effect that even if result_cell is actually an XConstant,
                # result stays an XCell, but the annotations about the constant
                # are also appliable to result.  This is bad because it means
                # functions returning constants won't propagate the constant
                # but only e.g. its type.  This is needed at this point because
                # XConstants are not too well supported in the forward_deps
                # lists: forward_deps cannot downgrade XConstant to XCell.
                result.share(result_cell)

        # XXX: generalize this later
        if func is range:
            t.set_type(result, list)
        if func is pow:
            tp1 = t.get_type(t.get('getitem', [varargs, self.constant(0)]))
            tp2 = t.get_type(t.get('getitem', [varargs, self.constant(1)]))
            if tp1 is int and tp2 is int:
                t.set_type(result, int)

    def consider_const(self,to_var,const):
        t = self.transaction()
        t.set('immutable', [], to_var)
        t.set_type(to_var,type(const.value))
        if isinstance(const.value, tuple):
            pass # XXX say something about the elements


class CannotSimplify(Exception):
    pass

class DelayAnnotation(Exception):
    pass
