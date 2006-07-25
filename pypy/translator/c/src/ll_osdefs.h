/************************************************************/
 /***  C header subsection: definition part extracted 
       from posixmodule.c                                 ***/

/* this file is only meant to be included by ll_os.h */

#if defined(PYOS_OS2)
#define  INCL_DOS
#define  INCL_DOSERRORS
#define  INCL_DOSPROCESS
#define  INCL_NOPMAPI
#include <os2.h>
#if defined(PYCC_GCC)
#include <ctype.h>
#include <io.h>
#include <stdio.h>
#include <process.h>
#endif
#include "osdefs.h"
#endif

#include <sys/types.h>
#include <sys/stat.h>

#ifdef HAVE_SYS_WAIT_H
#include <sys/wait.h>		/* For WNOHANG */
#endif

#include <signal.h>

#ifdef HAVE_FCNTL_H
#include <fcntl.h>
#endif /* HAVE_FCNTL_H */

#ifdef HAVE_SYS_FILE_H
#include <sys/file.h>
#endif

#if !defined(MS_WINDOWS)
#include <sys/ioctl.h>
#endif

#include <sys/types.h>

#if !defined(MS_WINDOWS)
#include <sys/mman.h>
#endif

#ifdef HAVE_STROPTS_H
#include <stropts.h>
#endif

#ifdef HAVE_GRP_H
#include <grp.h>
#endif

#ifdef HAVE_SYSEXITS_H
#include <sysexits.h>
#endif /* HAVE_SYSEXITS_H */

#ifdef HAVE_SYS_LOADAVG_H
#include <sys/loadavg.h>
#endif

/* Various compilers have only certain posix functions */
/* XXX Gosh I wish these were all moved into pyconfig.h */
#if defined(PYCC_VACPP) && defined(PYOS_OS2)
#include <process.h>
#else
#if defined(__WATCOMC__) && !defined(__QNX__)		/* Watcom compiler */
#define HAVE_GETCWD     1
#define HAVE_OPENDIR    1
#define HAVE_SYSTEM	1
#if defined(__OS2__)
#define HAVE_EXECV      1
#define HAVE_WAIT       1
#endif
#include <process.h>
#else
#ifdef __BORLANDC__		/* Borland compiler */
#define HAVE_EXECV      1
#define HAVE_GETCWD     1
#define HAVE_OPENDIR    1
#define HAVE_PIPE       1
#define HAVE_POPEN      1
#define HAVE_SYSTEM	1
#define HAVE_WAIT       1
#else
#ifdef _MSC_VER		/* Microsoft compiler */
#define HAVE_GETCWD     1
#define HAVE_SPAWNV	1
#define HAVE_EXECV      1
#define HAVE_PIPE       1
#define HAVE_POPEN      1
#define HAVE_SYSTEM	1
#define HAVE_CWAIT	1
#define HAVE_FSYNC	1
#define fsync _commit
#else
#if defined(PYOS_OS2) && defined(PYCC_GCC) || defined(__VMS)
/* Everything needed is defined in PC/os2emx/pyconfig.h or vms/pyconfig.h */
#else			/* all other compilers */
/* Unix functions that the configure script doesn't check for */
#define HAVE_EXECV      1
#define HAVE_FORK       1
#if defined(__USLC__) && defined(__SCO_VERSION__)	/* SCO UDK Compiler */
#define HAVE_FORK1      1
#endif
#define HAVE_GETCWD     1
#define HAVE_GETEGID    1
#define HAVE_GETEUID    1
#define HAVE_GETGID     1
#define HAVE_GETPPID    1
#define HAVE_GETUID     1
#define HAVE_KILL       1
#define HAVE_OPENDIR    1
#define HAVE_PIPE       1
#ifndef __rtems__
#define HAVE_POPEN      1
#endif
#define HAVE_SYSTEM	1
#define HAVE_WAIT       1
#define HAVE_TTYNAME	1
#endif  /* PYOS_OS2 && PYCC_GCC && __VMS */
#endif  /* _MSC_VER */
#endif  /* __BORLANDC__ */
#endif  /* ! __WATCOMC__ || __QNX__ */
#endif /* ! __IBMC__ */

#ifndef _MSC_VER

#if defined(__sgi)&&_COMPILER_VERSION>=700
/* declare ctermid_r if compiling with MIPSPro 7.x in ANSI C mode
   (default) */
extern char        *ctermid_r(char *);
#endif

#ifndef HAVE_UNISTD_H
#if defined(PYCC_VACPP)
extern int mkdir(char *);
#else
#if ( defined(__WATCOMC__) || defined(_MSC_VER) ) && !defined(__QNX__)
extern int mkdir(const char *);
#else
extern int mkdir(const char *, mode_t);
#endif
#endif
#if defined(__IBMC__) || defined(__IBMCPP__)
extern int chdir(char *);
extern int rmdir(char *);
#else
extern int chdir(const char *);
extern int rmdir(const char *);
#endif
#ifdef __BORLANDC__
extern int chmod(const char *, int);
#else
extern int chmod(const char *, mode_t);
#endif
extern int chown(const char *, uid_t, gid_t);
extern char *getcwd(char *, int);
extern char *strerror(int);
extern int link(const char *, const char *);
extern int rename(const char *, const char *);
extern int stat(const char *, struct stat *);
extern int unlink(const char *);
extern int pclose(FILE *);
#ifdef HAVE_SYMLINK
extern int symlink(const char *, const char *);
#endif /* HAVE_SYMLINK */
#ifdef HAVE_LSTAT
extern int lstat(const char *, struct stat *);
#endif /* HAVE_LSTAT */
#endif /* !HAVE_UNISTD_H */

#endif /* !_MSC_VER */

#ifdef HAVE_UTIME_H
#include <utime.h>
#endif /* HAVE_UTIME_H */

#ifdef HAVE_SYS_UTIME_H
#include <sys/utime.h>
#define HAVE_UTIME_H /* pretend we do for the rest of this file */
#endif /* HAVE_SYS_UTIME_H */

#ifdef HAVE_SYS_TIMES_H
#include <sys/times.h>
#endif /* HAVE_SYS_TIMES_H */

#ifdef HAVE_SYS_PARAM_H
#include <sys/param.h>
#endif /* HAVE_SYS_PARAM_H */

#ifdef HAVE_SYS_UTSNAME_H
#include <sys/utsname.h>
#endif /* HAVE_SYS_UTSNAME_H */

#ifdef HAVE_DIRENT_H
#include <dirent.h>
#define NAMLEN(dirent) strlen((dirent)->d_name)
#else
#if defined(__WATCOMC__) && !defined(__QNX__)
#include <direct.h>
#define NAMLEN(dirent) strlen((dirent)->d_name)
#else
#define dirent direct
#define NAMLEN(dirent) (dirent)->d_namlen
#endif
#ifdef HAVE_SYS_NDIR_H
#include <sys/ndir.h>
#endif
#ifdef HAVE_SYS_DIR_H
#include <sys/dir.h>
#endif
#ifdef HAVE_NDIR_H
#include <ndir.h>
#endif
#endif

#ifdef _MSC_VER
#include <direct.h>
#include <io.h>
#include <process.h>
#include "osdefs.h"
#define _WIN32_WINNT 0x0400	  /* Needed for CryptoAPI on some systems */
#include <windows.h>
#include <shellapi.h>	/* for ShellExecute() */
#define popen	_popen
#define pclose	_pclose
#endif /* _MSC_VER */

#if defined(PYCC_VACPP) && defined(PYOS_OS2)
#include <io.h>
#endif /* OS2 */

#ifndef MAXPATHLEN
#define MAXPATHLEN 1024
#endif /* MAXPATHLEN */

#ifdef UNION_WAIT
/* Emulate some macros on systems that have a union instead of macros */

#ifndef WIFEXITED
#define WIFEXITED(u_wait) (!(u_wait).w_termsig && !(u_wait).w_coredump)
#endif

#ifndef WEXITSTATUS
#define WEXITSTATUS(u_wait) (WIFEXITED(u_wait)?((u_wait).w_retcode):-1)
#endif

#ifndef WTERMSIG
#define WTERMSIG(u_wait) ((u_wait).w_termsig)
#endif

#endif /* UNION_WAIT */

/* Don't use the "_r" form if we don't need it (also, won't have a
   prototype for it, at least on Solaris -- maybe others as well?). */
#if defined(HAVE_CTERMID_R) && defined(WITH_THREAD)
#define USE_CTERMID_R
#endif

#if defined(HAVE_TMPNAM_R) && defined(WITH_THREAD)
#define USE_TMPNAM_R
#endif

/* choose the appropriate stat and fstat functions and return structs */
#undef STAT
#if defined(MS_WIN64) || defined(MS_WINDOWS)
#	define STAT _stati64
#	define FSTAT _fstati64
#	define STRUCT_STAT struct _stati64
#else
#	define STAT stat
#	define FSTAT fstat
#	define STRUCT_STAT struct stat
#endif

#if defined(MAJOR_IN_MKDEV)
#include <sys/mkdev.h>
#else
#if defined(MAJOR_IN_SYSMACROS)
#include <sys/sysmacros.h>
#endif
#if defined(HAVE_MKNOD) && defined(HAVE_SYS_MKDEV_H)
#include <sys/mkdev.h>
#endif
#endif

/* Return a dictionary corresponding to the POSIX environment table */
#ifdef WITH_NEXT_FRAMEWORK
/* On Darwin/MacOSX a shared library or framework has no access to
** environ directly, we must obtain it with _NSGetEnviron().
*/
#include <crt_externs.h>
static char **environ;
#elif !defined(_MSC_VER) && ( !defined(__WATCOMC__) || defined(__QNX__) )
extern char **environ;
#endif /* !_MSC_VER */
