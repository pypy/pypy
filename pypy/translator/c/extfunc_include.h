/************************************************************/
 /***  C header subsection: external functions             ***/

#include <time.h>

/* The functions below are mapped to functions from pypy.rpython.extfunctable
   by the pypy.translator.c.fixedname.EXTERNALS dictionary. */


double LL_time_clock(void)
{
	return ((double) clock()) / CLOCKS_PER_SEC;
}
