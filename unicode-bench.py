
import time

LGT = 100

unicodes = [unicode("u" * LGT + str(i)) for i in range(100)]
non_ascii_unicodes = [u"u" * LGT + unicode(i) + u"å" for i in range(100)]

RANGE = 250000000 // LGT

def upper(main_l):
    l = [None] * 1000
    for i in xrange(RANGE):
        l[i % 1000] = main_l[i % 100].upper()

def lower(main_l):
    l = [None]
    for i in xrange(RANGE):
        l[0] = main_l[i % 100].lower()

def islower(main_l):
    l = [None]
    for i in xrange(RANGE * 3):
        l[0] = main_l[i % 100].islower()

def title(main_l):
    l = [None]
    for i in xrange(RANGE):
        l[0] = main_l[i % 100].title()

def add(main_l):
    l = [None]
    for i in xrange(RANGE):
        l[0] = main_l[i % 100] + u"foo"

def find(main_l):
    l = [None]
    for i in xrange(RANGE):
        l[0] = main_l[i % 100].find(u"foo")

for func in [upper]:#, lower, isupper, islower]:
    t0 = time.time()
    func(unicodes)
    t1 = time.time()
    print "ascii %s %.2f" % (func.__name__, t1 - t0)
    func(non_ascii_unicodes)
    t2 = time.time()
    print "non-ascii %s %.2f" % (func.__name__, t2 - t1)
