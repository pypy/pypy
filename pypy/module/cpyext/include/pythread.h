#ifndef Py_PYTHREAD_H
#define Py_PYTHREAD_H

#define WITH_THREAD

#ifdef __cplusplus
extern "C" {
#endif

typedef void *PyThread_type_lock;
#define WAIT_LOCK	1
#define NOWAIT_LOCK	0

/* Thread Local Storage (TLS) API */
PyAPI_FUNC(int) PyThread_create_key(void);
PyAPI_FUNC(void) PyThread_delete_key(int);
PyAPI_FUNC(int) PyThread_set_key_value(int, void *);
PyAPI_FUNC(void *) PyThread_get_key_value(int);
PyAPI_FUNC(void) PyThread_delete_key_value(int key);

/* Cleanup after a fork */
PyAPI_FUNC(void) PyThread_ReInitTLS(void);

#ifdef __cplusplus
}
#endif

#endif
