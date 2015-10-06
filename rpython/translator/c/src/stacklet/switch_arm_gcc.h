#if defined(__ARM_ARCH_4__) || defined (__ARM_ARCH_4T__)
# define call_reg(x) "mov lr, pc ; bx " #x "\n"
#else
/* ARM >= 5 */
# define call_reg(x) "blx " #x "\n"
#endif

static void *slp_switch(void *(*save_state)(void*, void*),
                        void *(*restore_state)(void*, void*),
                        void *extra)
{
  void *result;
  __asm__ volatile (
    "ldr r3, %[save_state]\n"
    /* save values in callee saved registers for later */
    "ldr r4, %[restore_state]\n"
    "ldr r5, %[extra]\n"
    "mov r0, sp\n"        	/* arg 1: current (old) stack pointer */
    "mov r1, r5\n"        	/* arg 2: extra                       */
    call_reg(r3)		/* call save_state()                  */

    /* skip the rest if the return value is null */
    "cmp r0, #0\n"
    "beq zero\n"

    "mov sp, r0\n"			/* change the stack pointer */

	/* From now on, the stack pointer is modified, but the content of the
	stack is not restored yet.  It contains only garbage here. */
    "mov r1, r5\n"       	/* arg 2: extra                       */
   	 						/* arg 1: current (new) stack pointer is already in r0*/
    call_reg(r4)		/* call restore_state()               */

    /* The stack's content is now restored. */
    "zero:\n"
    "str r0, %[result]\n"

    : [result]"=m"(result)	/* output variables */
	/* input variables  */
    : [restore_state]"m"(restore_state),
      [save_state]"m"(save_state),
      [extra]"m"(extra)
    : "lr", "r0", "r1", "r2", "r3", "r4", "r5", "r6", "r7", "r8", "r9",
      "r10", "r11", "r12",    /* r13 is sp, r14 is lr, and r15 is pc */
      "memory", "cc", "f0", "f1", "f2", "f3", "f4", "f5", "f6", "f7"
  );
  return result;
}
