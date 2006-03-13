#ifndef GECODE_WRAP_HH
#define GECODE_WRAP_HH

#include <vector>
#include "kernel.hh"
#include "int.hh"
#include "search.hh"
#include "py_gecode_types.hh"

class PySpace;

class PyVar {
public:
    PyVar() {}
    virtual update();
};

%(var_subclasses_decl)s

class PySpace : public Gecode::Space {
public:
    PySpace() {}

    PySpace( bool share, PySpace& s ):Space(share,s),
				      vars(s.vars.size())
    {
	var_vector_iterator its, itd;
	for( its=s.vars.begin(), itd=vars.begin();itd!=vars.end(); ++its,++itd ) {
	    itd->update( this, share, *its );
	}
    }

    %(var_factories_decl)s

    %(var_propagators_decl)s


    virtual Space* copy( bool share ) {
	return new PySpace( share, *this );
    }
protected:
    var_vector  vars;
};


#endif GECODE_WRAP_HH
