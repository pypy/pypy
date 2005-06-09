import autopath
from pypy.translator.translator import Translator


def example(d):
    try:
        d['key']
    except KeyError:
        d['key'] = 'value'

def test_example():
    t = Translator(example)
    t.simplify()    # this specific example triggered a bug in simplify.py
    #t.view()
