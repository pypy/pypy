/************************************************************/
 /***  C header subsection: os module                      ***/

#include <unistd.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#ifndef PATH_MAX
  /* assume windows */
#  define PATH_MAX 254
#endif

/* The functions below are mapped to functions from pypy.rpython.module.*
   by the pypy.translator.c.extfunc.EXTERNALS dictionary.
   They should correspond to the functions with the suggested_primitive
   flag set, and NOT necessarily directly to the ll_os_*() functions.
   See for example ll_read_into(), which is called by ll_os_read().
   The latter would be messy to write here, but LL_read_into() is quite easy.
*/


int LL_os_open(RPyString *filename, int flag, int mode)
{
	/* XXX unicode_file_names */
	char buf[PATH_MAX];
	int fd, error, namelen = RPyString_Size(filename);
	if (namelen >= PATH_MAX) {
		RAISE_OSERROR(ENAMETOOLONG);
		return -1;
	}
	else {
		memcpy(buf, RPyString_AsString(filename), namelen);
		buf[namelen] = 0;
		fd = open(buf, flag, mode);
		if (fd < 0)
			RAISE_OSERROR(errno);
		return fd;
	}
}

long LL_read_into(int fd, RPyString *buffer)
{
	long n = read(fd, RPyString_AsString(buffer), RPyString_Size(buffer));
	if (n < 0)
		RAISE_OSERROR(errno);
	return n;
}

long LL_os_write(int fd, RPyString *buffer)
{
	long n = write(fd, RPyString_AsString(buffer), RPyString_Size(buffer));
	if (n < 0)
		RAISE_OSERROR(errno);
	return n;
}

void LL_os_close(int fd)
{
	if (close(fd) < 0)
		RAISE_OSERROR(errno);
}

int LL_os_dup(int fd)
{
	fd = dup(fd);
	if (fd < 0)
		RAISE_OSERROR(errno);
	return fd;
}

RPyString *LL_os_getcwd(void)
{
	char buf[PATH_MAX];
	char *res;
	res = getcwd(buf, sizeof buf);
	if (res == NULL) {
		RAISE_OSERROR(errno);
		return NULL;
	}
	return RPyString_FromString(buf);
}
