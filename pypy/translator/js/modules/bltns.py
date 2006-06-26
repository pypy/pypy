
""" Some other function
"""

from pypy.translator.stackless.test.test_transform import one

def date():
    if one():
        return 3.2
    else:
        return 5.8

date.suggested_primitive = True
