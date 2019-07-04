
static void *slp_switch(void *(*save_state)(void*, void*),
                        void *(*restore_state)(void*, void*),
                        void *extra) __attribute__((noinline));

static void *slp_switch(void *(*save_state)(void*, void*),
                        void *(*restore_state)(void*, void*),
                        void *extra)
{
  void *result;
  /*
      registers to preserve: x18-x28, x29(fp), x30(lr), and v8-v15
      registers marked as clobbered: x0-x18

      Note that x18 appears in both lists; see below.

      Don't assume gcc saves any register for us when generating
      code for slp_switch().

      The values 'save_state', 'restore_state' and 'extra' are first moved
      by gcc to some registers that are not marked as clobbered, so >= x19.
      Similarly, gcc expects 'result' to be in a register >= x19.
      We don't want x18 to be used here, because of some special meaning
      it might have.

      This means that three of the values we happen to save and restore
      will, in fact, contain the three arguments, and one of these values
      will, in fact, not be restored at all but receive 'result'.

      The following two points may no longer be true, because "x30" is
      now present in the clobbered list, but the extra workarounds we
      do might be safer just in case:

          (1) Careful writing "blr %[...]": if gcc resolves it to x30---and it
          can!---then you're in trouble, because "blr x30" does not jump
          anywhere at all (it probably loads the current position into x30
          before it jumps to x30...)

          (2) Also, because "%[...]" can resolve to x30, we can't use that after
          the first call.  Instead, we need to copy the values somewhere
          safe, like x24 and x25.  We do that in such an order that it should
          work even if any of the "%[...]" expressions becomes x24 or x25 too.
  */

  __asm__ volatile (

    /* The stack is supposed to be aligned as necessary already.
       Save 13 registers from x18 to x30, plus 8 from v8 to v15 */

    "stp x29, x30, [sp, -176]!\n"
    "stp x18, x19, [sp, 16]\n"
    "stp x20, x21, [sp, 32]\n"
    "stp x22, x23, [sp, 48]\n"
    "stp x24, x25, [sp, 64]\n"
    "stp x26, x27, [sp, 80]\n"
    "str x28,      [sp, 96]\n"
    "str d8,  [sp, 104]\n"
    "str d9,  [sp, 112]\n"
    "str d10, [sp, 120]\n"
    "str d11, [sp, 128]\n"
    "str d12, [sp, 136]\n"
    "str d13, [sp, 144]\n"
    "str d14, [sp, 152]\n"
    "str d15, [sp, 160]\n"

    "mov x0, sp\n"        	/* arg 1: current (old) stack pointer */
    "mov x1, %[extra]\n"   	/* arg 2: extra, from >= x18          */
    "mov x3, %[save_state]\n"
    "mov x24, %[restore_state]\n"   /* save restore_state => x24 */
    "mov x25, x1\n"                 /* save extra => x25 */
    "blr x3\n"			/* call save_state()                  */

    /* skip the rest if the return value is null */
    "cbz x0, zero\n"

    "mov sp, x0\n"			/* change the stack pointer */

	/* From now on, the stack pointer is modified, but the content of the
	stack is not restored yet.  It contains only garbage here. */
    "mov x1, x25\n"		/* arg 2: extra                       */
                /* arg 1: current (new) stack pointer is already in x0*/
    "blr x24\n"			/* call restore_state()               */

    /* The stack's content is now restored. */
    "zero:\n"

    /* Restore all saved registers */
    "ldp x18, x19, [sp, 16]\n"
    "ldp x20, x21, [sp, 32]\n"
    "ldp x22, x23, [sp, 48]\n"
    "ldp x24, x25, [sp, 64]\n"
    "ldp x26, x27, [sp, 80]\n"
    "ldr x28,      [sp, 96]\n"
    "ldr d8,  [sp, 104]\n"
    "ldr d9,  [sp, 112]\n"
    "ldr d10, [sp, 120]\n"
    "ldr d11, [sp, 128]\n"
    "ldr d12, [sp, 136]\n"
    "ldr d13, [sp, 144]\n"
    "ldr d14, [sp, 152]\n"
    "ldr d15, [sp, 160]\n"
    "ldp x29, x30, [sp], 176\n"

    /* Move x0 into the final location of 'result' */
    "mov %[result], x0\n"

    : [result]"=r"(result)	/* output variables */
	/* input variables  */
    : [restore_state]"r"(restore_state),
      [save_state]"r"(save_state),
      [extra]"r"(extra)
    : "x0", "x1", "x2", "x3", "x4", "x5", "x6", "x7", "x8", "x9",
      "x10", "x11", "x12", "x13", "x14", "x15", "x16", "x17", "x18",
      "memory", "cc", "x30"  // x30==lr
  );
  return result;
}
