
/************************************************************/
 /***  C header subsection: generic operations on lists    ***/


#define OP_LIST_FASTGETITEM(s,i,r,err)    r = s->items[i];
#define OP_LIST_FASTSETITEM(s,i,o,r,err)  s->items[i] = o;  r = 0;
#define OP_LIST_SETCOUNT(s,n,r,err)   s->count = n;     r = 0;

#define OP_LIST_GETITEM(s,i,r,err)					      \
	if (((unsigned) i) >= s->count) {				      \
		PyErr_SetString(PyExc_IndexError, "list index out of range"); \
		FAIL(err)						      \
	}								      \
	r = s->items[i];

#define OP_LIST_SETITEM(s,i,o,r,err)					      \
	if (((unsigned) i) >= s->count) {				      \
		PyErr_SetString(PyExc_IndexError, "list index out of range"); \
		FAIL(err)						      \
	}								      \
	s->items[i] = o;						      \
	r = 0;
