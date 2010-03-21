#include <assert.h>

#include <pypy_rename.h>
#include <Python.h>

    
int
PyPyType_Ready(PyTypeObject *type)
{
	PyObject *dict, *bases;
	PyTypeObject *base;
	Py_ssize_t i, n;

	if (type->tp_flags & Py_TPFLAGS_READY) {
		assert(type->tp_dict != NULL);
		return 0;
	}
	assert((type->tp_flags & Py_TPFLAGS_READYING) == 0);

	type->tp_flags |= Py_TPFLAGS_READYING;

#ifdef Py_TRACE_REFS
	/* PyType_Ready is the closest thing we have to a choke point
	 * for type objects, so is the best place I can think of to try
	 * to get type objects into the doubly-linked list of all objects.
	 * Still, not all type objects go thru PyType_Ready.
	 */
	_Py_AddToAllObjects((PyObject *)type, 0);
#endif

	/* Initialize tp_base (defaults to BaseObject unless that's us) */
	base = type->tp_base;
	if (base == NULL && type != &PyBaseObject_Type) {
		base = type->tp_base = &PyBaseObject_Type;
		Py_INCREF(base);
	}

	/* Now the only way base can still be NULL is if type is
	 * &PyBaseObject_Type.
	 */

	/* Initialize the base class */
	if (base && base->tp_dict == NULL) {
		if (PyType_Ready(base) < 0)
			goto error;
	}

	/* Initialize ob_type if NULL.	This means extensions that want to be
	   compilable separately on Windows can call PyType_Ready() instead of
	   initializing the ob_type field of their type objects. */
	/* The test for base != NULL is really unnecessary, since base is only
	   NULL when type is &PyBaseObject_Type, and we know its ob_type is
	   not NULL (it's initialized to &PyType_Type).	 But coverity doesn't
	   know that. */
	if (Py_TYPE(type) == NULL && base != NULL)
		Py_TYPE(type) = Py_TYPE(base);

	/* Initialize tp_bases */
	bases = type->tp_bases;
	if (bases == NULL) {
		if (base == NULL)
			bases = PyTuple_New(0);
		else
			bases = PyTuple_Pack(1, base);
		if (bases == NULL)
			goto error;
		type->tp_bases = bases;
	}

	/* Initialize tp_dict */
	dict = type->tp_dict;
	if (dict == NULL) {
		dict = PyDict_New();
		if (dict == NULL)
			goto error;
		type->tp_dict = dict;
	}

	/* Add type-specific descriptors to tp_dict */
	if (add_operators(type) < 0)
		goto error;
	if (type->tp_methods != NULL) {
		if (add_methods(type, type->tp_methods) < 0)
			goto error;
	}
	if (type->tp_members != NULL) {
		if (add_members(type, type->tp_members) < 0)
			goto error;
	}
	if (type->tp_getset != NULL) {
		if (add_getset(type, type->tp_getset) < 0)
			goto error;
	}

	/* Calculate method resolution order */
	if (mro_internal(type) < 0) {
		goto error;
	}

	/* Inherit special flags from dominant base */
	if (type->tp_base != NULL)
		inherit_special(type, type->tp_base);

	/* Initialize tp_dict properly */
	bases = type->tp_mro;
	assert(bases != NULL);
	assert(PyTuple_Check(bases));
	n = PyTuple_GET_SIZE(bases);
	for (i = 1; i < n; i++) {
		PyObject *b = PyTuple_GET_ITEM(bases, i);
		if (PyType_Check(b))
			inherit_slots(type, (PyTypeObject *)b);
	}

	/* Sanity check for tp_free. */
	if (PyType_IS_GC(type) && (type->tp_flags & Py_TPFLAGS_BASETYPE) &&
	    (type->tp_free == NULL || type->tp_free == PyObject_Del)) {
		/* This base class needs to call tp_free, but doesn't have
		 * one, or its tp_free is for non-gc'ed objects.
		 */
		PyErr_Format(PyExc_TypeError, "type '%.100s' participates in "
			     "gc and is a base type but has inappropriate "
			     "tp_free slot",
			     type->tp_name);
		goto error;
	}

	/* if the type dictionary doesn't contain a __doc__, set it from
	   the tp_doc slot.
	 */
	if (PyDict_GetItemString(type->tp_dict, "__doc__") == NULL) {
		if (type->tp_doc != NULL) {
			PyObject *doc = PyString_FromString(type->tp_doc);
			if (doc == NULL)
				goto error;
			PyDict_SetItemString(type->tp_dict, "__doc__", doc);
			Py_DECREF(doc);
		} else {
			PyDict_SetItemString(type->tp_dict,
					     "__doc__", Py_None);
		}
	}

	/* Some more special stuff */
	base = type->tp_base;
	if (base != NULL) {
		if (type->tp_as_number == NULL)
			type->tp_as_number = base->tp_as_number;
		if (type->tp_as_sequence == NULL)
			type->tp_as_sequence = base->tp_as_sequence;
		if (type->tp_as_mapping == NULL)
			type->tp_as_mapping = base->tp_as_mapping;
		if (type->tp_as_buffer == NULL)
			type->tp_as_buffer = base->tp_as_buffer;
	}

	/* Link into each base class's list of subclasses */
	bases = type->tp_bases;
	n = PyTuple_GET_SIZE(bases);
	for (i = 0; i < n; i++) {
		PyObject *b = PyTuple_GET_ITEM(bases, i);
		if (PyType_Check(b) &&
		    add_subclass((PyTypeObject *)b, type) < 0)
			goto error;
	}

	/* All done -- set the ready flag */
	assert(type->tp_dict != NULL);
	type->tp_flags =
		(type->tp_flags & ~Py_TPFLAGS_READYING) | Py_TPFLAGS_READY;
	return 0;

  error:
	type->tp_flags &= ~Py_TPFLAGS_READYING;
	return -1;
}


