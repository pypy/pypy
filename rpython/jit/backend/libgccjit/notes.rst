This is an experiment, and merely a work-in-progress.

In particular, this needs some late-breaking changes to gcc 5's
libgccjit; gcc r219480 onwards (2015-01-12) should have everything:

   * new API entrypoints:

     * :c:func:`gcc_jit_result_get_global` (added in gcc r219480)

     * :c:func:`gcc_jit_context_new_rvalue_from_long` (added in gcc r219401)

     * :c:func:`gcc_jit_context_get_last_error` (added in gcc r219363)

   * a new value :c:macro:`GCC_JIT_UNARY_OP_ABS` within
     :c:type:`enum gcc_jit_unary_op` (added in r219321)

   * an extra param to :c:func:`gcc_jit_context_new_global`
     (enum gcc_jit_global_kind; added in gcc r219480).
