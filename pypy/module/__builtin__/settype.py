from pypy.interpreter import gateway

applevel = gateway.applevel('''
def mk_set():
    import sets
    return sets.Set

def mk_frozenset():
    import sets
    return sets.ImmutableSet
''')
mk_set = applevel.interphook('mk_set')
mk_frozenset = applevel.interphook('mk_frozenset')
