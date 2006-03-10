
#include "gecode_wrap.h"
#include "space_wrap.hh"


void* new_space()
{
	return (void*) new MySpace();
}

int new_int_var( void* spc, int is_temp, int _min, int _max )
{
	MySpace* _spc = static_cast<MySpace*>(spc);
	return _spc->intVar( is_temp, _min, _max );
}

void space_alldiff( void* spc, int n, int* vars )
{
	MySpace* _spc = static_cast<MySpace*>(spc);
	_spc->alldiff( vars, vars+n );
}

void space_linear( void* spc, int n, int* coefs, int* vars,
	     int type, int val )
{
	MySpace* _spc = static_cast<MySpace*>(spc);
	_spc->linear( coefs, coefs+n, vars, vars+n, (IntRelType)type, val );
}

void space_branch( void* spc )
{
	MySpace* _spc = static_cast<MySpace*>(spc);
	_spc->branch();
}

void* new_dfs( void* spc, int d_c, int d_a )
{
	MySpace* _spc = static_cast<MySpace*>(spc);
	return new MyDFSEngine( _spc, d_c, d_a );
}

void* search_next( void* search )
{
	MySearchEngine* _eng = static_cast<MySearchEngine*>(search);
	return _eng->next();
}


void space_values( void* spc, int n, int* vars, int* values )
{
	MySpace* _spc = static_cast<MySpace*>(spc);
	_spc->int_values( n, vars, values );
}

void space_release( void* spc )
{
	MySpace* _spc = static_cast<MySpace*>(spc);
	delete _spc;
}



void* new_propagator( void* spc, PropagatorCallback cb )
{
    MySpace* _spc = static_cast<MySpace*>(spc);
    return (void*)new (_spc) MyPropagator(_spc, cb);
}

int propagator_create_int_view( void* prp, int var )
{
    MyPropagator* _prp = static_cast<MyPropagator*>(prp);
    return _prp->add_int_view( var );
}

int int_view_lq( void* prp, int view, int value )
{
    MyPropagator* _prp = static_cast<MyPropagator*>(prp);
    IntView& _view = _prp->get_int_view( view );
    return _view.lq( _prp->home, value );
} 

int int_view_gq( void* prp, int view, int value )
{
    MyPropagator* _prp = static_cast<MyPropagator*>(prp);
    IntView& _view = _prp->get_int_view( view );
    return _view.gq( _prp->home, value );
} 

int int_view_min( void* prp, int view )
{
    MyPropagator* _prp = static_cast<MyPropagator*>(prp);
    IntView& _view = _prp->get_int_view( view );
    return _view.min();
} 

int int_view_max( void* prp, int view )
{
    MyPropagator* _prp = static_cast<MyPropagator*>(prp);
    IntView& _view = _prp->get_int_view( view );
    return _view.max( );
} 

int int_view_val( void* prp, int view )
{
    MyPropagator* _prp = static_cast<MyPropagator*>(prp);
    IntView& _view = _prp->get_int_view( view );
    return _view.val( );
} 

int int_view_assigned( void* prp, int view )
{
    MyPropagator* _prp = static_cast<MyPropagator*>(prp);
    IntView& _view = _prp->get_int_view( view );
    return _view.assigned( );
}

