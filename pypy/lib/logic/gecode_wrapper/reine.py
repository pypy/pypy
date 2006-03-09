

from ctypes import *

gecode = cdll.LoadLibrary("./libgecode_wrap.so")

IRT_NQ = 1

import sys

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

gecode.space_branch( spc )

engine = gecode.new_dfs( spc, 5, 2 )

result = Narray( *([0]*N ) )

nsol = 0
while 1:
    sol = gecode.search_next( engine )
    if not sol:
        break
    if nsol%10 == 0:
        print "Sol", nsol
        gecode.space_values( sol, N, qvars, result )
        for i in result:
            print i,
        print
    gecode.space_release( sol )
    nsol+=1

