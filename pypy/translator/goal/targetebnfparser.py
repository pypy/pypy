from pypy.interpreter.pyparser.ebnfparse import target_parse_grammar_text
from pypy.annotation import policy as annpolicy


entry_point = target_parse_grammar_text

# _____ Define and setup target ___

def target(*args):
    policy = annpolicy.AnnotatorPolicy()
    policy.allow_someobjects = False
    return entry_point, [str]# , policy

def get_llinterp_args():
    return [1]

# _____ Run translated _____
def run(c_entry_point):
    import sys
    NBC=100
    import time
    src = file("../../interpreter/pyparser/data/Grammar2.4").read()
    print "Translated:"
    t1 = time.time()
    for i in range(NBC):
	c_entry_point( src )
    t2 = time.time()
    print "%8.5f sec/loop" % (float(t2-t1)/NBC)
    print "CPython:"
    t1 = time.time()
    for i in range(NBC):
	entry_point( src )
    t2 = time.time()
    print "%8.5f sec/loop" % (float(t2-t1)/NBC)


