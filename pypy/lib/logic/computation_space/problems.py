import computationspace as cs
import constraint as c
import distributor as di

def dummy_problem(computation_space):
    ret = computation_space.var('__dummy__')
    computation_space.set_dom(ret, c.FiniteDomain([]))
    return (ret)

def satisfiable_problem(computation_space):
    cs = computation_space
    x, y, z = cs.var('x'), cs.var('y'), cs.var('z')
    cs.set_dom(x, c.FiniteDomain([-4, -2, -1, 0, 1, 2, 4]))
    cs.set_dom(y, c.FiniteDomain([0, 2, 3, 4, 5, 16]))
    cs.set_dom(z, c.FiniteDomain([-2, -1, 0, 1, 2]))
    cs.add_constraint([x, y, z], 'y==x**2-z')
    # set up a distribution strategy
    cs.set_distributor(di.DichotomyDistributor(cs))
    return (x, y, z)

def one_solution_problem(computation_space):
    cs = computation_space
    x, y, z, w = (cs.var('x'), cs.var('y'),
                  cs.var('z'), cs.var('w'))
    cs.set_dom(x, c.FiniteDomain([2, 6]))
    cs.set_dom(y, c.FiniteDomain([2, 3]))
    cs.set_dom(z, c.FiniteDomain([4, 5]))
    cs.set_dom(w, c.FiniteDomain([1, 4, 5]))
    cs.add_constraint([x, y, z], 'x == y + z')
    cs.add_constraint([z, w], 'z < w')
    # set up a distribution strategy
    cs.set_distributor(di.DichotomyDistributor(cs))
    return (x, w, y)


def unsatisfiable_problem(computation_space):
    cs = computation_space
    x, y, z, w = (cs.var('x'), cs.var('y'),
                  cs.var('z'), cs.var('w'))
    cs.set_dom(x, c.FiniteDomain([2, 6]))
    cs.set_dom(y, c.FiniteDomain([2, 3]))
    cs.set_dom(z, c.FiniteDomain([4, 5]))
    cs.set_dom(w, c.FiniteDomain([1]))
    cs.add_constraint([x, y, z], 'x == y + z')
    cs.add_constraint([z, w], 'z < w')
    # set up a distribution strategy
    cs.set_distributor(di.DichotomyDistributor(cs))
    return (x, w, y)

def send_more_money(computation_space):
    cs = computation_space

    variables = (s, e, n, d, m, o, r, y) = cs.make_vars('s', 'e', 'n', 'd', 'm', 'o', 'r', 'y')

    digits = range(10)
    for var in variables:
        cs.set_dom(var, c.FiniteDomain(digits))

    # use fd.AllDistinct
    for v1 in variables:
        for v2 in variables:
            if v1 != v2:
                cs.add_constraint([v1, v2],
                                  '%s != %s' % (v1.name, v2.name))

    # use fd.NotEquals
    cs.add_constraint([s], 's != 0')
    cs.add_constraint([m], 'm != 0')
    cs.add_constraint([s, e, n, d, m, o, r, y],
                                   '1000*s+100*e+10*n+d+1000*m+100*o+10*r+e == 10000*m+1000*o+100*n+10*e+y')
    cs.set_distributor(di.DichotomyDistributor(cs))
    print cs.constraints
    return (s, e, n, d, m, o, r, y)

def conference_scheduling(computation_space):
    cs = computation_space

    variables = [cs.var(v)
                 for v in ('c01','c02','c03','c04','c05',
                           'c06','c07','c08','c09','c10')]

    dom_values = [(room,slot) 
          for room in ('room A','room B','room C') 
          for slot in ('day 1 AM','day 1 PM','day 2 AM',
                       'day 2 PM')]
    for v in variables:
        cs.set_dom(v, c.FiniteDomain(dom_values))

    for conf in ('c03','c04','c05','c06'):
        v = cs.get_var_by_name(conf)
        cs.add_constraint([v], "%s[0] == 'room C'" % v.name)

    for conf in ('c01','c05','c10'):
        v = cs.get_var_by_name(conf)
        cs.add_constraint([v], "%s[1].startswith('day 1')" % v.name)

    for conf in ('c02','c03','c04','c09'):
        v = cs.get_var_by_name(conf)
        cs.add_constraint([v], "%s[1].startswith('day 2')" % v.name)

    groups = (('c01','c02','c03','c10'),
              ('c02','c06','c08','c09'),
              ('c03','c05','c06','c07'),
              ('c01','c03','c07','c08'))

    for g in groups:
        for conf1 in g:
            for conf2 in g:
                v1, v2 = cs.find_vars(conf1, conf2)
                if conf2 > conf1:
                    cs.add_constraint([v1,v2], '%s[1] != %s[1]'% (v1.name,v2.name))

    for conf1 in variables:
        for conf2 in variables:
            if conf2 > conf1:
                cs.add_constraint([conf1,conf2], '%s != %s'%(conf1.name,conf2.name))
    return tuple(variables)
