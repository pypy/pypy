from rpython.jit.backend.llsupport.assembler import BaseAssembler
from rpython.jit.backend.model import CompiledLoopToken
from rpython.jit.backend.libgccjit.rffi_bindings import make_eci, Library, make_param_array
from rpython.jit.metainterp.history import BoxInt, ConstInt
from rpython.rtyper.lltypesystem.rffi import *

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
        print(self.ctxt)
        self.t_int = self.lib.gcc_jit_context_get_type(self.ctxt,
                                                       self.lib.GCC_JIT_TYPE_INT)

    def make_context(self):
        eci = make_eci()
        self.lib = Library(eci)
        self.ctxt = self.lib.gcc_jit_context_acquire()
        self.lib.gcc_jit_context_set_bool_option(self.ctxt,
                                            self.lib.GCC_JIT_BOOL_OPTION_DUMP_INITIAL_GIMPLE,
                                            r_int(1))
        self.lib.gcc_jit_context_set_int_option(self.ctxt,
                                           self.lib.GCC_JIT_INT_OPTION_OPTIMIZATION_LEVEL,
                                           r_int(3))
        self.lib.gcc_jit_context_set_bool_option(self.ctxt,
                                            self.lib.GCC_JIT_BOOL_OPTION_KEEP_INTERMEDIATES,
                                            r_int(1))
        self.lib.gcc_jit_context_set_bool_option(self.ctxt,
                                            self.lib.GCC_JIT_BOOL_OPTION_DUMP_EVERYTHING,
                                            r_int(1))
        self.lib.gcc_jit_context_set_bool_option(self.ctxt,
                                            self.lib.GCC_JIT_BOOL_OPTION_DUMP_GENERATED_CODE,
                                            r_int(1))

    def assemble_loop(self, inputargs, operations, looptoken, log,
                      loopname, logger):
        print('assemble_loop')
        clt = CompiledLoopToken(self.cpu, looptoken.number)
        print(clt)

        # Make function:
        self.lvalue_for_box = {}
        print('  inputargs: %r' % (inputargs, ))
        params = []
        for arg in inputargs:
            param_name = str2charp(str(arg))
            param = self.lib.gcc_jit_context_new_param(self.ctxt,
                                                       self.lib.null_location_ptr,
                                                       self.t_int, # FIXME: use correct type
                                                       param_name)
            self.lvalue_for_box[arg] = self.lib.gcc_jit_param_as_lvalue(param)
            free_charp(param_name)
            params.append(param)
        
        print("loopname: %r" % loopname)
        if not loopname:
            loopname = 'anonloop_%i' % self.num_anon_loops
            self.num_anon_loops += 1
        fn_name = str2charp(loopname)
        param_array = make_param_array(self.lib, params)
        self.fn = self.lib.gcc_jit_context_new_function(self.ctxt,
                                                        self.lib.null_location_ptr,
                                                        self.lib.GCC_JIT_FUNCTION_EXPORTED,
                                                        self.t_int,
                                                        fn_name,
                                                        r_int(len(params)),
                                                        param_array,
                                                        r_int(0))
        lltype.free(param_array, flavor='raw')
        free_charp(fn_name)

        self.b_current = self.lib.gcc_jit_function_new_block(self.fn, NULL)

        for op in operations:       
            print(op)
            print(type(op))
            print(dir(op))
            print(repr(op.getopname()))
            # Add a comment describing this ResOperation
            comment_text = str2charp(str(op))
            self.lib.gcc_jit_block_add_comment(self.b_current,
                                               self.lib.null_location_ptr,
                                               comment_text)
            free_charp(comment_text)

            # Compile the operation itself...
            methname = '_on_%s' % op.getopname()
            getattr(self, methname) (op)

        jit_result = self.lib.gcc_jit_context_compile(self.ctxt)
        self.lib.gcc_jit_context_release(self.ctxt)
        if not jit_result:
            # FIXME: get error from context
            raise Exception("jit_result is NULL")
        raise foo

    def expr_to_rvalue(self, expr):
        print('expr_to_rvalue')
        print(' %s' % expr)
        print(' %r' % expr)
        print(' %s' % type(expr))
        print(' %s' % dir(expr))
        print(' %s' % expr.__dict__)

        if isinstance(expr, BoxInt):
            return self.lib.gcc_jit_lvalue_as_rvalue(self.get_box_as_lvalue(expr))
        elif isinstance(expr, ConstInt):
            #print('value: %r' % expr.value)
            #print('type(value): %r' % type(expr.value))
            return self.lib.gcc_jit_context_new_rvalue_from_int(self.ctxt,
                                                                self.t_int,
                                                                r_int(expr.value))

    def get_box_as_lvalue(self, box):
        if box not in self.lvalue_for_box:
            local_name = str2charp(str(box))
            self.lvalue_for_box[box] = (
                self.lib.gcc_jit_function_new_local(self.fn,
                                                    self.lib.null_location_ptr,
                                                    self.t_int, # FIXME: use correct type
                                                    local_name))
            free_charp(local_name)
        return self.lvalue_for_box[box]

    def expr_to_lvalue(self, expr):
        print('expr_to_lvalue')
        print(' %s' % expr)
        print(' %r' % expr)
        print(' %s' % type(expr))
        print(' %s' % dir(expr))
        print(' %s' % expr.__dict__)
        if isinstance(expr, BoxInt):
            return self.get_box_as_lvalue(expr)
        raise foo

    # Handling of specific ResOperation subclasses

    def _on_int_add(self, op):
        print(op._arg0)
        print(op._arg1)
        print(op.result)
        print(op.__dict__)

        rval0 = self.expr_to_rvalue(op._arg0)
        rval1 = self.expr_to_rvalue(op._arg1)
        lvalres = self.expr_to_lvalue(op.result)

        op_add = (
            self.lib.gcc_jit_context_new_binary_op(self.ctxt,
                                                   self.lib.null_location_ptr,
                                                   self.lib.GCC_JIT_BINARY_OP_PLUS,
                                                   self.t_int,
                                                   rval0, rval1))
        #self.lib.gcc_jit_object_get_debug_string(gcc_jit_rvalue_as_object(op_add))
        self.lib.gcc_jit_block_add_assignment(self.b_current,
                                              self.lib.null_location_ptr,
                                              lvalres,
                                              op_add)

    def _on_finish(self, op):
        print(op.__dict__)
        # FIXME: assume just 1-ary FINISH for now
        assert len(op._args) == 1
        result = op._args[0]
        self.lib.gcc_jit_block_end_with_return(self.b_current,
                                               self.lib.null_location_ptr,
                                               self.expr_to_rvalue(result))
