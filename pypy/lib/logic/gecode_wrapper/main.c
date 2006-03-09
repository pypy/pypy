/* -*- c-style: stroustrup -*-
 */

#include <stdio.h>
#include <stdlib.h>
#include "gecode_wrap.h"

	enum IntRelType {
		IRT_EQ, ///< Equality (\f$=\f$)
		IRT_NQ, ///< Disequality (\f$\neq\f$)
		IRT_LQ, ///< Less or equal (\f$\leq\f$)
		IRT_LE, ///< Less (\f$<\f$)
		IRT_GQ, ///< Greater or equal (\f$\geq\f$)
		IRT_GR  ///< Greater (\f$>\f$)
	};


int main( int argc, char** argv )
{
    int coefs[2] = { 1, -1};
    int q[2];
    int n;
    void *spc, *engine, *sol;
    int* vars, *res;
    int i,j;
    int nsol = 0;

    if (argc<2) {
	printf( "reines N\n" );
	exit(1);
    }
    n = atoi(argv[1]);
 
    spc = new_space();
    vars = (int*)malloc(n*sizeof(int));
    res = (int*)malloc(n*sizeof(int));

    for(i=0;i<n;++i) {
	int v;
	v = new_int_var(spc, 0, 0, n-1);
	vars[i] = v ;
    }

    space_alldiff( spc, n, vars );

    for(i=0;i<n;++i) {
	for( j=i+1; j<n; ++j ) {
	    /* */
	    q[0] = i;
	    q[1] = j;
	    space_linear( spc, 2, coefs, q, IRT_NQ, i-j );
	    space_linear( spc, 2, coefs, q, IRT_NQ, j-i );
	}
    }
    space_branch(spc);

    engine = new_dfs( spc, 5, 2 );

    printf("Sols\n");
    while (sol=search_next(engine)) {
//	sol->print_vars();
	nsol++;
	if (nsol%100==0) {
	    printf("sol:%d\n", nsol );
	    space_values( sol, n, vars, res );
	    for(j=0;j<n;++j) {
		    printf("% 5d ", res[j]);
	    }
	    printf("\n");
	}

	space_release(sol);
    }
    printf("NB sols:%d\n", nsol );

    free(vars);
}
