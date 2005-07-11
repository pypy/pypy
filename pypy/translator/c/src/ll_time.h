/************************************************************/
 /***  C header subsection: time module                    ***/

#include <time.h>


double LL_time_clock(void)
{
	/* XXX gives imprecise results on some systems */
	return ((double) clock()) / CLOCKS_PER_SEC;
}
