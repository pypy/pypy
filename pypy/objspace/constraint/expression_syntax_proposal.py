

#-- with a new expr construct (lambda on steroids)

def queens_problem(n):
    s = newspace()
    queens = []
    for i in range(n):
        queens.append(s.var('q%02d'%i,
                            FiniteDomain([(i,j)
                                          for i in range(n)
                                          for j in range(n)])))
    for i in range(n):
        for j in range(i,n):
            s.add(expr queens[i], queens[j]: queens[i][0] != queen[j][0])
            ## -> s.add(make_expression([queen[i], queen[j]],
            ##          '%s[0] != %s[0]'%[q.name for q in [queen[i], queen[j]])
            s.add(expr queens[i], queens[j]: queens[i][1] != queen[j][1])
    s.add(AllDistinct(queens))
    return s


#-- redefining python operators

class Variable:
    def __getitem__(self, key):
        return ViewVariable(self,
    def __neq__(self, other):
        return NotEqualConstraint(self, other)
    def __add__(self, other):
        pass
    def __radd__(self, other):
        pass


class QueensProblem(ComputationSpace):
    def __init__(self, n):
        vars =  [Variable(FiniteDomain([(i,j)
                                        for i in range(n)
                                        for j in range(n)])
                          )
                 for k in n]
        constraints = []
        for i in range(n):
            for j in range(i,n):
                constraint.append(vars[i][0] != vars[j][0])
        ComputationSpace.__init__(self, vars, constraints)
    
 
