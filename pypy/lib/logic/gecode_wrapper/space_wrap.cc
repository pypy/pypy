#include <vector>
#include <iostream>
#include <stdlib.h>
#include <exception>
#include "kernel.hh"
#include "int.hh"
#include "search.hh"

#include "space_wrap.hh"




class MyVar {
    virtual MyVar* copy();
};
/*
class MyIntVar : public MyVar {
public:
    MyIntVar( Space* spc, int _min, int _max ):_var(spc, _min, _max ) {}
    MyIntVar( Space* spc, MyIntVar& mvar ):_var( spc, mvar._var ) {}
protected:
    IntVar _var;
};
*/
enum {
    REL_EQ,
    REL_NQ,
};


class Index {};




void* new_dfs( MySpace* spc, int c_d, int c_a )
{
    return new MyDFSEngine( spc, c_d, c_a );
}



MyPropagator::MyPropagator(MySpace* _home, PropagatorCallback cb )
    : Propagator(_home), _cb(cb), home(_home)
{
}

ExecStatus
MyPropagator::post(Space* home) {
    /* post domain reduction done from python */
    return ES_OK;
}


MyPropagator::MyPropagator(Space* _home, bool share, MyPropagator& p)
    : Propagator(_home,share,p), home(static_cast<MySpace*>(_home)), _cb(p._cb)
{
    IntViewVectIterator it;
    for(it=p._int_views.begin();it!=p._int_views.end();++it) {
	_int_views.push_back( IntView() );
	_int_views.back().update(_home, share, *it );
    }
}

Actor*
MyPropagator::copy(Space* home, bool share) {
    return new (home) MyPropagator(home,share,*this);
}


ExecStatus
MyPropagator::propagate(Space* home) {
    ExecStatus status;
    status = (ExecStatus)_cb( this );
    return status;
}

int
MyPropagator::add_int_view( int var )
{
    IntVar& intvar = home->get_int_var( var );
    _int_views.push_back( IntView( intvar ) );
    _int_views.back().subscribe( home, this, PC_INT_BND );
    return _int_views.size()-1;
}

PropCost
MyPropagator::cost(void) const
{
    return PC_MAX;
}
