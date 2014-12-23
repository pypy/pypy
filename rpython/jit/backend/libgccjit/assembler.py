from rpython.jit.backend.llsupport import jitframe
from rpython.jit.backend.llsupport.assembler import BaseAssembler
from rpython.jit.backend.llsupport.asmmemmgr import MachineDataBlockWrapper
from rpython.jit.backend.llsupport.regalloc import FrameManager
from rpython.jit.backend.model import CompiledLoopToken
from rpython.jit.backend.libgccjit.rffi_bindings import (
    make_eci, Library, make_param_array, make_field_array, Context, Type,
    RValue)
from rpython.jit.metainterp.history import (
    BoxInt, ConstInt, BoxFloat, ConstFloat, BoxPtr, ConstPtr)
from rpython.jit.metainterp.resoperation import *
from rpython.rtyper.annlowlevel import (
    llhelper, cast_instance_to_gcref, cast_object_to_ptr)
from rpython.rtyper.lltypesystem.rffi import *
from rpython.rtyper.lltypesystem import lltype, rffi, rstr, llmemory

# Global state
num_anon_loops = 0
num_guard_failure_fns = 0
num_bridges = 0

class Params:
    def __init__(self, assembler):
        self.paramlist = []
        self.param_frame = assembler.ctxt.new_param(assembler.t_jit_frame_ptr,
                                                    "jitframe")
        self.paramlist.append(self.param_frame)

        self.param_addr = assembler.ctxt.new_param(assembler.t_void_ptr,
                                                   "addr")
        self.paramlist.append(self.param_addr)
        self.paramtypes = [assembler.t_jit_frame_ptr,
                           assembler.t_void_ptr]

class Function:
    """
    Wrapper around a rffi_bindings.Function, for a loop or bridge
    """
    def __init__(self, name, rffi_fn):
        self.name = name
        self.rffi_fn = rffi_fn
        self.patchpoints = []

    def new_block(self, name):
       return self.rffi_fn.new_block(name)

    def new_local(self, type_, name):
       return self.rffi_fn.new_local(type_, name)

class Patchpoint:
    """
    We need to be able to patch out the generated code that runs when a
    guard fails; this class handles that.

    We handle guard failure with a tail-call through a function pointer,
    equivalent to this C code:

      struct JITFRAME * (*guard_failure_fn_ptr_0) (struct JITFRAME *, void *);

      extern struct JITFRAME *
      anonloop_0 (struct JITFRAME * jitframe, void * addr)
      {
        ...various operations...

        if (!guard)
         goto on_guard_failure;

        ...various operations...

       on_guard_failure:
          return guard_failure_fn_ptr_0 (frame, );
      }

    This can hopefully be optimized to a jump through a ptr, since it's
    a tail call:

      0x00007fffeb7086d0 <+16>:  jle    0x7fffeb7086c8 <anonloop_0+8>
      0x00007fffeb7086d2 <+18>:  mov    %rax,0x48(%rdi)
      0x00007fffeb7086d6 <+22>:  mov    0x2008fb(%rip),%rax   # 0x7fffeb908fd8
      0x00007fffeb7086dd <+29>:  mov    (%rax),%rax
      0x00007fffeb7086e0 <+32>:  jmpq   *%rax
    """
    def __init__(self, assembler):
        self.failure_params = Params(assembler)
        global num_guard_failure_fns
        self.serial = num_guard_failure_fns
        num_guard_failure_fns += 1
        self.t_fn_ptr_type = assembler.ctxt.new_function_ptr_type (
            assembler.t_jit_frame_ptr,
            self.failure_params.paramtypes,
            r_int(0))
        # Create the function ptr
        # Globals are zero-initialized, so we'll need to
        # write in the ptr to the initial handler before the loop is called,
        # or we'll have a jump-through-NULL segfault.
        self.fn_ptr_name = "guard_failure_fn_ptr_%i" % self.serial
        self.failure_fn_ptr = (
            assembler.ctxt.new_global(assembler.lib.GCC_JIT_GLOBAL_EXPORTED,
                                      self.t_fn_ptr_type,
                                      self.fn_ptr_name))
        self.handler_name = "on_guard_failure_%i" % self.serial
        self.failure_fn = (
            assembler.ctxt.new_function(assembler.lib.GCC_JIT_FUNCTION_EXPORTED,
                                        assembler.t_jit_frame_ptr,
                                        self.handler_name,
                                        self.failure_params.paramlist,
                                        r_int(0)))

    def write_initial_handler(self, result):
        # Get the address of the machine code for the handler;
        # this is a:
        #   struct JITFRAME * (*guard_failure_fn) (struct JITFRAME *, void *)
        handler = result.get_code(self.handler_name)

        # Get the address of the function ptr to be written to;
        # this is a:
        #   struct JITFRAME * (**guard_failure_fn) (struct JITFRAME *, void *)
        # i.e. one extra level of indirection.
        self.fn_ptr_ptr = result.get_global(self.fn_ptr_name)

        self.set_handler(handler)

    def set_handler(self, handler):
        print('set_handler(%r)' % handler)

        # We want to write the equivalent of:
        #    (*fn_ptr_ptr) = handler;
        #
        # "fn_ptr_ptr" and "handler" are both currently (void *).
        # so we need to cast them to a form where we can express
        # the above.

        # We can't directly express the function ptr ptr in lltype,
        # so instead pretend we have a (const char **) and a (const char *):
        fn_ptr_ptr = rffi.cast(rffi.CCHARPP, self.fn_ptr_ptr)
        handler = rffi.cast(rffi.CCHARP, handler)

        # ...and write through the ptr:
        fn_ptr_ptr[0] = handler

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

        self.sizeof_signed = rffi.sizeof(lltype.Signed)
        self.label_for_descr = {}
        self.block_for_label_descr = {}
        self.function_for_label_descr = {}
        self.patchpoint_for_descr = {}

        eci = make_eci()
        self.lib = Library(eci)

    def make_context(self):
        self.ctxt = Context.acquire(self.lib)#self.lib.gcc_jit_context_acquire()
        if 0:
            self.ctxt.set_bool_option(
                self.lib.GCC_JIT_BOOL_OPTION_DUMP_INITIAL_TREE,
                r_int(1))
        if 0:
            self.ctxt.set_bool_option(
                self.lib.GCC_JIT_BOOL_OPTION_DUMP_INITIAL_GIMPLE,
                r_int(1))
        if 1:
            self.ctxt.set_bool_option(
                self.lib.GCC_JIT_BOOL_OPTION_DEBUGINFO,
                r_int(1))
        if 1:
            self.ctxt.set_int_option(
                self.lib.GCC_JIT_INT_OPTION_OPTIMIZATION_LEVEL,
                r_int(2))
        if 1:
            self.ctxt.set_bool_option(
                self.lib.GCC_JIT_BOOL_OPTION_KEEP_INTERMEDIATES,
                r_int(1))
        if 1:
            self.ctxt.set_bool_option(
                self.lib.GCC_JIT_BOOL_OPTION_DUMP_EVERYTHING,
                r_int(1))
        if 0:
            self.ctxt.set_bool_option(
                self.lib.GCC_JIT_BOOL_OPTION_DUMP_GENERATED_CODE,
                r_int(1))

        self.t_Signed = self.ctxt.get_int_type(r_int(self.sizeof_signed),
                                               r_int(1))
        self.t_UINT = self.ctxt.get_int_type(r_int(self.sizeof_signed),
                                             r_int(0))
        self.t_float = self.ctxt.get_type(self.lib.GCC_JIT_TYPE_DOUBLE) # FIXME
        self.t_bool = self.ctxt.get_type(self.lib.GCC_JIT_TYPE_BOOL)
        self.t_void_ptr = self.ctxt.get_type(self.lib.GCC_JIT_TYPE_VOID_PTR)
        self.t_void = self.ctxt.get_type(self.lib.GCC_JIT_TYPE_VOID)
        self.t_char_ptr = self.ctxt.get_type(
            self.lib.GCC_JIT_TYPE_CHAR).get_pointer()

        self.u_signed = self.ctxt.new_field(self.t_Signed, "u_signed")
        self.u_float = self.ctxt.new_field(self.t_float, "u_float")
        self.u_ptr = self.ctxt.new_field(self.t_void_ptr, "u_ptr")
        self.t_any = self.ctxt.new_union_type ("any",
                                               [self.u_signed,
                                                self.u_float,
                                                self.u_ptr])

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
        #print(clt)
        looptoken.compiled_loop_token = clt
        clt._debug_nbargs = len(inputargs)

        self.setup(looptoken)

        frame_info = self.datablockwrapper.malloc_aligned(
            jitframe.JITFRAMEINFO_SIZE, alignment=64) #WORD)
        clt.frame_info = rffi.cast(jitframe.JITFRAMEINFOPTR, frame_info)
        clt.allgcrefs = []
        clt.frame_info.clear() # for now

        self.make_context()
        max_args, initial_locs = self.make_JITFRAME_struct(inputargs,
                                                           operations)
        self.lvalue_for_box = {}

        if not loopname:
            global num_anon_loops
            loopname = 'anonloop_%i' % num_anon_loops
            num_anon_loops += 1
        print("  loopname: %r" % loopname)
        self.make_function(loopname, inputargs, operations)

        # Ensure that the frame is large enough
        baseofs = self.cpu.get_baseofs_of_frame_field()
        clt.frame_info.update_frame_depth(baseofs,
                                          max_args)

        self.datablockwrapper.done()      # finish using cpu.asmmemmgr
        self.datablockwrapper = None

        self.ctxt.dump_to_file("/tmp/%s.c" % loopname, r_int(1))

        #raise foo

        jit_result = self.ctxt.compile()
        self.ctxt.release()

        # Patch all patchpoints to their initial handlers:
        for pp in self.fn.patchpoints:
            pp.write_initial_handler(jit_result)

        fn_ptr = jit_result.get_code(loopname)

        looptoken._ll_function_addr = fn_ptr

        looptoken.compiled_loop_token._ll_initial_locs = initial_locs

        # FIXME: this leaks the gcc_jit_result

    def assemble_bridge(self, logger, faildescr, inputargs, operations,
                        original_loop_token, log):
        print('assemble_bridge(%r)' % locals())
        if not we_are_translated():
            # Arguments should be unique
            assert len(set(inputargs)) == len(inputargs)

        self.make_context()
        max_args, initial_locs = self.make_JITFRAME_struct(inputargs,
                                                           operations)
        self.lvalue_for_box = {}

        global num_bridges
        name = "bridge_%i" % num_bridges
        num_bridges += 1

        self.make_function(name, inputargs, operations)

        self.datablockwrapper.done()      # finish using cpu.asmmemmgr
        self.datablockwrapper = None

        self.ctxt.dump_to_file("/tmp/%s.c" % name, r_int(1))
        jit_result = self.ctxt.compile()
        self.ctxt.release()

        # Patch all patchpoints to their initial handlers:
        for pp in self.fn.patchpoints:
            pp.write_initial_handler(jit_result)

        # Patch the patchpoint for "faildescr" to point to our new code
        fn_ptr = jit_result.get_code(name)
        self.patchpoint_for_descr[faildescr].set_handler(fn_ptr)

    def make_JITFRAME_struct(self, inputargs, operations):
        #print(jitframe.JITFRAME)
        #print(dir(jitframe.JITFRAME))
        #print('jitframe.JITFRAME._flds: %r' % jitframe.JITFRAME._flds)

        # For now, build a "struct JITFRAME".
        # This will have the fields of jitframe,
        # plus additional numbered arg0..argN for use
        # for inputargs and the outputs
        #
        # They'll each be of type "union any", so that we can freely read/write
        # to them as any of the fundamental types.

        fields = []
        def make_field(name, jit_type):
            field = self.ctxt.new_field(jit_type,name)
            fields.append(field)
            return field
        make_field('jfi_frame_depth', self.t_Signed)
        make_field('jfi_frame_size', self.t_Signed)

        t_JITFRAMEINFO = (
            self.ctxt.new_struct_type ("JITFRAMEINFO",
                                       fields).as_type())

        t_JITFRAMEINFOPTR = t_JITFRAMEINFO.get_pointer()

        struct_jit_frame = self.ctxt.new_opaque_struct ("JITFRAME")

        self.t_jit_frame_ptr = struct_jit_frame.as_type().get_pointer()

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
        make_field('jf_extra_stack_depth', self.t_Signed)
        make_field('jf_savedata', self.t_void_ptr)
        make_field('jf_guard_exc', self.t_void_ptr)
        make_field('jf_forward', self.t_jit_frame_ptr)
        # FIXME: for some reason there's an implicit word here;
        # create it
        make_field('jf_frame', self.t_Signed)

        initial_locs = []
        #loc = jitframe.getofs('jf_frame')

        max_args = len(inputargs)
        for op in operations:
            if op.getopname() == 'finish':
                max_args = max(max_args, len(op._args))
            if op.getopname() == 'guard_true':
                max_args = max(max_args, len(op._fail_args))
            # FIXME: other ops

        self.field_for_arg_idx = {}
        for idx in range(max_args):
            self.field_for_arg_idx[idx] = make_field("arg%i" % idx,
                                                     self.t_any)
            initial_locs.append(idx * self.sizeof_signed) # hack!

        struct_jit_frame.set_fields (fields)

        return max_args, initial_locs

    def make_function(self, name, inputargs, operations):
        # Make function:
        #print('  inputargs: %r' % (inputargs, ))
        #jitframe.JITFRAMEINFOPTR
        self.loop_params = Params(self)

        self.fn = Function(
            name,
            self.ctxt.new_function(self.lib.GCC_JIT_FUNCTION_EXPORTED,
                                   self.t_jit_frame_ptr,
                                   name,
                                   self.loop_params.paramlist,
                                   r_int(0)))

        self.lvalue_ovf = self.fn.new_local(self.t_bool, "ovf")
        self.b_current = self.fn.new_block("initial")

        # Add an initial comment summarizing the loop or bridge:
        text = '\n\tinputargs: %s\n\n' % inputargs
        for op in operations:
            #print(op)
            #print(type(op))
            #print(dir(op))
            #print(repr(op.getopname()))
            text += '\t%s\n' % op
        self.b_current.add_comment(str(text))

        # Get initial values from input args:
        for idx, arg in enumerate(inputargs):
            self.b_current.add_comment("inputargs[%i]: %s" % (idx, arg))
            # (gdb) p *(double*)&jitframe->arg0
            # $7 = 10.5
            # (gdb) p *(double*)&jitframe->arg1
            # $8 = -2.25
            #src_ptr_rvalue = self.get_arg_as_lvalue(idx).get_address()
            #src_ptr_rvalue = self.ctxt.new_cast(src_ptr_rvalue,
            #                                    self.t_float.get_pointer())
            #src_rvalue = self.ctxt.new_dereference(src_ptr_rvalue)
            # or do it as a union
            field = self.get_union_field_for_expr(arg)
            src_rvalue = self.get_arg_as_lvalue(
                idx).access_field(field).as_rvalue()
            # FIXME: this may need a cast:
            #src_rvalue = self.ctxt.new_cast(src_rvalue, self.t_float)
            self.b_current.add_assignment(
                self.get_box_as_lvalue(arg),
                src_rvalue)

        for op in operations:
            #print(op)
            #print(type(op))
            #print(dir(op))
            #print(repr(op.getopname()))
            # Add a comment describing this ResOperation
            self.b_current.add_comment(str(op))

            # Compile the operation itself...
            methname = 'emit_%s' % op.getopname()
            if not hasattr(self, methname):
                raise NotImplementedError('resop not yet implemented: %s' % op)
            getattr(self, methname) (op)

    def expr_to_rvalue(self, expr):
        """
        print('expr_to_rvalue')
        print(' %s' % expr)
        print(' %r' % expr)
        print(' %s' % type(expr))
        print(' %s' % dir(expr))
        print(' %s' % expr.__dict__)
        """

        if isinstance(expr, (BoxInt, BoxFloat, BoxPtr)):
            return self.get_box_as_lvalue(expr).as_rvalue()
        elif isinstance(expr, ConstInt):
            #print('value: %r' % expr.value)
            #print('type(value): %r' % type(expr.value))
            if isinstance(expr.value, llmemory.AddressAsInt):
                assert isinstance(expr.value.adr, llmemory.fakeaddress)
                assert isinstance(expr.value.adr.ptr, lltype._ptr)
                return self.ctxt.new_rvalue_from_ptr(self.t_void_ptr,
                                                     expr.value.adr.ptr)
            return self.ctxt.new_rvalue_from_long(self.t_Signed,
                                                  r_long(expr.value))
        elif isinstance(expr, ConstFloat):
            #print('value: %r' % expr.value)
            #print('type(value): %r' % type(expr.value))
            return self.ctxt.new_rvalue_from_double(
                self.t_float,
                expr.value)#r_double(expr.value))
        elif isinstance(expr, ConstPtr):
            #print('value: %r' % expr.value)
            #print('type(value): %r' % type(expr.value))
            return self.ctxt.new_rvalue_from_ptr(self.t_void_ptr,
                                                 expr.value)
        raise NotImplementedError('unhandled expr: %s %s' % (expr, type(expr)))

    def get_box_as_lvalue(self, box):
        if box not in self.lvalue_for_box:
            self.lvalue_for_box[box] = (
                self.fn.new_local(self.get_type_for_box(box),
                                  str(box)))
        return self.lvalue_for_box[box]

    def get_arg_as_lvalue(self, idx):
        return self.loop_params.param_frame.as_rvalue ().dereference_field (
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
        if isinstance(expr, (BoxInt, BoxFloat, BoxPtr)):
            return self.get_box_as_lvalue(expr)

        raise NotImplementedError('unhandled expr: %s' % expr)

    def get_type_for_box(self, box):
        if isinstance(box, BoxInt):
            return self.t_Signed;
        elif isinstance(box, BoxFloat):
            return self.t_float;
        elif isinstance(box, BoxPtr):
            return self.t_void_ptr;
        else:
            raise NotImplementedError('unhandled box: %s %s' % (box, type(box)))

    def get_union_field_for_expr(self, expr):
        if isinstance(expr, (BoxInt, ConstInt)):
            return self.u_signed;
        elif isinstance(expr, (BoxFloat, ConstFloat)):
            return self.u_float;
        elif isinstance(expr, (BoxPtr, ConstPtr)):
            return self.u_ptr;
        else:
            raise NotImplementedError('unhandled expr: %s %s'
                                      % (expr, type(expr)))

    # Handling of specific ResOperation subclasses: each one is
    # a method named "emit_foo", where "foo" is the str() of the resop.
    #
    # Keep these in the same order as _oplist within
    # rpython/jit/metainterp/resoperation.py.

    # JUMP and FINISH:

    def emit_jump(self, jumpop):
        print(jumpop)
        print(jumpop.__dict__)
        label = self.label_for_descr[jumpop.getdescr()]
        print(jumpop.getdescr())
        print('label: %r' % label)

        assert len(jumpop._args) == len(label._args)

        # We need to write to the boxes listed in the label's args
        # with the values from those listed in the jump's args.
        # However, there are potential cases like JUMP(i0, i1) going
        # to LABEL(i1, i0) where all such assignments happen "simultaneously".
        # Hence we need to set up temporaries.
        # First pass: capture the value of relevant boxes at the JUMP:
        tmps = []
        for i in range(len(jumpop._args)):
            tmps.append(self.fn.new_local(self.t_Signed, "tmp%i" % i))
            self.b_current.add_assignment(
                tmps[i],
                self.get_box_as_lvalue(jumpop._args[i]).as_rvalue())
        # Second pass: write the values to the boxes at the LABEL:
        for i in range(len(jumpop._args)):
            self.b_current.add_assignment(
                self.get_box_as_lvalue(label._args[i]),
                tmps[i].as_rvalue())

        print('jumpop.getdescr(): %r' % jumpop.getdescr())
        dest_fn = self.function_for_label_descr[jumpop.getdescr()]
        print('dest_fn: %r' % dest_fn)
        if dest_fn == self.fn:
            b_dest = self.block_for_label_descr[jumpop.getdescr()]
            self.b_current.end_with_jump(b_dest)
        else:
            # Implement as a tail-call:
            # Sadly, we need to "import" the fn by name, since it was
            # created on a different gcc_jit_context.
            p = Params(self)
            other_fn = self.ctxt.new_function(
                self.lib.GCC_JIT_FUNCTION_IMPORTED,
                self.t_jit_frame_ptr,
                dest_fn.name,
                p.paramlist,
                r_int(0))
            args = [param.as_rvalue()
                    for param in self.loop_params.paramlist]
            call = self.ctxt.new_call(other_fn, args)
            self.b_current.end_with_return(call)

    def emit_finish(self, resop):
        self._impl_write_output_args(self.loop_params, resop._args)
        self._impl_write_jf_descr(self.loop_params, resop)
        self.b_current.end_with_return(
            self.loop_params.param_frame.as_rvalue ())

    def emit_label(self, resop):
        print(resop)
        print(resop.__dict__)
        #print('resop.getdescr(): %r' % resop.getdescr())
        #print('resop.getdescr().__dict__: %r' % resop.getdescr().__dict__)

        b_new = self.fn.new_block(str(resop))
        self.block_for_label_descr[resop.getdescr()] = b_new
        self.label_for_descr[resop.getdescr()] = resop
        self.function_for_label_descr[resop.getdescr()] = self.fn
        self.b_current.end_with_jump(b_new)
        self.b_current = b_new

    # GUARD_*

    def _impl_guard(self, resop, istrue, boolval):
        assert isinstance(boolval, RValue)
        b_true = self.fn.new_block("on_true_at_%s" % resop)
        b_false = self.fn.new_block("on_false_at_%s" % resop)
        self.b_current.end_with_conditional(boolval,
                                            b_true, b_false)

        if istrue:
            b_guard_failure = b_false
            b_guard_success = b_true
        else:
            b_guard_failure = b_true
            b_guard_success = b_false

        # Write out guard failure impl:
        self.b_current = b_guard_failure

        # Implement it as a tail-call through a function ptr to
        # a handler function, allowing patchability
        pp = Patchpoint(self)
        self.fn.patchpoints.append(pp)
        self.patchpoint_for_descr[resop.getdescr()] = pp
        args = [param.as_rvalue()
                for param in self.loop_params.paramlist]
        call = self.ctxt.new_call_through_ptr (pp.failure_fn_ptr.as_rvalue(),
                                               args)
        self._impl_write_output_args(self.loop_params, resop._fail_args)
        self.b_current.end_with_return(call)

        b_within_failure_fn = pp.failure_fn.new_block("initial")
        self.b_current = b_within_failure_fn
        self._impl_write_jf_descr(pp.failure_params, resop)
        self.b_current.end_with_return(
            pp.failure_params.param_frame.as_rvalue ())
        rd_locs = []
        for idx, arg in enumerate(resop._fail_args):
            rd_locs.append(idx * self.sizeof_signed)
        resop.getdescr().rd_locs = rd_locs

        # Further operations go into the guard success block in the original fn:
        self.b_current = b_guard_success

    def _impl_bool_guard(self, resop, istrue):
        boolval = self.ctxt.new_cast(self.expr_to_rvalue(resop._arg0),
                                     self.t_bool)
        self._impl_guard(resop, istrue, boolval)

    def emit_guard_true(self, resop):
        self._impl_bool_guard(resop, r_int(1))

    def emit_guard_false(self, resop):
        self._impl_bool_guard(resop, r_int(0))

    def emit_guard_value(self, resop):
        boolval = self.ctxt.new_comparison(
            self.lib.GCC_JIT_COMPARISON_EQ,
            self.expr_to_rvalue(resop._arg0),
            self.expr_to_rvalue(resop._arg1))
        self._impl_guard(resop, r_int(1), boolval)

    def emit_guard_class(self, resop):
        vtable_offset = self.cpu.vtable_offset
        assert vtable_offset is not None
        lvalue_obj_vtable = self.impl_get_lvalue_at_offset_from_ptr(
            resop._arg0, r_int(vtable_offset), self.t_void_ptr)
        boolval = self.ctxt.new_comparison(
            self.lib.GCC_JIT_COMPARISON_EQ,
            lvalue_obj_vtable.as_rvalue(),
            self.expr_to_rvalue(resop._arg1))
        self._impl_guard(resop, r_int(1), boolval)

    def emit_guard_nonnull(self, resop):
        ptr_rvalue = self.expr_to_rvalue(resop._arg0)
        boolval = self.ctxt.new_comparison(
            self.lib.GCC_JIT_COMPARISON_NE,
            ptr_rvalue,
            self.ctxt.null(ptr_rvalue.get_type()))
        self._impl_guard(resop, r_int(1), boolval)

    def emit_guard_isnull(self, resop):
        ptr_rvalue = self.expr_to_rvalue(resop._arg0)
        boolval = self.ctxt.new_comparison(
            self.lib.GCC_JIT_COMPARISON_EQ,
            ptr_rvalue,
            self.ctxt.null(ptr_rvalue.get_type()))
        self._impl_guard(resop, r_int(1), boolval)

    def emit_guard_nonnull_class(self, resop):
        # GUARD_NONNULL_CLASS means:
        #   "check that _arg0 (instance ptr) is non-NULL
        #    and then (if non-NULL)
        #       check the ptr's vtable for equality against _arg1
        #    if both true then guard is true,
        #    if either fails then guard has failed"

        # Hence we need two conditionals; we can do this
        # using a logical AND of the two conditionals;
        # libgccjit should shortcircuit things appropriately.

        ptr_rvalue = self.expr_to_rvalue(resop._arg0)
        boolval_is_nonnull = self.ctxt.new_comparison(
            self.lib.GCC_JIT_COMPARISON_NE,
            ptr_rvalue,
            self.ctxt.null(ptr_rvalue.get_type()))

        vtable_offset = self.cpu.vtable_offset
        assert vtable_offset is not None
        lvalue_obj_vtable = self.impl_get_lvalue_at_offset_from_ptr(
            resop._arg0, r_int(vtable_offset), self.t_void_ptr)
        boolval_vtable_equality = self.ctxt.new_comparison(
            self.lib.GCC_JIT_COMPARISON_EQ,
            lvalue_obj_vtable.as_rvalue(),
            self.expr_to_rvalue(resop._arg1))

        self._impl_guard(resop, r_int(1),
                         self.ctxt.new_binary_op(
                             self.lib.GCC_JIT_BINARY_OP_LOGICAL_AND,
                             self.t_bool,
                             boolval_is_nonnull, boolval_vtable_equality))

    def emit_guard_no_overflow(self, resop):
        self._impl_guard(resop, r_int(0),
                         self.lvalue_ovf.as_rvalue())

    def emit_guard_overflow(self, resop):
        self._impl_guard(resop, r_int(1),
                         self.lvalue_ovf.as_rvalue())

    def _impl_write_output_args(self, params, args):
        # Write outputs back:
        for idx, arg in enumerate(args):
            if arg is not None:
                src_rvalue = self.expr_to_rvalue(arg)
                field = self.get_union_field_for_expr(arg)
                dst_lvalue = self.get_arg_as_lvalue(idx).access_field(field)
                self.b_current.add_assignment(dst_lvalue, src_rvalue)
            else:
                # FIXME: see test_compile_with_holes_in_fail_args
                raise ValueError("how to handle holes in fail args?")
                """
                self.b_current.add_assignment(
                    self.get_arg_as_lvalue(idx),
                    self.ctxt.new_rvalue_from_int (self.t_Signed,
                                                   r_int(0)))
                """

    def _impl_write_jf_descr(self, params, resop):
        # Write back to the jf_descr:
        #  "jitframe->jf_descr = resop.getdescr();"
        descr = rffi.cast(lltype.Signed,
                          cast_instance_to_gcref(resop.getdescr()))

        self.b_current.add_assignment(
            params.param_frame.as_rvalue ().dereference_field (
                self.field_jf_descr),
            self.ctxt.new_rvalue_from_ptr (self.t_void_ptr,
                                           rffi.cast(VOIDP, descr)))

    # Binary operations on "int":
    def impl_int_binop(self, resop, gcc_jit_binary_op):
        rval0 = self.expr_to_rvalue(resop._arg0)
        rval1 = self.expr_to_rvalue(resop._arg1)
        lvalres = self.expr_to_lvalue(resop.result)
        binop_expr = self.ctxt.new_binary_op(gcc_jit_binary_op,
                                             self.t_Signed,
                                             rval0, rval1)
        self.b_current.add_assignment(lvalres, binop_expr)

    def _impl_uint_binop(self, resop, gcc_jit_binary_op):
        rval0 = self.expr_to_rvalue(resop._arg0)
        rval0 = self.ctxt.new_cast(rval0, self.t_UINT)
        rval1 = self.expr_to_rvalue(resop._arg1)
        rval1 = self.ctxt.new_cast(rval1, self.t_UINT)
        lvalres = self.expr_to_lvalue(resop.result)
        binop_expr = self.ctxt.new_binary_op(gcc_jit_binary_op,
                                             self.t_UINT,
                                             rval0, rval1)
        self.b_current.add_assignment(lvalres,
                                      self.ctxt.new_cast(binop_expr,
                                                         self.t_Signed))

    def emit_int_add(self, resop):
        self.impl_int_binop(resop, self.lib.GCC_JIT_BINARY_OP_PLUS)
    def emit_int_sub(self, resop):
        self.impl_int_binop(resop, self.lib.GCC_JIT_BINARY_OP_MINUS)
    def emit_int_mul(self, resop):
        self.impl_int_binop(resop, self.lib.GCC_JIT_BINARY_OP_MULT)
    def emit_int_floordiv(self, resop):
        self.impl_int_binop(resop, self.lib.GCC_JIT_BINARY_OP_DIVIDE)
    def emit_uint_floordiv(self, resop):
        self._impl_uint_binop(resop, self.lib.GCC_JIT_BINARY_OP_DIVIDE)
    def emit_int_mod(self, resop):
        self.impl_int_binop(resop, self.lib.GCC_JIT_BINARY_OP_MODULO)
    def emit_int_and(self, resop):
        self.impl_int_binop(resop, self.lib.GCC_JIT_BINARY_OP_BITWISE_AND)
    def emit_int_or(self, resop):
        self.impl_int_binop(resop, self.lib.GCC_JIT_BINARY_OP_BITWISE_OR)
    def emit_int_xor(self, resop):
        self.impl_int_binop(resop, self.lib.GCC_JIT_BINARY_OP_BITWISE_XOR)
    def emit_int_rshift(self, resop):
        self.impl_int_binop(resop, self.lib.GCC_JIT_BINARY_OP_RSHIFT)
    def emit_int_lshift(self, resop):
        self.impl_int_binop(resop, self.lib.GCC_JIT_BINARY_OP_LSHIFT)
    def emit_uint_rshift(self, resop):
        self._impl_uint_binop(resop, self.lib.GCC_JIT_BINARY_OP_RSHIFT)

    # "FLOAT" binary ops:
    def impl_float_binop(self, resop, gcc_jit_binary_op):
        rval0 = self.expr_to_rvalue(resop._arg0)
        rval1 = self.expr_to_rvalue(resop._arg1)
        lvalres = self.expr_to_lvalue(resop.result)
        binop_expr = self.ctxt.new_binary_op(gcc_jit_binary_op,
                                             self.t_float,
                                             rval0, rval1)
        self.b_current.add_assignment(lvalres, binop_expr)

    def emit_float_add(self, resop):
        self.impl_float_binop(resop, self.lib.GCC_JIT_BINARY_OP_PLUS)
    def emit_float_sub(self, resop):
        self.impl_float_binop(resop, self.lib.GCC_JIT_BINARY_OP_MINUS)
    def emit_float_mul(self, resop):
        self.impl_float_binop(resop, self.lib.GCC_JIT_BINARY_OP_MULT)
    def emit_float_truediv(self, resop):
        self.impl_float_binop(resop, self.lib.GCC_JIT_BINARY_OP_DIVIDE)

    # "FLOAT" unary ops:
    def _impl_float_unaryop(self, resop, gcc_jit_unary_op):
        rvalue = self.expr_to_rvalue(resop._arg0)
        lvalres = self.expr_to_lvalue(resop.result)
        unaryop_expr = self.ctxt.new_unary_op(gcc_jit_unary_op,
                                            self.t_float,
                                            rvalue)
        self.b_current.add_assignment(lvalres, unaryop_expr)

    def emit_float_neg(self, resop):
        self._impl_float_unaryop(resop, self.lib.GCC_JIT_UNARY_OP_MINUS)
    def emit_float_abs(self, resop):
        self._impl_float_unaryop(resop, self.lib.GCC_JIT_UNARY_OP_ABS)

    # "CAST_" operations:
    def emit_cast_float_to_int(self, resop):
        rvalue = self.expr_to_rvalue(resop._arg0)
        lvalres = self.expr_to_lvalue(resop.result)
        cast_expr = self.ctxt.new_cast(rvalue, self.t_Signed)
        self.b_current.add_assignment(lvalres, cast_expr)
    def emit_cast_int_to_float(self, resop):
        rvalue = self.expr_to_rvalue(resop._arg0)
        lvalres = self.expr_to_lvalue(resop.result)
        cast_expr = self.ctxt.new_cast(rvalue, self.t_float)
        self.b_current.add_assignment(lvalres, cast_expr)

    # Comparisons:
    #   "INT" comparisons:
    def impl_int_cmp(self, resop, gcc_jit_comparison):
        rval0 = self.expr_to_rvalue(resop._arg0)
        rval1 = self.expr_to_rvalue(resop._arg1)
        lvalres = self.expr_to_lvalue(resop.result)
        resop_cmp = (
            self.ctxt.new_cast(
                self.ctxt.new_comparison(gcc_jit_comparison,
                                         rval0, rval1),
                self.t_Signed)
            )
        self.b_current.add_assignment(lvalres,
                                      resop_cmp)
    def emit_int_lt(self, resop):
        self.impl_int_cmp(resop, self.lib.GCC_JIT_COMPARISON_LT)
    def emit_int_le(self, resop):
        self.impl_int_cmp(resop, self.lib.GCC_JIT_COMPARISON_LE)
    def emit_int_eq(self, resop):
        self.impl_int_cmp(resop, self.lib.GCC_JIT_COMPARISON_EQ)
    def emit_int_ne(self, resop):
        self.impl_int_cmp(resop, self.lib.GCC_JIT_COMPARISON_NE)
    def emit_int_gt(self, resop):
        self.impl_int_cmp(resop, self.lib.GCC_JIT_COMPARISON_GT)
    def emit_int_ge(self, resop):
        self.impl_int_cmp(resop, self.lib.GCC_JIT_COMPARISON_GE)

    #   "UINT" comparisons:
    def impl_uint_cmp(self, resop, gcc_jit_comparison):
        rval0 = self.expr_to_rvalue(resop._arg0)
        rval1 = self.expr_to_rvalue(resop._arg1)
        rval0 = self.ctxt.new_cast(rval0, self.t_UINT)
        rval1 = self.ctxt.new_cast(rval1, self.t_UINT)
        lvalres = self.expr_to_lvalue(resop.result)
        resop_cmp = (
            self.ctxt.new_cast(
                self.ctxt.new_comparison(gcc_jit_comparison,
                                         rval0, rval1),
                self.t_Signed)
            )
        self.b_current.add_assignment(lvalres,
                                      resop_cmp)
    def emit_uint_lt(self, resop):
        self.impl_uint_cmp(resop, self.lib.GCC_JIT_COMPARISON_LT)
    def emit_uint_le(self, resop):
        self.impl_uint_cmp(resop, self.lib.GCC_JIT_COMPARISON_LE)
    def emit_uint_gt(self, resop):
        self.impl_uint_cmp(resop, self.lib.GCC_JIT_COMPARISON_GT)
    def emit_uint_ge(self, resop):
        self.impl_uint_cmp(resop, self.lib.GCC_JIT_COMPARISON_GE)

    #   "FLOAT" comparisons:
    def impl_float_cmp(self, resop, gcc_jit_comparison):
        rval0 = self.expr_to_rvalue(resop._arg0)
        rval1 = self.expr_to_rvalue(resop._arg1)
        lvalres = self.expr_to_lvalue(resop.result)
        resop_cmp = (
            self.ctxt.new_cast(
                self.ctxt.new_comparison(gcc_jit_comparison,
                                         rval0, rval1),
                self.t_Signed)
            )
        self.b_current.add_assignment(lvalres,
                                      resop_cmp)

    def emit_float_lt(self, resop):
        self.impl_float_cmp(resop, self.lib.GCC_JIT_COMPARISON_LT)
    def emit_float_le(self, resop):
        self.impl_float_cmp(resop, self.lib.GCC_JIT_COMPARISON_LE)
    def emit_float_eq(self, resop):
        self.impl_float_cmp(resop, self.lib.GCC_JIT_COMPARISON_EQ)
    def emit_float_ne(self, resop):
        self.impl_float_cmp(resop, self.lib.GCC_JIT_COMPARISON_NE)
    def emit_float_gt(self, resop):
        self.impl_float_cmp(resop, self.lib.GCC_JIT_COMPARISON_GT)
    def emit_float_ge(self, resop):
        self.impl_float_cmp(resop, self.lib.GCC_JIT_COMPARISON_GE)

    # Unary "INT" operations:
    def _impl_int_unaryop(self, resop, gcc_jit_unary_op):
        rvalue = self.expr_to_rvalue(resop._arg0)
        lvalres = self.expr_to_lvalue(resop.result)
        unaryop_expr = self.ctxt.new_unary_op(gcc_jit_unary_op,
                                              self.t_Signed,
                                              rvalue)
        self.b_current.add_assignment(lvalres, unaryop_expr)

    def emit_int_is_zero(self, resop):
        self._impl_int_unaryop(resop, self.lib.GCC_JIT_UNARY_OP_LOGICAL_NEGATE)
    def emit_int_is_true(self, resop):
        rvalarg = self.expr_to_rvalue(resop._arg0)
        lvalres = self.expr_to_lvalue(resop.result)
        resop_cmp = (
            self.ctxt.new_cast(
                self.ctxt.new_comparison(self.lib.GCC_JIT_COMPARISON_NE,
                                         rvalarg,
                                         self.ctxt.zero(self.t_Signed)),
                self.t_Signed)
            )
        self.b_current.add_assignment(lvalres,
                                      resop_cmp)
    def emit_int_neg(self, resop):
        self._impl_int_unaryop(resop, self.lib.GCC_JIT_UNARY_OP_MINUS)
    def emit_int_invert(self, resop):
        self._impl_int_unaryop(resop, self.lib.GCC_JIT_UNARY_OP_BITWISE_NEGATE)

    #

    def impl_get_lvalue_at_offset_from_ptr(self, ptr_expr, ll_offset, t_field):
        ptr = self.expr_to_rvalue(ptr_expr)

        # Cast to (char *) so we can use offset:
        # ((char *)ARG0)
        ptr = self.ctxt.new_cast(ptr, self.t_char_ptr)

        # ((char *)ARG0)[offset]
        ptr = self.ctxt.new_array_access(
            ptr,
            self.ctxt.new_rvalue_from_int(self.t_Signed, ll_offset))

        # (char **)(((char *)ARG0)[offset])
        field_ptr_address = ptr.get_address ()

        # (T *)(char **)(((char *)ARG0)[offset])
        field_ptr = self.ctxt.new_cast(field_ptr_address,
                                       t_field.get_pointer())

        # and dereference:
        # *(T *)(char **)(((char *)ARG0)[offset])
        field_lvalue = field_ptr.dereference()

        return field_lvalue

    def impl_get_type_for_field(self, fielddescr):
        # ...and cast back to the correct type:
        if fielddescr.is_pointer_field():
            return self.t_void_ptr
        elif fielddescr.is_float_field():
            # FIXME: do we need to handle C float vs C double?
            return self.t_float
        else:
            return self.ctxt.get_int_type(r_int(fielddescr.field_size),
                                          r_int(fielddescr.is_field_signed()))

    def impl_get_lvalue_for_field(self, ptr_expr, fielddescr):
        assert isinstance(ptr_expr, (BoxPtr, ConstPtr))
        #print(fielddescr)
        #print(dir(fielddescr))
        #print('fielddescr.field_size: %r' % fielddescr.field_size)

        offset = fielddescr.offset
        t_field = self.impl_get_type_for_field(fielddescr)

        return self.impl_get_lvalue_at_offset_from_ptr(
            ptr_expr, r_int(offset), t_field)

    def emit_getfield_gc(self, resop):
        #print(repr(resop))
        assert isinstance(resop._arg0, (BoxPtr, ConstPtr))
        lvalres = self.expr_to_lvalue(resop.result)
        field_lvalue = self.impl_get_lvalue_for_field(
            resop._arg0,
            resop.getdescr())
        self.b_current.add_assignment(
            lvalres,
            self.ctxt.new_cast(field_lvalue.as_rvalue(),
                               self.get_type_for_box(resop.result)))

    def emit_setfield_gc(self, resop):
        #print(repr(resop))
        assert isinstance(resop._arg0, (BoxPtr, ConstPtr))
        #print(resop._arg1)

        field_lvalue = self.impl_get_lvalue_for_field(
            resop._arg0,
            resop.getdescr())
        t_field = self.impl_get_type_for_field(fielddescr)

        self.b_current.add_assignment(
            field_lvalue,
            # ... = ARG1,
            self.ctxt.new_cast(self.expr_to_rvalue(resop._arg1),
                               t_field))

    # "INT_*_OVF" operations:
    def _impl_int_ovf(self, resop, builtin_name):
        """
        We implement ovf int binops using GCC builtins,
        generating a call of the form:
          ovf = __builtin_FOO_overflow(arg0, arg1, &result);
        This is then optimized by gcc's builtins.c
        fold_builtin_arith_overflow.
        """
        rval0 = self.expr_to_rvalue(resop._arg0)
        rval1 = self.expr_to_rvalue(resop._arg1)
        lvalres = self.expr_to_lvalue(resop.result)
        builtin_fn = self.ctxt.get_builtin_function(builtin_name)
        # "ovf = __builtin_FOO_overflow(arg0, arg1, &result);"
        call = self.ctxt.new_call(builtin_fn,
                                  [rval0,
                                   rval1,
                                   lvalres.get_address()])
        self.b_current.add_assignment(self.lvalue_ovf, call)
    def emit_int_add_ovf(self, resop):
        self._impl_int_ovf(resop, '__builtin_add_overflow')
    def emit_int_sub_ovf(self, resop):
        self._impl_int_ovf(resop, '__builtin_sub_overflow')
    def emit_int_mul_ovf(self, resop):
        self._impl_int_ovf(resop, '__builtin_mul_overflow')
