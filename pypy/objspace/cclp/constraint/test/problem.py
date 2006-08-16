

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

