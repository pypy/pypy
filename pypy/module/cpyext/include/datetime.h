#ifndef DATETIME_H
#define DATETIME_H
#ifdef __cplusplus
extern "C" {
#endif

#define PyDateTime_IMPORT _PyDateTime_Import()

typedef struct {
    PyObject_HEAD
} PyDateTime_Delta;

#ifdef __cplusplus
}
#endif
#endif
