
static void __attribute__((optimize("O3"))) *slp_switch(void *(*save_state)(void*, void*),
                        void *(*restore_state)(void*, void*),
                        void *extra)
{
  void *result;
  __asm__ volatile (
    "mov r3, %[save_state]\n"
    /* save values in calee saved registers for later */
    "mov r4, %[restore_state]\n"
    "mov r5, %[extra]\n"
    "mov r0, sp\n"        	/* arg 1: current (old) stack pointer */
    "mov r1, r5\n"        	/* arg 2: extra                       */
    "blx r3\n"				/* call save_state()                  */

    /* skip the rest if the return value is null */
    "cmp r0, #0\n"
    "beq zero\n"

    "mov sp, r0\n"			/* change the stack pointer */

	/* From now on, the stack pointer is modified, but the content of the
	stack is not restored yet.  It contains only garbage here. */
    "mov r1, r5\n"       	/* arg 2: extra                       */
   	 						/* arg 1: current (new) stack pointer is already in r0*/
    "blx r4\n"           	/* call restore_state()               */

    /* The stack's content is now restored. */
    "zero:\n"
    "mov %[result], r0\n"

    : [result]"=r"(result)	/* output variables */
	/* input variables  */
    : [restore_state]"r"(restore_state),
      [save_state]"r"(save_state),
      [extra]"r"(extra)
    : "lr", "r4", "r5", "r6", "r7", "r8", "r9", "r10", "r11", "r13"
  );
  return result;
}
