import computationspace as cs
import constraint as c
import distributor as di


def satisfiable_problem(computation_space):
    cs = computation_space
    x, y, z, w = (cs.var('x'), cs.var('y'),
                  cs.var('z'), cs.var('w'))
    x.cs_set_dom(cs, c.FiniteDomain([2, 6]))
    y.cs_set_dom(cs, c.FiniteDomain([2, 3]))
    z.cs_set_dom(cs, c.FiniteDomain([4, 5]))
    w.cs_set_dom(cs, c.FiniteDomain([1, 4, 5, 6, 7]))
    cs.add_constraint(c.Expression([x, y, z], 'x == y + z'))
    cs.add_constraint(c.Expression([z, w], 'z < w'))
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
    cs.add_constraint(c.Expression([x, y, z], 'x == y + z'))
    cs.add_constraint(c.Expression([z, w], 'z < w'))
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
    cs.add_constraint(c.Expression([x, y, z], 'x == y + z'))
    cs.add_constraint(c.Expression([z, w], 'z < w'))
    # set up a distribution strategy
    cs.set_distributor(di.DichotomyDistributor(cs))
    return (x, w, y)

def dummy_problem(computation_space):
    ret = computation_space.var('__dummy__')
    ret.dom = c.FiniteDomain([1, 2])
    return ret
