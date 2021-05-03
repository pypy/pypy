#ifndef Py_PYCONFIG_H
#define Py_PYCONFIG_H
#ifdef __cplusplus
extern "C" {
#endif

/* in CPython, this is done in PC/pyconfig.h
   We do it here since we are not using autoconf to generate this file
   At some point we should re-sync with CPython
*/
#ifdef _WIN64
#define MS_WIN64
#endif

#define HAVE_PROTOTYPES 1
#define STDC_HEADERS 1

#define HAVE_LONG_LONG 1
#define HAVE_STDARG_PROTOTYPES 1
#define PY_FORMAT_LONG_LONG "ll"
#define PY_FORMAT_SIZE_T "z"
#define WITH_DOC_STRINGS
#define HAVE_UNICODE
#define WITHOUT_COMPLEX
#define HAVE_WCHAR_H 1
#define HAVE_SYS_TYPES_H 1
#define HAVE_SYS_STAT_H 1

/* PyPy supposes Py_UNICODE == wchar_t */
#define HAVE_USABLE_WCHAR_T 1
#ifdef _WIN32
#define MS_WIN32 /* only support win32 and greater. */
#define MS_WINDOWS
#define SIZEOF_WCHAR_T 2
#else
#define SIZEOF_WCHAR_T 4
#endif

#ifndef _WIN32
#define VA_LIST_IS_ARRAY
#ifndef __APPLE__
#define HAVE_CLOCK_GETTIME
#endif
#endif

#ifndef Py_BUILD_CORE /* not building the core - must be an ext */
#  if defined(_MSC_VER) && !defined(_CFFI_)
   /* So MSVC users need not specify the .lib file in
    * their Makefile (other compilers are generally
    * taken care of by distutils.) 
    */
#    ifdef _DEBUG
#      error("debug first with cpython")    
#            pragma comment(lib,"python37.lib")
#    else
#            pragma comment(lib,"python37.lib")
#    endif /* _DEBUG */
#    define HAVE_COPYSIGN 1
#    define copysign _copysign
#    ifdef MS_WIN64
       typedef __int64 ssize_t;
#    else
       typedef _W64 int ssize_t;
#    endif
#define HAVE_SSIZE_T 1


#    endif
#endif /* _MSC_VER */



#ifdef __cplusplus
}
#endif
#endif
