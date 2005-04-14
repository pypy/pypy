
/************************************************************/
 /***  C header subsection: untyped operations             ***/
  /***  as OP_XXX() macros calling the CPython API          ***/


#define op_bool(r,err,what) { \
		int _retval = what; \
		if (_retval < 0) { \
			FAIL(err) \
		} \
		r = PyBool_FromLong(_retval); \
	}

#define op_richcmp(x,y,r,err,dir) \
					if (!(r=PyObject_RichCompare(x,y,dir))) FAIL(err)
#define OP_LT(x,y,r,err)  op_richcmp(x,y,r,err, Py_LT)
#define OP_LE(x,y,r,err)  op_richcmp(x,y,r,err, Py_LE)
#define OP_EQ(x,y,r,err)  op_richcmp(x,y,r,err, Py_EQ)
#define OP_NE(x,y,r,err)  op_richcmp(x,y,r,err, Py_NE)
#define OP_GT(x,y,r,err)  op_richcmp(x,y,r,err, Py_GT)
#define OP_GE(x,y,r,err)  op_richcmp(x,y,r,err, Py_GE)

#define OP_IS_(x,y,r,err) op_bool(r,err,(x == y))

#define OP_IS_TRUE(x,r,err) op_bool(r,err,PyObject_IsTrue(x))
#define OP_NONZERO(x,r,err) op_bool(r,err,PyObject_IsTrue(x))

#define OP_LEN(x,r,err) { \
		int _retval = PyObject_Size(x); \
		if (_retval < 0) { \
			FAIL(err) \
		} \
		r = PyInt_FromLong(_retval); \
	}
#define OP_NEG(x,r,err)           if (!(r=PyNumber_Negative(x)))     FAIL(err)
#define OP_POS(x,r,err)           if (!(r=PyNumber_Positive(x)))     FAIL(err)
#define OP_INVERT(x,r,err)        if (!(r=PyNumber_Invert(x)))       FAIL(err)
#define OP_ABS(x,r,err)           if (!(r=PyNumber_Absolute(x)))     FAIL(err)

#define OP_ADD(x,y,r,err)         if (!(r=PyNumber_Add(x,y)))        FAIL(err)
#define OP_SUB(x,y,r,err)         if (!(r=PyNumber_Subtract(x,y)))   FAIL(err)
#define OP_MUL(x,y,r,err)         if (!(r=PyNumber_Multiply(x,y)))   FAIL(err)
#define OP_TRUEDIV(x,y,r,err)     if (!(r=PyNumber_TrueDivide(x,y))) FAIL(err)
#define OP_FLOORDIV(x,y,r,err)    if (!(r=PyNumber_FloorDivide(x,y)))FAIL(err)
#define OP_DIV(x,y,r,err)         if (!(r=PyNumber_Divide(x,y)))     FAIL(err)
#define OP_MOD(x,y,r,err)         if (!(r=PyNumber_Remainder(x,y)))  FAIL(err)
#define OP_DIVMOD(x,y,r,err)      if (!(r=PyNumber_Divmod(x,y)))     FAIL(err)
#define OP_POW(x,y,z,r,err)       if (!(r=PyNumber_Power(x,y,z)))    FAIL(err)
#define OP_LSHIFT(x,y,r,err)      if (!(r=PyNumber_Lshift(x,y)))     FAIL(err)
#define OP_RSHIFT(x,y,r,err)      if (!(r=PyNumber_Rshift(x,y)))     FAIL(err)
#define OP_AND_(x,y,r,err)        if (!(r=PyNumber_And(x,y)))        FAIL(err)
#define OP_OR_(x,y,r,err)         if (!(r=PyNumber_Or(x,y)))         FAIL(err)
#define OP_XOR(x,y,r,err)         if (!(r=PyNumber_Xor(x,y)))        FAIL(err)

#define OP_INPLACE_ADD(x,y,r,err) if (!(r=PyNumber_InPlaceAdd(x,y)))           \
								     FAIL(err)
#define OP_INPLACE_SUB(x,y,r,err) if (!(r=PyNumber_InPlaceSubtract(x,y)))      \
								     FAIL(err)
#define OP_INPLACE_MUL(x,y,r,err) if (!(r=PyNumber_InPlaceMultiply(x,y)))      \
								     FAIL(err)
#define OP_INPLACE_TRUEDIV(x,y,r,err) if (!(r=PyNumber_InPlaceTrueDivide(x,y)))\
								     FAIL(err)
#define OP_INPLACE_FLOORDIV(x,y,r,err)if(!(r=PyNumber_InPlaceFloorDivide(x,y)))\
								     FAIL(err)
#define OP_INPLACE_DIV(x,y,r,err) if (!(r=PyNumber_InPlaceDivide(x,y)))        \
								     FAIL(err)
#define OP_INPLACE_MOD(x,y,r,err) if (!(r=PyNumber_InPlaceRemainder(x,y)))     \
								     FAIL(err)
#define OP_INPLACE_POW(x,y,r,err) if (!(r=PyNumber_InPlacePower(x,y,Py_None))) \
								     FAIL(err)
#define OP_INPLACE_LSHIFT(x,y,r,err) if (!(r=PyNumber_InPlaceLshift(x,y)))     \
								     FAIL(err)
#define OP_INPLACE_RSHIFT(x,y,r,err) if (!(r=PyNumber_InPlaceRshift(x,y)))     \
								     FAIL(err)
#define OP_INPLACE_AND(x,y,r,err)    if (!(r=PyNumber_InPlaceAnd(x,y)))        \
								     FAIL(err)
#define OP_INPLACE_OR(x,y,r,err)     if (!(r=PyNumber_InPlaceOr(x,y)))         \
								     FAIL(err)
#define OP_INPLACE_XOR(x,y,r,err)    if (!(r=PyNumber_InPlaceXor(x,y)))        \
								     FAIL(err)

#define OP_GETITEM(x,y,r,err)     if (!(r=PyObject_GetItem1(x,y)))   FAIL(err)
#define OP_SETITEM(x,y,z,r,err)   if ((PyObject_SetItem1(x,y,z))<0)  FAIL(err) \
				  r=Py_None; Py_INCREF(r);
#define OP_DELITEM(x,y,r,err)     if ((PyObject_DelItem(x,y))<0)     FAIL(err) \
				  r=Py_None; Py_INCREF(r);
#define OP_CONTAINS(x,y,r,err)    op_bool(r,err,(PySequence_Contains(x,y)))

#define OP_GETATTR(x,y,r,err)     if (!(r=PyObject_GetAttr(x,y)))    FAIL(err)
#define OP_SETATTR(x,y,z,r,err)   if ((PyObject_SetAttr(x,y,z))<0)   FAIL(err) \
				  r=Py_None; Py_INCREF(r);
#define OP_DELATTR(x,y,r,err)     if ((PyObject_SetAttr(x,y,NULL))<0)FAIL(err) \
				  r=Py_None; Py_INCREF(r);

#define OP_NEWSLICE(x,y,z,r,err)  if (!(r=PySlice_New(x,y,z)))       FAIL(err)

#define OP_GETSLICE(x,y,z,r,err)  {					\
		PyObject *__yo = y, *__zo = z;				\
		int __y = 0, __z = INT_MAX;				\
		if (__yo == Py_None) __yo = NULL;			\
		if (__zo == Py_None) __zo = NULL;			\
		if (!_PyEval_SliceIndex(__yo, &__y) ||			\
		    !_PyEval_SliceIndex(__zo, &__z) ||			\
		    !(r=PySequence_GetSlice(x, __y, __z))) FAIL(err)	\
	}

#define OP_ALLOC_AND_SET(x,y,r,err) { \
		/* XXX check for long/int overflow */ \
		int __i, __x = PyInt_AsLong(x); \
		if (PyErr_Occurred()) FAIL(err) \
		if (!(r = PyList_New(__x))) FAIL(err) \
		for (__i=0; __i<__x; __i++) { \
			Py_INCREF(y); \
			PyList_SET_ITEM(r, __i, y); \
		} \
	}

#define OP_ITER(x,r,err)          if (!(r=PyObject_GetIter(x)))      FAIL(err)
#define OP_NEXT(x,r,err)          if (!(r=PyIter_Next(x))) {                   \
		if (!PyErr_Occurred()) PyErr_SetNone(PyExc_StopIteration);     \
		FAIL(err)                                                      \
	}

#define OP_STR(x,r,err)           if (!(r=PyObject_Str(x)))          FAIL(err)
#define OP_REPR(x,r,err)          if (!(r=PyObject_Repr(x)))         FAIL(err)
#define OP_ORD(s,r,err) { \
	char *__c = PyString_AsString(s); \
	int __len; \
	if ( !__c) FAIL(err) \
	if ((__len = PyString_GET_SIZE(s)) != 1) { \
	    PyErr_Format(PyExc_TypeError, \
		  "ord() expected a character, but string of length %d found", \
		  __len); \
	    FAIL(err) \
	} \
	if (!(r = PyInt_FromLong((unsigned char)(__c[0])))) \
	    FAIL(err) \
    }
#define OP_ID(x,r,err)    if (!(r=PyLong_FromVoidPtr(x))) FAIL(err)
#define OP_HASH(x,r,err)  { \
	long __hash = PyObject_Hash(x); \
	if (__hash == -1 && PyErr_Occurred()) FAIL(err) \
	if (!(r = PyInt_FromLong(__hash))) FAIL(err) \
    }

#define OP_HEX(x,r,err)   { \
	PyNumberMethods *__nb; \
	if ((__nb = x->ob_type->tp_as_number) == NULL || \
	    __nb->nb_hex == NULL) { \
		PyErr_SetString(PyExc_TypeError, \
			   "hex() argument can't be converted to hex"); \
		FAIL(err) \
	} \
	if (!(r = (*__nb->nb_hex)(x))) FAIL(err) \
    }
#define OP_OCT(x,r,err)   { \
	PyNumberMethods *__nb; \
	if ((__nb = x->ob_type->tp_as_number) == NULL || \
	    __nb->nb_oct == NULL) { \
		PyErr_SetString(PyExc_TypeError, \
			   "oct() argument can't be converted to oct"); \
		FAIL(err) \
	} \
	if (!(r = (*__nb->nb_oct)(x))) FAIL(err) \
    }

#define OP_INT(x,r,err)   { \
	long __val = PyInt_AsLong(x); \
	if (__val == -1 && PyErr_Occurred()) FAIL(err) \
	if (!(r = PyInt_FromLong(__val))) FAIL (err) \
    }
#define OP_FLOAT(x,r,err)   { \
	double __val = PyFloat_AsDouble(x); \
	if (PyErr_Occurred()) FAIL(err) \
	if (!(r = PyFloat_FromDouble(__val))) FAIL (err) \
    }

#define OP_CMP(x,y,r,err)   { \
	int __val = PyObject_Compare(x, y); \
	if (PyErr_Occurred()) FAIL(err) \
	if (!(r = PyInt_FromLong(__val))) FAIL (err) \
    }


#define OP_SIMPLE_CALL(args,r,err) if (!(r=PyObject_CallFunctionObjArgs args)) \
					FAIL(err)
#define OP_CALL_ARGS(args,r,err)   if (!(r=CallWithShape args))    FAIL(err)

/* Needs to act like getattr(x, '__class__', type(x)) */
#define OP_TYPE(x,r,err) { \
		PyObject *o = x; \
		if (PyInstance_Check(o)) { \
			r = (PyObject*)(((PyInstanceObject*)o)->in_class); \
		} else { \
			r = (PyObject*)o->ob_type; \
		} \
		Py_INCREF(r); \
	}

/* Needs to act like instance(x,y) */
#define OP_ISSUBTYPE(x,y,r,err)  \
		op_bool(r,err,PyObject_IsSubclass(x, y))


/*** operations with a variable number of arguments ***/

#define OP_NEWLIST0(r,err)         if (!(r=PyList_New(0))) FAIL(err)
#define OP_NEWLIST(args,r,err)     if (!(r=PyList_Pack args)) FAIL(err)
#define OP_NEWDICT0(r,err)         if (!(r=PyDict_New())) FAIL(err)
#define OP_NEWDICT(args,r,err)     if (!(r=PyDict_Pack args)) FAIL(err)
#define OP_NEWTUPLE(args,r,err)    if (!(r=PyTuple_Pack args)) FAIL(err)

/*** argument parsing ***/

#define OP_DECODE_ARG(fname, pos, name, vargs, vkwds, r, err)	\
	if (!(r=decode_arg(fname, pos, name, vargs, vkwds, NULL))) FAIL(err)
#define OP_DECODE_ARG_DEF(fname, pos, name, vargs, vkwds, def, r, err)	\
	if (!(r=decode_arg(fname, pos, name, vargs, vkwds, def))) FAIL(err)
#define OP_CHECK_NO_MORE_ARG(fname, n, vargs, r, err)	\
	if (check_no_more_arg(fname, n, vargs) < 0) FAIL(err)

/*** conversions, reference counting ***/

#define OP_INCREF_pyobj(o)          Py_INCREF(o);
#define OP_DECREF_pyobj(o)          Py_DECREF(o);
#define CONV_TO_OBJ_pyobj(o)        ((void)Py_INCREF(o), o)
#define CONV_FROM_OBJ_pyobj(o)      ((void)Py_INCREF(o), o)

#define OP_INCREF_borrowedpyobj(o)  /* nothing */
#define OP_DECREF_borrowedpyobj(o)  /* nothing */
