/************************************************************/
 /***  C header subsection: external functions             ***/

#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <time.h>

/* The functions below are mapped to functions from pypy.rpython.extfunctable
   by the pypy.translator.c.fixedname.EXTERNALS dictionary. */

#define RPyString_Size(rps)		((rps)->rs_chars.length)
#define RPyString_AsString(rps)		((rps)->rs_chars.items)


int LL_os_open(RPyString *filename, int flag, int mode)
{
	char buf[PATH_MAX];
	int fd, error, namelen = RPyString_Size(filename);
	if (namelen >= PATH_MAX) {
		error = ENAMETOOLONG;
	}
	else {
		memcpy(buf, RPyString_AsString(filename), namelen);
		buf[namelen] = 0;
		fd = open(buf, flag, mode);
		if (fd != -1)
			return fd;
		error = errno;
	}
	/* XXX */
	Py_FatalError("oups, that gives an OSError");
}


double LL_time_clock(void)
{
	return ((double) clock()) / CLOCKS_PER_SEC;
}
