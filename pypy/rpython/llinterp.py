from pypy.objspace.flow.model import FunctionGraph, Constant, Variable, c_last_exception
from pypy.rpython.rarithmetic import intmask, r_uint, ovfcheck, r_longlong, r_ulonglong
from pypy.rpython.lltypesystem import lltype, llmemory, lloperation, llheap
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.objectmodel import ComputedIntSymbolic

import sys
import math
import py
import traceback, cStringIO

log = py.log.Producer('llinterp')

class LLException(Exception):
    def __str__(self):
        etype = self.args[0]
        evalue = self.args[0]
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

def type_name(etype):
    if isinstance(lltype.typeOf(etype), lltype.Ptr):
        return ''.join(etype.name).rstrip('\x00')
    else:
        # ootype!
        return etype.class_._INSTANCE._name.split(".")[-1] 

class LLInterpreter(object):
    """ low level interpreter working with concrete values. """

    def __init__(self, typer, heap=llheap, tracing=True):
        self.bindings = {}
        self.typer = typer
        self.heap = heap  #module that provides malloc, etc for lltypes
        self.active_frame = None
        # XXX hack: set gc to None because
        # prepare_graphs_and_create_gc might already use the llinterpreter!
        self.gc = None
        self.tracer = None
        self.frame_class = LLFrame
        if hasattr(heap, "prepare_graphs_and_create_gc"):
            flowgraphs = typer.annotator.translator.graphs
            self.gc = heap.prepare_graphs_and_create_gc(self, flowgraphs)
        if tracing:
            self.tracer = Tracer()

    def eval_graph(self, graph, args=()):
        llframe = self.frame_class(graph, args, self)
        if self.tracer:
            self.tracer.start()
        retval = None
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
            if self.tracer:
                if retval is not None:
                    self.tracer.dump('   ---> %r\n' % (retval,))
                self.tracer.stop()
        return retval

    def print_traceback(self):
        frame = self.active_frame
        frames = []
        while frame is not None:
            frames.append(frame)
            frame = frame.f_back
        frames.reverse()
        lines = []
        for frame in frames:
            logline = frame.graph.name
            if frame.curr_block is None:
                logline += " <not running yet>"
                lines.append(logline)
                continue
            try:
                logline += " " + self.typer.annotator.annotated[frame.curr_block].__module__
            except (KeyError, AttributeError):
                # if the graph is from the GC it was not produced by the same
                # translator :-(
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
        #log.findroots("starting")
        frame = self.active_frame
        roots = []
        while frame is not None:
            #log.findroots("graph", frame.graph.name)
            frame.find_roots(roots)
            frame = frame.f_back
        return roots

    def find_exception(self, exc):
        assert isinstance(exc, LLException)
        import exceptions
        klass, inst = exc.args[0], exc.args[1]
        exdata = self.typer.getexceptiondata()
        frame = self.frame_class(None, [], self)
        old_active_frame = self.active_frame
        try:
            for cls in exceptions.__dict__.values():
                if type(cls) is type(Exception):
                    evalue = frame.op_direct_call(exdata.fn_pyexcclass2exc,
                            lltype.pyobjectptr(cls))
                    etype = frame.op_direct_call(exdata.fn_type_of_exc_inst, evalue)
                    if etype == klass:
                        return cls
        finally:
            self.active_frame = old_active_frame
        raise ValueError, "couldn't match exception"


def checkptr(ptr):
    assert isinstance(lltype.typeOf(ptr), lltype.Ptr)

def checkadr(addr):
    assert lltype.typeOf(addr) is llmemory.Address
    
def is_inst(inst):
    return isinstance(lltype.typeOf(inst), (ootype.Instance, ootype.BuiltinType))

def checkinst(inst):
    assert is_inst(inst)


class LLFrame(object):
    def __init__(self, graph, args, llinterpreter, f_back=None):
        assert not graph or isinstance(graph, FunctionGraph)
        self.graph = graph
        self.args = args
        self.llinterpreter = llinterpreter
        self.heap = llinterpreter.heap
        self.bindings = {}
        self.f_back = f_back
        self.curr_block = None
        self.curr_operation_index = 0
        self.alloca_objects = []

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
                assert False, "type error: %r val -> %r var" % (lltype.typeOf(val), var.concretetype)
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

    # _______________________________________________________
    # other helpers
    def getoperationhandler(self, opname):
        ophandler = getattr(self, 'op_' + opname, None)
        if ophandler is None:
            # try to import the operation from opimpl.py
            from pypy.rpython.lltypesystem.opimpl import get_op_impl
            ophandler = get_op_impl(opname)
            LLFrame.ophandler = staticmethod(ophandler)
        return ophandler
    # _______________________________________________________
    # evaling functions

    def eval(self):
        self.llinterpreter.active_frame = self
        graph = self.graph
        tracer = self.llinterpreter.tracer
        if tracer:
            tracer.enter(graph)
        try:
            nextblock = graph.startblock
            args = self.args
            while 1:
                self.clear()
                self.fillvars(nextblock, args)
                nextblock, args = self.eval_block(nextblock)
                if nextblock is None:
                    self.llinterpreter.active_frame = self.f_back
                    for obj in self.alloca_objects:
                        #XXX slighly unclean
                        obj._setobj(None)
                    return args
        finally:
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
            if tracer:
                tracer.dump('return')
            resultvar, = block.getvariables()
            result = self.getval(resultvar)
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
                    assert issubclass(link.exitcase, Exception)
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
            for link in block.exits:
                if link.llexitcase == llexitvalue:
                    break   # found -- the result is in 'link'
            else:
                if block.exits[-1].exitcase == "default":
                    assert block.exits[-1].llexitcase is None
                    link = block.exits[-1]
                else:
                    raise ValueError("exit case %r not found in the exit links "
                                     "of %r" % (llexitvalue, block))
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
        vals = [self.getval(x) for x in operation.args]
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
        except Exception:
            self.make_llexception()

    def find_roots(self, roots):
        #log.findroots(self.curr_block.inputargs)
        PyObjPtr = lltype.Ptr(lltype.PyObject)
        for arg in self.curr_block.inputargs:
            if (isinstance(arg, Variable) and
                isinstance(getattr(arg, 'concretetype', PyObjPtr), lltype.Ptr)):
                roots.append(self.getval(arg))
        for op in self.curr_block.operations[:self.curr_operation_index]:
            if isinstance(getattr(op.result, 'concretetype', PyObjPtr), lltype.Ptr):
                roots.append(self.getval(op.result))

    # __________________________________________________________
    # misc LL operation implementations

    def op_debug_view(self, *ll_objects):
        from pypy.translator.tool.lltracker import track
        track(*ll_objects)

    def op_debug_print(self, *ll_args):
        from pypy.rpython.lltypesystem.rstr import STR
        for arg in ll_args:
            T = lltype.typeOf(arg)
            if T == lltype.Ptr(STR):
                arg = ''.join(arg.chars)
            print arg,
        print

    def op_debug_pdb(self, *ll_args):
        if self.llinterpreter.tracer:
            self.llinterpreter.tracer.flush()
        print "entering pdb...", ll_args
        import pdb
        pdb.set_trace()

    def op_debug_log_exc(self, exc_type):
        # do nothing, this is useful in compiled code
        pass

    def op_keepalive(self, value):
        pass

    def op_hint(self, x, hints):
        return x

    def op_resume_point(self, *args):
        pass

    def op_resume_state_create(self, *args):
        raise RuntimeError("resume_state_create can not be called.")

    def op_resume_state_invoke(self, *args):
        raise RuntimeError("resume_state_invoke can not be called.")

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
        if FIELDTYPE != lltype.Void:
            gc = self.llinterpreter.gc
            if gc is None or not gc.needs_write_barrier(FIELDTYPE):
                setattr(obj, fieldname, fieldvalue)
            else:
                args = gc.get_arg_write_barrier(obj, fieldname, fieldvalue)
                write_barrier = gc.get_funcptr_write_barrier()
                result = self.op_direct_call(write_barrier, *args)

    op_bare_setfield = op_setfield

    def op_getarrayitem(self, array, index):
        return array[index]

    def op_setarrayitem(self, array, index, item):
        # array should be a pointer
        ITEMTYPE = lltype.typeOf(array).TO.OF
        if ITEMTYPE != lltype.Void:
            gc = self.llinterpreter.gc
            if gc is None or not gc.needs_write_barrier(ITEMTYPE):
                array[index] = item
            else:
                args = gc.get_arg_write_barrier(array, index, item)
                write_barrier = gc.get_funcptr_write_barrier()
                self.op_direct_call(write_barrier, *args)

    def op_direct_call(self, f, *args):
        obj = self.llinterpreter.typer.type_system.deref(f)
        has_callable = getattr(obj, '_callable', None) is not None
        if has_callable and getattr(obj._callable, 'suggested_primitive', False):
                return self.invoke_callable_with_pyexceptions(f, *args)
        if hasattr(obj, 'graph'):
            graph = obj.graph
        else:
            assert has_callable, "don't know how to execute %r" % f
            return self.invoke_callable_with_pyexceptions(f, *args)
        frame = self.__class__(graph, args, self.llinterpreter, self)
        return frame.eval()

    op_safe_call = op_direct_call

    def op_indirect_call(self, f, *args):
        graphs = args[-1]
        args = args[:-1]
        if graphs is not None:
            obj = self.llinterpreter.typer.type_system.deref(f)
            if hasattr(obj, 'graph'):
                assert obj.graph in graphs 
        else:
            log.warn("op_indirect_call with graphs=None:", f)
        return self.op_direct_call(f, *args)

    def op_unsafe_call(self, TGT, f):
        checkadr(f)
        assert f.offset is None
        obj = self.llinterpreter.typer.type_system.deref(f.ob)
        assert hasattr(obj, 'graph') # don't want to think about that
        graph = obj.graph
        args = []
        for arg in obj.graph.startblock.inputargs:
            args.append(arg.concretetype._defl())
        frame = self.__class__(graph, args, self.llinterpreter, self)
        result = frame.eval()
        from pypy.translator.stackless.frame import storage_type
        assert storage_type(lltype.typeOf(result)) == TGT
        return lltype._cast_whatever(TGT, result)
    op_unsafe_call.need_result_type = True

    def op_malloc(self, obj):
        if self.llinterpreter.gc is not None:
            args = self.llinterpreter.gc.get_arg_malloc(obj)
            malloc = self.llinterpreter.gc.get_funcptr_malloc()
            result = self.op_direct_call(malloc, *args)
            return self.llinterpreter.gc.adjust_result_malloc(result, obj)
        else:
            return self.heap.malloc(obj)

    def op_malloc_varsize(self, obj, size):
        if self.llinterpreter.gc is not None:
            args = self.llinterpreter.gc.get_arg_malloc(obj, size)
            malloc = self.llinterpreter.gc.get_funcptr_malloc()
            result = self.op_direct_call(malloc, *args)
            return self.llinterpreter.gc.adjust_result_malloc(result, obj, size)
        else:
            try:
                return self.heap.malloc(obj, size)
            except MemoryError:
                self.make_llexception()

    def op_flavored_malloc(self, flavor, obj):
        assert isinstance(flavor, str)
        if flavor == "stack":
            if isinstance(obj, lltype.Struct) and obj._arrayfld is None:
                result = self.heap.malloc(obj)
                self.alloca_objects.append(result)
                return result
            else:
                raise ValueError("cannot allocate variable-sized things on the stack")
        return self.heap.malloc(obj, flavor=flavor)

    def op_flavored_free(self, flavor, obj):
        assert isinstance(flavor, str)
        self.heap.free(obj, flavor=flavor)

    def op_getfield(self, obj, field):
        checkptr(obj)
        # check the difference between op_getfield and op_getsubstruct:
        assert not isinstance(getattr(lltype.typeOf(obj).TO, field),
                              lltype.ContainerType)
        return getattr(obj, field)

    def op_cast_int_to_ptr(self, RESTYPE, int1):
        return lltype.cast_int_to_ptr(RESTYPE, int1)
    op_cast_int_to_ptr.need_result_type = True

    def op_cast_ptr_to_int(self, ptr1):
        checkptr(ptr1)
        assert isinstance(lltype.typeOf(ptr1).TO, (lltype.Array, lltype.Struct)
)
        return lltype.cast_ptr_to_int(ptr1)


    def op_gc__collect(self):
        import gc
        gc.collect()

    def op_gc_free(self, addr):
        raise NotImplementedError("gc_free")

    def op_gc_fetch_exception(self):
        raise NotImplementedError("gc_fetch_exception")

    def op_gc_restore_exception(self, exc):
        raise NotImplementedError("gc_restore_exception")

    def op_gc_call_rtti_destructor(self, rtti, addr):
        raise NotImplementedError("gc_call_rtti_destructor")

    def op_gc_deallocate(self, TYPE, addr):
        raise NotImplementedError("gc_deallocate")

    def op_gc_push_alive_pyobj(self, pyobj):
        raise NotImplementedError("gc_push_alive_pyobj")

    def op_gc_pop_alive_pyobj(self, pyobj):
        raise NotImplementedError("gc_pop_alive_pyobj")

    def op_gc_protect(self, obj):
        raise NotImplementedError("gc_protect")

    def op_gc_unprotect(self, obj):
        raise NotImplementedError("gc_unprotect")

    def op_gc_reload_possibly_moved(self, newaddr, ptr):
        raise NotImplementedError("gc_reload_possibly_moved")

    def op_yield_current_frame_to_caller(self):
        raise NotImplementedError("yield_current_frame_to_caller")

    def op_call_boehm_gc_alloc(self):
        raise NotImplementedError("call_boehm_gc_alloc")


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
        return self.heap.raw_malloc(size)

    def op_raw_malloc_usage(self, size):
        assert lltype.typeOf(size) == lltype.Signed
        return self.heap.raw_malloc_usage(size)

    def op_raw_free(self, addr):
        checkadr(addr) 
        self.heap.raw_free(addr)

    def op_raw_memcopy(self, fromaddr, toaddr, size):
        checkadr(fromaddr)
        checkadr(toaddr)
        self.heap.raw_memcopy(fromaddr, toaddr, size)

    def op_raw_load(self, addr, typ, offset):
        checkadr(addr)
        value = getattr(addr, str(typ).lower())[offset]
        assert lltype.typeOf(value) == typ
        return value

    def op_raw_store(self, addr, typ, offset, value):
        checkadr(addr)
        assert lltype.typeOf(value) == typ
        getattr(addr, str(typ).lower())[offset] = value

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
        exec py.code.Source("""
        def %(fn)s(self, x, y):
            assert isinstance(x, %(xtype)s)
            assert isinstance(y, %(ytype)s)
            try:
                return %(checkfn)s(x %(operator)s y)
            except (OverflowError, ValueError, ZeroDivisionError):
                self.make_llexception()
        """ % locals()).compile() in globals(), d

    _makefunc2('op_int_add_ovf', '+', '(int, llmemory.AddressOffset)')
    _makefunc2('op_int_mul_ovf', '*', '(int, llmemory.AddressOffset)', 'int')
    _makefunc2('op_int_sub_ovf',          '-',  'int')
    _makefunc2('op_int_floordiv_ovf',     '//', 'int')
    _makefunc2('op_int_floordiv_zer',     '//', 'int')
    _makefunc2('op_int_floordiv_ovf_zer', '//', 'int')
    _makefunc2('op_int_mod_ovf',          '%',  'int')
    _makefunc2('op_int_mod_zer',          '%',  'int')
    _makefunc2('op_int_mod_ovf_zer',      '%',  'int')
    _makefunc2('op_int_lshift_ovf',       '<<', 'int')
    _makefunc2('op_int_lshift_val',       '<<', 'int')
    _makefunc2('op_int_lshift_ovf_val',   '<<', 'int')
    _makefunc2('op_int_rshift_val',       '>>', 'int')

    _makefunc2('op_uint_floordiv_zer',    '//', 'r_uint')
    _makefunc2('op_uint_mod_zer',         '%',  'r_uint')
    _makefunc2('op_uint_lshift_val',      '<<', 'r_uint')
    _makefunc2('op_uint_rshift_val',      '>>', 'r_uint')

    _makefunc2('op_llong_floordiv_zer',   '//', 'r_longlong')
    _makefunc2('op_llong_mod_zer',        '%',  'r_longlong')
    _makefunc2('op_llong_lshift_val',     '<<', 'r_longlong')
    _makefunc2('op_llong_rshift_val',     '>>', 'r_longlong')

    _makefunc2('op_ullong_floordiv_zer',  '//', 'r_ulonglong')
    _makefunc2('op_ullong_mod_zer',       '%',  'r_ulonglong')
    _makefunc2('op_ullong_lshift_val',    '<<', 'r_ulonglong')
    _makefunc2('op_ullong_rshift_val',    '>>', 'r_ulonglong')

    def op_cast_float_to_int(self, f):
        assert type(f) is float
        try:
            return ovfcheck(int(f))
        except OverflowError:
            self.make_llexception()

    #Operation of ootype

    def op_new(self, INST):
        assert isinstance(INST, (ootype.Instance, ootype.BuiltinType))
        return ootype.new(INST)

    def op_runtimenew(self, class_):
        return ootype.runtimenew(class_)

    def op_oonewcustomdict(self, DICT, eq_func, eq_method_name, hash_func, hash_method_name):
        eq_name, interp_eq = \
                 wrap_func_or_boundmethod(self.llinterpreter, eq_func, eq_method_name)
        EQ_FUNC = ootype.StaticMethod([DICT._KEYTYPE, DICT._KEYTYPE], ootype.Bool)
        sm_eq = ootype.static_meth(EQ_FUNC, eq_name, _callable=interp_eq)        

        hash_name, interp_hash = \
                   wrap_func_or_boundmethod(self.llinterpreter, hash_func, hash_method_name)
        HASH_FUNC = ootype.StaticMethod([DICT._KEYTYPE], ootype.Signed)
        sm_hash = ootype.static_meth(HASH_FUNC, hash_name, _callable=interp_hash)

        # XXX: is it fine to have StaticMethod type for bound methods, too?
        return ootype.oonewcustomdict(DICT, sm_eq, sm_hash)

    def op_oosetfield(self, inst, name, value):
        checkinst(inst)
        assert isinstance(name, str)
        FIELDTYPE = lltype.typeOf(inst)._field_type(name)
        if FIELDTYPE != lltype.Void:
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
        return self.op_direct_call(m, inst, *args)

    def op_ooupcast(self, INST, inst):
        return ootype.ooupcast(INST, inst)
    op_ooupcast.need_result_type = True
    
    def op_oodowncast(self, INST, inst):
        return ootype.oodowncast(INST, inst)
    op_oodowncast.need_result_type = True

    def op_oononnull(self, inst):
        checkinst(inst)
        return bool(inst)

    def op_oois(self, obj1, obj2):
        if is_inst(obj1):
            checkinst(obj2)
            return obj1 == obj2   # NB. differently-typed NULLs must be equal
        elif isinstance(obj1, ootype._class):
            assert isinstance(obj2, ootype._class)
            return obj1 is obj2
        else:
            assert False, "oois on something silly"
            
    def op_instanceof(self, inst, INST):
        return ootype.instanceof(inst, INST)

    def op_classof(self, inst):
        return ootype.classof(inst)

    def op_subclassof(self, class1, class2):
        return ootype.subclassof(class1, class2)

    def op_ooidentityhash(self, inst):
        return ootype.ooidentityhash(inst)

    def op_oostring(self, obj, base):
        return ootype.oostring(obj, base)

    def op_ooparse_int(self, s, base):
        try:
            return ootype.ooparse_int(s, base)
        except ValueError:
            self.make_llexception()

class Tracer(object):
    Counter = 0
    file = None

    HEADER = """<html><head>
        <script language=javascript type='text/javascript'>
        function togglestate(name) {
          item = document.getElementById(name)
          if (item.style.display == 'none')
            item.style.display = 'block';
          else
            item.style.display = 'none';
        }
        </script>
        </head>

        <body><pre>
    """

    FOOTER = """</pre></body></html>"""

    ENTER = ('''\n\t<a href="javascript:togglestate('div%d')">%s</a>'''
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
        from pypy.tool.udir import udir
        n = Tracer.Counter
        Tracer.Counter += 1
        self.file = udir.join('llinterp_trace_%d.html' % n).open('w')
        print >> self.file, self.HEADER
        self.count = 0
        self.indentation = ''

    def stop(self):
        # end of a dump file
        if self.file:
            print >> self.file, self.FOOTER
            self.file.close()
            self.file = None

    def enter(self, graph):
        # enter evaluation of a graph
        if self.file:
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

    def dump(self, text, bold=False):
        if self.file:
            text = self.htmlquote(text)
            if bold:
                text = '<b>%s</b>' % (text,)
            self.file.write(text.replace('\n', '\n'+self.indentation))

    def flush(self):
        self.file.flush()

def wrap_func_or_boundmethod(llinterpreter, func, method_name):
    """
    Returns a callable that inteprets the given func or method_name when called.
    """
    if method_name is None:
        # eq_func is a HalfConcreteWrapper wrapping a StaticMethod
        self_arg = []
        func_graph = func.concretize().value.graph
    else:
        # eq_func is an instance, we want to call 'method_name' on it
        self_arg = [func]
        func_graph = func._TYPE._methods[method_name].graph

    def interp_func(*args):
        graph_args = self_arg + list(args)
        return llinterpreter.eval_graph(func_graph, args=graph_args)
    return func_graph.name, interp_func


# by default we route all logging messages to nothingness
# e.g. tests can then switch on logging to get more help
# for failing tests
from pypy.tool.ansi_print import ansi_log
py.log.setconsumer('llinterp', ansi_log)
