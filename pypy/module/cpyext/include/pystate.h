#ifndef Py_PYSTATE_H
#define Py_PYSTATE_H

struct _ts; /* Forward */
struct _is; /* Forward */

typedef struct _is {
    struct _is *next;
} PyInterpreterState;

typedef struct _ts {
    PyInterpreterState *interp;
} PyThreadState;

#define Py_BEGIN_ALLOW_THREADS { \
			PyThreadState *_save; \
			_save = PyEval_SaveThread();
#define Py_BLOCK_THREADS	PyEval_RestoreThread(_save);
#define Py_UNBLOCK_THREADS	_save = PyEval_SaveThread();
#define Py_END_ALLOW_THREADS	PyEval_RestoreThread(_save); \
		 }

typedef
    enum {PyGILState_LOCKED, PyGILState_UNLOCKED}
        PyGILState_STATE;

#endif /* !Py_PYSTATE_H */
