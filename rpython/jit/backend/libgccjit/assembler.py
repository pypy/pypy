from rpython.jit.backend.llsupport import jitframe
from rpython.jit.backend.llsupport.assembler import BaseAssembler
from rpython.jit.backend.llsupport.asmmemmgr import MachineDataBlockWrapper
from rpython.jit.backend.llsupport.regalloc import FrameManager
from rpython.jit.backend.model import CompiledLoopToken
from rpython.jit.backend.libgccjit.rffi_bindings import make_eci, Library, make_param_array, make_field_array, Context, Type
from rpython.jit.metainterp.history import BoxInt, ConstInt
from rpython.jit.metainterp.resoperation import *
from rpython.rtyper.annlowlevel import llhelper, cast_instance_to_gcref, cast_object_to_ptr
from rpython.rtyper.lltypesystem.rffi import *
from rpython.rtyper.lltypesystem import lltype, rffi, rstr, llmemory

class AssemblerLibgccjit(BaseAssembler):
    _regalloc = None
    #_output_loop_log = None
    #_second_tmp_reg = ecx

    DEBUG_FRAME_DEPTH = False

    def __init__(self, cpu, translate_support_code=False):
        BaseAssembler.__init__(self, cpu, translate_support_code)
        #self.verbose = False
        self.verbose = True
        self.loop_run_counters = []
        self.float_const_neg_addr = 0
        self.float_const_abs_addr = 0
        self.malloc_slowpath = 0
        self.malloc_slowpath_varsize = 0
        self.wb_slowpath = [0, 0, 0, 0, 0]
        #self.setup_failure_recovery()
        self.datablockwrapper = None
        self.stack_check_slowpath = 0
        self.propagate_exception_path = 0
        #self.teardown()

        self.num_anon_loops = 0

        self.make_context()
        self.t_long = self.ctxt.get_type(self.lib.GCC_JIT_TYPE_LONG)
        self.t_bool = self.ctxt.get_type(self.lib.GCC_JIT_TYPE_BOOL)
        self.t_void_ptr = self.ctxt.get_type(self.lib.GCC_JIT_TYPE_VOID_PTR)

    def make_context(self):
        eci = make_eci()
        self.lib = Library(eci)
        self.ctxt = Context.acquire(self.lib)#self.lib.gcc_jit_context_acquire()
        self.ctxt.set_bool_option(self.lib.GCC_JIT_BOOL_OPTION_DUMP_INITIAL_TREE, r_int(1))
        if 1:
            self.ctxt.set_bool_option(self.lib.GCC_JIT_BOOL_OPTION_DUMP_INITIAL_GIMPLE,
                                      r_int(1))
        self.ctxt.set_bool_option(self.lib.GCC_JIT_BOOL_OPTION_DEBUGINFO,
                                  r_int(1))
        if 1:
            self.ctxt.set_int_option(self.lib.GCC_JIT_INT_OPTION_OPTIMIZATION_LEVEL,
                                     r_int(3))
        self.ctxt.set_bool_option(self.lib.GCC_JIT_BOOL_OPTION_KEEP_INTERMEDIATES,
                                  r_int(1))
        self.ctxt.set_bool_option(self.lib.GCC_JIT_BOOL_OPTION_DUMP_EVERYTHING,
                                  r_int(1))
        if 1:
            self.ctxt.set_bool_option(self.lib.GCC_JIT_BOOL_OPTION_DUMP_GENERATED_CODE,
                                      r_int(1))
        
    def setup(self, looptoken):
        allblocks = self.get_asmmemmgr_blocks(looptoken)
        self.datablockwrapper = MachineDataBlockWrapper(self.cpu.asmmemmgr,
                                                        allblocks)

    def get_asmmemmgr_blocks(self, looptoken):
        clt = looptoken.compiled_loop_token
        if clt.asmmemmgr_blocks is None:
            clt.asmmemmgr_blocks = []
        return clt.asmmemmgr_blocks

    def assemble_loop(self, inputargs, operations, looptoken, log,
                      loopname, logger):
        print('assemble_loop')
        clt = CompiledLoopToken(self.cpu, looptoken.number)
        print(clt)
        looptoken.compiled_loop_token = clt
        clt._debug_nbargs = len(inputargs)

        self.setup(looptoken)

        frame_info = self.datablockwrapper.malloc_aligned(
            jitframe.JITFRAMEINFO_SIZE, alignment=64) #WORD)
        clt.frame_info = rffi.cast(jitframe.JITFRAMEINFOPTR, frame_info)
        clt.allgcrefs = []
        clt.frame_info.clear() # for now

        self.lvalue_for_box = {}

        print(jitframe.JITFRAME)
        print(dir(jitframe.JITFRAME))
        print('jitframe.JITFRAME._flds: %r' % jitframe.JITFRAME._flds)

        # For now, build a "struct jit_frame".
        # This will have the fields of jitframe,
        # We'll construct numbered arg0..argN for use
        # for inputargs and the outputs

        fields = []
        def make_field(name, jit_type):
            field = self.ctxt.new_field(jit_type,name)
            fields.append(field)
            return field
        make_field('jfi_frame_depth', self.t_long)
        make_field('jfi_frame_size', self.t_long)

        t_JITFRAMEINFO = (
            self.ctxt.new_struct_type ("JITFRAMEINFO",
                                       fields).as_type())

        t_JITFRAMEINFOPTR = t_JITFRAMEINFO.get_pointer()

        struct_jit_frame = self.ctxt.new_opaque_struct ("JITFRAME")

        t_jit_frame_ptr = struct_jit_frame.as_type().get_pointer()

        fields = []
        # FIXME: Does the GCStruct implicitly add any fields?
        # If I omit this, then the jf_* fields appears in the same
        # place in llmodel.py's get_latest_descr deadframe as
        # in my generated code as seen in gdb.
        #make_field('hack_rtti', self.t_void_ptr)
        make_field('jf_frame_info', t_JITFRAMEINFOPTR)
        self.field_jf_descr = make_field('jf_descr', self.t_void_ptr)
        make_field('jf_force_descr', self.t_void_ptr)
        make_field('jf_gcmap', self.t_void_ptr)
        make_field('jf_extra_stack_depth', self.t_long)
        make_field('jf_savedata', self.t_void_ptr)
        make_field('jf_guard_exc', self.t_void_ptr)
        make_field('jf_forward', t_jit_frame_ptr)
        # FIXME: for some reason there's an implicit word here;
        # create it
        make_field('jf_frame', self.t_long)

        locs = []
        #loc = jitframe.getofs('jf_frame')

        max_args = len(inputargs)
        for op in operations:
            if op.getopname() == 'finish':
                max_args = max(max_args, len(op._args))
            # FIXME: other ops

        self.field_for_arg_idx = {}
        for idx in range(max_args):
            self.field_for_arg_idx[idx] = make_field("arg%i" % idx,
                                                     self.t_long)
            locs.append(idx) # hack!

        struct_jit_frame.set_fields (fields)

        # Make function:
        print('  inputargs: %r' % (inputargs, ))
        #jitframe.JITFRAMEINFOPTR
        params = []

        self.param_frame = self.ctxt.new_param(t_jit_frame_ptr, "jitframe")
        params.append(self.param_frame)

        self.param_addr = self.ctxt.new_param(self.t_void_ptr, "addr")
        params.append(self.param_addr)

        print("loopname: %r" % loopname)
        if not loopname:
            loopname = 'anonloop_%i' % self.num_anon_loops
            self.num_anon_loops += 1
        self.fn = self.ctxt.new_function(self.lib.GCC_JIT_FUNCTION_EXPORTED,
                                         t_jit_frame_ptr, # self.t_long,
                                         loopname,
                                         params,
                                         r_int(0))

        self.b_current = self.fn.new_block("initial")
        self.label_for_descr = {}
        self.block_for_label_descr = {}

        # Add an initial comment summarizing the loop
        text = '\n\tinputargs: %s\n\n' % inputargs
        for op in operations:
            print(op)
            print(type(op))
            print(dir(op))
            print(repr(op.getopname()))
            text += '\t%s\n' % op
        self.b_current.add_comment(str(text))
    
        # Get initial values from input args:
        for idx, arg in enumerate(inputargs):
            self.b_current.add_comment("inputargs[%i]: %s" % (idx, arg))
            self.b_current.add_assignment(
                self.get_box_as_lvalue(arg),
                self.get_arg_as_lvalue(idx).as_rvalue())

        for op in operations:
            print(op)
            print(type(op))
            print(dir(op))
            print(repr(op.getopname()))
            # Add a comment describing this ResOperation
            self.b_current.add_comment(str(op))

            # Compile the operation itself...
            methname = 'emit_%s' % op.getopname()
            getattr(self, methname) (op)

        
        self.ctxt.dump_to_file("/tmp/foo.c", r_int(1))

        #raise foo

        jit_result = self.ctxt.compile()
        self.ctxt.release()

        fn_ptr = jit_result.get_code(loopname)

        looptoken._ll_function_addr = fn_ptr

        looptoken.compiled_loop_token._ll_initial_locs = locs

        # FIXME: this leaks the gcc_jit_result

    def expr_to_rvalue(self, expr):
        """
        print('expr_to_rvalue')
        print(' %s' % expr)
        print(' %r' % expr)
        print(' %s' % type(expr))
        print(' %s' % dir(expr))
        print(' %s' % expr.__dict__)
        """

        if isinstance(expr, BoxInt):
            return self.get_box_as_lvalue(expr).as_rvalue()
        elif isinstance(expr, ConstInt):
            #print('value: %r' % expr.value)
            #print('type(value): %r' % type(expr.value))
            return self.ctxt.new_rvalue_from_int(self.t_long,
                                                 r_int(expr.value))
        raise ValueError('unhandled expr: %s' % expr)

    def get_box_as_lvalue(self, box):
        if box not in self.lvalue_for_box:
            self.lvalue_for_box[box] = self.fn.new_local(self.t_long,
                                                         str(box))
        return self.lvalue_for_box[box]

    def get_arg_as_lvalue(self, idx):
        return self.param_frame.as_rvalue ().dereference_field (
            self.field_for_arg_idx[idx])

    def expr_to_lvalue(self, expr):
        """
        print('expr_to_lvalue')
        print(' %s' % expr)
        print(' %r' % expr)
        print(' %s' % type(expr))
        print(' %s' % dir(expr))
        print(' %s' % expr.__dict__)
        """
        if isinstance(expr, BoxInt):
            return self.get_box_as_lvalue(expr)
        raise ValueError('unhandled expr: %s' % expr)

    # Handling of specific ResOperation subclasses

    def emit_int_add(self, op):
        """
        print(op._arg0)
        print(op._arg1)
        print(op.result)
        print(op.__dict__)
        """
        rval0 = self.expr_to_rvalue(op._arg0)
        rval1 = self.expr_to_rvalue(op._arg1)
        lvalres = self.expr_to_lvalue(op.result)

        op_add = (
            self.ctxt.new_binary_op(self.lib.GCC_JIT_BINARY_OP_PLUS,
                                    self.t_long,
                                    rval0, rval1))
        self.b_current.add_assignment(lvalres, op_add)

    def emit_label(self, op):
        print(op)
        print(op.__dict__)
        #print('op.getdescr(): %r' % op.getdescr())
        #print('op.getdescr().__dict__: %r' % op.getdescr().__dict__)

        b_new = self.fn.new_block(str(op))
        self.block_for_label_descr[op.getdescr()] = b_new
        self.label_for_descr[op.getdescr()] = op
        self.b_current.end_with_jump(b_new)
        self.b_current = b_new

    def emit_jump(self, jumpop):
        print(jumpop)
        print(jumpop.__dict__)
        label = self.label_for_descr[jumpop.getdescr()]
        print(jumpop.getdescr())
        print('label: %r' % label)

        assert len(jumpop._args) == len(label._args)

        # We need to write to the boxes listed in the label's args
        # with the values from those listed in the jump's args.
        # However, there are potential cases like JUMP(i0, i1) going to LABEL(i1, i0)
        # where all such assignments happen "simultaneously".
        # Hence we need to set up temporaries.
        # First pass: capture the value of relevant boxes at the JUMP:
        tmps = []
        for i in range(len(jumpop._args)):
            tmps.append(self.fn.new_local(self.t_long, "tmp%i" % i))
            self.b_current.add_assignment(
                tmps[i],
                self.get_box_as_lvalue(jumpop._args[i]).as_rvalue())
        # Second pass: write the values to the boxes at the LABEL:
        for i in range(len(jumpop._args)):
            self.b_current.add_assignment(
                self.get_box_as_lvalue(label._args[i]),
                tmps[i].as_rvalue())
            
        self.b_current.end_with_jump(self.block_for_label_descr[jumpop.getdescr()])

    def impl_int_cmp(self, op, gcc_jit_comparison):
        rval0 = self.expr_to_rvalue(op._arg0)
        rval1 = self.expr_to_rvalue(op._arg1)
        lvalres = self.expr_to_lvalue(op.result)
        op_cmp = (
            self.ctxt.new_cast(
                self.ctxt.new_comparison(gcc_jit_comparison,
                                         rval0, rval1),
                self.t_long)
            )
        self.b_current.add_assignment(lvalres,
                                      op_cmp)

    def emit_int_le(self, op):
        self.impl_int_cmp(op, self.lib.GCC_JIT_COMPARISON_LE)

    def emit_int_ge(self, op):
        self.impl_int_cmp(op, self.lib.GCC_JIT_COMPARISON_GE)

    def emit_guard_true(self, op):
        print(op)
        print(op.__dict__)
        b_true = self.fn.new_block("on_true_at_%s" % op)
        b_false = self.fn.new_block("on_false_at_%s" % op)
        boolval = self.ctxt.new_cast(self.expr_to_rvalue(op._arg0),
                                     self.t_bool)
        self.b_current.end_with_conditional(boolval,
                                            b_true, b_false)

        self.b_current = b_false
        self.impl_write_output_args(op._fail_args)
        self.impl_write_jf_descr(op)
        self.b_current.end_with_return(self.param_frame.as_rvalue ())
        rd_locs = []
        for idx, arg in enumerate(op._fail_args):
            rd_locs.append(idx)
        op.getdescr().rd_locs = rd_locs

        self.b_current = b_true

    def impl_write_output_args(self, args):
        # Write outputs back:
        for idx, arg in enumerate(args):
            self.b_current.add_assignment(
                self.get_arg_as_lvalue(idx),
                self.get_box_as_lvalue(arg).as_rvalue())

    def impl_write_jf_descr(self, op):
        # Write back to the jf_descr:
        #  "jitframe->jf_descr = op.getdescr();"
        descr = rffi.cast(lltype.Signed,
                          cast_instance_to_gcref(op.getdescr()))

        self.b_current.add_assignment(
            self.param_frame.as_rvalue ().dereference_field (
                self.field_jf_descr),
            self.ctxt.new_rvalue_from_ptr (self.t_void_ptr,
                                           rffi.cast(VOIDP, descr)))
    
    def emit_finish(self, op):
        self.impl_write_output_args(op._args)
        self.impl_write_jf_descr(op)
        self.b_current.end_with_return(self.param_frame.as_rvalue ())
