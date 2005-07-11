/************************************************************/
/***  C header subsection: operations between chars       ***/

/*** unary operations ***/

/***  binary operations ***/

/* typedef unsigned pypy_unichar; */
#define OP_UNICHAR_EQ(x,y,r,err)	 r = ((x) == (y));
#define OP_UNICHAR_NE(x,y,r,err)	 r = ((x) != (y));

