"""Snippets for translation

This module holds various snippets, to be used by translator
unittests.

TODO, or sanxiyn's plan:

Each snippet should know about suitable arguments to test it.
(Otherwise, there's a duplcation!) Should the result also be
stored? It can computed by CPython if we don't store it.

In case of typed translation test, we can give input_arg_types
by actually trying type() on arguments.

Each unittest should define a list of functions which it is able
to translate correctly, and import the list for tests. When
a translator can handle more, simply adding a function to the
list should suffice.

But for now, none of the above applies.
"""

def if_then_else(cond, x, y):
    if cond:
        return x
    else:
        return y

def my_gcd(a, b):
    r = a % b
    while r:
        a = b
        b = r
        r = a % b
    return b

def is_perfect_number(n):
    div = 1
    sum = 0
    while div < n:
        if n % div == 0:
            sum += div
        div += 1
    return n == sum

def my_bool(x):
    return not not x

def two_plus_two():
    """Array test"""
    array = [0] * 3
    array[0] = 2
    array[1] = 2
    array[2] = array[0] + array[1]
    return array[2]

def sieve_of_eratosthenes():
    """Sieve of Eratosthenes
    
    This one is from an infamous benchmark, "The Great Computer
    Language Shootout".

    URL is: http://www.bagley.org/~doug/shootout/
    """
    flags = [True] * (8192+1)
    count = 0
    i = 2
    while i <= 8192:
        if flags[i]:
            k = i + i
            while k <= 8192:
                flags[k] = False
                k = k + i
            count = count + 1
        i = i + 1
    return count

def simple_func(i):
    return i + 1

def while_func(i):
    total = 0
    while i > 0:
        total = total + i
        i = i - 1
    return total

def nested_whiles(i, j):
    s = ''
    z = 5
    while z > 0:
        z = z - 1
        u = i
        while u < j:
            u = u + 1
            s = s + '.'
        s = s + '!'
    return s

def poor_man_range(i):
    lst = []
    while i > 0:
        i = i - 1
        lst.append(i)
    lst.reverse()
    return lst

def simple_id(x):
    return x

def branch_id(cond, a, b):
    while 1:
        if cond:
            return a
        else:
            return b

def attrs():
    def b(): pass
    b.f = 4
    b.g = 5
    return b.f + b.g

def builtinusage():
    return pow(2, 2)

def yast(lst):
    total = 0
    for z in lst:
        total = total + z
    return total

def time_waster(n):
    """Arbitrary test function"""
    i = 0
    x = 1
    while i<n:
        j = 0
        while j<=i:
            j = j + 1
            x = x + (i&j)
        i = i + 1
    return x

def half_of_n(n):
    """Slice test"""
    i = 0
    lst = range(n)
    while lst:
        lst = lst[1:-1]
        i = i + 1
    return i

def int_id(x):
    i = 0
    while i < x:
        i = i + 1
    return i

def greet(target):
    """String test"""
    hello = "hello"
    return hello + target

def choose_last():
    """For loop test"""
    set = ["foo", "bar", "spam", "egg", "python"]
    for choice in set:
        pass
    return choice
