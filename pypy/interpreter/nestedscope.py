from pypy.interpreter.error import OperationError
from pypy.interpreter.pyopcode import PyInterpFrame
from pypy.interpreter import function, pycode
from pypy.interpreter.baseobjspace import Wrappable

class Cell(Wrappable):
    "A simple container for a wrapped value."
    
    def __init__(self, w_value=None):
        self.w_value = w_value

    def clone(self):
        return self.__class__(self.w_value)

    def empty(self):
        return self.w_value is None

    def get(self):
        if self.w_value is None:
            raise ValueError, "get() from an empty cell"
        return self.w_value

    def set(self, w_value):
        self.w_value = w_value

    def delete(self):
        if self.w_value is None:
            raise ValueError, "delete() on an empty cell"
        self.w_value = None

    def __repr__(self):
        """ representation for debugging purposes """
        if self.w_value is None:
            content = ""
        else:
            content = repr(self.w_value)
        return "<%s(%s) at 0x%x>" % (self.__class__.__name__,
                                     content, id(self))


class PyNestedScopeFrame(PyInterpFrame):
    """This class enhances a standard frame with nested scope abilities,
    i.e. handling of cell/free variables."""

    # Cell Vars:
    #     my local variables that are exposed to my inner functions
    # Free Vars:
    #     variables coming from a parent function in which i'm nested
    # 'closure' is a list of Cell instances: the received free vars.

    def __init__(self, space, code, w_globals, closure):
        PyInterpFrame.__init__(self, space, code, w_globals, closure)
        ncellvars = len(code.co_cellvars)
        nfreevars = len(code.co_freevars)
        if closure is None:
            if nfreevars:
                raise OperationError(space.w_TypeError,
                                     "directly executed code object "
                                     "may not contain free variables")
            closure = []
        else:
            if len(closure) != nfreevars:
                raise ValueError("code object received a closure with "
                                 "an unexpected number of free variables")
        self.cells = [Cell() for i in range(ncellvars)] + closure

    def getclosure(self):
        ncellvars = len(self.code.co_cellvars)  # not part of the closure
        return self.cells[ncellvars:]

    def fast2locals(self):
        PyInterpFrame.fast2locals(self)
        # cellvars are values exported to inner scopes
        # freevars are values coming from outer scopes 
        # for locals we only want the ones exported to inner-scopes 
        # XXX check more exactly how CPython does it 
        freevarnames = self.code.co_cellvars # + self.code.co_freevars
        for name, cell in zip(freevarnames, self.cells):
            try:
                w_value = cell.get()
            except ValueError:
                pass
            else:
                w_name = self.space.wrap(name)
                self.space.setitem(self.w_locals, w_name, w_value)

    def locals2fast(self):
        PyInterpFrame.locals2fast(self)
        freevarnames = self.code.co_cellvars + self.code.co_freevars
        for name, cell in zip(freevarnames, self.cells):
            w_name = self.space.wrap(name)
            try:
                w_value = self.space.getitem(self.w_locals, w_name)
            except OperationError, e:
                if not e.match(self.space, self.space.w_KeyError):
                    raise
            else:
                cell.set(w_value)

    def setfastscope(self, scope_w):
        PyInterpFrame.setfastscope(self, scope_w)
        if self.code.co_cellvars:
            # the first few cell vars could shadow already-set arguments,
            # in the same order as they appear in co_varnames
            code     = self.code
            argvars  = code.co_varnames
            cellvars = code.co_cellvars
            next     = 0
            nextname = cellvars[0]
            for i in range(len(scope_w)):
                if argvars[i] == nextname:
                    # argument i has the same name as the next cell var
                    w_value = scope_w[i]
                    self.cells[next] = Cell(w_value)
                    next += 1
                    try:
                        nextname = cellvars[next]
                    except IndexError:
                        break   # all cell vars initialized this way

    def getfreevarname(self, index):
        freevarnames = self.code.co_cellvars + self.code.co_freevars
        return freevarnames[index]

    def iscellvar(self, index):
        # is the variable given by index a cell or a free var?
        return index < len(self.code.co_cellvars)

    ### extra opcodes ###

    def LOAD_CLOSURE(f, varindex):
        # nested scopes: access the cell object
        cell = f.cells[varindex]
        w_value = f.space.wrap(cell)
        f.valuestack.push(w_value)

    def LOAD_DEREF(f, varindex):
        # nested scopes: access a variable through its cell object
        cell = f.cells[varindex]
        try:
            w_value = cell.get()
        except ValueError:
            varname = f.getfreevarname(varindex)
            if f.iscellvar(varindex):
                message = "local variable '%s' referenced before assignment"
                w_exc_type = f.space.w_UnboundLocalError
            else:
                message = ("free variable '%s' referenced before assignment"
                           " in enclosing scope")
                w_exc_type = f.space.w_NameError
            raise OperationError(w_exc_type, f.space.wrap(message % varname))
        else:
            f.valuestack.push(w_value)

    def STORE_DEREF(f, varindex):
        # nested scopes: access a variable through its cell object
        w_newvalue = f.valuestack.pop()
        #try:
        cell = f.cells[varindex]
        #except IndexError:
        #    import pdb; pdb.set_trace()
        #    raise
        cell.set(w_newvalue)

    def MAKE_CLOSURE(f, numdefaults):
        w_codeobj = f.valuestack.pop()
        codeobj = f.space.interpclass_w(w_codeobj)
        assert isinstance(codeobj, pycode.PyCode)
        nfreevars = len(codeobj.co_freevars)
        freevars = [f.space.interpclass_w(f.valuestack.pop()) for i in range(nfreevars)]
        freevars.reverse()
        defaultarguments = [f.valuestack.pop() for i in range(numdefaults)]
        defaultarguments.reverse()
        fn = function.Function(f.space, codeobj, f.w_globals,
                               defaultarguments, freevars)
        f.valuestack.push(f.space.wrap(fn))
