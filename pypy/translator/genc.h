
/************************************************************/
 /***  Generic C header section                            ***/

#include <Python.h>
#include <structmember.h>


#define op_richcmp(x,y,r,err,dir)   \
                       if (!(r=PyObject_RichCompare(x,y,dir))) goto err;
#define OP_LT(x,y,r,err)  op_richcmp(x,y,r,err, Py_LT)
#define OP_LE(x,y,r,err)  op_richcmp(x,y,r,err, Py_LE)
#define OP_EQ(x,y,r,err)  op_richcmp(x,y,r,err, Py_EQ)
#define OP_NE(x,y,r,err)  op_richcmp(x,y,r,err, Py_NE)
#define OP_GT(x,y,r,err)  op_richcmp(x,y,r,err, Py_GT)
#define OP_GE(x,y,r,err)  op_richcmp(x,y,r,err, Py_GE)

#define OP_IS_TRUE(x,r,err)	switch (PyObject_IsTrue(x)) {	\
				case 0: r=Py_False; break;	\
				case 1: r=Py_True;  break;	\
				default: goto err;		\
				}				\
				Py_INCREF(r);

#define OP_NEG(x,r,err)           if (!(r=PyNumber_Negative(x)))     goto err;
#define OP_POS(x,r,err)           if (!(r=PyNumber_Positive(x)))     goto err;
#define OP_INVERT(x,r,err)        if (!(r=PyNumber_Invert(x)))       goto err;

#define OP_ADD(x,y,r,err)         if (!(r=PyNumber_Add(x,y)))        goto err;
#define OP_SUB(x,y,r,err)         if (!(r=PyNumber_Subtract(x,y)))   goto err;
#define OP_MUL(x,y,r,err)         if (!(r=PyNumber_Multiply(x,y)))   goto err;
#define OP_TRUEDIV(x,y,r,err)     if (!(r=PyNumber_TrueDivide(x,y))) goto err;
#define OP_FLOORDIV(x,y,r,err)    if (!(r=PyNumber_FloorDivide(x,y)))goto err;
#define OP_DIV(x,y,r,err)         if (!(r=PyNumber_Divide(x,y)))     goto err;
#define OP_MOD(x,y,r,err)         if (!(r=PyNumber_Remainder(x,y)))  goto err;
#define OP_POW(x,y,r,err)         if (!(r=PyNumber_Power(x,y,Py_None)))goto err;
#define OP_LSHIFT(x,y,r,err)      if (!(r=PyNumber_Lshift(x,y)))     goto err;
#define OP_RSHIFT(x,y,r,err)      if (!(r=PyNumber_Rshift(x,y)))     goto err;
#define OP_AND_(x,y,r,err)        if (!(r=PyNumber_And(x,y)))        goto err;
#define OP_OR_(x,y,r,err)         if (!(r=PyNumber_Or(x,y)))         goto err;
#define OP_XOR(x,y,r,err)         if (!(r=PyNumber_Xor(x,y)))        goto err;

#define OP_INPLACE_ADD(x,y,r,err) if (!(r=PyNumber_InPlaceAdd(x,y)))           \
								     goto err;
#define OP_INPLACE_SUB(x,y,r,err) if (!(r=PyNumber_InPlaceSubtract(x,y)))      \
								     goto err;
#define OP_INPLACE_MUL(x,y,r,err) if (!(r=PyNumber_InPlaceMultiply(x,y)))      \
								     goto err;
#define OP_INPLACE_TRUEDIV(x,y,r,err) if (!(r=PyNumber_InPlaceTrueDivide(x,y)))\
								     goto err;
#define OP_INPLACE_FLOORDIV(x,y,r,err)if(!(r=PyNumber_InPlaceFloorDivide(x,y)))\
								     goto err;
#define OP_INPLACE_DIV(x,y,r,err) if (!(r=PyNumber_InPlaceDivide(x,y)))        \
								     goto err;
#define OP_INPLACE_MOD(x,y,r,err) if (!(r=PyNumber_InPlaceRemainder(x,y)))     \
								     goto err;
#define OP_INPLACE_POW(x,y,r,err) if (!(r=PyNumber_InPlacePower(x,y,Py_None))) \
								     goto err;
#define OP_INPLACE_LSHIFT(x,y,r,err) if (!(r=PyNumber_InPlaceLshift(x,y)))     \
								     goto err;
#define OP_INPLACE_RSHIFT(x,y,r,err) if (!(r=PyNumber_InPlaceRshift(x,y)))     \
								     goto err;
#define OP_INPLACE_AND(x,y,r,err)    if (!(r=PyNumber_InPlaceAnd(x,y)))        \
								     goto err;
#define OP_INPLACE_OR(x,y,r,err)     if (!(r=PyNumber_InPlaceOr(x,y)))         \
								     goto err;
#define OP_INPLACE_XOR(x,y,r,err)    if (!(r=PyNumber_InPlaceXor(x,y)))        \
								     goto err;

#define OP_GETITEM(x,y,r,err)     if (!(r=PyObject_GetItem1(x,y)))   goto err;
#define OP_SETITEM(x,y,z,r,err)   if ((PyObject_SetItem1(x,y,z))<0)  goto err; \
				  r=Py_None; Py_INCREF(r);

#define OP_GETATTR(x,y,r,err)     if (!(r=PyObject_GetAttr(x,y)))    goto err;
#define OP_SETATTR(x,y,z,r,err)   if ((PyObject_SetAttr(x,y,z))<0)   goto err; \
				  r=Py_None; Py_INCREF(r);
#define OP_DELATTR(x,y,r,err)     if ((PyObject_SetAttr(x,y,NULL))<0)goto err; \
				  r=Py_None; Py_INCREF(r);

#define OP_NEWSLICE(x,y,z,r,err)  if (!(r=PySlice_New(x,y,z)))       goto err;


/*** tests ***/

#define EQ_False(o)     (o == Py_False)
#define EQ_True(o)      (o == Py_True)
#define EQ_0(o)         (PyInt_Check(o) && PyInt_AS_LONG(o)==0)
#define EQ_1(o)         (PyInt_Check(o) && PyInt_AS_LONG(o)==1)


/*** misc ***/

  /* XXX exceptions not implemented */
#define OP_EXCEPTION(x,r,err)  r=Py_None; Py_INCREF(r);

#define MOVE(x, y)             y = x;

#define INITCHK(expr)          if (!(expr)) return;


/*** classes ***/

#define SETUP_CLASS(t, name, base)				\
	t = PyObject_CallFunction((PyObject*) &PyType_Type,	\
				  "s(O){}", name, base)

#define SETUP_CLASS_ATTR(t, attr, value)	\
	(PyObject_SetAttrString(t, attr, value) >= 0)

/* we need a subclass of 'builtin_function_or_method' which can be used
   as methods: builtin function objects that can be bound on instances */
static PyObject *
gencfunc_descr_get(PyObject *func, PyObject *obj, PyObject *type)
{
	if (obj == Py_None)
		obj = NULL;
	return PyMethod_New(func, obj, type);
}
static PyTypeObject PyGenCFunction_Type = {
	PyObject_HEAD_INIT(NULL)
	0,
	"pypy_generated_function",
	sizeof(PyCFunctionObject),
	0,
	0,					/* tp_dealloc */
	0,					/* tp_print */
	0,					/* tp_getattr */
	0,					/* tp_setattr */
	0,					/* tp_compare */
	0,					/* tp_repr */
	0,					/* tp_as_number */
	0,					/* tp_as_sequence */
	0,					/* tp_as_mapping */
	0,					/* tp_hash */
	0,					/* tp_call */
	0,					/* tp_str */
	0,					/* tp_getattro */
	0,					/* tp_setattro */
	0,					/* tp_as_buffer */
	Py_TPFLAGS_DEFAULT,			/* tp_flags */
	0,					/* tp_doc */
	0,					/* tp_traverse */
	0,					/* tp_clear */
	0,					/* tp_richcompare */
	0,					/* tp_weaklistoffset */
	0,					/* tp_iter */
	0,					/* tp_iternext */
	0,					/* tp_methods */
	0,					/* tp_members */
	0,					/* tp_getset */
	/*&PyCFunction_Type set below*/ 0,	/* tp_base */
	0,					/* tp_dict */
	gencfunc_descr_get,			/* tp_descr_get */
	0,					/* tp_descr_set */
};

#define SETUP_MODULE						\
	PyGenCFunction_Type.tp_base = &PyCFunction_Type;	\
	PyType_Ready(&PyGenCFunction_Type);


/*** operations with a variable number of arguments ***/

#define OP_NEWLIST0(r,err)         if (!(r=PyList_New(0))) goto err;
#define OP_NEWLIST(args,r,err)     if (!(r=PyList_Pack args)) goto err;
#define OP_NEWTUPLE(args,r,err)    if (!(r=PyTuple_Pack args)) goto err;
#define OP_SIMPLE_CALL(args,r,err) if (!(r=PyObject_CallFunctionObjArgs args)) \
					goto err;

static PyObject* PyList_Pack(int n, ...)
{
	int i;
	PyObject *o;
	PyObject *result;
	va_list vargs;

	va_start(vargs, n);
	result = PyList_New(n);
	if (result == NULL)
		return NULL;
	for (i = 0; i < n; i++) {
		o = va_arg(vargs, PyObject *);
		Py_INCREF(o);
		PyList_SET_ITEM(result, i, o);
	}
	va_end(vargs);
	return result;
}

#if PY_VERSION_HEX < 0x02040000   /* 2.4 */
static PyObject* PyTuple_Pack(int n, ...)
{
	int i;
	PyObject *o;
	PyObject *result;
	PyObject **items;
	va_list vargs;

	va_start(vargs, n);
	result = PyTuple_New(n);
	if (result == NULL)
		return NULL;
	items = ((PyTupleObject *)result)->ob_item;
	for (i = 0; i < n; i++) {
		o = va_arg(vargs, PyObject *);
		Py_INCREF(o);
		items[i] = o;
	}
	va_end(vargs);
	return result;
}
#endif

#if PY_VERSION_HEX >= 0x02030000   /* 2.3 */
# define PyObject_GetItem1  PyObject_GetItem
# define PyObject_SetItem1  PyObject_SetItem
#else
/* for Python 2.2 only */
static PyObject* PyObject_GetItem1(PyObject* obj, PyObject* index)
{
  int start, stop, step;
  if (!PySlice_Check(index))
    return PyObject_GetItem(obj, index);
  if (((PySliceObject*) index)->start == Py_None)
    start = -INT_MAX-1;
  else
    {
      start = PyInt_AsLong(((PySliceObject*) index)->start);
      if (start == -1 && PyErr_Occurred()) return NULL;
    }
  if (((PySliceObject*) index)->stop == Py_None)
    stop = INT_MAX;
  else
    {
      stop = PyInt_AsLong(((PySliceObject*) index)->stop);
      if (stop == -1 && PyErr_Occurred()) return NULL;
    }
  if (((PySliceObject*) index)->step != Py_None)
    {
      step = PyInt_AsLong(((PySliceObject*) index)->step);
      if (step == -1 && PyErr_Occurred()) return NULL;
      if (step != 1) {
        PyErr_SetString(PyExc_ValueError, "obj[slice]: no step allowed");
        return NULL;
      }
    }
  return PySequence_GetSlice(obj, start, stop);
}
static PyObject* PyObject_SetItem1(PyObject* obj, PyObject* index, PyObject* v)
{
  int start, stop, step;
  if (!PySlice_Check(index))
    return PyObject_SetItem(obj, index, v);
  if (((PySliceObject*) index)->start == Py_None)
    start = -INT_MAX-1;
  else
    {
      start = PyInt_AsLong(((PySliceObject*) index)->start);
      if (start == -1 && PyErr_Occurred()) return NULL;
    }
  if (((PySliceObject*) index)->stop == Py_None)
    stop = INT_MAX;
  else
    {
      stop = PyInt_AsLong(((PySliceObject*) index)->stop);
      if (stop == -1 && PyErr_Occurred()) return NULL;
    }
  if (((PySliceObject*) index)->step != Py_None)
    {
      step = PyInt_AsLong(((PySliceObject*) index)->step);
      if (step == -1 && PyErr_Occurred()) return NULL;
      if (step != 1) {
        PyErr_SetString(PyExc_ValueError, "obj[slice]: no step allowed");
        return NULL;
      }
    }
  return PySequence_SetSlice(obj, start, stop, v);
}
#endif


/************************************************************/
 /***  The rest is produced by genc.py                     ***/
