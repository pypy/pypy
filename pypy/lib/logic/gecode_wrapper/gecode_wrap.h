
#ifndef GECODE_WRAP_H
#define GECODE_WRAP_H

#ifdef __cplusplus
extern "C" {
#endif

	void* new_space();
	
	int new_int_var( void* spc, int is_temp, int _min, int _max );

	void space_alldiff( void* spc, int n, int* vars );

	void space_linear( void* spc, int n, int* coefs, int* vars,
			   int type, int val );

	void space_branch( void* spc );
	
	void* new_dfs( void* spc, int d_c, int d_a );

	void* search_next( void* search );

	void space_values( void* spc, int n, int* vars /*in*/, int* values /*out*/ );

	void space_release( void* spc );

	/* propagators */

	typedef int (*PropagatorCallback)(void*);
	void* new_propagator( void* spc, PropagatorCallback cb );

	int propagator_create_int_view( void* prp, int var );

	int int_view_lq( void* prp, int view, int value );
	int int_view_gq( void* prp, int view, int value );
	int int_view_min( void* prp, int view );
	int int_view_max( void* prp, int view );
	int int_view_val( void* prp, int view );
	int int_view_assigned( void* prp, int view );

#ifdef __cplusplus
};
#endif

#endif
