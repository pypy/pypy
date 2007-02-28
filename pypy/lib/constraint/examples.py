from cclp import tell, distribute, make_expression, all_diff

# Queens

def queens1(size=8):
    variables = []
    for i in range(size):
        name = 'Q%02d'%i
        variables.append(domain([(i,j) for j in range(size)], name))

    for q1 in variables:
        for q2 in variables:
            if name_of(q1) < name_of(q2):
                tell(make_expression([q1,q2],
                                       '%(q1)s[0] < %(q2)s[0] and '
                                       '%(q1)s[1] != %(q2)s[1] and '
                                       'abs(%(q1)s[0]-%(q2)s[0]) != '
                                       'abs(%(q1)s[1]-%(q2)s[1])'%\
                                       {'q1':name_of(q1),'q2':name_of(q2)}))

    distribute('dichotomy')
    return variables


def queens2(size=8):
    variables = {}
    for i in range(size):
        name = 'Q%02d'%i
        variables[name] = domain(range(size), name)

    for r1 in range(size):
        for r2 in range(size):
            q1 = 'Q%02d' % r1
            q2 = 'Q%02d' % r2
            if r1 < r2:
                D = {'q1':q1,'q2':q2, 'r1' : r1, 'r2' : r2 }
                tell(make_expression([variables[q1],variables[q2]],
                                     '%(q1)s != %(q2)s and '
                                     'abs(%(r1)s-%(r2)s) != '
                                     'abs(%(q1)s-%(q2)s)'% D ))
    distribute('dichotomy')
    return variables.values()


def queens3(size=8,verbose=0):
    from constraint.chess import QueensConstraint
    variables = []

    for i in range(size):
        name = 'Q%02d'%i
        variables.append(domain([(i,j) for i in range(size)
                                 for j in range(size)], name))

    for q1 in variables:
        for q2 in variables:
            if name_of(q1) < name_of(q2):
                tell(QueensConstraint([q1,q2]))

    distribute('dichotomy')
    return variables


def draw_queens1_solution(s):
    "s is a solution list"
    size = len(s)
    queens = {}
    board = ''
    for p in s:
        queens[p] = True
    board += '_'*(size*2+1)+'\n'
    for i in range(size):
        for j in range(size):
            q = queens.get((i,j))
            if q is None:
                board+='|'+'·-'[(i+j)%2]
            else:
                board+='|Q'
        board+='|\n'
    board += '¯'*(size*2+1)
    print board

def draw_queens2_solution(s):
    size = len(s)
    board = ''
    queens = s.items()
    queens.sort()
    board += '_'*(size*2+1)+'\n'
    for i in range(size):
        qj = queens[i][1]
        for j in range(size):
            if j != qj:
                board+='|'+'·-'[(i+j)%2]
            else:
                board+='|Q'
        board+='|\n'
    board += '¯'*(size*2+1)
    print board


# Knights

def knight_tour(size=6):
    variables = {}
    #domains = {}
    #constraints = []
    black_checker=[]
    # the black tiles
    white_checker=[]
    #the white tiles: one less if n is odd
    for row in range(size):
        for column in range(size):
            if (row+column)%2==0:
                black_checker.append((row,column))
            else:
                white_checker.append((row, column))

    # One variable for each step in the tour
    for i in range(size*size):
        name = 'x%02d'%i
        #variables.append(name)
        # The knight's move jumps from black to white
        # and vice versa, so we make all the even steps black
        # and all the odd ones white.
        if i%2==0:
            variables[name] = domain(black_checker, name)
        else:
            variables[name] = domain(white_checker, name)
        if i > 0:
            j = i - 1
            k1 = 'x%02d'%j
            k2 = 'x%02d'%i
            # the knight's move constraint
            tell(make_expression([variables[k1], variables[k2]],
                                 'abs(%(v1)s[0]-%(v2)s[0]) + abs(%(v1)s[1]-%(v2)s[1]) == 3'%\
                                 {'v1':k1,'v2':k2}))
            tell(make_expression([variables[k1], variables[k2]],
                                 'abs(abs(%(v1)s[0]-%(v2)s[0]) - abs(%(v1)s[1]-%(v2)s[1])) == 1'%\
                                 {'v1':k1,'v2':k2}))
    tell(all_diff(variables.values()))
    
    distribute('dichotomy')
    return variables.values()

def draw_knights_solution(sol, size):
    # change the keys into elements, elements into keys
    # to display the results.
    # I'm sure there's a better way to do this, but I'm 
    # new to python
    board = ''
    board += '_'*(size*3+1)+'\n'
    squares = {}
    for t in sol.items():
        squares[(t[1][0]*size)+t[1][1]]=t[0]   
    for i in range(size):
        for j in range(size):
        # find the variable whose value is (i,j)
            square = squares[i*size+j]
            # numbering should start from 1 ,not 0
            intsquare = int(square[1:4]) + 1
            board+='|%02s'%intsquare
        board+='|\n'
    board += '¯'*(size*3+1)+'\n'
    print board

# Scheduling

def conference_scheduling():

    dom_values = [(room,slot) 
          for room in ('room A','room B','room C') 
          for slot in ('day 1 AM','day 1 PM','day 2 AM',
                       'day 2 PM')]

    variables = {}
    for v in ('c01','c02','c03','c04','c05', 'c06','c07','c08','c09','c10'):
        variables[v] = domain(dom_values, v)

    for conf in ('c03','c04','c05','c06'):
        v = variables[conf]
        tell(make_expression([v], "%s[0] == 'room C'" % conf))

    for conf in ('c01','c05','c10'):
        v = variables[conf]
        tell(make_expression([v], "%s[1].startswith('day 1')" % conf))

    for conf in ('c02','c03','c04','c09'):
        v = variables[conf]
        tell(make_expression([v], "%s[1].startswith('day 2')" % conf))

    groups = (('c01','c02','c03','c10'),
              ('c02','c06','c08','c09'),
              ('c03','c05','c06','c07'),
              ('c01','c03','c07','c08'))

    for group in groups:
        for conf1 in group:
            for conf2 in group:
                if conf2 > conf1:
                    v1, v2 = variables[conf1], variables[conf2]
                    tell(make_expression([v1, v2], '%s[1] != %s[1]'% (conf1, conf2)))

    
    tell(all_diff(variables.values()))

    distribute('dichotomy')

    return variables.values()


# Money

def money1():
    """ SEND
       +MORE
      -------
       MONEY
    """
    digits = range(10)
    var = {}
    for v in list('sendmory'):
        var[v] = domain(digits, v)

    tell(all_diff(var.values()))
    tell(make_expression([var['m']], 'm != 0'))
    tell(make_expression([var['s']], 'm != 0'))
    
    tell(make_expression([var['s'], var['m'], var['o']],
                         '(s+m) in (10*m+o,10*m+o-1)'))
    tell(make_expression([var['d'], var['e'], var['y']],
                         '(d+e)%10 == y'))
    tell(make_expression([var['n'], var['r'], var['e']],
                          '(n+r)%10 in (e,e-1)'))
    tell(make_expression([var['o'], var['e'], var['n']],
                          '(o+e)%10 in (n,n-1)'))
    tell(make_expression(var.values(),
                         'm*10000+(o-m-s)*1000+(n-o-e)*100+(e-r-n)*10+y-e-d == 0'))

    distribute('dichotomy')

    return var.values()

def money2():
    """ SEND
       +MORE
      -------
       MONEY
    """
    digits = range(10)
    var = {}
    for v in list('sendmory'):
        var[v] = domain(digits, v)

    tell(all_diff(var.values()))
    tell(make_expression([var['m']], 'm != 0'))
    tell(make_expression([var['s']], 'm != 0'))

    for v1 in variables:
        for v2 in variables:
            if v1 < v2:
                tell(make_expression([var[v1], var[v2]],
                                     '%s != %s'%(v1, v2)))
    tell(make_expression(var.values(),
                         'm*10000+(o-m-s)*1000+(n-o-e)*100+(e-r-n)*10+y-e-d == 0'))

    distribute('dichotomy')
    return var.values()

def display_money_solution(d):
    for s in d:
        print '  SEND\t  \t','  %(s)d%(e)d%(n)d%(d)d'%s
        print '+ MORE\t  \t','+ %(m)d%(o)d%(r)d%(e)d'%s
        print '------\t-->\t','------'
        print ' MONEY\t  \t',' %(m)d%(o)d%(n)d%(e)d%(y)d'%s
        print 

