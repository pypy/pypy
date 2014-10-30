/***** Start of precommondefs.h *****/

/* This is extracted from pyconfig.h from CPython.  It sets the macros
   that affect the features we get from system include files.
   It must not #include anything. */

#ifndef __PYPY_PRECOMMONDEFS_H
#define __PYPY_PRECOMMONDEFS_H


/* Define on Darwin to activate all library features */
#define _DARWIN_C_SOURCE 1
/* This must be set to 64 on some systems to enable large file support. */
#define _FILE_OFFSET_BITS 64
/* Define on Linux to activate all library features */
#define _GNU_SOURCE 1
/* This must be defined on some systems to enable large file support. */
#define _LARGEFILE_SOURCE 1
/* Define on NetBSD to activate all library features */
#define _NETBSD_SOURCE 1
/* Define to activate features from IEEE Stds 1003.1-2001 */
#ifndef _POSIX_C_SOURCE
#  define _POSIX_C_SOURCE 200112L
#endif
/* Define on FreeBSD to activate all library features */
#define __BSD_VISIBLE 1
#define __XSI_VISIBLE 700
/* Windows: winsock/winsock2 mess */
#define WIN32_LEAN_AND_MEAN
#ifdef _WIN64
   typedef          __int64 Signed;
   typedef unsigned __int64 Unsigned;
#  define SIGNED_MIN LLONG_MIN
#else
   typedef          long Signed;
   typedef unsigned long Unsigned;
#  define SIGNED_MIN LONG_MIN
#endif

#if !defined(RPY_ASSERT) && !defined(RPY_LL_ASSERT)
#  define NDEBUG
#endif


#ifdef __GNUC__
#  define RPY_EXPORTED __attribute__((visibility("default")))
#  define RPY_HIDDEN   __attribute__((visibility("hidden")))
#else
#  define RPY_EXPORTED __declspec(dllexport)
#  define RPY_HIDDEN   /* nothing */
#endif
#ifndef RPY_EXPORTED_FOR_TESTS
#  define RPY_EXPORTED_FOR_TESTS  /* nothing */
#endif


#endif /* __PYPY_PRECOMMONDEFS_H */

/***** End of precommondefs.h *****/
