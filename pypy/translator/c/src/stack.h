
/************************************************************/
 /***  C header subsection: stack operations               ***/

#ifndef MAX_STACK_SIZE
#    define MAX_STACK_SIZE (1 << 19)
#endif

char LL_stack_too_big(void);

#ifndef PYPY_NOT_MAIN_FILE

void LL_stack_unwind(void)
{
#ifdef USE_STACKLESS
    LL_stackless_stack_unwind();
#else
	RPyRaiseSimpleException(PyExc_RuntimeError, "Recursion limit exceeded");
#endif
}

char LL_stack_too_big(void)
{
  char local;
  long result;
  static char *stack_base_pointer = NULL;

  if( stack_base_pointer == NULL )
	  stack_base_pointer = &local;

  /* compute the difference between local variable and
   * and a stack origin pointer
   */
  result = &local - stack_base_pointer;
  if (-MAX_STACK_SIZE < result && result < MAX_STACK_SIZE){
    return 0;
  }
  return 1;
}
#endif
