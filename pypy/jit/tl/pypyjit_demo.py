import pypyjit
pypyjit.set_param(threshold=200)


def main(a, b):
    i = sa = 0
    while i < 300:
        if a > 0: # Specialises the loop
            pass
        if b < 2 and b > 0:
            pass
        if (a >> b) >= 0:
            sa += 1
        if (a << b) > 2:
            sa += 10000
        i += 1
    return sa

try:
    print main(2, 1)

except Exception, e:
    print "Exception: ", type(e)
    print e

