/************************************************************/
 /***  C header subsection: os module                      ***/

#if !(defined(MS_WIN64) || defined(MS_WINDOWS))
#  include <unistd.h>
#  include <sys/types.h>
#  include <sys/stat.h>
#endif

#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#ifndef PATH_MAX
  /* assume windows */
#  define PATH_MAX 254
#endif

#ifndef MAXPATHLEN
#if defined(PATH_MAX) && PATH_MAX > 1024
#define MAXPATHLEN PATH_MAX
#else
#define MAXPATHLEN 1024
#endif
#endif /* MAXPATHLEN */

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
#       define LSTAT STAT
#else
#       define STAT stat
#       define FSTAT fstat
#       define STRUCT_STAT struct stat
/* plus some approximate guesses */
#       define LSTAT lstat
#       define HAVE_FILESYSTEM_WITH_LINKS
#endif


/* prototypes */

RPySTAT_RESULT* _stat_construct_result_helper(STRUCT_STAT st);
RPySTAT_RESULT* LL_os_stat(RPyString * fname);
RPySTAT_RESULT* LL_os_lstat(RPyString * fname);
RPySTAT_RESULT* LL_os_fstat(long fd);
RPyPIPE_RESULT* LL_os_pipe(void);
long LL_os_lseek(long fd, long pos, long how);
int LL_os_isatty(long fd);
RPyString *LL_os_strerror(int errnum);
long LL_os_system(RPyString * fname);
void LL_os_unlink(RPyString * fname);
RPyString *LL_os_getcwd(void);
void LL_os_chdir(RPyString * path);
void LL_os_mkdir(RPyString * path, int mode);
void LL_os_rmdir(RPyString * path);
void LL_os_chmod(RPyString * path, int mode);
void LL_os_rename(RPyString * path1, RPyString * path2);
int LL_os_umask(int mode);
long LL_os_getpid(void);
void LL_os_kill(int pid, int sig);
void LL_os_link(RPyString * path1, RPyString * path2);
void LL_os_symlink(RPyString * path1, RPyString * path2);
long LL_readlink_into(RPyString *path, RPyString *buffer);
long LL_os_fork(void);
#if defined(HAVE_SPAWNV) && defined(HAVE_RPY_LIST_OF_STRING) /* argh */
long LL_os_spawnv(int mode, RPyString *path, RPyListOfString *args);
#endif
RPyWAITPID_RESULT* LL_os_waitpid(long pid, long options);
void LL_os__exit(long status);
void LL_os_putenv(RPyString * name_eq_value);
void LL_os_unsetenv(RPyString * name);
RPyString* LL_os_environ(int idx);
struct RPyOpaque_DIR *LL_os_opendir(RPyString *dirname);
RPyString *LL_os_readdir(struct RPyOpaque_DIR *dir);
void LL_os_closedir(struct RPyOpaque_DIR *dir);

static int geterrno(void)
{
    return errno;
}


/* implementations */

#ifndef PYPY_NOT_MAIN_FILE

#include "ll_osdefs.h"

#ifdef LL_NEED_OS_STAT

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

RPySTAT_RESULT* LL_os_lstat(RPyString * fname) {
  STRUCT_STAT st;
  int error = LSTAT(RPyString_AsString(fname), &st);
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

#endif

#ifdef LL_NEED_OS_PIPE

RPyPIPE_RESULT* LL_os_pipe(void) {
#if !defined(MS_WINDOWS)
	int filedes[2];
	int error = pipe(filedes);
	if (error != 0) {
		RPYTHON_RAISE_OSERROR(errno);
		return NULL;
	}
	return ll_pipe_result(filedes[0], filedes[1]);
#else
	HANDLE read, write;
	int read_fd, write_fd;
	BOOL ok = CreatePipe(&read, &write, NULL, 0);
	if (!ok) {
		RPYTHON_RAISE_OSERROR(errno);
		return NULL;
	}
	read_fd = _open_osfhandle((long)read, 0);
	write_fd = _open_osfhandle((long)write, 1);
	return ll_pipe_result(read_fd, write_fd);
#endif
}

#endif

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

void LL_os_chmod(RPyString * path, int mode) {
    int error = chmod(RPyString_AsString(path), mode);
    if (error != 0) {
	RPYTHON_RAISE_OSERROR(errno);
    }
}

void LL_os_rename(RPyString * path1, RPyString * path2) {
    int error = rename(RPyString_AsString(path1), RPyString_AsString(path2));
    if (error != 0) {
	RPYTHON_RAISE_OSERROR(errno);
    }
}

int LL_os_umask(int mode) {
	return umask(mode);
}

long LL_os_getpid(void) {
	return getpid();
}

#ifdef HAVE_KILL
void LL_os_kill(int pid, int sig) {
    int error = kill(pid, sig);
    if (error != 0) {
	RPYTHON_RAISE_OSERROR(errno);
    }
}
#endif

#ifdef HAVE_FILESYSTEM_WITH_LINKS

void LL_os_link(RPyString * path1, RPyString * path2) {
    int error = link(RPyString_AsString(path1), RPyString_AsString(path2));
    if (error != 0) {
	RPYTHON_RAISE_OSERROR(errno);
    }
}

void LL_os_symlink(RPyString * path1, RPyString * path2) {
    int error = symlink(RPyString_AsString(path1), RPyString_AsString(path2));
    if (error != 0) {
	RPYTHON_RAISE_OSERROR(errno);
    }
}

long LL_readlink_into(RPyString *path, RPyString *buffer)
{
	long n = readlink(RPyString_AsString(path),
			  RPyString_AsString(buffer), RPyString_Size(buffer));
	if (n < 0)
		RPYTHON_RAISE_OSERROR(errno);
	return n;
}

#endif

#ifdef HAVE_FORK
long LL_os_fork(void) {
	int pid = fork();
	if (pid == -1)
		RPYTHON_RAISE_OSERROR(errno);
	return pid;
}
#endif

/*
  The following code is only generated if spawnv exists and
  if RPyListOfString exists. The latter is a bit tricky:
  The RPyListOfString is necessary to correctly declare this function.
  For this to work, the test code must be properly written in a way
  that RPyListOfString is really annotated as such.
  Please see the test in test_extfunc.py - creating the correct
  argument string type is not obvious and error prone.
 */
#if defined(HAVE_SPAWNV) && defined(HAVE_RPY_LIST_OF_STRING)
long LL_os_spawnv(int mode, RPyString *path, RPyListOfString *args) {
	int pid, i, nargs = args->l_length;
	char **slist = malloc((nargs+1) * sizeof(char*));
	pid = -1;
	if (slist) {
		for (i=0; i<nargs; i++)
			slist[i] = RPyString_AsString(args->l_items->items[i]);
		slist[nargs] = NULL;
		pid = spawnv(mode, RPyString_AsString(path), slist);
		free(slist);
	}
	if (pid == -1)
		RPYTHON_RAISE_OSERROR(errno);
	return pid;
}
#endif

#ifdef LL_NEED_OS_WAITPID
/* note: LL_NEED_ is computed in extfunc.py, can't grep */

#ifdef HAVE_WAITPID
RPyWAITPID_RESULT* LL_os_waitpid(long pid, long options) {
	int status;
	pid = waitpid(pid, &status, options);
	if (pid == -1) {
		RPYTHON_RAISE_OSERROR(errno);
		return NULL;
	}
	return ll_waitpid_result(pid, status);
}

#elif defined(HAVE_CWAIT)

RPyWAITPID_RESULT* LL_os_waitpid(long pid, long options) {
	int status;
	pid = _cwait(&status, pid, options);
	if (pid == -1) {
		RPYTHON_RAISE_OSERROR(errno);
		return NULL;
	}
		/* shift the status left a byte so this is more like the
		   POSIX waitpid */
	return ll_waitpid_result(pid, status << 8);
}
#endif /* HAVE_WAITPID || HAVE_CWAIT */
#endif

void LL_os__exit(long status) {
	_exit((int)status);
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
    char arg[1]; /*also used as flag */
} DIR;

static DIR *opendir(char *dirname)
{
    int lng = strlen(dirname);
    DIR *d = malloc(sizeof(DIR) + lng + 4);

    if (d != NULL) {
	char *ptr = (char*)d->arg;
	strcpy(ptr, dirname);
	strcpy(ptr + lng, "\\*.*" + (*(ptr + lng - 1) == '\\'));
	d->hFind = FindFirstFile(ptr, &d->FileData);
	d->d_name = d->FileData.cFileName;
	if (d->hFind == INVALID_HANDLE_VALUE) {
	    d->d_name = NULL;
	    if (GetLastError() != ERROR_FILE_NOT_FOUND) {
		errno = GetLastError();
		free(d);
		d = NULL;
	    }
	}
    }
    return d;
}

static struct dirent *readdir(DIR *d)
{
    if (d->arg[0])
	d->arg[0] = 0; /* use existing result first time */
    else {
	if (FindNextFile(d->hFind, &d->FileData))
	    d->d_name = d->FileData.cFileName;
	else {
	    d->d_name = NULL;
	    if (GetLastError() != ERROR_NO_MORE_FILES)
		errno = GetLastError();
	}
    }
    return d->d_name ? d : NULL;
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
