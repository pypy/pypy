#ifndef Py_PYCONFIG_H
#define Py_PYCONFIG_H
#ifdef __cplusplus
extern "C" {
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
#ifndef _WIN32
#define Py_UNICODE_SIZE 4
#define Py_UNICODE_WIDE
#else
#define Py_UNICODE_SIZE 2
#endif

#ifndef Py_BUILD_CORE /* not building the core - must be an ext */
#    if defined(_MSC_VER)
     /* So MSVC users need not specify the .lib file in
      * their Makefile (other compilers are generally
      * taken care of by distutils.) */
#        ifdef _DEBUG
#            error("debug first with cpython")    
#            pragma comment(lib,"python27.lib")
#        else
#            pragma comment(lib,"python27.lib")
#        endif /* _DEBUG */
#    endif
#endif /* _MSC_VER */



#ifdef __cplusplus
}
#endif
#endif
