from __future__ import generators

from types import FunctionType
from pypy.annotation.model import SomeValue, ANN
from pypy.annotation.annset import AnnotationSet
from pypy.annotation.annset import impossiblevalue, mostgeneralvalue
from pypy.objspace.flow.model import Variable, Constant, UndefinedConstant
from pypy.objspace.flow.model import SpaceOperation


class AnnotatorError(Exception):
    pass

intvalue = SomeValue()
boolvalue = SomeValue()


class RPythonAnnotator:
    """Block annotator for RPython.
    See description in doc/transation/annotation.txt."""

    def __init__(self, translator=None):
        self.heap = AnnotationSet()
        self.heap.settype(intvalue,  int)
        self.heap.settype(boolvalue, bool)
        self.pendingblocks = []  # list of (block, list-of-SomeValues-args)
        self.delayedblocks = []  # list of blocked blocks
        self.bindings = {}       # map Variables/Constants to SomeValues
        self.annotated = {}      # set of blocks already seen
        self.translator = translator

        self.classes = {} # map classes to attr-name -> SomaValue dicts

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

    def gettype(self, variable):
        """Return the known type of a control flow graph variable, or None."""
        if isinstance(variable, Constant):
            return type(variable.value)
        elif isinstance(variable, Variable):
            cell = self.bindings.get(variable)
            if cell:
                cell = self.heap.get(ANN.type, cell)
                if cell:
                    return cell
            return None
        else:
            raise TypeError, ("Variable or Constant instance expected, "
                              "got %r" % (variable,))


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
                                 len(delayedblocks))

    def binding(self, arg):
        "Gives the SomeValue corresponding to the given Variable or Constant."
        try:
            return self.bindings[arg]
        except KeyError:
            if not isinstance(arg, Constant):
                raise   # propagate missing bindings for Variables
            if isinstance(arg, UndefinedConstant):
                result = impossiblevalue  # undefined local variables
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
        constvalue = self.heap.get(ANN.const, cell)
        if constvalue is not mostgeneralvalue:
            return Constant(constvalue)
        else:
            for v in known_variables:
                if self.heap.isshared(self.bindings[v], cell):
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
            self.annotated[block] = True
            try:
                self.flowin(block)
            except DelayAnnotation:
                self.annotated[block] = False   # failed, hopefully temporarily
                self.delayedblocks.append(block)
            else:
                # When flowin succeeds, i.e. when the analysis progress,
                # we can tentatively re-schedlue the delayed blocks.
                for block in self.delayedblocks:
                    self.addpendingblock(block, None)
                del self.delayedblocks[:]

    def reflowpendingblock(self, block):
        self.pendingblocks.append((block, None))
        assert block in self.annotated
        self.annotated[block] = False  # must re-flow

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
        # if the merged cells changed, we must redo the analysis
        #print '** oldcells = ', oldcells
        #print '** newcells = ', newcells
        for cell1, cell2 in zip(oldcells, newcells):
            if not self.heap.isshared(cell1, cell2):
                self.bindinputargs(block, newcells)
                return

    def flowin(self, block):
        self.heap.enter(block, self.reflowpendingblock)
        for op in block.operations:
            self.consider_op(op)
        self.heap.leave()
        for link in block.exits:
            cells = [self.binding(a) for a in link.args]
            self.addpendingblock(link.target, cells)


    #___ creating the annotations based on operations ______

    def consider_op(self,op):
        argcells = [self.binding(a) for a in op.args]
        consider_meth = getattr(self,'consider_op_'+op.opname,
                                self.default_consider_op)
        resultcell = consider_meth(*argcells)
        if resultcell is impossiblevalue:
            raise DelayAnnotation  # the operation cannot succeed
        assert isinstance(resultcell, (SomeValue, type(mostgeneralvalue)))
        assert isinstance(op.result, Variable)
        self.bindings[op.result] = resultcell   # bind resultcell to op.result

    def consider_op_setattr(self,obj,attr,newval):
        objtype = self.heap.get(ANN.type,obj)
        if isinstance(objtype,type):
            attrdict = self.classes.setdefault(objtype,{})
            attr = self.heap.get(ANN.const,attr)
            if attr is not mostgeneralvalue:
                oldval = attrdict.get(attr,impossiblevalue)
                newval = self.heap.merge(oldval,newval)
                # XXX
                # if newval is not oldval (using isshared)
                # we should reflow the places that depend on this
                # we really need to make the attrdict an annotation
                # on the type as const
                # or invent a fake annotation
                # that we get on getattr and kill and reset on setattr
                # to trigger that
                attrdict[attr] = newval
            else:
                raise ValueError,"setattr op with non-const attrname not expected"
        return SomeValue()

    def consider_op_getattr(self,obj,attr):
        result = SomeValue()
        objtype = self.heap.get(ANN.type,obj)
        if isinstance(objtype,type):
            attrdict = self.classes.setdefault(objtype,{})
            attr = self.heap.get(ANN.const,attr)
            if attr is not mostgeneralvalue:
                if hasattr(objtype,attr): # XXX shortcut to keep methods working
                    return result
                oldval = attrdict.get(attr,impossiblevalue)
                if oldval is impossiblevalue:
                    return impossiblevalue
                return oldval
            else:
                raise ValueError,"getattr op with non-const attrname not expected"
        return result
        

    def default_consider_op(self, *args):
        return mostgeneralvalue

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
            self.heap.kill(ANN.len, arg1)
            item2 = self.heap.get(ANN.listitems, arg2)
            self.heap.generalize(ANN.listitems, arg1, item2)
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
    consider_op_mod  = consider_op_sub
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
        self.heap.set(ANN.len, result, len(args))
        for i in range(len(args)):
            self.heap.set(ANN.tupleitem[i], result, args[i])
        return result

    def consider_op_newlist(self, *args):
        result = SomeValue()
        self.heap.settype(result, list)
        self.heap.set(ANN.len, result, len(args))
        item_cell = impossiblevalue
        for a in args:
            item_cell = self.heap.merge(item_cell, a)
        self.heap.set(ANN.listitems, result, item_cell)
        return result

    def consider_op_newslice(self, *args):
        result = SomeValue()
        self.heap.settype(result, slice)
        return result

    def consider_op_newdict(self, *args):
        result = SomeValue()
        self.heap.settype(result, dict)
        if not args:
            self.heap.set(ANN.len, result, 0)
        return result

    def consider_op_getitem(self, arg1, arg2):
        tp = self.heap.checktype
        if tp(arg2, int):
            if tp(arg1, tuple):
                index = self.heap.get(ANN.const, arg2)
                if index is not mostgeneralvalue:
                    return self.heap.get(ANN.tupleitem[index], arg1)
            if tp(arg1, list):
                return self.heap.get(ANN.listitems, arg1)
        result = SomeValue()
        if tp(arg2, slice):
            self.heap.copytype(arg1, result)
            # XXX copy some information about the items
        return result

    def decode_simple_call(self, varargs_cell, varkwds_cell):
        nbargs = self.heap.get(ANN.len, varargs_cell)
        if nbargs is mostgeneralvalue:
            return None
        arg_cells = [self.heap.get(ANN.tupleitem[j], varargs_cell)
                     for j in range(nbargs)]
        nbkwds = self.heap.get(ANN.len, varkwds_cell)
        if nbkwds != 0:
            return None  # XXX deal with dictionaries with constant keys
        return arg_cells

    def consider_op_call(self, func, varargs, kwargs):
        result = SomeValue()
        tp = self.heap.checktype
        func = self.heap.get(ANN.const, func)
        # XXX: generalize this later
        if func is range:
            self.heap.settype(result, list)
        elif func is pow:
            args = self.decode_simple_call(varargs, kwargs)
            if args is not None and len(args) == 2:
                if tp(args[0], int) and tp(args[1], int):
                    self.heap.settype(result, int)
        elif isinstance(func, FunctionType) and self.translator:
            args = self.decode_simple_call(varargs, kwargs)
            return self.translator.consider_call(self, func, args)
        elif isinstance(func,type):
            # XXX flow into __init__/__new__
            self.heap.settype(result,func)
        return result

    def consider_const(self, constvalue):
        result = SomeValue()
        self.heap.set(ANN.const, result, constvalue)
        self.heap.settype(result, type(constvalue))
        if isinstance(constvalue, tuple):
            pass # XXX say something about the elements
        return result


class CannotSimplify(Exception):
    pass

class DelayAnnotation(Exception):
    pass
