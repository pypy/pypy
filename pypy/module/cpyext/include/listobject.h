/* empty */
#define PyList_Check(op) \
		 PyType_FastSubclass((op)->ob_type, Py_TPFLAGS_LIST_SUBCLASS)
#define PyList_CheckExact(op) ((op)->ob_type == &PyList_Type)
