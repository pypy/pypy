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

MySpace* search_next( void* _search )
{
    MySearchEngine* search = static_cast<MySearchEngine*>(_search);
    return search->next();
}


