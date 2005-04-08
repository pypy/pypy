
/************************************************************/
 /***  C header subsection: containers data structures     ***/


#define OP_TUPLE_NEW(r,err)   /* r is a struct, can be left uninitialized */
#define OP_TUPLE_GETITEM(s,i,r,err)    r = s.f##i;
#define OP_TUPLE_SETITEM(s,i,o,r,err)  s.f##i = o;  r = 0;

#define OP_PYTUPLE_GETITEM(t,i,r,err)  if (!(r=PyTuple_GetItem(t,i))) FAIL(err)
#define OP_PYTUPLE_SETITEM(t,i,o,r,err) \
		if (PyTuple_SetItem(t,i,o)) FAIL(err) else r = 0;
