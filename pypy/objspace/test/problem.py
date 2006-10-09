

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


def queens(size=8):
    # still not used/tested
    variables = []
    for i in range(size):
        variables.append(domain(range(size), 'Q%02d'%i))

    for r1 in range(size):
        for r2 in range(size):
            q1 = 'Q%02d' % r1
            q2 = 'Q%02d' % r2
            if r1 < r2:
                D = {'q1':q1,'q2':q2, 'r1' : r1, 'r2' : r2 }
                c = tell(make_expression([q1,q2],
                                       '%(q1)s != %(q2)s and '
                                       'abs(%(r1)s-%(r2)s) != '
                                       'abs(%(q1)s-%(q2)s)'% D ))
    distribute('dichotomy')
    return variables
