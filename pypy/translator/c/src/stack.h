
/************************************************************/
 /***  C header subsection: stack operations               ***/

static stack_base_pointer = NULL;

char LL_stack_too_big(void)
{
  char local;
  long result;
  int simple_check = MAX_STACK_SIZE / 2;

  if( stack_base_pointer == NULL )
	  stack_base_pointer = &local;

  /* compute the difference between local variable and
   * and a stack origin pointer
   */
  result = &local - slp_base_stack_pointer;
  if (-simple_check < result && result < simple_check){
    return 0;
  }
  return 1;
}




