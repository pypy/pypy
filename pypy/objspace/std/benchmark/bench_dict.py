
""" some simple benchmarikng stuff
"""

import random, time

def get_random_string(l):
    strings = 'qwertyuiopasdfghjklzxcvbm,./;QWERTYUIOPASDFGHJKLZXCVBNM!@#$%^&*()_+1234567890-='
    random.sample(strings, l)

def count_operation(name, function):
    print name
    t0 = time.time()
    retval = function()
    tk = time.time()
    print name, " takes: %f" % (tk - t0)
    return retval

def bench_simple_dict(SIZE = 1000000):
    keys = [get_random_string(20) for i in xrange(SIZE)]
    values = [random.random() for i in xrange(SIZE)]
    
    lookup_keys = random.sample(keys, 100000)
    random_keys = [get_random_string(20) for i in xrange(100000)]
    
    test_d = count_operation("Creation", lambda : dict(zip(keys, values)))

    def rand_keys(keys):
        for key in keys:
            try:
                test_d[key]
            except KeyError:
                pass
    
    count_operation("Random key access", lambda : rand_keys(random_keys))
    count_operation("Existing key access", lambda : rand_keys(lookup_keys))

if __name__ == '__main__':
    bench_simple_dict()
