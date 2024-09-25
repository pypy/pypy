/* This code was taken from https://github.com/GoogleCloudPlatform/cloud-profiler-python/blob/main/googlecloudprofiler/src/populate_frames.h */ 

#ifndef pp_frames
#define pp_frames

#include <Python.h>

#include <frameobject.h>

#define Py_BUILD_CORE
#include "internal/pycore_frame.h"
#undef Py_BUILD_CORE

_PyInterpreterFrame *unsafe_PyThreadState_GetInterpreterFrame(PyThreadState *tstate);

PyCodeObject *unsafe_PyInterpreterFrame_GetCode(_PyInterpreterFrame *frame);

_PyInterpreterFrame *unsafe_PyInterpreterFrame_GetBack(_PyInterpreterFrame *frame);

int _PyInterpreterFrame_GetLine(_PyInterpreterFrame *frame);

#endif