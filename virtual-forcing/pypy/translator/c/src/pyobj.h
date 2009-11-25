
/************************************************************/
 /***  C header subsection: untyped operations             ***/
  /***  as OP_XXX() macros calling the CPython API          ***/


#define op_bool(r,what) { \
		int _retval = what; \
		if (_retval < 0) {CFAIL(); } \
                else                         \
                    r = PyBool_FromLong(_retval); \
	}

#define op_richcmp(x,y,r,dir) \
					if (!(r=PyObject_RichCompare(x,y,dir))) CFAIL()
#define OP_LT(x,y,r)  op_richcmp(x,y,r, Py_LT)
#define OP_LE(x,y,r)  op_richcmp(x,y,r, Py_LE)
#define OP_EQ(x,y,r)  op_richcmp(x,y,r, Py_EQ)
#define OP_NE(x,y,r)  op_richcmp(x,y,r, Py_NE)
#define OP_GT(x,y,r)  op_richcmp(x,y,r, Py_GT)
#define OP_GE(x,y,r)  op_richcmp(x,y,r, Py_GE)

#define OP_IS_(x,y,r) op_bool(r,(x == y))

#define OP_IS_TRUE(x,r) op_bool(r,PyObject_IsTrue(x))
#define OP_NONZERO(x,r) op_bool(r,PyObject_IsTrue(x))

#define OP_LEN(x,r) do { \
		int _retval = PyObject_Size(x);  \
		if (_retval < 0) { CFAIL(); }    \
                else                             \
                    r = PyInt_FromLong(_retval); \
	} while (0)
#define OP_NEG(x,r)           if (!(r=PyNumber_Negative(x)))     CFAIL()
#define OP_POS(x,r)           if (!(r=PyNumber_Positive(x)))     CFAIL()
#define OP_INVERT(x,r)        if (!(r=PyNumber_Invert(x)))       CFAIL()
#define OP_ABS(x,r)           if (!(r=PyNumber_Absolute(x)))     CFAIL()

#define OP_ADD(x,y,r)         if (!(r=PyNumber_Add(x,y)))        CFAIL()
#define OP_SUB(x,y,r)         if (!(r=PyNumber_Subtract(x,y)))   CFAIL()
#define OP_MUL(x,y,r)         if (!(r=PyNumber_Multiply(x,y)))   CFAIL()
#define OP_TRUEDIV(x,y,r)     if (!(r=PyNumber_TrueDivide(x,y))) CFAIL()
#define OP_FLOORDIV(x,y,r)    if (!(r=PyNumber_FloorDivide(x,y)))CFAIL()
#define OP_DIV(x,y,r)         if (!(r=PyNumber_Divide(x,y)))     CFAIL()
#define OP_MOD(x,y,r)         if (!(r=PyNumber_Remainder(x,y)))  CFAIL()
#define OP_DIVMOD(x,y,r)      if (!(r=PyNumber_Divmod(x,y)))     CFAIL()
#define OP_POW(x,y,z,r)       if (!(r=PyNumber_Power(x,y,z)))    CFAIL()
#define OP_LSHIFT(x,y,r)      if (!(r=PyNumber_Lshift(x,y)))     CFAIL()
#define OP_RSHIFT(x,y,r)      if (!(r=PyNumber_Rshift(x,y)))     CFAIL()
#define OP_AND_(x,y,r)        if (!(r=PyNumber_And(x,y)))        CFAIL()
#define OP_OR_(x,y,r)         if (!(r=PyNumber_Or(x,y)))         CFAIL()
#define OP_XOR(x,y,r)         if (!(r=PyNumber_Xor(x,y)))        CFAIL()

#define OP_INPLACE_ADD(x,y,r) if (!(r=PyNumber_InPlaceAdd(x,y)))        \
								     CFAIL()
#define OP_INPLACE_SUB(x,y,r) if (!(r=PyNumber_InPlaceSubtract(x,y)))   \
								     CFAIL()
#define OP_INPLACE_MUL(x,y,r) if (!(r=PyNumber_InPlaceMultiply(x,y)))   \
								     CFAIL()
#define OP_INPLACE_TRUEDIV(x,y,r) if (!(r=PyNumber_InPlaceTrueDivide(x,y)))\
								     CFAIL()
#define OP_INPLACE_FLOORDIV(x,y,r)if(!(r=PyNumber_InPlaceFloorDivide(x,y)))\
								     CFAIL()
#define OP_INPLACE_DIV(x,y,r) if (!(r=PyNumber_InPlaceDivide(x,y)))        \
								     CFAIL()
#define OP_INPLACE_MOD(x,y,r) if (!(r=PyNumber_InPlaceRemainder(x,y)))     \
								     CFAIL()
#define OP_INPLACE_POW(x,y,r) if (!(r=PyNumber_InPlacePower(x,y,Py_None))) \
								     CFAIL()
#define OP_INPLACE_LSHIFT(x,y,r) if (!(r=PyNumber_InPlaceLshift(x,y)))     \
								     CFAIL()
#define OP_INPLACE_RSHIFT(x,y,r) if (!(r=PyNumber_InPlaceRshift(x,y)))     \
								     CFAIL()
#define OP_INPLACE_AND(x,y,r)    if (!(r=PyNumber_InPlaceAnd(x,y)))        \
								     CFAIL()
#define OP_INPLACE_OR(x,y,r)     if (!(r=PyNumber_InPlaceOr(x,y)))         \
								     CFAIL()
#define OP_INPLACE_XOR(x,y,r)    if (!(r=PyNumber_InPlaceXor(x,y)))        \
								     CFAIL()

#define OP_GETITEM(x,y,r)    if (!(r=PyObject_GetItem1(x,y)))   CFAIL()
#define OP_SETITEM(x,y,z,r)  if ((PyObject_SetItem1(x,y,z))<0)  {CFAIL(); }\
                             else                                       \
				  r=Py_None; Py_INCREF(r)
#define OP_DELITEM(x,y,r)    if ((PyObject_DelItem(x,y))<0)     CFAIL();\
				  r=Py_None; Py_INCREF(r)
#define OP_CONTAINS(x,y,r)    op_bool(r,(PySequence_Contains(x,y)))

#define OP_GETATTR(x,y,r)    if (!(r=PyObject_GetAttr(x,y)))    CFAIL()
#define OP_SETATTR(x,y,z,r)  if ((PyObject_SetAttr(x,y,z))<0)   {CFAIL();}\
                             else                                       \
				  r=Py_None; Py_INCREF(r)
#define OP_DELATTR(x,y,r)    if ((PyObject_SetAttr(x,y,NULL))<0) {CFAIL();}\
                             else                                       \
				  r=Py_None; Py_INCREF(r)

#define OP_NEWSLICE(x,y,z,r) if (!(r=PySlice_New(x,y,z)))       CFAIL()

#define OP_GETSLICE(x,y,z,r)  {		         			\
		PyObject *__yo = y, *__zo = z;				\
		int __y = 0, __z = INT_MAX;				\
		if (__yo == Py_None) __yo = NULL;			\
		if (__zo == Py_None) __zo = NULL;			\
		if (!_PyEval_SliceIndex(__yo, &__y) ||			\
		    !_PyEval_SliceIndex(__zo, &__z) ||			\
		    !(r=PySequence_GetSlice(x, __y, __z))) CFAIL();	\
	}

#define OP_ALLOC_AND_SET(x,y,r) { \
		/* XXX check for long/int overflow */ \
		int __i, __x = PyInt_AsLong(x); \
		if (PyErr_Occurred()) CFAIL(); \
                else {                         \
                    if (!(r = PyList_New(__x))) CFAIL(); \
                    else {   \
                        for (__i=0; __i<__x; __i++) { \
                                Py_INCREF(y); \
                                PyList_SET_ITEM(r, __i, y); \
                        } \
                    } \
                } \
	}

#define OP_ITER(x,r)          if (!(r=PyObject_GetIter(x)))      CFAIL()
#define OP_NEXT(x,r)          if (!(r=PyIter_Next(x))) {                   \
		if (!PyErr_Occurred()) PyErr_SetNone(PyExc_StopIteration);     \
		CFAIL();                                                    \
	}

#define OP_STR(x,r)           if (!(r=PyObject_Str(x)))          CFAIL()
#define OP_REPR(x,r)          if (!(r=PyObject_Repr(x)))         CFAIL()
#define OP_ORD(s,r) { \
	char *__c = PyString_AsString(s); \
	int __len; \
	if ( !__c) CFAIL(); \
        else { \
            if ((__len = PyString_GET_SIZE(s)) != 1) { \
                PyErr_Format(PyExc_TypeError, \
                      "ord() expected a character, but string of length %d found", \
                      __len); \
                CFAIL(); \
            } \
            else if (!(r = PyInt_FromLong((unsigned char)(__c[0])))) \
                { CFAIL(); }\
        } \
    }
#define OP_ID(x,r)    if (!(r=PyLong_FromVoidPtr(x))) CFAIL()
#define OP_HASH(x,r)  { \
	long __hash = PyObject_Hash(x); \
	if (__hash == -1 && PyErr_Occurred()) CFAIL(); \
        else if (!(r = PyInt_FromLong(__hash))) { CFAIL(); } \
    }

#define OP_HEX(x,r)   { \
	PyNumberMethods *__nb; \
	if ((__nb = x->ob_type->tp_as_number) == NULL || \
	    __nb->nb_hex == NULL) { \
		PyErr_SetString(PyExc_TypeError, \
			   "hex() argument can't be converted to hex"); \
		CFAIL(); \
	} \
        else if (!(r = (*__nb->nb_hex)(x))) { CFAIL(); } \
    }
#define OP_OCT(x,r)   { \
	PyNumberMethods *__nb; \
	if ((__nb = x->ob_type->tp_as_number) == NULL || \
	    __nb->nb_oct == NULL) { \
		PyErr_SetString(PyExc_TypeError, \
			   "oct() argument can't be converted to oct"); \
		CFAIL(); \
	} \
        else if (!(r = (*__nb->nb_oct)(x))) { CFAIL(); } \
    }

#define OP_INT(x,r)   { \
	long __val = PyInt_AsLong(x); \
	if (__val == -1 && PyErr_Occurred()) CFAIL(); \
        else if (!(r = PyInt_FromLong(__val))) { CFAIL (); } \
    }
#define OP_FLOAT(x,r)   { \
	double __val = PyFloat_AsDouble(x); \
	if (PyErr_Occurred()) CFAIL(); \
        else if (!(r = PyFloat_FromDouble(__val))) { CFAIL (); } \
    }

#define OP_CMP(x,y,r)   { \
	int __val = PyObject_Compare(x, y); \
	if (PyErr_Occurred()) CFAIL(); \
        else if (!(r = PyInt_FromLong(__val))) { CFAIL (); }\
    }


#define OP_SIMPLE_CALL(args,r) if (!(r=PyObject_CallFunctionObjArgs args)) \
					CFAIL()
#define OP_CALL_ARGS(args,r)   if (!(r=CallWithShape args))    CFAIL()

/* Needs to act like getattr(x, '__class__', type(x)) */
#define OP_TYPE(x,r) { \
		PyObject *o = x; \
		if (PyInstance_Check(o)) { \
			r = (PyObject*)(((PyInstanceObject*)o)->in_class); \
		} else { \
			r = (PyObject*)o->ob_type; \
		} \
		Py_INCREF(r); \
	}

/* Needs to act like instance(x,y) */
#define OP_ISSUBTYPE(x,y,r)  \
		op_bool(r,PyObject_IsSubclass(x, y))


/*** operations with a variable number of arguments ***/

#define OP_NEWLIST0(r)         if (!(r=PyList_New(0))) CFAIL()
#define OP_NEWLIST(args,r)     if (!(r=PyList_Pack args)) CFAIL()
#define OP_NEWDICT0(r)         if (!(r=PyDict_New())) CFAIL()
#define OP_NEWDICT(args,r)     if (!(r=PyDict_Pack args)) CFAIL()
#define OP_NEWTUPLE(args,r)    if (!(r=PyTuple_Pack args)) CFAIL()

unsigned long long RPyLong_AsUnsignedLongLong(PyObject *v);
long long RPyLong_AsLongLong(PyObject *v);

#ifndef PYPY_NOT_MAIN_FILE

#if (PY_VERSION_HEX < 0x02040000)

unsigned long RPyLong_AsUnsignedLong(PyObject *v) 
{
	if (PyInt_Check(v)) {
		long val = PyInt_AsLong(v);
		if (val < 0) {
			PyErr_SetNone(PyExc_OverflowError);
			return (unsigned long)-1;
		}
		return val;
        } else {
		return PyLong_AsUnsignedLong(v);
	}
}

#else
#define RPyLong_AsUnsignedLong PyLong_AsUnsignedLong
#endif


unsigned long long RPyLong_AsUnsignedLongLong(PyObject *v)
{
	if (PyInt_Check(v))
		return PyInt_AsLong(v);
	else
		return PyLong_AsUnsignedLongLong(v);
}

long long RPyLong_AsLongLong(PyObject *v)
{
	if (PyInt_Check(v))
		return PyInt_AsLong(v);
	else
		return PyLong_AsLongLong(v);
}

#endif
