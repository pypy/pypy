from __future__ import generators

from pypy.translator.annheap import AnnotationHeap, Transaction
from pypy.translator.annotation import XCell, XConstant, nothingyet
from pypy.translator.annotation import Annotation
from pypy.objspace.flow.model import Variable, Constant, UndefinedConstant
from pypy.objspace.flow.model import SpaceOperation


class RPythonAnnotator:
    """Block annotator for RPython.
    See description in doc/transation/annotation.txt."""

    def __init__(self):
        self.heap = AnnotationHeap()
        self.pendingblocks = []  # list of (block, list-of-XCells)
        self.bindings = {}       # map Variables/Constants to XCells/XConstants
        self.annotated = {}      # set of blocks already seen
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


    #___ flowing annotations in blocks _____________________

    def processblock(self, block, cells):
        #print '* processblock', block, cells
        if block not in self.annotated:
            self.annotated[block] = True
            self.flowin(block, cells)
        else:
            # already seen; merge each of the block's input variable
            oldcells = []
            newcells = []
            for a, cell2 in zip(block.inputargs, cells):
                cell1 = self.bindings[a]   # old binding
                oldcells.append(cell1)
                newcells.append(self.heap.merge(cell1, cell2))
            #print '** oldcells = ', oldcells
            #print '** newcells = ', newcells
            # re-flowin unless the newcells are equal to the oldcells
            if newcells != oldcells:
                self.flowin(block, newcells)

    def flowin(self, block, inputcells):
        #print '...'
        for a, cell in zip(block.inputargs, inputcells):
            self.bindings[a] = cell
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

    def consider_op_getitem(self, (arg1,arg2), result, t):
        type1 = t.get_type(arg1)
        type2 = t.get_type(arg2)
        if type1 in (list, tuple) and type2 is slice:
            t.set_type(result, type1)

    def consider_op_call(self, (func,varargs,kwargs), result, t):
        if not isinstance(func, XConstant):
            return
        func = func.value
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
