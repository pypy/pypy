from pypy.objspace.flow.model import FunctionGraph, Constant, Variable, c_last_exception
from pypy.rlib.rarithmetic import intmask, r_uint, ovfcheck, r_longlong
from pypy.rlib.rarithmetic import r_ulonglong, ovfcheck_lshift
from pypy.rpython.lltypesystem import lltype, llmemory, lloperation, llheap
from pypy.rpython.lltypesystem import rclass
from pypy.rpython.ootypesystem import ootype
from pypy.rlib.objectmodel import ComputedIntSymbolic, CDefinedIntSymbolic
from pypy.rlib.objectmodel import Symbolic
from pypy.rlib import rstackovf

import sys, os
import math
import py
import traceback, cStringIO

log = py.log.Producer('llinterp')

class LLException(Exception):
    def __init__(self, *args):
        "NOT_RPYTHON"
        Exception.__init__(self, *args)
    def __str__(self):
        etype = self.args[0]
        #evalue = self.args[1]
        if len(self.args) > 2:
            f = cStringIO.StringIO()
            original_type, original_value, original_tb = self.args[2]
            traceback.print_exception(original_type, original_value, original_tb,
                                      file=f)
            extra = '\n' + f.getvalue().rstrip('\n')
            extra = extra.replace('\n', '\n | ') + '\n `------'
        else:
            extra = ''
        return '<LLException %r%s>' % (type_name(etype), extra)

class LLFatalError(Exception):
    def __str__(self):
        return ': '.join([str(x) for x in self.args])

def type_name(etype):
    if isinstance(lltype.typeOf(etype), lltype.Ptr):
        return ''.join(etype.name).rstrip('\x00')
    else:
        # ootype!
        return etype._INSTANCE._name.split(".")[-1] 

class LLInterpreter(object):
    """ low level interpreter working with concrete values. """

    current_interpreter = None

    def __init__(self, typer, tracing=True, exc_data_ptr=None):
        self.bindings = {}
        self.typer = typer
        # 'heap' is module or object that provides malloc, etc for lltype ops
        self.heap = llheap
        self.exc_data_ptr = exc_data_ptr
        self.frame_stack = []
        self.tracer = None
        self.frame_class = LLFrame
        if tracing:
            self.tracer = Tracer()

    def eval_graph(self, graph, args=(), recursive=False):
        llframe = self.frame_class(graph, args, self)
        if self.tracer and not recursive:
            global tracer1
            tracer1 = self.tracer
            self.tracer.start()
        retval = None
        self.traceback_frames = []
        old_frame_stack = self.frame_stack[:]
        prev_interpreter = LLInterpreter.current_interpreter
        LLInterpreter.current_interpreter = self
        try:
            try:
                retval = llframe.eval()
            except LLException, e:
                log.error("LLEXCEPTION: %s" % (e, ))
                self.print_traceback()
                if self.tracer:
                    self.tracer.dump('LLException: %s\n' % (e,))
                raise
            except Exception, e:
                if getattr(e, '_go_through_llinterp_uncaught_', False):
                    raise
                log.error("AN ERROR OCCURED: %s" % (e, ))
                self.print_traceback()
                if self.tracer:
                    line = str(e)
                    if line:
                        line = ': ' + line
                    line = '* %s' % (e.__class__.__name__,) + line
                    self.tracer.dump(line + '\n')
                raise
        finally:
            LLInterpreter.current_interpreter = prev_interpreter
            assert old_frame_stack == self.frame_stack
            if self.tracer:
                if retval is not None:
                    self.tracer.dump('   ---> %r\n' % (retval,))
                if not recursive:
                    self.tracer.stop()
        return retval

    def print_traceback(self):
        frames = self.traceback_frames
        frames.reverse()
        self.traceback_frames = []
        lines = []
        for frame in frames:
            logline = frame.graph.name + "()"
            if frame.curr_block is None:
                logline += " <not running yet>"
                lines.append(logline)
                continue
            try:
                logline += " " + self.typer.annotator.annotated[frame.curr_block].func.__module__
            except (KeyError, AttributeError, TypeError):
                logline += " <unknown module>"
            lines.append(logline)
            for i, operation in enumerate(frame.curr_block.operations):
                if i == frame.curr_operation_index:
                    logline = "E  %s"
                else:
                    logline = "   %s"
                lines.append(logline % (operation, ))
        if self.tracer:
            self.tracer.dump('Traceback\n', bold=True)
            for line in lines:
                self.tracer.dump(line + '\n')
        for line in lines:
            log.traceback(line)

    def find_roots(self):
        """Return a list of the addresses of the roots."""
        #log.findroots("starting")
        roots = []
        for frame in self.frame_stack:
            #log.findroots("graph", frame.graph.name)
            frame.find_roots(roots)
        return roots

    def find_exception(self, exc):
        assert isinstance(exc, LLException)
        klass, inst = exc.args[0], exc.args[1]
        exdata = self.typer.getexceptiondata()
        frame = self.frame_class(None, [], self)
        for cls in enumerate_exceptions_top_down():
            evalue = frame.op_direct_call(exdata.fn_pyexcclass2exc,
                    lltype.pyobjectptr(cls))
            etype = frame.op_direct_call(exdata.fn_type_of_exc_inst, evalue)
            if etype == klass:
                return cls
        raise ValueError, "couldn't match exception"

    def get_transformed_exc_data(self, graph):
        if hasattr(graph, 'exceptiontransformed'):
            return graph.exceptiontransformed
        if getattr(graph, 'rgenop', False):
            return self.exc_data_ptr
        return None

    def _store_exception(self, exc):
        raise PleaseOverwriteStoreException("You just invoked ll2ctypes callback without overwriting _store_exception on llinterpreter")

class PleaseOverwriteStoreException(Exception):
    pass

def checkptr(ptr):
    assert isinstance(lltype.typeOf(ptr), lltype.Ptr)

def checkadr(addr):
    assert lltype.typeOf(addr) is llmemory.Address

def is_inst(inst):
    return isinstance(lltype.typeOf(inst), (ootype.Instance, ootype.BuiltinType, ootype.StaticMethod))

def checkinst(inst):
    assert is_inst(inst)


class LLFrame(object):
    def __init__(self, graph, args, llinterpreter):
        assert not graph or isinstance(graph, FunctionGraph)
        self.graph = graph
        self.args = args
        self.llinterpreter = llinterpreter
        self.heap = llinterpreter.heap
        self.bindings = {}
        self.curr_block = None
        self.curr_operation_index = 0
        self.alloca_objects = []

    def newsubframe(self, graph, args):
        return self.__class__(graph, args, self.llinterpreter)

    # _______________________________________________________
    # variable setters/getters helpers

    def clear(self):
        self.bindings.clear()

    def fillvars(self, block, values):
        vars = block.inputargs
        assert len(vars) == len(values), (
                   "block %s received %d args, expected %d" % (
                    block, len(values), len(vars)))
        for var, val in zip(vars, values):
            self.setvar(var, val)

    def setvar(self, var, val):
        if var.concretetype is not lltype.Void:
            try:
                val = lltype.enforce(var.concretetype, val)
            except TypeError:
                assert False, "type error: input value of type:\n\n\t%r\n\n===> variable of type:\n\n\t%r\n" % (lltype.typeOf(val), var.concretetype)
        assert isinstance(var, Variable)
        self.bindings[var] = val

    def setifvar(self, var, val):
        if isinstance(var, Variable):
            self.setvar(var, val)

    def getval(self, varorconst):
        try:
            val = varorconst.value
        except AttributeError:
            val = self.bindings[varorconst]
        if isinstance(val, ComputedIntSymbolic):
            val = val.compute_fn()
        if varorconst.concretetype is not lltype.Void:
            try:
                val = lltype.enforce(varorconst.concretetype, val)
            except TypeError:
                assert False, "type error: %r val from %r var/const" % (lltype.typeOf(val), varorconst.concretetype)
        return val

    def getval_or_subop(self, varorsubop):
        from pypy.translator.oosupport.treebuilder import SubOperation
        if isinstance(varorsubop, SubOperation):
            self.eval_operation(varorsubop.op)
            resultval = self.getval(varorsubop.op.result)
            del self.bindings[varorsubop.op.result] # XXX hack
            return resultval
        else:
            return self.getval(varorsubop)

    # _______________________________________________________
    # other helpers
    def getoperationhandler(self, opname):
        ophandler = getattr(self, 'op_' + opname, None)
        if ophandler is None:
            # try to import the operation from opimpl.py
            ophandler = lloperation.LL_OPERATIONS[opname].fold
            setattr(self.__class__, 'op_' + opname, staticmethod(ophandler))
        return ophandler
    # _______________________________________________________
    # evaling functions

    def eval(self):
        graph = self.graph
        tracer = self.llinterpreter.tracer
        if tracer:
            tracer.enter(graph)
        self.llinterpreter.frame_stack.append(self)
        try:
            try:
                nextblock = graph.startblock
                args = self.args
                while 1:
                    self.clear()
                    self.fillvars(nextblock, args)
                    nextblock, args = self.eval_block(nextblock)
                    if nextblock is None:
                        for obj in self.alloca_objects:
                            obj._obj._free()
                        return args
            except Exception:
                self.llinterpreter.traceback_frames.append(self)
                raise
        finally:
            leavingframe = self.llinterpreter.frame_stack.pop()
            assert leavingframe is self
            if tracer:
                tracer.leave()

    def eval_block(self, block):
        """ return (nextblock, values) tuple. If nextblock
            is None, values is the concrete return value.
        """
        self.curr_block = block
        catch_exception = block.exitswitch == c_last_exception
        e = None

        try:
            for i, op in enumerate(block.operations):
                self.curr_operation_index = i
                self.eval_operation(op)
        except LLException, e:
            if not (catch_exception and op is block.operations[-1]):
                raise
        except RuntimeError, e:
            rstackovf.check_stack_overflow()
            # xxx fish fish fish for proper etype and evalue to use
            rtyper = self.llinterpreter.typer
            bk = rtyper.annotator.bookkeeper
            classdef = bk.getuniqueclassdef(rstackovf._StackOverflow)
            exdata = rtyper.getexceptiondata()
            evalue = exdata.get_standard_ll_exc_instance(rtyper, classdef)
            etype = exdata.fn_type_of_exc_inst(evalue)
            e = LLException(etype, evalue)
            if not (catch_exception and op is block.operations[-1]):
                raise e

        # determine nextblock and/or return value
        if len(block.exits) == 0:
            # return block
            tracer = self.llinterpreter.tracer
            if len(block.inputargs) == 2:
                # exception
                if tracer:
                    tracer.dump('raise')
                etypevar, evaluevar = block.getvariables()
                etype = self.getval(etypevar)
                evalue = self.getval(evaluevar)
                # watch out, these are _ptr's
                raise LLException(etype, evalue)
            resultvar, = block.getvariables()
            result = self.getval(resultvar)
            exc_data = self.llinterpreter.get_transformed_exc_data(self.graph)
            if exc_data:
                # re-raise the exception set by this graph, if any
                etype = exc_data.exc_type
                if etype:
                    evalue = exc_data.exc_value
                    if tracer:
                        tracer.dump('raise')
                    exc_data.exc_type  = lltype.typeOf(etype )._defl()
                    exc_data.exc_value = lltype.typeOf(evalue)._defl()
                    from pypy.translator import exceptiontransform
                    T = resultvar.concretetype
                    errvalue = exceptiontransform.error_value(T)
                    # check that the exc-transformed graph returns the error
                    # value when it returns with an exception set
                    assert result == errvalue
                    raise LLException(etype, evalue)
            if tracer:
                tracer.dump('return')
            return None, result
        elif block.exitswitch is None:
            # single-exit block
            assert len(block.exits) == 1
            link = block.exits[0]
        elif catch_exception:
            link = block.exits[0]
            if e:
                exdata = self.llinterpreter.typer.getexceptiondata()
                cls = e.args[0]
                inst = e.args[1]
                for link in block.exits[1:]:
                    assert issubclass(link.exitcase, py.builtin.BaseException)
                    if self.op_direct_call(exdata.fn_exception_match,
                                           cls, link.llexitcase):
                        self.setifvar(link.last_exception, cls)
                        self.setifvar(link.last_exc_value, inst)
                        break
                else:
                    # no handler found, pass on
                    raise e
        else:
            llexitvalue = self.getval(block.exitswitch)
            if block.exits[-1].exitcase == "default":
                defaultexit = block.exits[-1]
                nondefaultexits = block.exits[:-1]
                assert defaultexit.llexitcase is None
            else:
                defaultexit = None
                nondefaultexits = block.exits
            for link in nondefaultexits:
                if link.llexitcase == llexitvalue:
                    break   # found -- the result is in 'link'
            else:
                if defaultexit is None:
                    raise ValueError("exit case %r not found in the exit links "
                                     "of %r" % (llexitvalue, block))
                else:
                    link = defaultexit
        return link.target, [self.getval(x) for x in link.args]

    def eval_operation(self, operation):
        tracer = self.llinterpreter.tracer
        if tracer:
            tracer.dump(str(operation))
        ophandler = self.getoperationhandler(operation.opname)
        # XXX slighly unnice but an important safety check
        if operation.opname == 'direct_call':
            assert isinstance(operation.args[0], Constant)
        elif operation.opname == 'indirect_call':
            assert isinstance(operation.args[0], Variable)
        if getattr(ophandler, 'specialform', False):
            retval = ophandler(*operation.args)
        else:
            vals = [self.getval_or_subop(x) for x in operation.args]
            if getattr(ophandler, 'need_result_type', False):
                vals.insert(0, operation.result.concretetype)
            try:
                retval = ophandler(*vals)
            except LLException, e:
                # safety check check that the operation is allowed to raise that
                # exception
                if operation.opname in lloperation.LL_OPERATIONS:
                    canraise = lloperation.LL_OPERATIONS[operation.opname].canraise
                    if Exception not in canraise:
                        exc = self.llinterpreter.find_exception(e)
                        for canraiseexc in canraise:
                            if issubclass(exc, canraiseexc):
                                break
                        else:
                            raise TypeError("the operation %s is not expected to raise %s" % (operation, exc))

                # for exception-transformed graphs, store the LLException
                # into the exc_data used by this graph
                exc_data = self.llinterpreter.get_transformed_exc_data(
                    self.graph)
                if exc_data:
                    etype = e.args[0]
                    evalue = e.args[1]
                    exc_data.exc_type  = etype
                    exc_data.exc_value = evalue
                    from pypy.translator import exceptiontransform
                    retval = exceptiontransform.error_value(
                        operation.result.concretetype)
                else:
                    raise
        self.setvar(operation.result, retval)
        if tracer:
            if retval is None:
                tracer.dump('\n')
            else:
                tracer.dump('   ---> %r\n' % (retval,))

    def make_llexception(self, exc=None):
        if exc is None:
            original = sys.exc_info()
            exc = original[1]
            # it makes no sense to convert some exception classes that
            # just mean something buggy crashed
            if isinstance(exc, (AssertionError, AttributeError,
                                TypeError, NameError,
                                KeyboardInterrupt, SystemExit,
                                ImportError, SyntaxError)):
                raise original[0], original[1], original[2]     # re-raise it
            # for testing the JIT (see ContinueRunningNormally) we need
            # to let some exceptions introduced by the JIT go through
            # the llinterpreter uncaught
            if getattr(exc, '_go_through_llinterp_uncaught_', False):
                raise original[0], original[1], original[2]     # re-raise it
            extraargs = (original,)
        else:
            extraargs = ()
        typer = self.llinterpreter.typer
        exdata = typer.getexceptiondata()
        if isinstance(exc, OSError):
            self.op_direct_call(exdata.fn_raise_OSError, exc.errno)
            assert False, "op_direct_call above should have raised"
        else:
            exc_class = exc.__class__
            evalue = self.op_direct_call(exdata.fn_pyexcclass2exc,
                                         self.heap.pyobjectptr(exc_class))
            etype = self.op_direct_call(exdata.fn_type_of_exc_inst, evalue)
        raise LLException(etype, evalue, *extraargs)

    def invoke_callable_with_pyexceptions(self, fptr, *args):
        obj = self.llinterpreter.typer.type_system.deref(fptr)
        try:
            return obj._callable(*args)
        except LLException, e:
            raise
        except Exception, e:
            if getattr(e, '_go_through_llinterp_uncaught_', False):
                raise
            if getattr(obj, '_debugexc', False):
                log.ERROR('The llinterpreter got an '
                          'unexpected exception when calling')
                log.ERROR('the external function %r:' % (fptr,))
                log.ERROR('%s: %s' % (e.__class__.__name__, e))
                if self.llinterpreter.tracer:
                    self.llinterpreter.tracer.flush()
                import sys
                from pypy.translator.tool.pdbplus import PdbPlusShow
                PdbPlusShow(None).post_mortem(sys.exc_info()[2])
            self.make_llexception()

    def find_roots(self, roots):
        #log.findroots(self.curr_block.inputargs)
        vars = []
        for v in self.curr_block.inputargs:
            if isinstance(v, Variable):
                vars.append(v)
        for op in self.curr_block.operations[:self.curr_operation_index]:
            vars.append(op.result)

        for v in vars:
            TYPE = getattr(v, 'concretetype', None)
            if isinstance(TYPE, lltype.Ptr) and TYPE.TO._gckind == 'gc':
                roots.append(_address_of_local_var(self, v))

    # __________________________________________________________
    # misc LL operation implementations

    def op_debug_view(self, *ll_objects):
        from pypy.translator.tool.lltracker import track
        track(*ll_objects)

    def op_debug_assert(self, x, msg):
        assert x, msg

    def op_debug_fatalerror(self, ll_msg, ll_exc=None):
        msg = ''.join(ll_msg.chars)
        if ll_exc is None:
            raise LLFatalError(msg)
        else:
            ll_exc_type = lltype.cast_pointer(rclass.OBJECTPTR, ll_exc).typeptr
            raise LLFatalError(msg, LLException(ll_exc_type, ll_exc))

    def op_debug_llinterpcall(self, pythonfunction, *args_ll):
        try:
            return pythonfunction(*args_ll)
        except:
            self.make_llexception()

    def op_debug_start_traceback(self, *args):
        pass    # xxx write debugging code here?

    def op_debug_reraise_traceback(self, *args):
        pass    # xxx write debugging code here?

    def op_debug_record_traceback(self, *args):
        pass    # xxx write debugging code here?

    def op_debug_print_traceback(self, *args):
        pass    # xxx write debugging code here?

    def op_debug_catch_exception(self, *args):
        pass    # xxx write debugging code here?

    def op_jit_marker(self, *args):
        pass

    def op_get_exception_addr(self, *args):
        raise NotImplementedError

    def op_get_exc_value_addr(self, *args):
        raise NotImplementedError

    def op_instrument_count(self, ll_tag, ll_label):
        pass # xxx for now

    def op_keepalive(self, value):
        pass

    def op_hint(self, x, hints):
        return x

    def op_decode_arg(self, fname, i, name, vargs, vkwds):
        raise NotImplementedError("decode_arg")

    def op_decode_arg_def(self, fname, i, name, vargs, vkwds, default):
        raise NotImplementedError("decode_arg_def")

    def op_check_no_more_arg(self, fname, n, vargs):
        raise NotImplementedError("check_no_more_arg")

    def op_getslice(self, vargs, start, stop_should_be_None):
        raise NotImplementedError("getslice")   # only for argument parsing

    def op_check_self_nonzero(self, fname, vself):
        raise NotImplementedError("check_self_nonzero")

    def op_setfield(self, obj, fieldname, fieldvalue):
        # obj should be pointer
        FIELDTYPE = getattr(lltype.typeOf(obj).TO, fieldname)
        if FIELDTYPE is not lltype.Void:
            self.heap.setfield(obj, fieldname, fieldvalue)

    def op_bare_setfield(self, obj, fieldname, fieldvalue):
        # obj should be pointer
        FIELDTYPE = getattr(lltype.typeOf(obj).TO, fieldname)
        if FIELDTYPE is not lltype.Void:
            setattr(obj, fieldname, fieldvalue)

    def op_getinteriorfield(self, obj, *offsets):
        checkptr(obj)
        ob = obj
        for o in offsets:
            if isinstance(o, str):
                ob = getattr(ob, o)
            else:
                ob = ob[o]
        assert not isinstance(ob, lltype._interior_ptr)
        return ob

    def getinneraddr(self, obj, *offsets):
        TYPE = lltype.typeOf(obj).TO
        addr = llmemory.cast_ptr_to_adr(obj)
        for o in offsets:
            if isinstance(o, str):
                addr += llmemory.offsetof(TYPE, o)
                TYPE = getattr(TYPE, o)
            else:
                addr += llmemory.itemoffsetof(TYPE, o)
                TYPE = TYPE.OF
        return addr, TYPE

    def op_setinteriorfield(self, obj, *fieldnamesval):
        offsets, fieldvalue = fieldnamesval[:-1], fieldnamesval[-1]
        inneraddr, FIELD = self.getinneraddr(obj, *offsets)
        if FIELD is not lltype.Void:
            self.heap.setinterior(obj, inneraddr, FIELD, fieldvalue, offsets)

    def op_bare_setinteriorfield(self, obj, *fieldnamesval):
        offsets, fieldvalue = fieldnamesval[:-1], fieldnamesval[-1]
        inneraddr, FIELD = self.getinneraddr(obj, *offsets)
        if FIELD is not lltype.Void:
            llheap.setinterior(obj, inneraddr, FIELD, fieldvalue)

    def op_getarrayitem(self, array, index):
        return array[index]

    def op_setarrayitem(self, array, index, item):
        # array should be a pointer
        ITEMTYPE = lltype.typeOf(array).TO.OF
        if ITEMTYPE is not lltype.Void:
            self.heap.setarrayitem(array, index, item)

    def op_bare_setarrayitem(self, array, index, item):
        # array should be a pointer
        ITEMTYPE = lltype.typeOf(array).TO.OF
        if ITEMTYPE is not lltype.Void:
            array[index] = item


    def perform_call(self, f, ARGS, args):
        fobj = self.llinterpreter.typer.type_system.deref(f)
        has_callable = getattr(fobj, '_callable', None) is not None
        if hasattr(fobj, 'graph'):
            graph = fobj.graph
        else:
            assert has_callable, "don't know how to execute %r" % f
            return self.invoke_callable_with_pyexceptions(f, *args)
        args_v = graph.getargs()
        if len(ARGS) != len(args_v):
            raise TypeError("graph with %d args called with wrong func ptr type: %r" %(len(args_v), ARGS)) 
        for T, v in zip(ARGS, args_v):
            if not lltype.isCompatibleType(T, v.concretetype):
                raise TypeError("graph with %r args called with wrong func ptr type: %r" %
                                (tuple([v.concretetype for v in args_v]), ARGS)) 
        frame = self.newsubframe(graph, args)
        return frame.eval()

    def op_direct_call(self, f, *args):
        FTYPE = self.llinterpreter.typer.type_system.derefType(lltype.typeOf(f))
        return self.perform_call(f, FTYPE.ARGS, args)

    def op_indirect_call(self, f, *args):
        graphs = args[-1]
        args = args[:-1]
        if graphs is not None:
            obj = self.llinterpreter.typer.type_system.deref(f)
            if hasattr(obj, 'graph'):
                assert obj.graph in graphs 
        else:
            pass
            #log.warn("op_indirect_call with graphs=None:", f)
        return self.op_direct_call(f, *args)

    def op_malloc(self, obj, flags):
        flavor = flags['flavor']
        zero = flags.get('zero', False)
        track_allocation = flags.get('track_allocation', True)
        if flavor == "stack":
            result = self.heap.malloc(obj, zero=zero, flavor='raw')
            self.alloca_objects.append(result)
            return result
        ptr = self.heap.malloc(obj, zero=zero, flavor=flavor,
                               track_allocation=track_allocation)
        return ptr

    def op_malloc_varsize(self, obj, flags, size):
        flavor = flags['flavor']
        zero = flags.get('zero', False)
        track_allocation = flags.get('track_allocation', True)
        assert flavor in ('gc', 'raw')
        try:
            ptr = self.heap.malloc(obj, size, zero=zero, flavor=flavor,
                                   track_allocation=track_allocation)
            return ptr
        except MemoryError:
            self.make_llexception()

    def op_malloc_nonmovable(self, TYPE, flags):
        flavor = flags['flavor']
        assert flavor == 'gc'
        zero = flags.get('zero', False)
        return self.heap.malloc_nonmovable(TYPE, zero=zero)

    def op_malloc_nonmovable_varsize(self, TYPE, flags, size):
        flavor = flags['flavor']
        assert flavor == 'gc'
        zero = flags.get('zero', False)
        return self.heap.malloc_nonmovable(TYPE, size, zero=zero)

    def op_free(self, obj, flags):
        assert flags['flavor'] == 'raw'
        track_allocation = flags.get('track_allocation', True)
        self.heap.free(obj, flavor='raw', track_allocation=track_allocation)

    def add_memory_pressure(self, size):
        self.heap.add_memory_pressure(size)

    def op_shrink_array(self, obj, smallersize):
        return self.heap.shrink_array(obj, smallersize)

    def op_zero_gc_pointers_inside(self, obj):
        raise NotImplementedError("zero_gc_pointers_inside")

    def op_gc_writebarrier_before_copy(self, source, dest,
                                       source_start, dest_start, length):
        if hasattr(self.heap, 'writebarrier_before_copy'):
            return self.heap.writebarrier_before_copy(source, dest,
                                                      source_start, dest_start,
                                                      length)
        else:
            return True

    def op_getfield(self, obj, field):
        checkptr(obj)
        # check the difference between op_getfield and op_getsubstruct:
        assert not isinstance(getattr(lltype.typeOf(obj).TO, field),
                              lltype.ContainerType)
        return getattr(obj, field)

    def op_force_cast(self, RESTYPE, obj):
        from pypy.rpython.lltypesystem import ll2ctypes
        return ll2ctypes.force_cast(RESTYPE, obj)
    op_force_cast.need_result_type = True

    def op_cast_int_to_ptr(self, RESTYPE, int1):
        return lltype.cast_int_to_ptr(RESTYPE, int1)
    op_cast_int_to_ptr.need_result_type = True

    def op_cast_ptr_to_int(self, ptr1):
        checkptr(ptr1)
        return lltype.cast_ptr_to_int(ptr1)

    def op_cast_opaque_ptr(self, RESTYPE, obj):
        checkptr(obj)
        return lltype.cast_opaque_ptr(RESTYPE, obj)
    op_cast_opaque_ptr.need_result_type = True

    def op_cast_ptr_to_adr(self, ptr):
        checkptr(ptr)
        return llmemory.cast_ptr_to_adr(ptr)

    def op_cast_adr_to_int(self, adr, mode):
        checkadr(adr)
        return llmemory.cast_adr_to_int(adr, mode)

    def op_weakref_create(self, v_obj):
        def objgetter():    # special support for gcwrapper.py
            return self.getval(v_obj)
        return self.heap.weakref_create_getlazy(objgetter)
    op_weakref_create.specialform = True

    def op_weakref_deref(self, PTRTYPE, obj):
        return self.heap.weakref_deref(PTRTYPE, obj)
    op_weakref_deref.need_result_type = True

    def op_cast_ptr_to_weakrefptr(self, obj):
        return llmemory.cast_ptr_to_weakrefptr(obj)

    def op_cast_weakrefptr_to_ptr(self, PTRTYPE, obj):
        return llmemory.cast_weakrefptr_to_ptr(PTRTYPE, obj)
    op_cast_weakrefptr_to_ptr.need_result_type = True

    def op_gc__collect(self, *gen):
        self.heap.collect(*gen)

    def op_gc_heap_stats(self):
        raise NotImplementedError

    def op_gc_obtain_free_space(self, size):
        raise NotImplementedError

    def op_gc_can_move(self, ptr):
        addr = llmemory.cast_ptr_to_adr(ptr)
        return self.heap.can_move(addr)

    def op_gc_thread_prepare(self):
        self.heap.thread_prepare()

    def op_gc_thread_run(self):
        self.heap.thread_run()

    def op_gc_thread_start(self):
        self.heap.thread_start()

    def op_gc_thread_die(self):
        self.heap.thread_die()

    def op_gc_thread_before_fork(self):
        raise NotImplementedError

    def op_gc_thread_after_fork(self):
        raise NotImplementedError

    def op_gc_free(self, addr):
        # what can you do?
        pass
        #raise NotImplementedError("gc_free")

    def op_gc_fetch_exception(self):
        raise NotImplementedError("gc_fetch_exception")

    def op_gc_restore_exception(self, exc):
        raise NotImplementedError("gc_restore_exception")

    def op_gc_adr_of_nursery_top(self):
        raise NotImplementedError
    def op_gc_adr_of_nursery_free(self):
        raise NotImplementedError

    def op_gc_adr_of_root_stack_base(self):
        raise NotImplementedError
    def op_gc_adr_of_root_stack_top(self):
        raise NotImplementedError

    def op_gc_call_rtti_destructor(self, rtti, addr):
        if hasattr(rtti._obj, 'destructor_funcptr'):
            d = rtti._obj.destructor_funcptr
            obptr = addr.ref()
            return self.op_direct_call(d, obptr)

    def op_gc_deallocate(self, TYPE, addr):
        raise NotImplementedError("gc_deallocate")

    def op_gc_push_alive_pyobj(self, pyobj):
        raise NotImplementedError("gc_push_alive_pyobj")

    def op_gc_pop_alive_pyobj(self, pyobj):
        raise NotImplementedError("gc_pop_alive_pyobj")

    def op_gc_reload_possibly_moved(self, v_newaddr, v_ptr):
        assert v_newaddr.concretetype is llmemory.Address
        assert isinstance(v_ptr.concretetype, lltype.Ptr)
        assert v_ptr.concretetype.TO._gckind == 'gc'
        newaddr = self.getval(v_newaddr)
        p = llmemory.cast_adr_to_ptr(newaddr, v_ptr.concretetype)
        if isinstance(v_ptr, Constant):
            assert v_ptr.value == p
        else:
            self.setvar(v_ptr, p)
    op_gc_reload_possibly_moved.specialform = True

    def op_gc_identityhash(self, obj):
        return lltype.identityhash(obj)

    def op_gc_id(self, ptr):
        PTR = lltype.typeOf(ptr)
        if isinstance(PTR, lltype.Ptr):
            return self.heap.gc_id(ptr)
        elif isinstance(PTR, ootype.OOType):
            return ootype.identityhash(ptr)     # XXX imprecise
        raise NotImplementedError("gc_id on %r" % (PTR,))

    def op_gc_set_max_heap_size(self, maxsize):
        raise NotImplementedError("gc_set_max_heap_size")

    def op_gc_asmgcroot_static(self, index):
        raise NotImplementedError("gc_asmgcroot_static")

    def op_gc_stack_bottom(self):
        pass       # marker for trackgcroot.py

    def op_gc_shadowstackref_new(self):   # stacklet+shadowstack
        raise NotImplementedError("gc_shadowstackref_new")
    def op_gc_shadowstackref_context(self):
        raise NotImplementedError("gc_shadowstackref_context")
    def op_gc_shadowstackref_destroy(self):
        raise NotImplementedError("gc_shadowstackref_destroy")
    def op_gc_save_current_state_away(self):
        raise NotImplementedError("gc_save_current_state_away")
    def op_gc_forget_current_state(self):
        raise NotImplementedError("gc_forget_current_state")
    def op_gc_restore_state_from(self):
        raise NotImplementedError("gc_restore_state_from")
    def op_gc_start_fresh_new_state(self):
        raise NotImplementedError("gc_start_fresh_new_state")

    def op_gc_get_type_info_group(self):
        raise NotImplementedError("gc_get_type_info_group")

    def op_gc_get_rpy_memory_usage(self):
        raise NotImplementedError("gc_get_rpy_memory_usage")

    def op_gc_get_rpy_roots(self):
        raise NotImplementedError("gc_get_rpy_roots")

    def op_gc_get_rpy_referents(self):
        raise NotImplementedError("gc_get_rpy_referents")

    def op_gc_is_rpy_instance(self):
        raise NotImplementedError("gc_is_rpy_instance")

    def op_gc_get_rpy_type_index(self):
        raise NotImplementedError("gc_get_rpy_type_index")

    def op_gc_dump_rpy_heap(self):
        raise NotImplementedError("gc_dump_rpy_heap")

    def op_gc_typeids_z(self):
        raise NotImplementedError("gc_typeids_z")

    def op_do_malloc_fixedsize_clear(self):
        raise NotImplementedError("do_malloc_fixedsize_clear")

    def op_do_malloc_varsize_clear(self):
        raise NotImplementedError("do_malloc_varsize_clear")

    def op_get_write_barrier_failing_case(self):
        raise NotImplementedError("get_write_barrier_failing_case")

    def op_get_write_barrier_from_array_failing_case(self):
        raise NotImplementedError("get_write_barrier_from_array_failing_case")

    def op_stack_current(self):
        return 0

    # operations on pyobjects!
    for opname in lloperation.opimpls.keys():
        exec py.code.Source("""
        def op_%(opname)s(self, *pyobjs):
            for pyo in pyobjs:
                assert lltype.typeOf(pyo) == lltype.Ptr(lltype.PyObject)
            func = lloperation.opimpls[%(opname)r]
            try:
                pyo = func(*[pyo._obj.value for pyo in pyobjs])
            except Exception:
                self.make_llexception()
            return self.heap.pyobjectptr(pyo)
        """ % locals()).compile()
    del opname

    def op_simple_call(self, f, *args):
        assert lltype.typeOf(f) == lltype.Ptr(lltype.PyObject)
        for pyo in args:
            assert lltype.typeOf(pyo) == lltype.Ptr(lltype.PyObject)
        res = f._obj.value(*[pyo._obj.value for pyo in args])
        return self.heap.pyobjectptr(res)

    # __________________________________________________________
    # operations on addresses

    def op_raw_malloc(self, size):
        assert lltype.typeOf(size) == lltype.Signed
        return llmemory.raw_malloc(size)

    op_boehm_malloc = op_boehm_malloc_atomic = op_raw_malloc

    def op_boehm_register_finalizer(self, p, finalizer):
        pass

    def op_boehm_disappearing_link(self, link, obj):
        pass

    def op_raw_malloc_usage(self, size):
        assert lltype.typeOf(size) == lltype.Signed
        return llmemory.raw_malloc_usage(size)

    def op_raw_free(self, addr):
        checkadr(addr) 
        llmemory.raw_free(addr)

    def op_raw_memclear(self, addr, size):
        checkadr(addr)
        llmemory.raw_memclear(addr, size)

    def op_raw_memcopy(self, fromaddr, toaddr, size):
        checkadr(fromaddr)
        checkadr(toaddr)
        llmemory.raw_memcopy(fromaddr, toaddr, size)

    op_raw_memmove = op_raw_memcopy # this is essentially the same here

    def op_raw_load(self, addr, typ, offset):
        checkadr(addr)
        value = getattr(addr, str(typ).lower())[offset]
        assert lltype.typeOf(value) == typ
        return value

    def op_raw_store(self, addr, typ, offset, value):
        checkadr(addr)
        assert lltype.typeOf(value) == typ
        getattr(addr, str(typ).lower())[offset] = value

    def op_stack_malloc(self, size): # mmh
        raise NotImplementedError("backend only")

    def op_track_alloc_start(self, addr):
        # we don't do tracking at this level
        checkadr(addr)

    def op_track_alloc_stop(self, addr):
        checkadr(addr)

    # ____________________________________________________________
    # Overflow-detecting variants

    def op_int_neg_ovf(self, x):
        assert type(x) is int
        try:
            return ovfcheck(-x)
        except OverflowError:
            self.make_llexception()

    def op_int_abs_ovf(self, x):
        assert type(x) is int
        try:
            return ovfcheck(abs(x))
        except OverflowError:
            self.make_llexception()

    def op_int_lshift_ovf(self, x, y):
        assert isinstance(x, int)
        assert isinstance(y, int)
        try:
            return ovfcheck_lshift(x, y)
        except OverflowError:
            self.make_llexception()

    def _makefunc2(fn, operator, xtype, ytype=None):
        import sys
        d = sys._getframe(1).f_locals
        if ytype is None:
            ytype = xtype
        if '_ovf' in fn:
            checkfn = 'ovfcheck'
        elif fn.startswith('op_int_'):
            checkfn = 'intmask'
        else:
            checkfn = ''
        if operator == '//':
            code = '''r = %(checkfn)s(x // y)
                if x^y < 0 and x%%y != 0:
                    r += 1
                return r
                '''%locals()
        elif operator == '%':
            code = '''r = %(checkfn)s(x %% y)
                if x^y < 0 and x%%y != 0:
                    r -= y
                return r
                '''%locals()
        else:
            code = 'return %(checkfn)s(x %(operator)s y)'%locals()
        exec py.code.Source("""
        def %(fn)s(self, x, y):
            assert isinstance(x, %(xtype)s)
            assert isinstance(y, %(ytype)s)
            try:
                %(code)s
            except (OverflowError, ValueError, ZeroDivisionError):
                self.make_llexception()
        """ % locals()).compile() in globals(), d

    _makefunc2('op_int_add_ovf', '+', '(int, llmemory.AddressOffset)')
    _makefunc2('op_int_mul_ovf', '*', '(int, llmemory.AddressOffset)', 'int')
    _makefunc2('op_int_sub_ovf',          '-',  'int')
    _makefunc2('op_int_floordiv_ovf',     '//', 'int')  # XXX negative args
    _makefunc2('op_int_floordiv_zer',     '//', 'int')  # can get off-by-one
    _makefunc2('op_int_floordiv_ovf_zer', '//', 'int')  # (see op_int_floordiv)
    _makefunc2('op_int_mod_ovf',          '%',  'int')
    _makefunc2('op_int_mod_zer',          '%',  'int')
    _makefunc2('op_int_mod_ovf_zer',      '%',  'int')

    _makefunc2('op_uint_floordiv_zer',    '//', 'r_uint')
    _makefunc2('op_uint_mod_zer',         '%',  'r_uint')

    _makefunc2('op_llong_floordiv_zer',   '//', 'r_longlong')
    _makefunc2('op_llong_mod_zer',        '%',  'r_longlong')

    _makefunc2('op_ullong_floordiv_zer',  '//', 'r_ulonglong')
    _makefunc2('op_ullong_mod_zer',       '%',  'r_ulonglong')

    def op_int_add_nonneg_ovf(self, x, y):
        if isinstance(y, int):
            assert y >= 0
        return self.op_int_add_ovf(x, y)

    def op_cast_float_to_int(self, f):
        assert type(f) is float
        try:
            return ovfcheck(int(f))
        except OverflowError:
            self.make_llexception()

    def op_int_is_true(self, x):
        # special case
        if type(x) is CDefinedIntSymbolic:
            x = x.default
        # if type(x) is a subclass of Symbolic, bool(x) will usually raise
        # a TypeError -- unless __nonzero__ has been explicitly overridden.
        assert isinstance(x, (int, Symbolic))
        return bool(x)

    # hack for jit.codegen.llgraph

    def op_check_and_clear_exc(self):
        exc_data = self.llinterpreter.get_transformed_exc_data(self.graph)
        assert exc_data
        etype  = exc_data.exc_type
        evalue = exc_data.exc_value
        exc_data.exc_type  = lltype.typeOf(etype )._defl()
        exc_data.exc_value = lltype.typeOf(evalue)._defl()
        return bool(etype)

    #Operation of ootype

    def op_new(self, INST):
        assert isinstance(INST, (ootype.Instance, ootype.BuiltinType))
        return ootype.new(INST)
        
    def op_oonewarray(self, ARRAY, length):
        assert isinstance(ARRAY, ootype.Array)
        assert isinstance(length, int)
        return ootype.oonewarray(ARRAY, length)

    def op_runtimenew(self, class_):
        return ootype.runtimenew(class_)

    def op_oonewcustomdict(self, DICT, eq_func, eq_obj, eq_method_name,
                           hash_func, hash_obj, hash_method_name):
        eq_name, interp_eq = \
                 wrap_callable(self.llinterpreter, eq_func, eq_obj, eq_method_name)
        EQ_FUNC = ootype.StaticMethod([DICT._KEYTYPE, DICT._KEYTYPE], ootype.Bool)
        sm_eq = ootype.static_meth(EQ_FUNC, eq_name, _callable=interp_eq)        

        hash_name, interp_hash = \
                   wrap_callable(self.llinterpreter, hash_func, hash_obj, hash_method_name)
        HASH_FUNC = ootype.StaticMethod([DICT._KEYTYPE], ootype.Signed)
        sm_hash = ootype.static_meth(HASH_FUNC, hash_name, _callable=interp_hash)

        # XXX: is it fine to have StaticMethod type for bound methods, too?
        return ootype.oonewcustomdict(DICT, sm_eq, sm_hash)

    def op_oosetfield(self, inst, name, value):
        checkinst(inst)
        assert isinstance(name, str)
        FIELDTYPE = lltype.typeOf(inst)._field_type(name)
        if FIELDTYPE is not lltype.Void:
            setattr(inst, name, value)

    def op_oogetfield(self, inst, name):
        checkinst(inst)
        assert isinstance(name, str)
        return getattr(inst, name)

    def op_oosend(self, message, inst, *args):
        checkinst(inst)
        assert isinstance(message, str)
        bm = getattr(inst, message)
        inst = bm.inst
        m = bm.meth
        args = m._checkargs(args, check_callable=False)
        if getattr(m, 'abstract', False):
            raise RuntimeError("calling abstract method %r" % (m,))
        return self.perform_call(m, (lltype.typeOf(inst),)+lltype.typeOf(m).ARGS, [inst]+args)

    def op_oostring(self, obj, base):
        return ootype.oostring(obj, base)

    def op_oounicode(self, obj, base):
        try:
            return ootype.oounicode(obj, base)
        except UnicodeDecodeError:
            self.make_llexception()

    def op_ooparse_int(self, s, base):
        try:
            return ootype.ooparse_int(s, base)
        except ValueError:
            self.make_llexception()

    def op_ooparse_float(self, s):
        try:
            return ootype.ooparse_float(s)
        except ValueError:
            self.make_llexception()

    def op_oobox_int(self, i):
        return ootype.oobox_int(i)

    def op_oounbox_int(self, x):
        return ootype.oounbox_int(x)

class Tracer(object):
    Counter = 0
    file = None
    TRACE = int(os.getenv('PYPY_TRACE') or '0')

    HEADER = """<html><head>
        <script language=javascript type='text/javascript'>
        function togglestate(n) {
          var item = document.getElementById('div'+n)
          if (item.style.display == 'none')
            item.style.display = 'block';
          else
            item.style.display = 'none';
        }

        function toggleall(lst) {
          for (var i = 0; i<lst.length; i++) {
            togglestate(lst[i]);
          }
        }
        </script>
        </head>

        <body><pre>
    """

    FOOTER = """</pre>
        <script language=javascript type='text/javascript'>
        toggleall(%r);
        </script>

    </body></html>"""

    ENTER = ('''\n\t<a href="javascript:togglestate(%d)">%s</a>'''
             '''\n<div id="div%d" style="display: %s">\t''')
    LEAVE = '''\n</div>\t'''

    def htmlquote(self, s, text_to_html={}):
        # HTML quoting, lazily initialized
        if not text_to_html:
            import htmlentitydefs
            for key, value in htmlentitydefs.entitydefs.items():
                text_to_html[value] = '&' + key + ';'
        return ''.join([text_to_html.get(c, c) for c in s])

    def start(self):
        # start of a dump file
        if not self.TRACE:
            return
        from pypy.tool.udir import udir
        n = Tracer.Counter
        Tracer.Counter += 1
        filename = 'llinterp_trace_%d.html' % n
        self.file = udir.join(filename).open('w')
        print >> self.file, self.HEADER

        linkname = str(udir.join('llinterp_trace.html'))
        try:
            os.unlink(linkname)
        except OSError:
            pass
        try:
            os.symlink(filename, linkname)
        except (AttributeError, OSError):
            pass

        self.count = 0
        self.indentation = ''
        self.depth = 0
        self.latest_call_chain = []

    def stop(self):
        # end of a dump file
        if self.file:
            print >> self.file, self.FOOTER % (self.latest_call_chain[1:])
            self.file.close()
            self.file = None

    def enter(self, graph):
        # enter evaluation of a graph
        if self.file:
            del self.latest_call_chain[self.depth:]
            self.depth += 1
            self.latest_call_chain.append(self.count)
            s = self.htmlquote(str(graph))
            i = s.rfind(')')
            s = s[:i+1] + '<b>' + s[i+1:] + '</b>'
            if self.count == 0:
                display = 'block'
            else:
                display = 'none'
            text = self.ENTER % (self.count, s, self.count, display)
            self.indentation += '    '
            self.file.write(text.replace('\t', self.indentation))
            self.count += 1

    def leave(self):
        # leave evaluation of a graph
        if self.file:
            self.indentation = self.indentation[:-4]
            self.file.write(self.LEAVE.replace('\t', self.indentation))
            self.depth -= 1

    def dump(self, text, bold=False):
        if self.file:
            text = self.htmlquote(text)
            if bold:
                text = '<b>%s</b>' % (text,)
            self.file.write(text.replace('\n', '\n'+self.indentation))

    def flush(self):
        if self.file:
            self.file.flush()

def wrap_callable(llinterpreter, fn, obj, method_name):
    if method_name is None:
        # fn is a StaticMethod
        if obj is not None:
            self_arg = [obj]
        else:
            self_arg = []
        func_graph = fn.graph
    else:
        # obj is an instance, we want to call 'method_name' on it
        assert fn is None
        self_arg = [obj]
        func_graph = obj._TYPE._methods[method_name._str].graph

    return wrap_graph(llinterpreter, func_graph, self_arg)

def wrap_graph(llinterpreter, graph, self_arg):
    """
    Returns a callable that inteprets the given func or method_name when called.
    """

    def interp_func(*args):
        graph_args = self_arg + list(args)
        return llinterpreter.eval_graph(graph, args=graph_args)
    interp_func.graph = graph
    interp_func.self_arg = self_arg
    return graph.name, interp_func


def enumerate_exceptions_top_down():
    import exceptions
    result = []
    seen = {}
    def addcls(cls):
        if (type(cls) is type(Exception) and
            issubclass(cls, py.builtin.BaseException)):
            if cls in seen:
                return
            for base in cls.__bases__:   # bases first
                addcls(base)
            result.append(cls)
            seen[cls] = True
    for cls in exceptions.__dict__.values():
        addcls(cls)
    return result

class _address_of_local_var(object):
    _TYPE = llmemory.Address
    def __init__(self, frame, v):
        self._frame = frame
        self._v = v
    def _getaddress(self):
        return _address_of_local_var_accessor(self._frame, self._v)
    address = property(_getaddress)

class _address_of_local_var_accessor(object):
    def __init__(self, frame, v):
        self.frame = frame
        self.v = v
    def __getitem__(self, index):
        if index != 0:
            raise IndexError("address of local vars only support [0] indexing")
        p = self.frame.getval(self.v)
        result = llmemory.cast_ptr_to_adr(p)
        # the GC should never see instances of _gctransformed_wref
        result = self.unwrap_possible_weakref(result)
        return result
    def __setitem__(self, index, newvalue):
        if index != 0:
            raise IndexError("address of local vars only support [0] indexing")
        if self.v.concretetype == llmemory.WeakRefPtr:
            # fish some more
            assert isinstance(newvalue, llmemory.fakeaddress)
            p = llmemory.cast_ptr_to_weakrefptr(newvalue.ptr)
        else:
            p = llmemory.cast_adr_to_ptr(newvalue, self.v.concretetype)
        self.frame.setvar(self.v, p)
    def unwrap_possible_weakref(self, addr):
        # fish fish fish
        if addr and isinstance(addr.ptr._obj, llmemory._gctransformed_wref):
            return llmemory.fakeaddress(addr.ptr._obj._ptr)
        return addr


# by default we route all logging messages to nothingness
# e.g. tests can then switch on logging to get more help
# for failing tests
from pypy.tool.ansi_print import ansi_log
py.log.setconsumer('llinterp', ansi_log)
