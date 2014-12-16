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
        self.t_int = self.ctxt.get_type(self.lib.GCC_JIT_TYPE_INT)
        self.t_void_ptr = self.ctxt.get_type(self.lib.GCC_JIT_TYPE_VOID_PTR)

    def make_context(self):
        eci = make_eci()
        self.lib = Library(eci)
        self.ctxt = Context.acquire(self.lib)#self.lib.gcc_jit_context_acquire()
        self.ctxt.set_bool_option(self.lib.GCC_JIT_BOOL_OPTION_DUMP_INITIAL_GIMPLE,
                                  r_int(1))
        self.ctxt.set_bool_option(self.lib.GCC_JIT_BOOL_OPTION_DEBUGINFO,
                                  r_int(1))
        self.ctxt.set_int_option(self.lib.GCC_JIT_INT_OPTION_OPTIMIZATION_LEVEL,
                                 r_int(3))
        self.ctxt.set_bool_option(self.lib.GCC_JIT_BOOL_OPTION_KEEP_INTERMEDIATES,
                                  r_int(1))
        self.ctxt.set_bool_option(self.lib.GCC_JIT_BOOL_OPTION_DUMP_EVERYTHING,
                                  r_int(1))
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
        # This will have the fields of jitframe, but instead of 
        # jf_frame, we'll have any input and output boxes:
        visible_boxes = []
        for arg in inputargs:
            visible_boxes.append(arg)
        for op in operations:
            if op.getopname() == 'finish':
                for arg in op._args:
                    if arg not in visible_boxes:
                        visible_boxes.append(arg)
        print('visible_boxes: %r' % visible_boxes)

        fields = []
        def make_field(name, jit_type):
            field = self.ctxt.new_field(jit_type,name)
            fields.append(field)
            return field
        make_field('jfi_frame_depth', self.t_int)
        make_field('jfi_frame_size', self.t_int)

        t_JITFRAMEINFO = (
            self.ctxt.new_struct_type ("JITFRAMEINFO",
                                       fields).as_type())

        t_JITFRAMEINFOPTR = t_JITFRAMEINFO.get_pointer()

        struct_jit_frame = self.ctxt.new_opaque_struct ("JITFRAME")

        t_jit_frame_ptr = struct_jit_frame.as_type().get_pointer()

        fields = []
        # FIXME: Does the GCStruct implicitly add any fields?
        # If I put this here, then the arguments appear to be written to the
        # place where I expect:
        make_field('hack_rtti', self.t_void_ptr)
        make_field('jf_frame_info', t_JITFRAMEINFOPTR)
        self.field_jf_descr = make_field('jf_descr', self.t_void_ptr)
        make_field('jf_force_descr', self.t_void_ptr)
        make_field('jf_gcmap', self.t_void_ptr)
        make_field('jf_extra_stack_depth', self.t_int)
        make_field('jf_savedata', self.t_void_ptr)
        make_field('jf_guard_exc', self.t_void_ptr)
        make_field('jf_forward', t_jit_frame_ptr)
        # jf_frame:
        self.field_for_box = {}
        locs = []
        #loc = jitframe.getofs('jf_frame')
        for loc, box in enumerate(visible_boxes):
            field = make_field(str(box), self.t_int)
            locs.append(loc) # hack!
            self.field_for_box[box] = field

        struct_jit_frame.set_fields (fields)

        # Make function:
        print('  inputargs: %r' % (inputargs, ))
        #jitframe.JITFRAMEINFOPTR
        params = []

        self.param_frame = self.ctxt.new_param(t_jit_frame_ptr, "jitframe")
        params.append(self.param_frame)

        self.param_addr = self.ctxt.new_param(self.t_void_ptr, "addr")
        params.append(self.param_addr)

        # For now, generate lvalues for the "visible boxes" directly as
        # field lookups within the jit_frame:
        for box in visible_boxes:
            self.lvalue_for_box[box] = (
                self.param_frame.as_rvalue().
                  dereference_field (self.field_for_box[box]))

        """
        for arg in inputargs:
            param_name = str2charp(str(arg))
            param = self.lib.gcc_jit_context_new_param(self.ctxt,
                                                       self.lib.null_location_ptr,
                                                       self.t_int, # FIXME: use correct type
                                                       param_name)
            self.lvalue_for_box[arg] = self.lib.gcc_jit_param_as_lvalue(param)
            free_charp(param_name)
            params.append(param)
        """
        
        print("loopname: %r" % loopname)
        if not loopname:
            loopname = 'anonloop_%i' % self.num_anon_loops
            self.num_anon_loops += 1
        self.fn = self.ctxt.new_function(self.lib.GCC_JIT_FUNCTION_EXPORTED,
                                         t_jit_frame_ptr, # self.t_int,
                                         loopname,
                                         params,
                                         r_int(0))

        self.b_current = self.fn.new_block()

        for op in operations:
            print(op)
            print(type(op))
            print(dir(op))
            print(repr(op.getopname()))
            # Add a comment describing this ResOperation
            self.b_current.add_comment(str(op))

            # Compile the operation itself...
            methname = '_emit_%s' % op.getopname()
            getattr(self, methname) (op)

        
        self.ctxt.dump_to_file("/tmp/foo.c", r_int(1))

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
            return self.ctxt.new_rvalue_from_int(self.t_int,
                                                 r_int(expr.value))
        raise ValueError('unhandled expr: %s' % expr)

    def get_box_as_lvalue(self, box):
        if box not in self.lvalue_for_box:
            raise foo
            self.lvalue_for_box[box] = (
                self.fn.new_local(self.t_int, # FIXME: use correct type
                                  local_name))
        return self.lvalue_for_box[box]

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

    def _emit_int_add(self, op):
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
                                    self.t_int,
                                    rval0, rval1))
        self.b_current.add_assignment(lvalres, op_add)

    def _emit_finish(self, op):
        # Write back to the jf_descr:
        #  "jitframe->jf_descr = op.getdescr();"
        descr = rffi.cast(lltype.Signed,
                          cast_instance_to_gcref(op.getdescr()))

        self.b_current.add_assignment(
            self.param_frame.as_rvalue ().dereference_field (
                self.field_jf_descr),
            self.ctxt.new_rvalue_from_ptr (self.t_void_ptr,
                                           rffi.cast(VOIDP, descr)))

        self.b_current.end_with_return(self.param_frame.as_rvalue ())
