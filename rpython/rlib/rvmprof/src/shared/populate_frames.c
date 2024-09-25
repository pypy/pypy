/* This code was taken from https://github.com/GoogleCloudPlatform/cloud-profiler-python/blob/main/googlecloudprofiler/src/populate_frames.cc */ 

#include "populate_frames.h"

#include <Python.h>


// 0x030B0000 is 3.11.
#define PY_311 0x030B0000
#if PY_VERSION_HEX >= PY_311

/**
 * The PyFrameObject structure members have been removed from the public C API
 * in 3.11:
https://docs.python.org/3/whatsnew/3.11.html#pyframeobject-3-11-hiding.
 *
 * Instead, getters are provided which participate in reference counting; since
 * this code runs as part of the SIGPROF handler, it cannot modify Python
 * objects (including their refcounts) and the getters can't be used. Instead,
 * we expose the internal _PyInterpreterFrame and use that directly.
 *
 */

#define Py_BUILD_CORE
#include "internal/pycore_frame.h"
#undef Py_BUILD_CORE

// Modified from
// https://github.com/python/cpython/blob/v3.11.4/Python/pystate.c#L1278-L1285
_PyInterpreterFrame *unsafe_PyThreadState_GetInterpreterFrame(
    PyThreadState *tstate) {
  assert(tstate != NULL);
  _PyInterpreterFrame *f = tstate->cframe->current_frame;
  while (f && _PyFrame_IsIncomplete(f)) {
    f = f->previous;
  }
  if (f == NULL) {
    return NULL;
  }
  return f;
}

// Modified from
// https://github.com/python/cpython/blob/v3.11.4/Objects/frameobject.c#L1310-L1315
// with refcounting removed
PyCodeObject *unsafe_PyInterpreterFrame_GetCode(
    _PyInterpreterFrame *frame) {
  assert(frame != NULL);
  assert(!_PyFrame_IsIncomplete(frame));
  PyCodeObject *code = frame->f_code;
  assert(code != NULL);
  return code;
}

// Modified from
// https://github.com/python/cpython/blob/v3.11.4/Objects/frameobject.c#L1326-L1329
// with refcounting removed
_PyInterpreterFrame *unsafe_PyInterpreterFrame_GetBack(
    _PyInterpreterFrame *frame) {
  assert(frame != NULL);
  assert(!_PyFrame_IsIncomplete(frame));
  _PyInterpreterFrame *prev = frame->previous;
  while (prev && _PyFrame_IsIncomplete(prev)) {
    prev = prev->previous;
  }
  return prev;
}

// Copied from
// https://github.com/python/cpython/blob/v3.11.4/Python/frame.c#L165-L170 as
// this function is not available in libpython
int _PyInterpreterFrame_GetLine(_PyInterpreterFrame *frame) {
  int addr = _PyInterpreterFrame_LASTI(frame) * sizeof(_Py_CODEUNIT);
  return PyCode_Addr2Line(frame->f_code, addr);
}
#endif  // PY_VERSION_HEX >= PY_311