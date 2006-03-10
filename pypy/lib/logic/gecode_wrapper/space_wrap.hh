

#ifndef SPACE_WRAP__HH
#define SPACE_WRAP__HH


#include <vector>
#include <iostream>
#include <stdlib.h>
#include <exception>
#include "kernel.hh"
#include "int.hh"
#include "search.hh"
#include "gecode_wrap.h"

/*
 */
using namespace Gecode;
using namespace Gecode::Int;
using namespace std;

class Unimplemented : public exception {};

class MySpace : public Space {
public:
    MySpace() {}

    int intVar( bool temp, int _min, int _max ) {
	if (!temp) {
	    _int_vars.push_back( IntVar(this, _min, _max) );
	    return _int_vars.size()-1;
	} else {
	    throw Unimplemented();
	}
    }

    void alldiff( int* begin, int*end )
    {
	IntVarArgs vars( end-begin );
	for(int* i=begin;i!=end;++i) {
	    vars[i-begin] = _int_vars[*i];
	}
	distinct( this, vars );
    }

    void linear( int* cb, int* ce, int* vb, int* ve, IntRelType reltype, int val )
    {
	IntArgs c(ce-cb);
	IntVarArgs v(ve-vb);

	for(int* i=cb;i!=ce;++i) {
	    c[i-cb]=*i;
	}
	for(int* j=vb;j!=ve;++j) {
	    v[j-vb]=_int_vars[*j];
	}
	Gecode::linear(this, c, v, reltype, val );
    }

    void branch()
    {
	IntVarArgs v(_int_vars.size());
	for(int i=0;i<_int_vars.size();++i) {
	    v[i] = _int_vars[i];
	}
	Gecode::branch(this, v, BVAR_SIZE_MIN, BVAL_MIN);
    }


    void int_values( int n, int* vars, int* values )
    {
	for(int i=0;i<n;++i) {
	    int val;
	    cout << _int_vars[vars[i]] << " ";
	    val = _int_vars[vars[i]].val(); // ???
	    values[i] = val;
	}
	cout << endl;
    }

    /// Constructor for cloning \a s
    MySpace(bool share, MySpace& s) : Space(share,s), _int_vars(s._int_vars.size()) {
	vector<IntVar>::iterator its,itd;
	for(itd=_int_vars.begin(),its=s._int_vars.begin();itd!=_int_vars.end();++itd,++its) {
	    itd->update(this, share, *its);
	}
    }
    
    /// Perform copying during cloning
    virtual Space* copy(bool share) {
	return new MySpace(share,*this);
    }
    
    
    void print_vars() {
	for(int i=0;i<_int_vars.size();++i)
	    cout << _int_vars[i] << " ";
	cout << endl;
    }

    IntVar& get_int_var( int n ) { return _int_vars[n]; }

protected:
    vector< IntVar >  _int_vars;

};


class MySearchEngine {
public:
    virtual MySpace* next() = 0;
};

class MyDFSEngine : public MySearchEngine {
public:
    MyDFSEngine( MySpace* spc, int c_d, int c_a ):dfs(spc,c_d,c_a) {}
    virtual MySpace* next() { return dfs.next(); }
protected:
    DFS<MySpace> dfs;
};


typedef vector<IntView> IntViewVect;
typedef IntViewVect::const_iterator IntViewVectConstIterator;
typedef IntViewVect::iterator IntViewVectIterator;

class MyPropagator : public Propagator {
public:
    MyPropagator(MySpace* home, PropagatorCallback cb );
    MyPropagator(Space* home, bool share, MyPropagator& p);
    virtual ExecStatus 	propagate (Space *);
    virtual PropCost 	cost (void) const;
    Actor* copy(Space* home, bool share);
    ExecStatus post(Space* home);

    int add_int_view( int var );
    IntView& get_int_view( int view ) { return _int_views[view]; }

    MySpace* home;
protected:
    IntViewVect _int_views;
    PropagatorCallback _cb;
};



#endif
