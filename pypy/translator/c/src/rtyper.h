/************************************************************/
 /***  C header subsection: tools for RTyper-aware code    ***/

#include <string.h>


#define RPyString_Size(rps)		((rps)->rs_chars.length)
#define RPyString_AsString(rps)		((rps)->rs_chars.items)


/* prototypes */

RPyString *RPyString_FromString(char *buf);


/* implementations */

#ifndef PYPY_NOT_MAIN_FILE

RPyString *RPyString_FromString(char *buf)
{
	int length = strlen(buf);
	RPyString *rps = RPyString_New(length);
	memcpy(RPyString_AsString(rps), buf, length);
	return rps;
}

#endif /* PYPY_NOT_MAIN_FILE */
