import computationspace as cs
import constraint as c
import distributor as di

def dummy_problem(computation_space):
    ret = computation_space.var('__dummy__')
    ret.dom = c.FiniteDomain([1, 2])
    return (ret)

def satisfiable_problem(computation_space):
    cs = computation_space
    x, y, z, w = (cs.var('x'), cs.var('y'),
                  cs.var('z'), cs.var('w'))
    x.cs_set_dom(cs, c.FiniteDomain([2, 6]))
    y.cs_set_dom(cs, c.FiniteDomain([2, 3]))
    z.cs_set_dom(cs, c.FiniteDomain([4, 5]))
    w.cs_set_dom(cs, c.FiniteDomain([1, 4, 5, 6, 7]))
    cs.add_constraint(c.Expression(cs, [x, y, z], 'x == y + z'))
    cs.add_constraint(c.Expression(cs, [z, w], 'z < w'))
    # set up a distribution strategy
    cs.set_distributor(di.DichotomyDistributor(cs))
    return (x, w, y)

def one_solution_problem(computation_space):
    cs = computation_space
    x, y, z, w = (cs.var('x'), cs.var('y'),
                  cs.var('z'), cs.var('w'))
    x.cs_set_dom(cs, c.FiniteDomain([2, 6]))
    y.cs_set_dom(cs, c.FiniteDomain([2, 3]))
    z.cs_set_dom(cs, c.FiniteDomain([4, 5]))
    w.cs_set_dom(cs, c.FiniteDomain([1, 4, 5]))
    cs.add_constraint(c.Expression(cs, [x, y, z], 'x == y + z'))
    cs.add_constraint(c.Expression(cs, [z, w], 'z < w'))
    # set up a distribution strategy
    cs.set_distributor(di.DichotomyDistributor(cs))
    return (x, w, y)


def unsatisfiable_problem(computation_space):
    cs = computation_space
    x, y, z, w = (cs.var('x'), cs.var('y'),
                  cs.var('z'), cs.var('w'))
    x.cs_set_dom(cs, c.FiniteDomain([2, 6]))
    y.cs_set_dom(cs, c.FiniteDomain([2, 3]))
    z.cs_set_dom(cs, c.FiniteDomain([4, 5]))
    w.cs_set_dom(cs, c.FiniteDomain([1]))
    cs.add_constraint(c.Expression(cs, [x, y, z], 'x == y + z'))
    cs.add_constraint(c.Expression(cs, [z, w], 'z < w'))
    # set up a distribution strategy
    cs.set_distributor(di.DichotomyDistributor(cs))
    return (x, w, y)

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
        v.cs_set_dom(cs, c.FiniteDomain(dom_values))

    for conf in ('c03','c04','c05','c06'):
        v = cs.get_var_by_name(conf)
        cs.add_constraint(c.Expression(cs, [v], "%s[0] == 'room C'" % v.name))

    for conf in ('c01','c05','c10'):
        v = cs.get_var_by_name(conf)
        cs.add_constraint(c.Expression(cs, [v], "%s[1].startswith('day 1')" % v.name))

    for conf in ('c02','c03','c04','c09'):
        v = cs.get_var_by_name(conf)
        cs.add_constraint(c.Expression(cs, [v], "%s[1].startswith('day 2')" % v.name))

    groups = (('c01','c02','c03','c10'),
              ('c02','c06','c08','c09'),
              ('c03','c05','c06','c07'),
              ('c01','c03','c07','c08'))

    for g in groups:
        for conf1 in g:
            for conf2 in g:
                v1, v2 = cs.find_vars(conf1, conf2)
                if conf2 > conf1:
                    cs.add_constraint(c.Expression(cs, [v1,v2],
                                                   '%s[1] != %s[1]'%\
                                                   (v1.name,v2.name)))

    for conf1 in variables:
        for conf2 in variables:
            if conf2 > conf1:
                cs.add_constraint(c.Expression(cs, [conf1,conf2],
                                               '%s != %s'%(conf1.name,conf2.name)))
    return tuple(variables)
