#ifndef Py_MYSNPRINTF_H
#define Py_MYSNPRINTF_H
#ifdef __cplusplus
extern "C" {
#endif

PyAPI_FUNC(int) PyOS_snprintf(char *str, size_t size, const  char  *format, ...);
PyAPI_FUNC(int) PyOS_vsnprintf(char *str, size_t size, const  char  *format, va_list va);

#ifdef __cplusplus
}
#endif
#endif
