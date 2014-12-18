This is an experiment, and merely a work-in-progress.

In particular, this needs some changes to libgccjit that are currently
only in my local repo:

   * new API entrypoints:

     * :c:func:`gcc_jit_result_get_global`

     * :c:func:`gcc_jit_context_new_rvalue_from_long`

   * a new value :c:macro:`GCC_JIT_UNARY_OP_ABS` within
     :c:type:`enum gcc_jit_unary_op`.

   * an extra param to :c:func:`gcc_jit_context_new_global`
     (enum gcc_jit_global_kind).
