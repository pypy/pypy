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


/* prototypes */

int LL_os_open(RPyString *filename, int flag, int mode);
long LL_read_into(int fd, RPyString *buffer);
long LL_os_write(int fd, RPyString *buffer);
void LL_os_close(int fd);
int LL_os_dup(int fd);
RPySTAT_RESULT* _stat_construct_result_helper(STRUCT_STAT st);
RPySTAT_RESULT* LL_os_stat(RPyString * fname);
RPySTAT_RESULT* LL_os_fstat(long fd);
long LL_os_lseek(long fd, long pos, long how);
int LL_os_isatty(long fd);
RPyString *LL_os_strerror(int errnum);
long LL_os_system(RPyString * fname);
void LL_os_unlink(RPyString * fname);
RPyString *LL_os_getcwd(void);
void LL_os_chdir(RPyString * path);
void LL_os_mkdir(RPyString * path, int mode);
void LL_os_rmdir(RPyString * path);
void LL_os_putenv(RPyString * name_eq_value);
void LL_os_unsetenv(RPyString * name);
RPyString* LL_os_environ(int idx);
struct RPyOpaque_DIR *LL_os_opendir(RPyString *dirname);
RPyString *LL_os_readdir(struct RPyOpaque_DIR *dir);
void LL_os_closedir(struct RPyOpaque_DIR *dir);

/* implementations */

#ifndef PYPY_NOT_MAIN_FILE

#include "ll_osdefs.h"

int LL_os_open(RPyString *filename, int flag, int mode)
{
	/* XXX unicode_file_names */
	int fd = open(RPyString_AsString(filename), flag, mode);
	if (fd < 0)
		RPYTHON_RAISE_OSERROR(errno);
	return fd;
}

long LL_read_into(int fd, RPyString *buffer)
{
	long n = read(fd, RPyString_AsString(buffer), RPyString_Size(buffer));
	if (n < 0)
		RPYTHON_RAISE_OSERROR(errno);
	return n;
}

long LL_os_write(int fd, RPyString *buffer)
{
	long n = write(fd, RPyString_AsString(buffer), RPyString_Size(buffer));
	if (n < 0)
		RPYTHON_RAISE_OSERROR(errno);
	return n;
}

void LL_os_close(int fd)
{
	if (close(fd) < 0)
		RPYTHON_RAISE_OSERROR(errno);
}

int LL_os_dup(int fd)
{
	fd = dup(fd);
	if (fd < 0)
		RPYTHON_RAISE_OSERROR(errno);
	return fd;
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
    RPYTHON_RAISE_OSERROR(errno);
    return NULL;
  }
  return _stat_construct_result_helper(st);
}

RPySTAT_RESULT* LL_os_fstat(long fd) {
  STRUCT_STAT st;
  int error = FSTAT(fd, &st);
  if (error != 0) {
    RPYTHON_RAISE_OSERROR(errno);
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
        RPYTHON_RAISE_OSERROR(errno);
    return res;
}

int LL_os_isatty(long fd) {
    return isatty((int)fd);
}

#ifdef HAVE_FTRUNCATE
void LL_os_ftruncate(long fd, long length) { /*XXX add longfile support */
    int res;
    res = ftruncate((int)fd, (off_t)length);
    if (res < 0) {
	RPYTHON_RAISE_OSERROR(errno);
    }
}
#endif

RPyString *LL_os_strerror(int errnum) {
	char *res;
	res = strerror(errnum);
	if (res == NULL) {
		RPyRaiseSimpleException(PyExc_ValueError,
					"strerror() argument out of range");
		return NULL;
	}
	return RPyString_FromString(res);
}

long LL_os_system(RPyString * fname) {
  return system(RPyString_AsString(fname));
}

void LL_os_unlink(RPyString * fname) {
    int error = unlink(RPyString_AsString(fname));
    if (error != 0) {
	RPYTHON_RAISE_OSERROR(errno);
    }
}

RPyString *LL_os_getcwd(void) {
	char buf[PATH_MAX];
	char *res;
	res = getcwd(buf, sizeof buf);
	if (res == NULL) {
		RPYTHON_RAISE_OSERROR(errno);
		return NULL;
	}
	return RPyString_FromString(buf);
}

void LL_os_chdir(RPyString * path) {
    int error = chdir(RPyString_AsString(path));
    if (error != 0) {
	RPYTHON_RAISE_OSERROR(errno);
    }
}

void LL_os_mkdir(RPyString * path, int mode) {
#if defined(MS_WIN64) || defined(MS_WINDOWS)
    /* no mode support on Windows */
    int error = mkdir(RPyString_AsString(path));
#else
    int error = mkdir(RPyString_AsString(path), mode);
#endif
    if (error != 0) {
	RPYTHON_RAISE_OSERROR(errno);
    }
}

void LL_os_rmdir(RPyString * path) {
    int error = rmdir(RPyString_AsString(path));
    if (error != 0) {
	RPYTHON_RAISE_OSERROR(errno);
    }
}

#ifdef HAVE_PUTENV
/* Note that this doesn't map to os.putenv, it is the name=value
 * version of C. See ros.py for the fake implementation.
 * Also note that we are responsible to keep the
 * value alive. This is done in interp_posix.py
 */
void LL_os_putenv(RPyString * name_eq_value) {
    int error = putenv(RPyString_AsString(name_eq_value));
    if (error != 0) {
	RPYTHON_RAISE_OSERROR(errno);
    }
}
#endif

#ifdef HAVE_UNSETENV
void LL_os_unsetenv(RPyString * name) {
    unsetenv(RPyString_AsString(name));
}
#endif

/* Return a dictionary corresponding to the POSIX environment table */
/*** actually, we create a string list here and do the rest in posix */

RPyString* LL_os_environ(int idx) {
    RPyString *rs = NULL;
    char *s;
#ifdef WITH_NEXT_FRAMEWORK
    if (environ == NULL)
	environ = *_NSGetEnviron();
#endif
    if (environ != NULL && (s = environ[idx]) != NULL) {
	rs = RPyString_FromString(s);
    }
    return rs;
}

/******************** opendir/readdir/closedir ********************/

#if defined(MS_WINDOWS) && !defined(HAVE_OPENDIR)

/* emulation of opendir, readdir, closedir */

/* 
    the problem is that Windows does not have something like
    opendir. Instead, FindFirstFile creates a handle and
    yields the first entry found. Furthermore, we need
    to mangle the filename.
    To keep the rpython interface, we need to buffer the
    first result and let readdir return this first time.
    Drawback of this approach: we need to use malloc,
    and the way I'm emulating dirent is maybe somewhat hackish.

    XXX we are lacking unicode support, completely.
    Might need a different interface.
 */

#undef dirent

typedef struct dirent {
    HANDLE hFind;
    WIN32_FIND_DATA FileData;
    char *d_name; /* faking dirent */
    int first_done;
} DIR;

static DIR *opendir(char *dirname)
{
    DIR *d = malloc(sizeof(DIR));
    int lng = strlen(dirname);
    char *mangled = strcpy(_alloca(lng + 5), dirname);
    char *p = mangled + lng;

    if (d == NULL)
	return NULL;

    if (lng && p[-1] == '\\')
	p--;
    strcpy(p, "\\*.*");

    d->first_done = 0;
    d->hFind = FindFirstFile(mangled, &d->FileData);
    if (d->hFind == INVALID_HANDLE_VALUE) {
	d->d_name = NULL;
	errno = GetLastError();
	if (errno == ERROR_FILE_NOT_FOUND) {
	    errno = 0;
	    return d;
	}
	free(d);
	return NULL;
    }
    d->d_name = d->FileData.cFileName;
    return d;
}

static struct dirent *readdir(DIR *d)
{
    if (!d->first_done) {
	d->first_done = 1;
	if (d->d_name == NULL)
	    return NULL;
	return d;
    }
    if (!FindNextFile(d->hFind, &d->FileData)) {
	errno = GetLastError();
	if (errno == ERROR_NO_MORE_FILES)
	    errno = 0;
	return NULL;
    }
    d->d_name = d->FileData.cFileName;
    return d;
}

static int closedir(DIR *d)
{
    HANDLE hFind = d->hFind;

    free(d);
    if (FindClose(hFind) == 0) {
	errno = GetLastError();
	return -1;
    }
    return 0;
}

#endif /* defined(MS_WINDOWS) && !defined(HAVE_OPENDIR) */

struct RPyOpaque_DIR *LL_os_opendir(RPyString *dirname)
{
    DIR *dir = opendir(RPyString_AsString(dirname));
    if (dir == NULL)
	RPYTHON_RAISE_OSERROR(errno);
    return (struct RPyOpaque_DIR *) dir;
}

RPyString *LL_os_readdir(struct RPyOpaque_DIR *dir)
{
    struct dirent *d;
    errno = 0;
    d = readdir((DIR *) dir);
    if (d != NULL)
	return RPyString_FromString(d->d_name);
    if (errno)
	RPYTHON_RAISE_OSERROR(errno);
    return NULL;
}

void LL_os_closedir(struct RPyOpaque_DIR *dir)
{
    if (closedir((DIR *) dir) < 0)
	RPYTHON_RAISE_OSERROR(errno);
}

#endif /* PYPY_NOT_MAIN_FILE */
