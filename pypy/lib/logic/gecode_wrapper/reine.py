

from ctypes import *

gecode = cdll.LoadLibrary("./libgecode_wrap.so")

IRT_NQ = 1
ES_FAILED          = -1 # < Execution has resulted in failure
ES_NOFIX           =  0 # < Propagation has not computed fixpoint
ES_OK              =  0 # < Execution is okay
ES_FIX             =  1 # < Propagation has computed fixpoint
ES_SUBSUMED        =  2 # < %Propagator is subsumed (entailed)


import sys

PROPCB = CFUNCTYPE(c_int, c_void_p)

def null_propagator( prop ):
    x = gecode.int_view_assigned( prop, 0 )
    y = gecode.int_view_assigned( prop, 1 )
    print "Assigned", x, y
    return ES_OK


nullpropcb = PROPCB(null_propagator)


N = int(sys.argv[1])

spc = gecode.new_space()

Narray = c_int*N
Pair = c_int*2

queens = [ gecode.new_int_var( spc, 0, 0, N-1 ) for i in range(N) ]

qvars = Narray(*queens)

gecode.space_alldiff( spc, N, qvars )

coefs = Pair( 1, -1 )

for i in range(N):
    for j in range(i+1,N):
        qpair = Pair( i, j )
        gecode.space_linear( spc, 2, coefs, qpair, IRT_NQ, i-j )
        gecode.space_linear( spc, 2, coefs, qpair, IRT_NQ, j-i )


myprop = gecode.new_propagator( spc, nullpropcb )

gecode.propagator_create_int_view( myprop, 0 )
gecode.propagator_create_int_view( myprop, N-1 )


gecode.space_branch( spc )

engine = gecode.new_dfs( spc, 5, 2 )

result = Narray( *([0]*N ) )

nsol = 0
while 1:
    sol = gecode.search_next( engine )
    if not sol:
        break
    if nsol%1 == 0:
        print "Sol", nsol
        gecode.space_values( sol, N, qvars, result )
        for i in result:
            print i,
        print
    gecode.space_release( sol )
    nsol+=1

