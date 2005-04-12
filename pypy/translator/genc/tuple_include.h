
/************************************************************/
 /***  C header subsection: operations involving tuples    ***/


#define OP_TUPLE_NEW(r,err)   /* r is a struct, can be left uninitialized */
#define OP_TUPLE_GETITEM(s,i,r,err)    r = s.f##i;
#define OP_TUPLE_SETITEM(s,i,o,r,err)  s.f##i = o;  r = 0;
