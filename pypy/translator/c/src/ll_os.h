/************************************************************/
 /***  C header subsection: os module                      ***/

#if !(defined(MS_WIN64) || defined(MS_WINDOWS))
#  include <unistd.h>
#  include <sys/types.h>
#  include <sys/stat.h>
#endif

#include <errno.h>
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


/* just do what CPython is doing... */

#if defined(MS_WIN64) || defined(MS_WINDOWS)
#       define STAT _stati64
#       define FSTAT _fstati64
#       define STRUCT_STAT struct _stati64
#else
#       define STAT stat
#       define FSTAT fstat
#       define STRUCT_STAT struct stat
#endif


int LL_os_open(RPyString *filename, int flag, int mode)
{
	/* XXX unicode_file_names */
	char buf[PATH_MAX];
	int fd, namelen = RPyString_Size(filename);
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

RPySTAT_RESULT* _stat_construct_result_helper(STRUCT_STAT st) {
  long res0, res1, res2, res3, res4, res5, res6, res7, res8, res9;
  res0 = (long)st.st_mode;
  res1 = (long)st.st_ino; /*XXX HAVE_LARGEFILE_SUPPORT!*/
  res2 = (long)st.st_dev; /*XXX HAVE_LONG_LONG!*/
  res3 = (long)st.st_nlink;
  res4 = (long)st.st_uid;
  res5 = (long)st.st_gid;
  res6 = (long)st.st_size; /*XXX HAVE_LARGEFILE_SUPPORT!*/
  res7 = (long)st.st_atime; /*XXX ignoring quite a lot of things for time here */
  res8 = (long)st.st_mtime; /*XXX ignoring quite a lot of things for time here */
  res9 = (long)st.st_ctime; /*XXX ignoring quite a lot of things for time here */
  /*XXX ignoring BLOCK info here*/

  return ll_stat_result(res0, res1, res2, res3, res4,
			res5, res6, res7, res8, res9);
}


RPySTAT_RESULT* LL_os_stat(RPyString * fname) {
  STRUCT_STAT st;
  int error = STAT(RPyString_AsString(fname), &st);
  if (error != 0) {
    RAISE_OSERROR(errno);
    return NULL;
  }
  return _stat_construct_result_helper(st);
}

RPySTAT_RESULT* LL_os_fstat(long fd) {
  STRUCT_STAT st;
  int error = FSTAT(fd, &st);
  if (error != 0) {
    RAISE_OSERROR(errno);
    return NULL;
  }
  return _stat_construct_result_helper(st);
}

long LL_os_lseek(long fd, long pos, long how) {
#if defined(MS_WIN64) || defined(MS_WINDOWS)
    PY_LONG_LONG res;
#else
    off_t res;
#endif
#ifdef SEEK_SET
    /* Turn 0, 1, 2 into SEEK_{SET,CUR,END} */
    switch (how) {
        case 0: how = SEEK_SET; break;
        case 1: how = SEEK_CUR; break;
        case 2: how = SEEK_END; break;
    }
#endif /* SEEK_END */
#if defined(MS_WIN64) || defined(MS_WINDOWS)
    res = _lseeki64(fd, pos, how);
#else
    res = lseek(fd, pos, how);
#endif
    if (res < 0)
        RAISE_OSERROR(errno);
    return res;
}

long LL_os_isatty(long fd) {
    return (int)isatty((int)fd);
}

#ifdef HAVE_FTRUNCATE
void LL_os_ftruncate(long fd, long length) { /*XXX add longfile support */
    int res;
    res = ftruncate((int)fd, (off_t)length);
    if (res < 0) {
	RAISE_OSERROR(errno);
    }
}
#endif

RPyString *LL_os_strerror(int errnum)
{
	char *res;
	res = strerror(errnum);
	return RPyString_FromString(res);
}
