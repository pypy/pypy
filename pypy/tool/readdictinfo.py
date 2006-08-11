# this is for use with a pypy-c build with multidicts and using the
# MeasuringDictImplementation -- it will create a file called
# 'dictinfo.txt' in the local directory and this file will turn the
# contents back into DictInfo objects.

# run with python -i !

import sys

infile = open(sys.argv[1])

curr = None
slots = []
for line in infile:
    if line == '------------------\n':
        if curr:
            break
        curr = 1
    else:
        attr, val = [s.strip() for s in line.split(':')]
        slots.append(attr)

class DictInfo(object):
    __slots__ = slots

infile = open(sys.argv[1])

infos = []

for line in infile:
    if line == '------------------\n':
        curr = object.__new__(DictInfo)
        infos.append(curr)
    else:
        attr, val = [s.strip() for s in line.split(':')]
        if '.' in val:
            val = float(val)
        else:
            val = int(val)
        setattr(curr, attr, val)

def histogram(infos, keyattr, *attrs):
    r = {}
    for info in infos:
        v = getattr(info, keyattr)
        l = r.setdefault(v, [0, {}])
        l[0] += 1
        for a in attrs:
            d2 = l[1].setdefault(a, {})
            v2 = getattr(info, a)
            d2[v2] = d2.get(v2, 0) + 1
    return sorted(r.items())

def reportDictInfos():
    d = {}
    stillAlive = 0
    totLifetime = 0.0
    for info in infos:
        for attr in slots:
            if attr == 'maxcontents':
                continue
            v = getattr(info, attr)
            if not isinstance(v, int):
                continue
            d[attr] = d.get(attr, 0) + v
        if info.lifetime != -1.0:
            totLifetime += info.lifetime
        else:
            stillAlive += 1
    print 'read info on', len(infos), 'dictionaries'
    if stillAlive != len(infos):
        print 'average lifetime', totLifetime/(len(infos) - stillAlive),
        print '('+str(stillAlive), 'still alive at exit)'
    print d

def Rify(fname, *attributes):
    output = open(fname, 'w')
    for attr in attributes:
        print >>output, attr,
    print >>output
    for info in infos:
        for attr in attributes:
            print >>output, getattr(info, attr),
        print >>output

if __name__ == '__main__':
#    reportDictInfos()

    # interactive stuff:

    import __builtin__

    def displayhook(v):
        if v is not None:
            __builtin__._ = v
            pprint.pprint(v)
    sys.displayhook = displayhook

    import pprint
    try:
        import readline
    except ImportError:
        pass
    else:
        import rlcompleter
        readline.parse_and_bind('tab: complete')

    if len(sys.argv) > 2:
        attrs = sys.argv[2].split(',')
        if attrs == ['all']:
            attrs = slots
        Rify("R.txt", *attrs)
        

