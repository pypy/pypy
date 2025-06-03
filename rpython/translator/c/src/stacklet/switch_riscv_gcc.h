#if __riscv_xlen != 64 || __riscv_flen != 64
#error "slp_switch only supports RV64IMAD now"
#endif

static void *slp_switch(void *(*save_state)(void*, void*),
                        void *(*restore_state)(void*, void*),
                        void *extra) __attribute__((noinline));

static void *slp_switch(void *(*save_state)(void*, void*),
                        void *(*restore_state)(void*, void*),
                        void *extra)
{
  void *result;
  /*
   * Registers to preserve (callee-saved registers):
   * x8-9, x18-27, f8-9, f18-27
   *
   * Registers marked as clobbered (caller-saved registers):
   * x1 (ra), x5-7, x10-17, x28-31, f0-7, f10-17, f28-f31
   *
   * Special registers:
   *
   * x0: Constant zero
   *
   * x2: Stack pointer is a callee-saved register.  It will be preserved
   *     around function calls to `save_state` and `restore_state`.  And this
   *     inline assembly preserve it by sub/add it with the same amount.
   *
   * x3: gp (don't use, gcc doesn't change them either)
   * x4: tp (don't use, gcc doesn't change them either)
   *
   * Don't assume gcc saves any register for us when generating code for
   * slp_switch().
   *
   * The values `save_state`, `restore_state` and `extra` are first moved by
   * gcc to some registers that are not marked as clobbered (some callee-saved
   * registers).  Similarly, gcc expects `result` to be in a register between
   * some callee-saved registers.
   *
   * This means that three of the values we happen to save and restore will, in
   * fact, contain the three arguments, and one of these values will, in fact,
   * not be restored at all but receive `result`.
   */

  __asm__ volatile (
    /* Note: The stack is supposed to be aligned as necessary already. */

    /* Save callee-saved registers. */
    "addi sp,  sp, -192\n"
    "sd   x8,  0(sp)\n"
    "sd   x9,  8(sp)\n"
    "sd   x18, 16(sp)\n"
    "sd   x19, 24(sp)\n"
    "sd   x20, 32(sp)\n"
    "sd   x21, 40(sp)\n"
    "sd   x22, 48(sp)\n"
    "sd   x23, 56(sp)\n"
    "sd   x24, 64(sp)\n"
    "sd   x25, 72(sp)\n"
    "sd   x26, 80(sp)\n"
    "sd   x27, 88(sp)\n"
    "fsd  f8,  96(sp)\n"
    "fsd  f9,  104(sp)\n"
    "fsd  f18, 112(sp)\n"
    "fsd  f19, 120(sp)\n"
    "fsd  f20, 128(sp)\n"
    "fsd  f21, 136(sp)\n"
    "fsd  f22, 144(sp)\n"
    "fsd  f23, 152(sp)\n"
    "fsd  f24, 160(sp)\n"
    "fsd  f25, 168(sp)\n"
    "fsd  f26, 176(sp)\n"
    "fsd  f27, 184(sp)\n"

    "mv   x10, sp\n"                /* arg 1: current (old) stack pointer */
    "mv   x11, %[extra]\n"          /* arg 2: extra */
    "jalr ra,  %[save_state], 0\n"  /* call save_state() */

    /* Skip the rest if the return value is null. */
    "beqz x10, 0f\n"

    "mv   sp,  x10\n"  /* change the stack pointer */

    /* From now on, the stack pointer is modified, but the content of the
     * stack is not restored yet.  It contains only garbage here.
     */
    /* arg 1: current (new) stack pointer is already in x10 */
    "mv   x11, %[extra]\n"             /* arg 2: extra */
    "jalr ra,  %[restore_state], 0\n"  /* call restore_state() */

    /* The stack's content is now restored. */
    "0:\n"

    /* Restore all saved registers */
    "ld   x8,  0(sp)\n"
    "ld   x9,  8(sp)\n"
    "ld   x18, 16(sp)\n"
    "ld   x19, 24(sp)\n"
    "ld   x20, 32(sp)\n"
    "ld   x21, 40(sp)\n"
    "ld   x22, 48(sp)\n"
    "ld   x23, 56(sp)\n"
    "ld   x24, 64(sp)\n"
    "ld   x25, 72(sp)\n"
    "ld   x26, 80(sp)\n"
    "ld   x27, 88(sp)\n"
    "fld  f8,  96(sp)\n"
    "fld  f9,  104(sp)\n"
    "fld  f18, 112(sp)\n"
    "fld  f19, 120(sp)\n"
    "fld  f20, 128(sp)\n"
    "fld  f21, 136(sp)\n"
    "fld  f22, 144(sp)\n"
    "fld  f23, 152(sp)\n"
    "fld  f24, 160(sp)\n"
    "fld  f25, 168(sp)\n"
    "fld  f26, 176(sp)\n"
    "fld  f27, 184(sp)\n"
    "addi sp,  sp, 192\n"

    /* Move x10 into the final location of `result`. */
    "mv   %[result], x10\n"

    : /* Output variables */
      [result]"=r"(result)
    : /* Input variables */
      [restore_state]"r"(restore_state),
      [save_state]"r"(save_state),
      [extra]"r"(extra)
    : /* Clobber caller-saved core registers */
      "x1", "x5", "x6", "x7",
      "x10", "x11", "x12", "x13", "x14", "x15", "x16", "x17",
      "x28", "x29", "x30", "x31",
      /* Clobber caller-saved float registers */
      "f0", "f1", "f2", "f3", "f4", "f5", "f6", "f7",
      "f10", "f11", "f12", "f13", "f14", "f15", "f16", "f17",
      "f28", "f29", "f30", "f31",
      "memory"
  );

  return result;
}
