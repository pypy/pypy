
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

#ifdef __cplusplus
};
#endif

#endif
