/************************************************************/
/***  C header subsection: operations between addresses   ***/

/*** unary operations ***/

/***  binary operations ***/

#define OP_ADR_DELTA(x,y,r,err) r = ((x) - (y))
#define OP_ADR_SUB(x,y,r,err)   r = ((x) - (y))
#define OP_ADR_ADD(x,y,r,err)   r = ((x) + (y))

#define OP_ADR_EQ(x,y,r,err)	  r = ((x) == (y))
#define OP_ADR_NE(x,y,r,err)	  r = ((x) != (y))
#define OP_ADR_LE(x,y,r,err)	  r = ((x) <= (y))
#define OP_ADR_GT(x,y,r,err)	  r = ((x) >  (y))
#define OP_ADR_LT(x,y,r,err)	  r = ((x) <  (y))
#define OP_ADR_GE(x,y,r,err)	  r = ((x) >= (y))

