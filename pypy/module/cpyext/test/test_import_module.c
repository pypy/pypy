#include "Python.h"
/* Initialize this module. */

PyMODINIT_FUNC
inittest_import_module(void)
{
	PyObject *m, *d;

	m = Py_InitModule("test_import_module", NULL);
	if (m == NULL)
	    return;
	d = PyModule_GetDict(m);
	if (d) {
        PyDict_SetItemString(d, "TEST", (PyObject *) Py_None);
    }
   	/* No need to check the error here, the caller will do that */
}
