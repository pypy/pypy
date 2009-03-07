import py
from pypy.rpython.lltypesystem import lltype, llmemory, rclass
from pypy.rpython.llinterp import LLException
from pypy.tool.sourcetools import func_with_new_name
from pypy.rlib.objectmodel import we_are_translated, r_dict
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.debug import debug_print

from pypy.jit.metainterp import history, support
from pypy.jit.metainterp.history import (Const, ConstInt, ConstPtr, Box,
                                         BoxInt, BoxPtr, GuardOp)
from pypy.jit.metainterp.compile import compile_new_loop, compile_new_bridge
from pypy.jit.metainterp.heaptracker import (get_vtable_for_gcstruct,
                                             populate_type_cache)
from pypy.jit.metainterp import codewriter, optimize

# ____________________________________________________________

def check_args(*args):
    for arg in args:
        assert isinstance(arg, (Box, Const))


class arguments(object):
    def __init__(self, *argtypes, **kwargs):
        self.result = kwargs.pop("returns", None)
        assert not kwargs
        self.argtypes = argtypes

    def __eq__(self, other):
        if not isinstance(other, arguments):
            return NotImplemented
        return self.argtypes == other.argtypes and self.result == other.result

    def __ne__(self, other):
        if not isinstance(other, arguments):
            return NotImplemented
        return self.argtypes != other.argtypes or self.result != other.result

    def __call__(self, func):
        result = self.result
        argtypes = unrolling_iterable(self.argtypes)
        def wrapped(self, orgpc):
            args = (self, )
            for argspec in argtypes:
                if argspec == "box":
                    args += (self.load_arg(), )
                elif argspec == "constbox":
                    args += (self.load_const_arg(), )
                elif argspec == "int":
                    args += (self.load_int(), )
                elif argspec == "jumptarget":
                    args += (self.load_3byte(), )
                elif argspec == "jumptargets":
                    num = self.load_int()
                    args += ([self.load_3byte() for i in range(num)], )
                elif argspec == "bool":
                    args += (self.load_bool(), )
                elif argspec == "2byte":
                    args += (self.load_int(), )
                elif argspec == "varargs":
                    args += (self.load_varargs(), )
                elif argspec == "intargs":
                    args += (self.load_intargs(), )
                elif argspec == "bytecode":
                    bytecode = self.load_const_arg()
                    assert isinstance(bytecode, codewriter.JitCode)
                    args += (bytecode, )
                elif argspec == "orgpc":
                    args += (orgpc, )
                elif argspec == "indirectcallset":
                    indirectcallset = self.load_const_arg()
                    assert isinstance(indirectcallset,
                                      codewriter.IndirectCallset)
                    args += (indirectcallset, )
                elif argspec == "builtin":
                    builtin = self.load_const_arg()
                    assert isinstance(builtin, codewriter.BuiltinDescr)
                    args += (builtin, )
                elif argspec == "virtualizabledesc":
                    from virtualizable import VirtualizableDesc
                    virtualizabledesc = self.load_const_arg()
                    assert isinstance(virtualizabledesc, VirtualizableDesc)
                    args += (virtualizabledesc, )
                else:
                    assert 0, "unknown argtype declaration: %r" % (argspec,)
            val = func(*args)
            if result is not None:
                if result == "box":
                    self.make_result_box(val)
                else:
                    assert 0, "unknown result declaration: %r" % (result,)
                return False
            if val is None:
                val = False
            return val
        wrapped.func_name = "wrap_" + func.func_name
        wrapped.argspec = self
        return wrapped

# ____________________________________________________________


class MIFrame(object):

    def __init__(self, metainterp, jitcode):
        assert isinstance(jitcode, codewriter.JitCode)
        self.metainterp = metainterp
        self.jitcode = jitcode
        self.bytecode = jitcode.code
        self.constants = jitcode.constants
        self.exception_target = -1

    # ------------------------------
    # Decoding of the JitCode

    def load_int(self):
        pc = self.pc
        result = ord(self.bytecode[pc])
        self.pc = pc + 1
        if result > 0x7F:
            result = self._load_larger_int(result)
        return result

    def _load_larger_int(self, result):    # slow path
        result = result & 0x7F
        shift = 7
        pc = self.pc
        while 1:
            byte = ord(self.bytecode[pc])
            pc += 1
            result += (byte & 0x7F) << shift
            shift += 7
            if not byte & 0x80:
                break
        self.pc = pc
        return result
    _load_larger_int._dont_inline_ = True

    def load_3byte(self):
        pc = self.pc
        result = (((ord(self.bytecode[pc + 0])) << 16) |
                  ((ord(self.bytecode[pc + 1])) <<  8) |
                  ((ord(self.bytecode[pc + 2])) <<  0))
        self.pc = pc + 3
        return result

    def load_bool(self):
        pc = self.pc
        result = ord(self.bytecode[pc])
        self.pc = pc + 1
        return bool(result)

    def getenv(self, i):
        j = i // 2
        if i % 2:
            return self.constants[j]
        else:
            assert j < len(self.env)
            return self.env[j]

    def load_arg(self):
        return self.getenv(self.load_int())

    def load_const_arg(self):
        return self.constants[self.load_int()]

    def load_varargs(self):
        count = self.load_int()
        return [self.load_arg() for i in range(count)]

    def load_intargs(self):
        count = self.load_int()
        return [self.load_int() for i in range(count)]

    def getvarenv(self, i):
        return self.env[i]

    def make_result_box(self, box):
        assert isinstance(box, Box) or isinstance(box, Const)
        self.env.append(box)

##    def starts_with_greens(self):
##        green_opcode = self.metainterp._green_opcode
##        if self.bytecode[self.pc] == green_opcode:
##            self.greens = []
##            while self.bytecode[self.pc] == green_opcode:
##                self.pc += 1
##                i = self.load_int()
##                assert isinstance(self.env[i], Const)
##                self.greens.append(i)
##        else:
##            self.greens = None

    # ------------------------------

    for _n in range(codewriter.MAX_MAKE_NEW_VARS):
        _decl = ', '.join(["'box'" for _i in range(_n)])
        _allargs = ', '.join(["box%d" % _i for _i in range(_n)])
        exec py.code.Source("""
            @arguments(%s)
            def opimpl_make_new_vars_%d(self, %s):
                ##self.greens = None
                if not we_are_translated():
                    check_args(%s)
                self.env = [%s]
        """ % (_decl, _n, _allargs, _allargs, _allargs)).compile()

    @arguments("varargs")
    def opimpl_make_new_vars(self, newenv):
        ##self.greens = None
        if not we_are_translated():
            check_args(*newenv)
        self.env = newenv

##    @arguments("int")
##    def opimpl_green(self, green):
##        assert isinstance(self.env[green], Const)
##        if not self.greens:
##            self.greens = []
##        self.greens.append(green)
##        #if not we_are_translated():
##        #    history.log.green(self.env[green])

    for _opimpl in ['int_add', 'int_sub', 'int_mul', 'int_floordiv', 'int_mod',
                    'int_lt', 'int_le', 'int_eq',
                    'int_ne', 'int_gt', 'int_ge',
                    'int_and', 'int_or', 'int_xor',
                    'int_rshift', 'int_lshift',
                    ]:
        exec py.code.Source('''
            @arguments("box", "box")
            def opimpl_%s(self, b1, b2):
                self.execute(%r, [b1, b2], "int", True)
        ''' % (_opimpl, _opimpl)).compile()

    for _opimpl in ['int_is_true', 'int_neg',
                    ]:
        exec py.code.Source('''
            @arguments("box")
            def opimpl_%s(self, b):
                self.execute(%r, [b], "int", True)
        ''' % (_opimpl, _opimpl)).compile()

    @arguments()
    def opimpl_return(self):
        assert len(self.env) == 1
        return self.metainterp.finishframe(self.env[0])

    @arguments()
    def opimpl_void_return(self):
        assert len(self.env) == 0
        return self.metainterp.finishframe(None)

    @arguments("jumptarget")
    def opimpl_goto(self, target):
        self.pc = target

    @arguments("box", "jumptarget")
    def opimpl_goto_if_not(self, box, target):
        switchcase = box.getint()
        if switchcase:
            currentpc = self.pc
            targetpc = target
            opname = "guard_true"
        else:
            currentpc = target
            targetpc = self.pc
            opname = "guard_false"
        self.generate_guard(targetpc, opname, box, ignore_box=switchcase)
        self.pc = currentpc

    @arguments("orgpc", "box", "intargs", "jumptargets")
    def opimpl_switch(self, pc, valuebox, intargs, jumptargets):
        box = self.implement_guard_value(pc, valuebox)
        switchcase = box.getint()
        # XXX implement dictionary for speedups at some point
        for i in range(len(intargs)):
            value = intargs[i]
            if switchcase == value:
                self.pc = jumptargets[i]
                break

    @arguments("int")
    def opimpl_new(self, size):
        self.execute('new', [ConstInt(size)], 'ptr')

    @arguments("int", "constbox")
    def opimpl_new_with_vtable(self, size, vtableref):
        self.execute('new_with_vtable', [ConstInt(size), vtableref], 'ptr')

    @arguments("box")
    def opimpl_ptr_nonzero(self, box):
        self.execute('oononnull', [box], 'int', True)

    @arguments("box")
    def opimpl_ptr_iszero(self, box):
        self.execute('ooisnull', [box], 'int', True)

    @arguments("box", "box")
    def opimpl_ptr_eq(self, box1, box2):
        self.execute('oois', [box1, box2], 'int', True)

    @arguments("box", "box")
    def opimpl_ptr_ne(self, box1, box2):
        self.execute('ooisnot', [box1, box2], 'int', True)


    @arguments("box", "int")
    def opimpl_getfield_gc(self, box, fielddesc):
        tp = self.metainterp.cpu.typefor(fielddesc)
        self.execute('getfield_gc', [box, ConstInt(fielddesc)], tp)
    @arguments("box", "int")
    def opimpl_getfield_pure_gc(self, box, fielddesc):
        tp = self.metainterp.cpu.typefor(fielddesc)
        self.execute('getfield_gc', [box, ConstInt(fielddesc)], tp, True)
    @arguments("box", "int", "box")
    def opimpl_setfield_gc(self, box, fielddesc, valuebox):
        self.execute('setfield_gc', [box, ConstInt(fielddesc), valuebox],
                     'void')

    @arguments("box", "int")
    def opimpl_getfield_raw(self, box, fielddesc):
        tp = self.metainterp.cpu.typefor(fielddesc)
        self.execute('getfield_raw', [box, ConstInt(fielddesc)], tp)
    @arguments("box", "int")
    def opimpl_getfield_pure_raw(self, box, fielddesc):
        tp = self.metainterp.cpu.typefor(fielddesc)
        self.execute('getfield_raw', [box, ConstInt(fielddesc)], tp, True)
    @arguments("box", "int", "box")
    def opimpl_setfield_raw(self, box, fielddesc, valuebox):
        self.execute('setfield_raw', [box, ConstInt(fielddesc), valuebox],
                     'void')

    @arguments("bytecode", "varargs")
    def opimpl_call(self, callee, varargs):
        f = self.metainterp.newframe(callee)
        f.setup_call(varargs)
        return True

    @arguments("varargs")
    def opimpl_green_call__1(self, varargs):
        return self.execute_with_exc('call__1', varargs, 'int', True)
    @arguments("varargs")
    def opimpl_green_call__2(self, varargs):
        return self.execute_with_exc('call__2', varargs, 'int', True)
    @arguments("varargs")
    def opimpl_green_call__4(self, varargs):
        return self.execute_with_exc('call__4', varargs, 'int', True)
    @arguments("varargs")
    def opimpl_green_call__8(self, varargs):
        return self.execute_with_exc('call__8', varargs, 'int', True)

    @arguments("varargs")
    def opimpl_green_call_ptr(self, varargs):
        return self.execute_with_exc('call_ptr', varargs, 'ptr', True)

    @arguments("varargs")
    def opimpl_residual_call__1(self, varargs):
        return self.execute_with_exc('call__1', varargs, 'int')
    @arguments("varargs")
    def opimpl_residual_call__2(self, varargs):
        return self.execute_with_exc('call__2', varargs, 'int')
    @arguments("varargs")
    def opimpl_residual_call__4(self, varargs):
        return self.execute_with_exc('call__4', varargs, 'int')
    @arguments("varargs")
    def opimpl_residual_call__8(self, varargs):
        return self.execute_with_exc('call__8', varargs, 'int')

    @arguments("varargs")
    def opimpl_residual_call_ptr(self, varargs):
        return self.execute_with_exc('call_ptr', varargs, 'ptr')

    @arguments("varargs")
    def opimpl_residual_call_void(self, varargs):
        return self.execute_with_exc('call_void', varargs, 'void')


    @arguments("builtin", "varargs")
    def opimpl_getitem(self, descr, varargs):
        args = [descr.getfunc] + varargs
        return self.execute_with_exc('getitem', args, descr.tp)

    @arguments("builtin", "varargs")
    def opimpl_setitem(self, descr, varargs):
        args = [descr.setfunc] + varargs
        return self.execute_with_exc('setitem', args, 'void')

    @arguments("builtin", "varargs")
    def opimpl_getitem_foldable(self, descr, varargs):
        args = [descr.getfunc] + varargs
        return self.execute_with_exc('getitem', args, descr.tp, True)

    @arguments("builtin", "varargs")
    def opimpl_setitem_foldable(self, descr, varargs):
        args = [descr.setfunc] + varargs
        return self.execute_with_exc('setitem', args, 'void', True)

    @arguments("builtin", "varargs")
    def opimpl_newlist(self, descr, varargs):
        args = [descr.malloc_func] + varargs
        if len(varargs) == 1:
            if descr.tp == "int":
                args.append(ConstInt(0))
            else:
                args.append(ConstPtr(lltype.nullptr(llmemory.GCREF.TO)))
        return self.execute_with_exc('newlist', args, 'ptr')

    @arguments("builtin", "varargs")
    def opimpl_append(self, descr, varargs):
        args = [descr.append_func] + varargs
        return self.execute_with_exc('append', args, 'void')

    @arguments("builtin", "varargs")
    def opimpl_insert(self, descr, varargs):
        args = [descr.insert_func] + varargs
        return self.execute_with_exc('insert', args, 'void')

    @arguments("builtin", "varargs")
    def opimpl_pop(self, descr, varargs):
        args = [descr.pop_func] + varargs
        return self.execute_with_exc('pop', args, descr.tp)

    @arguments("builtin", "varargs")
    def opimpl_len(self, descr, varargs):
        args = [descr.len_func] + varargs
        return self.execute_with_exc('len', args, 'int')

    @arguments("builtin", "varargs")
    def opimpl_listnonzero(self, descr, varargs):
        args = [descr.nonzero_func] + varargs
        return self.execute_with_exc('listnonzero', args, 'int')

    @arguments("indirectcallset", "box", "varargs")
    def opimpl_indirect_call(self, indirectcallset, box, varargs):
        assert isinstance(box, Const) # XXX
        cpu = self.metainterp.cpu
        jitcode = indirectcallset.bytecode_for_address(box.getaddr(cpu))
        f = self.metainterp.newframe(jitcode)
        f.setup_call(varargs)
        return True

    @arguments("box")
    def opimpl_strlen(self, str):
        self.execute('strlen', [str], 'int', True)

    @arguments("box", "box")
    def opimpl_strgetitem(self, str, index):
        self.execute('strgetitem', [str, index], 'int', True)

    @arguments("box", "box", "box")
    def opimpl_strsetitem(self, str, index, newchar):
        self.execute('strsetitem', [str, index, newchar], 'void')

    @arguments("box")
    def opimpl_newstr(self, length):
        self.execute('newstr', [length], 'ptr')

    @arguments("orgpc", "box", returns="box")
    def opimpl_guard_value(self, pc, box):
        return self.implement_guard_value(pc, box)

    @arguments("orgpc", "box", returns="box")
    def opimpl_guard_class(self, pc, box):
        clsbox = self.cls_of_box(box)
        if isinstance(box, Box):
            self.generate_guard(pc, 'guard_class', box, [clsbox])
        return clsbox

    @arguments("orgpc", "box", "builtin")
    def opimpl_guard_builtin(self, pc, box, builtin):
        self.generate_guard(pc, "guard_builtin", box, [builtin])

    @arguments("orgpc", "box", "builtin")
    def opimpl_guard_len(self, pc, box, builtin):
        intbox = self.metainterp.cpu.execute_operation(
            'len', [builtin.len_func, box], 'int')
        self.generate_guard(pc, "guard_len", box, [intbox])

    @arguments("orgpc", "box", "virtualizabledesc", "int")
    def opimpl_guard_nonvirtualized(self, pc, box, vdesc, guard_field):
        clsbox = self.cls_of_box(box)
        op = self.generate_guard(pc, 'guard_nonvirtualized', box,
                                 [clsbox, ConstInt(guard_field)])
        if op:
            op.desc = vdesc
        
    @arguments("box")
    def opimpl_keepalive(self, box):
        pass     # xxx?

    def generate_merge_point(self, pc, varargs):
        if isinstance(self.metainterp.history, history.BlackHole):
            raise self.metainterp.ContinueRunningNormally(varargs)
        num_green_args = self.metainterp.num_green_args
        for i in range(num_green_args):
            varargs[i] = self.implement_guard_value(pc, varargs[i])

    @arguments("orgpc", "varargs")
    def opimpl_can_enter_jit(self, pc, varargs):
        self.generate_merge_point(pc, varargs)
        raise GenerateMergePoint(varargs)

    @arguments("orgpc")
    def opimpl_jit_merge_point(self, pc):
        self.generate_merge_point(pc, self.env)

    @arguments("jumptarget")
    def opimpl_setup_exception_block(self, exception_target):
        self.exception_target = exception_target

    @arguments()
    def opimpl_teardown_exception_block(self):
        self.exception_target = -1

    @arguments("constbox", "jumptarget")
    def opimpl_goto_if_exception_mismatch(self, vtableref, next_exc_target):
        assert isinstance(self.exception_box, Const)    # XXX
        adr = vtableref.getaddr(self.metainterp.cpu)
        bounding_class = llmemory.cast_adr_to_ptr(adr, rclass.CLASSTYPE)
        adr = self.exception_box.getaddr(self.metainterp.cpu)
        real_class = llmemory.cast_adr_to_ptr(adr, rclass.CLASSTYPE)
        if not rclass.ll_issubclass(real_class, bounding_class):
            self.pc = next_exc_target

    @arguments("int")
    def opimpl_put_last_exception(self, index):
        self.env.insert(index, self.exception_box)

    @arguments("int")
    def opimpl_put_last_exc_value(self, index):
        self.env.insert(index, self.exc_value_box)

    @arguments()
    def opimpl_raise(self):
        assert len(self.env) == 2
        return self.metainterp.finishframe_exception(self.env[0], self.env[1])

    @arguments()
    def opimpl_reraise(self):
        xxx

    # ------------------------------

    def setup_call(self, argboxes):
        if not we_are_translated():
            check_args(*argboxes)
        self.pc = 0
        self.env = argboxes
        #self.starts_with_greens()
        #assert len(argboxes) == len(self.graph.getargs())

    def setup_resume_at_op(self, pc, envlength, liveboxes, lbindex,
                           exception_target):
        if not we_are_translated():
            check_args(*liveboxes)
        self.pc = pc
        self.env = liveboxes[lbindex:lbindex+envlength]
        self.exception_target = exception_target
        assert len(self.env) == envlength
        return lbindex + envlength

    def run_one_step(self):
        # Execute the frame forward.  This method contains a loop that leaves
        # whenever the 'opcode_implementations' (which is one of the 'opimpl_'
        # methods) returns True.  This is the case when the current frame
        # changes, due to a call or a return.
        while True:
            pc = self.pc
            op = ord(self.bytecode[pc])
            self.pc = pc + 1
            stop = self.metainterp.opcode_implementations[op](self, pc)
            #self.metainterp.most_recent_mp = None
            if stop:
                break

    def generate_guard(self, pc, opname, box, extraargs=[], ignore_box=None):
        if isinstance(box, Const):    # no need for a guard
            return
        if isinstance(self.metainterp.history, history.BlackHole):
            return
        liveboxes = []
        for frame in self.metainterp.framestack:
            for framebox in frame.env:
                if framebox is not ignore_box:
                    liveboxes.append(framebox)
        if box is not None:
            extraargs = [box] + extraargs
        guard_op = self.metainterp.history.record(opname, extraargs, [],
                                                  opcls=GuardOp)
        guard_op.liveboxes = liveboxes
        saved_pc = self.pc
        self.pc = pc
        guard_op.key = self.metainterp.record_state()
        self.pc = saved_pc
        return guard_op

    def implement_guard_value(self, pc, box):
        if isinstance(box, Box):
            promoted_box = box.constbox()
            self.generate_guard(pc, 'guard_value', box, [promoted_box])
            return promoted_box
        else:
            return box     # no promotion needed, already a Const

    def cls_of_box(self, box):
        obj = box.getptr(lltype.Ptr(rclass.OBJECT))
        cls = llmemory.cast_ptr_to_adr(obj.typeptr)
        return ConstInt(self.metainterp.cpu.cast_adr_to_int(cls))

    def follow_jump(self):
        self.pc -= 3
        self.pc = self.load_3byte()

    def execute(self, step, argboxes, result_type, pure=False):
        resboxes = self.metainterp.history.execute_and_record(step, argboxes,
                                                              result_type,
                                                              pure)
        assert len(resboxes) <= 1
        if len(resboxes) == 1:
            resultbox = resboxes[0]
            self.make_result_box(resultbox)
    execute._annspecialcase_ = 'specialize:arg(3, 4)'

    def execute_with_exc(self, step, argboxes, result_type, pure=False):
        old_index = len(self.metainterp.history.operations)
        try:
            self.execute(step, argboxes, result_type, pure)
        except Exception, e:
            if not we_are_translated():
                if not isinstance(e, LLException):
                    raise
                etype, evalue = e.args[:2]
            else:
                XXX
            if result_type == 'void':
                resultboxes = []
            else:
                if result_type == 'ptr':
                    resultbox = BoxPtr()
                else:
                    resultbox = BoxInt()
                self.make_result_box(resultbox)
                resultboxes = [resultbox]
            self.metainterp.history.record(step, argboxes, resultboxes)
        else:
            if not self.metainterp.history.generate_anything_since(old_index):
                assert pure
                return False
            etype = lltype.nullptr(rclass.OBJECT_VTABLE)
            evalue = lltype.nullptr(rclass.OBJECT)
        type_as_int = self.metainterp.cpu.cast_adr_to_int(
            llmemory.cast_ptr_to_adr(etype))
        value_as_gcref = lltype.cast_opaque_ptr(llmemory.GCREF, evalue)
        return self.metainterp.handle_exception(type_as_int, value_as_gcref)
    execute_with_exc._annspecialcase_ = 'specialize:arg(3, 4)'

# ____________________________________________________________


class OOMetaInterp(object):
    num_green_args = 0

    def __init__(self, portal_graph, graphs, cpu, stats, options):
        self.portal_graph = portal_graph
        self.cpu = cpu
        self.stats = stats
        self.options = options
        self.compiled_merge_points = r_dict(history.mp_eq, history.mp_hash)
                 # { greenkey: list-of-MergePoints }

        self.opcode_implementations = []
        self.opname_to_index = {}

        # helpers to eventually build the dictionary "self.builtins":
        self.builtins_keys = []
        self.builtins_values = []
        self.builtins_seen = {}

        self.class_sizes = populate_type_cache(graphs, self.cpu)

        self._virtualizabledescs = {}

    def generate_bytecode(self, policy):
        self._codewriter = codewriter.CodeWriter(self, policy)
        self.portal_code = self._codewriter.make_portal_bytecode(
            self.portal_graph)
        self.cpu.set_meta_interp(self)
        self.delete_history()

    def enable_stats(self):
        return not we_are_translated()

    def newframe(self, jitcode):
        f = MIFrame(self, jitcode)
        self.framestack.append(f)
        return f

    def finishframe(self, resultbox):
        self.framestack.pop()
        if self.framestack:
            if resultbox is not None:
                self.framestack[-1].make_result_box(resultbox)
            return True
        else:
            if resultbox is None:
                resultboxes = []
            else:
                resultboxes = [resultbox]
            #self.history.record('return', resultboxes, [])
            #self.guard_failure.make_ready_for_return(resultbox)
            #raise DoneMetaInterpreting
            raise self.DoneWithThisFrame(resultbox)

    def finishframe_exception(self, exceptionbox, excvaluebox):
        while self.framestack:
            frame = self.framestack[-1]
            if frame.exception_target >= 0:
                frame.pc = frame.exception_target
                frame.exception_target = -1
                frame.exception_box = exceptionbox
                frame.exc_value_box = excvaluebox
                return True
            self.framestack.pop()
        raise self.ExitFrameWithException(exceptionbox, excvaluebox)

    def create_empty_history(self):
        self.history = history.History(self.cpu)
        if self.enable_stats():
            self.stats.history_graph.operations = self.history.operations

    def delete_history(self):
        # XXX call me again later
        self.history = None
        self.framestack = None

    def interpret(self):
        # Execute the frames forward until we raise a DoneWithThisFrame,
        # a ContinueRunningNormally, or a GenerateMergePoint exception.
        if not we_are_translated():
            history.log.event('ENTER')
        else:
            debug_print('ENTER')
        try:
            while True:
                self.framestack[-1].run_one_step()
        finally:
            if not we_are_translated():
                history.log.event('LEAVE')
            else:
                debug_print('LEAVE')

    def compile_and_run(self, args):
        orig_boxes = self.initialize_state_from_start(args)
        try:
            self.interpret()
            assert False, "should always raise"
        except GenerateMergePoint, gmp:
            compiled_loop = self.compile(orig_boxes, gmp.argboxes)
            return self.designate_target_loop(gmp, compiled_loop)

    def handle_guard_failure(self, guard_failure):
        orig_boxes = self.initialize_state_from_guard_failure(guard_failure)
        try:
            if guard_failure.guard_op.opname in ['guard_exception',
                                                 'guard_no_exception']:
                self.raise_exception_upon_guard_failure(guard_failure)
            self.interpret()
            assert False, "should always raise"
        except GenerateMergePoint, gmp:
            compiled_bridge = self.compile_bridge(guard_failure, orig_boxes,
                                                  gmp.argboxes)
            loop, resargs = self.designate_target_loop(gmp,
                                                       compiled_bridge.jump_to)
            self.jump_after_guard_failure(guard_failure, loop, resargs)

    def designate_target_loop(self, gmp, loop):
        num_green_args = self.num_green_args
        residual_args = self.get_residual_args(loop,
                                               gmp.argboxes[num_green_args:])
        return (loop, residual_args)

    def jump_after_guard_failure(self, guard_failure, loop, residual_args):
        guard_failure.make_ready_for_continuing_at(loop.operations[0])
        for i in range(len(residual_args)):
            self.cpu.setvaluebox(guard_failure.frame, loop.operations[0],
                                 i, residual_args[i])

    def compile(self, original_boxes, live_arg_boxes):
        num_green_args = self.num_green_args
        for i in range(num_green_args):
            box1 = original_boxes[i]
            box2 = live_arg_boxes[i]
            if not box1.equals(box2):
                # not a valid loop
                raise self.ContinueRunningNormally(live_arg_boxes)
        mp = history.MergePoint('merge_point',
                                original_boxes[num_green_args:], [])
        mp.greenkey = original_boxes[:num_green_args]
        self.history.operations.insert(0, mp)
        old_loops = self.compiled_merge_points.setdefault(mp.greenkey, [])
        loop = compile_new_loop(self, old_loops,
                                live_arg_boxes[num_green_args:])
        if not loop:
            raise self.ContinueRunningNormally(live_arg_boxes)
        return loop

    def compile_bridge(self, guard_failure, original_boxes, live_arg_boxes):
        num_green_args = self.num_green_args
        mp = history.ResOperation('catch', original_boxes, [])
        mp.coming_from = guard_failure.guard_op
        self.history.operations.insert(0, mp)
        try:
            old_loops = self.compiled_merge_points[
                live_arg_boxes[:num_green_args]]
        except KeyError:
            bridge = None
        else:
            bridge = compile_new_bridge(self, old_loops,
                                        live_arg_boxes[num_green_args:])
        if bridge is None:
            raise self.ContinueRunningNormally(live_arg_boxes)
        guard_failure.guard_op.jump_target = bridge.operations[0]
        return bridge

    def get_residual_args(self, loop, args):
        mp = loop.operations[0]
        if mp.specnodes is None:     # it is None only for tests
            return args
        assert len(mp.specnodes) == len(args)
        expanded_args = []
        for i in range(len(mp.specnodes)):
            specnode = mp.specnodes[i]
            specnode.extract_runtime_data(self.cpu, args[i], expanded_args)
        return expanded_args

    def initialize_state_from_start(self, args):
        self.create_empty_history()
        num_green_args = self.num_green_args
        original_boxes = []
        for i in range(len(args)):
            value = args[i]
            if i < num_green_args:
                box = Const._new(value, self.cpu)
            else:
                box = Box._new(value, self.cpu)
            original_boxes.append(box)
        # ----- make a new frame -----
        self.framestack = []
        f = self.newframe(self.portal_code)
        f.pc = 0
        f.env = original_boxes[:]
        return original_boxes

    def initialize_state_from_guard_failure(self, guard_failure):
        # guard failure: rebuild a complete MIFrame stack
        if self.state.must_compile_from_failure(guard_failure):
            self.history = history.History(self.cpu)
        else:
            self.history = history.BlackHole(self.cpu)
        self.guard_failure = guard_failure
        guard_op = guard_failure.guard_op
        boxes_from_frame = []
        index = 0
        for box in guard_op.liveboxes:
            if isinstance(box, Box):
                newbox = self.cpu.getvaluebox(guard_failure.frame,
                                              guard_op, index)
                index += 1
            else:
                newbox = box
            boxes_from_frame.append(newbox)
        if guard_op.storage_info is not None:
            newboxes = optimize.rebuild_boxes_from_guard_failure(
                guard_op, self, boxes_from_frame)
        else:
            # xxx for tests only
            newboxes = boxes_from_frame
        self.rebuild_state_after_failure(guard_op.key, newboxes)
        return boxes_from_frame

    def raise_exception_upon_guard_failure(self, guard_failure):
        etype = self.cpu.get_exception(guard_failure.frame)
        evalue = self.cpu.get_exc_value(guard_failure.frame)
        self.handle_exception(etype, evalue)

    def handle_exception(self, etype, evalue):
        frame = self.framestack[-1]
        if etype:
            exception_box = ConstInt(etype)
            exc_value_box = BoxPtr(evalue)
            op = frame.generate_guard(frame.pc, 'guard_exception',
                                      None, [exception_box])
            if op:
                op.results = [exc_value_box]
            return self.finishframe_exception(exception_box, exc_value_box)
        else:
            frame.generate_guard(frame.pc, 'guard_no_exception', None, [])
            return False

##    def forced_vars_after_guard_failure(self, guard_failure):
##        # for a 'guard_true' or 'guard_false' failure, the purpose of this is
##        # to avoid a new 'guard' operation just to check for the other case
##        forced_vars = {}
##        guard_op = guard_failure.guard_op
##        assert guard_op.opname.startswith('guard_')
##        if guard_op.opname in ('guard_true', 'guard_false'):
##            guardbox = guard_op.args[0]
##            forced_vars[guardbox] = None
##        return forced_vars                

    def rebuild_state_after_failure(self, key, newboxes):
        self.framestack = []
        nbindex = 0
        for jitcode, pc, envlength, exception_target in key:
            f = self.newframe(jitcode)
            nbindex = f.setup_resume_at_op(pc, envlength, newboxes, nbindex,
                                           exception_target)
        assert nbindex == len(newboxes), "too many newboxes!"

    def record_compiled_merge_point(self, mp):
        pass
        #mplist = self.compiled_merge_points.setdefault(mp.greenkey, [])
        #mplist.append(mp)

    def record_state(self):
        # XXX this whole function should do a sharing
        key = []
        for frame in self.framestack:
            key.append((frame.jitcode, frame.pc, len(frame.env),
                        frame.exception_target))
        return key

##    def generate_mp_and_continue(self):
##        if self.most_recent_mp is not None:
##            return self.most_recent_mp
##        greenkey = []
##        liveboxes = []
##        memo = {}
##        for frame in self.framestack:
##            frame.record_state(greenkey, liveboxes, memo)
##        # try to loop back to a previous merge point with the same green key
##        mplist = self.history.get_merge_points_from_current_branch(greenkey)
##        for oldmp in mplist:
##            newloop = compile_new_loop(self, oldmp, liveboxes)
##            if newloop is not None:
##                self.execute_new_loop(newloop, liveboxes)
##                # ^^^ raised DoneMetaInterpreting
##        # else try to jump to some older already-compiled merge point
##        mplist = self.compiled_merge_points.get(greenkey, [])
##        for oldmp in mplist:
##            newbridge = compile_new_bridge(self, oldmp, liveboxes)
##            if newbridge is not None:
##                self.execute_new_loop(newbridge, liveboxes)
##                # ^^^ raised DoneMetaInterpreting
##        # else continue
##        mp = self.history.record_merge_point(greenkey, liveboxes)
##        self.most_recent_mp = mp
##        return mp

##    def execute_new_loop(self, loop, liveboxes):
##        mp = loop.get_final_target_mp()
##        specnode.copy_data_into_cpu_frame(self.cpu, self.guard_failure,
##                                          mp, liveboxes)
##        raise DoneMetaInterpreting

    def make_builtin_dictionary(self):
        # In case this is translated, the following runs at run-time.
        # It's not possible to make a dictionary with keys that are function
        # pointers at translation-time, as the actual address of each
        # function could change from run to run.
        if we_are_translated():
            self.builtins = {}
            for i in range(len(self.builtins_keys)):
                self.builtins[self.builtins_keys[i]] = self.builtins_values[i]

    def builtins_get(self, addr):
        assert lltype.typeOf(addr) == llmemory.Address
        if we_are_translated():
            return self.builtins.get(addr, (None, None))
        else:
            for i in range(len(self.builtins_keys)):
                if self.builtins_keys[i] == addr:
                    return self.builtins_values[i]
            return (None, None)

    # ____________________________________________________________
    # construction-time interface

    def _register_opcode(self, opname):
        assert len(self.opcode_implementations) < 256, \
               "too many implementations of opcodes!"
        name = "opimpl_" + opname
        self.opname_to_index[opname] = len(self.opcode_implementations)
        self.opcode_implementations.append(getattr(MIFrame, name).im_func)

    def find_opcode(self, name):
        try:
            return self.opname_to_index[name]
        except KeyError:
            self._register_opcode(name)
            return self.opname_to_index[name]


class GenerateMergePoint(Exception):
    def __init__(self, args):
        self.argboxes = args


class Options:
    def __init__(self, specialize=True):
        self.specialize = specialize
    def _freeze_(self):
        return True
