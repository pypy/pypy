#ifndef Py_PYSTATE_H
#define Py_PYSTATE_H

struct _ts; /* Forward */
struct _is; /* Forward */

typedef struct _is {
    struct _is *next;
} PyInterpreterState;

typedef struct _ts {
    PyInterpreterState *interp;
    PyObject *dict;  /* Stores per-thread state */
} PyThreadState;

#define Py_BEGIN_ALLOW_THREADS { \
			PyThreadState *_save; \
			_save = PyEval_SaveThread();
#define Py_BLOCK_THREADS	PyEval_RestoreThread(_save);
#define Py_UNBLOCK_THREADS	_save = PyEval_SaveThread();
#define Py_END_ALLOW_THREADS	PyEval_RestoreThread(_save); \
		 }

enum {PyGILState_LOCKED, PyGILState_UNLOCKED};
typedef int PyGILState_STATE;

#define PyThreadState_GET() PyThreadState_Get()

#endif /* !Py_PYSTATE_H */
