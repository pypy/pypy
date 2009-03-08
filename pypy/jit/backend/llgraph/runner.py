"""
Minimal-API wrapper around the llinterpreter to run operations.
"""

import sys
from pypy.rpython.lltypesystem import lltype, llmemory, rclass
from pypy.rpython.llinterp import LLInterpreter
from pypy.jit.metainterp import history
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.backend.llgraph import llimpl, symbolic


class MiniStats:
    pass


class CPU(object):

    def __init__(self, rtyper, stats=None, translate_support_code=False,
                 annmixlevel=None):
        self.rtyper = rtyper
        self.translate_support_code = translate_support_code
        self.jumptarget2loop = {}
        self.guard_ops = []
        self.compiled_single_ops = {}
        self.stats = stats or MiniStats()
        self.stats.exec_counters = {}
        self.stats.exec_jumps = 0
        self.memo_cast = llimpl.new_memo_cast()
        llimpl._stats = self.stats
        llimpl._rtyper = self.rtyper
        llimpl._llinterp = LLInterpreter(self.rtyper)
        if translate_support_code:
            self.mixlevelann = annmixlevel
        self.fielddescrof_vtable = self.fielddescrof(rclass.OBJECT, 'typeptr')

    def set_meta_interp(self, metainterp):
        self.metainterp = metainterp    # to handle guard failures

    def compile_operations(self, operations, from_guard=None):
        """In a real assembler backend, this should assemble the given
        list of operations.  Here we just generate a similar LoopOrBridge
        instance.  The code here is RPython, whereas the code in llimpl
        is not.
        """

        c = llimpl.compile_start()
        var2index = {}
        for i in range(len(operations[0].args)):
            box = operations[0].args[i]
            if isinstance(box, history.BoxInt):
                var2index[box] = llimpl.compile_start_int_var(c)
            elif isinstance(box, history.BoxPtr):
                var2index[box] = llimpl.compile_start_ptr_var(c)
            elif isinstance(box, history.Const):
                pass     # accept anything and ignore it
            else:
                raise Exception("box is: %r" % (box,))
        j = 0
        for i in range(len(operations)):
            op = operations[i]
            #if op.opname[0] == '#':
            #    continue
            op._compiled = c
            op._opindex = j
            j += 1
            llimpl.compile_add(c, op.opnum, op.descr)
            for x in op.args:
                if isinstance(x, history.Box):
                    llimpl.compile_add_var(c, var2index[x])
                elif isinstance(x, history.ConstInt):
                    llimpl.compile_add_int_const(c, x.value)
                elif isinstance(x, history.ConstPtr):
                    llimpl.compile_add_ptr_const(c, x.value)
                elif isinstance(x, history.ConstAddr):
                    llimpl.compile_add_int_const(c, x.getint())
                else:
                    raise Exception("%s args contain: %r" % (op.getopname(),
                                                             x))
            x = op.result
            if x is not None:
                if isinstance(x, history.BoxInt):
                    var2index[x] = llimpl.compile_add_int_result(c)
                elif isinstance(x, history.BoxPtr):
                    var2index[x] = llimpl.compile_add_ptr_result(c)
                else:
                    raise Exception("%s.result contain: %r" % (op.getopname(),
                                                               x))
            if op.jump_target is not None:
                loop_target, loop_target_index = \
                                           self.jumptarget2loop[op.jump_target]
                llimpl.compile_add_jump_target(c, loop_target,
                                                  loop_target_index)
            if op.is_guard():
                llimpl.compile_add_failnum(c, len(self.guard_ops))
                self.guard_ops.append(op)
                for box in op.liveboxes:
                    if isinstance(box, history.Box):
                        llimpl.compile_add_livebox(c, var2index[box])
            if op.opnum == rop.MERGE_POINT:
                self.jumptarget2loop[op] = c, i
        if from_guard is not None:
            llimpl.compile_from_guard(c, from_guard._compiled,
                                         from_guard._opindex)

    def execute_operations_in_new_frame(self, name, operations, valueboxes):
        """Perform a 'call' to the given merge point, i.e. create
        a new CPU frame and use it to execute the operations that
        follow the merge point.
        """
        frame = llimpl.new_frame(self.memo_cast)
        merge_point = operations[0]
        llimpl.frame_clear(frame, merge_point._compiled, merge_point._opindex)
        for box in valueboxes:
            if isinstance(box, history.BoxInt):
                llimpl.frame_add_int(frame, box.value)
            elif isinstance(box, history.BoxPtr):
                llimpl.frame_add_ptr(frame, box.value)
            elif isinstance(box, history.ConstInt):
                llimpl.frame_add_int(frame, box.value)
            elif isinstance(box, history.ConstPtr):
                llimpl.frame_add_ptr(frame, box.value)
            else:
                raise Exception("bad box in valueboxes: %r" % (box,))
        return self.loop(frame)

    def loop(self, frame):
        """Execute a loop.  When the loop fails, ask the metainterp for more.
        """
        while True:
            guard_index = llimpl.frame_execute(frame)
            guard_op = self.guard_ops[guard_index]
            assert isinstance(lltype.typeOf(frame), lltype.Ptr)
            gf = GuardFailed(frame, guard_op)
            self.metainterp.handle_guard_failure(gf)
            if gf.returns:
                return gf.retbox

    def getrealbox(self, guard_op, argindex):
        box = None
        i = 0
        j = argindex
        while j >= 0:
            box = guard_op.liveboxes[i]
            i += 1
            if isinstance(box, history.Box):
                j -= 1
        return box

    def getvaluebox(self, frame, guard_op, argindex):
        box = self.getrealbox(guard_op, argindex)
        if isinstance(box, history.BoxInt):
            value = llimpl.frame_int_getvalue(frame, argindex)
            return history.BoxInt(value)
        elif isinstance(box, history.BoxPtr):
            value = llimpl.frame_ptr_getvalue(frame, argindex)
            return history.BoxPtr(value)
        else:
            raise AssertionError('getvalue: box = %s' % (box,))

    def setvaluebox(self, frame, guard_op, argindex, valuebox):
        if isinstance(valuebox, history.BoxInt):
            llimpl.frame_int_setvalue(frame, argindex, valuebox.value)
        elif isinstance(valuebox, history.BoxPtr):
            llimpl.frame_ptr_setvalue(frame, argindex, valuebox.value)
        elif isinstance(valuebox, history.ConstInt):
            llimpl.frame_int_setvalue(frame, argindex, valuebox.value)
        elif isinstance(valuebox, history.ConstPtr):
            llimpl.frame_ptr_setvalue(frame, argindex, valuebox.value)
        elif isinstance(valuebox, history.ConstAddr):
            llimpl.frame_int_setvalue(frame, argindex, valuebox.getint())
        else:
            raise AssertionError('setvalue: valuebox = %s' % (valuebox,))

    def get_exception(self):
        return self.cast_adr_to_int(llimpl.get_exception())

    def get_exc_value(self):
        return llimpl.get_exc_value()

    def clear_exception(self):
        llimpl.clear_exception()

    def set_overflow_error(self):
        llimpl.set_overflow_error()

    @staticmethod
    def sizeof(S):
        return symbolic.get_size(S)

    @staticmethod
    def numof(S):
        return 4

    addresssuffix = '4'

    @staticmethod
    def fielddescrof(S, fieldname):
        ofs, size = symbolic.get_field_token(S, fieldname)
        token = history.getkind(getattr(S, fieldname))
        if token == 'ptr':
            bit = 1
        else:
            bit = 0
        return ofs*2 + bit

    @staticmethod
    def arraydescrof(A):
        assert isinstance(A, lltype.GcArray)
        size = symbolic.get_size(A)
        token = history.getkind(A.OF)
        if token == 'ptr':
            bit = 1
        else:
            bit = 0
        return size*2 + bit

    @staticmethod
    def calldescrof(ARGS, RESULT, ignored=None):
        if RESULT is lltype.Void:
            return sys.maxint
        token = history.getkind(RESULT)
        if token == 'ptr':
            return 1
        else:
            return 0

    @staticmethod
    def typefor(fielddesc):
        if fielddesc == sys.maxint:
            return 'void'
        if fielddesc % 2:
            return 'ptr'
        return 'int'

    @staticmethod
    def itemoffsetof(A):
        basesize, itemsize, ofs_length = symbolic.get_array_token(A)
        return basesize

    @staticmethod
    def arraylengthoffset(A):
        basesize, itemsize, ofs_length = symbolic.get_array_token(A)
        return ofs_length

    def cast_adr_to_int(self, adr):
        return llimpl.cast_adr_to_int(self.memo_cast, adr)

    def cast_int_to_adr(self, int):
        return llimpl.cast_int_to_adr(self.memo_cast, int)

    # ---------- the backend-dependent operations ----------

    def do_arraylen_gc(self, args, arraydescr):
        array = args[0].getptr_base()
        return history.BoxInt(llimpl.do_arraylen_gc(arraydescr, array))

    def do_strlen(self, args, descr=0):
        string = args[0].getptr_base()
        return history.BoxInt(llimpl.do_strlen(0, string))

    def do_strgetitem(self, args, descr=0):
        string = args[0].getptr_base()
        index = args[1].getint()
        return history.BoxInt(llimpl.do_strgetitem(0, string, index))

    def do_getarrayitem_gc(self, args, arraydescr):
        array = args[0].getptr_base()
        index = args[1].getint()
        if self.typefor(arraydescr) == 'ptr':
            return history.BoxPtr(llimpl.do_getarrayitem_gc_ptr(array, index))
        else:
            return history.BoxInt(llimpl.do_getarrayitem_gc_int(array, index,
                                                               self.memo_cast))

    def do_getfield_gc(self, args, fielddescr):
        struct = args[0].getptr_base()
        if self.typefor(fielddescr) == 'ptr':
            return history.BoxPtr(llimpl.do_getfield_gc_ptr(struct,
                                                            fielddescr))
        else:
            return history.BoxInt(llimpl.do_getfield_gc_int(struct,
                                                            fielddescr,
                                                            self.memo_cast))

    def do_getfield_raw(self, args, fielddescr):
        struct = self.cast_int_to_adr(args[0].getint())
        if self.typefor(fielddescr) == 'ptr':
            return history.BoxPtr(llimpl.do_getfield_raw_ptr(struct,
                                                             fielddescr))
        else:
            return history.BoxInt(llimpl.do_getfield_raw_int(struct,
                                                             fielddescr,
                                                             self.memo_cast))

    def do_new(self, args, size):
        return history.BoxPtr(llimpl.do_new(size))

    def do_new_with_vtable(self, args, size):
        vtable = args[0].getint()
        result = llimpl.do_new(size)
        llimpl.do_setfield_gc_int(result, self.fielddescrof_vtable, vtable,
                                  self.memo_cast)
        return history.BoxPtr(result)

    def do_new_array(self, args, size):
        count = args[0].getint()
        return history.BoxPtr(llimpl.do_new_array(size, count))

    def do_setarrayitem_gc(self, args, arraydescr):
        array = args[0].getptr_base()
        index = args[1].getint()
        if self.typefor(arraydescr) == 'ptr':
            newvalue = args[2].getptr_base()
            llimpl.do_setarrayitem_gc_ptr(array, index, newvalue)
        else:
            newvalue = args[2].getint()
            llimpl.do_setarrayitem_gc_int(array, index, newvalue,
                                          self.memo_cast)

    def do_setfield_gc(self, args, fielddescr):
        struct = args[0].getptr_base()
        if self.typefor(fielddescr) == 'ptr':
            newvalue = args[1].getptr_base()
            llimpl.do_setfield_gc_ptr(struct, fielddescr, newvalue)
        else:
            newvalue = args[1].getint()
            llimpl.do_setfield_gc_int(struct, fielddescr, newvalue,
                                      self.memo_cast)

    def do_setfield_raw(self, args, fielddescr):
        struct = self.cast_int_to_adr(args[0].getint())
        if self.typefor(fielddescr) == 'ptr':
            newvalue = args[1].getptr_base()
            llimpl.do_setfield_raw_ptr(struct, fielddescr, newvalue)
        else:
            newvalue = args[1].getint()
            llimpl.do_setfield_raw_int(struct, fielddescr, newvalue,
                                       self.memo_cast)

    def do_newstr(self, args, descr=0):
        length = args[0].getint()
        return history.BoxPtr(llimpl.do_newstr(0, length))

    def do_strsetitem(self, args, descr=0):
        string = args[0].getptr_base()
        index = args[1].getint()
        newvalue = args[2].getint()
        llimpl.do_strsetitem(0, string, index, newvalue)

    def do_call(self, args, calldescr):
        func = args[0].getint()
        for arg in args[1:]:
            if (isinstance(arg, history.BoxPtr) or
                isinstance(arg, history.ConstPtr)):
                llimpl.do_call_pushptr(arg.getptr_base())
            else:
                llimpl.do_call_pushint(arg.getint())
        restype = self.typefor(calldescr)
        if restype == 'ptr':
            return history.BoxPtr(llimpl.do_call_ptr(func, self.memo_cast))
        elif restype == 'int':
            return history.BoxInt(llimpl.do_call_int(func, self.memo_cast))
        else:  # restype == 'void'
            llimpl.do_call_void(func, self.memo_cast)


class GuardFailed(object):
    returns = False

    def __init__(self, frame, guard_op):
        self.frame = frame
        self.guard_op = guard_op

    def make_ready_for_return(self, retbox):
        self.returns = True
        self.retbox = retbox

    def make_ready_for_continuing_at(self, merge_point):
        llimpl.frame_clear(self.frame, merge_point._compiled,
                           merge_point._opindex)
        self.merge_point = merge_point

# ____________________________________________________________

import pypy.jit.metainterp.executor
pypy.jit.metainterp.executor.make_execute_list(CPU)
