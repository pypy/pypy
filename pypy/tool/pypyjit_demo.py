import pypyjit
pypyjit.set_param(threshold=200)

kwargs = {"z": 1}

def f(*args, **kwargs):
    result = g(1, *args, **kwargs)
    return result + 2

def g(x, y, z=2):
    return x - y + z

def main():
    res = 0
    i = 0
    while i < 10000:
        res = f(res, z=i)
        g(1, res, **kwargs)
        i += 1
    return res


try:
    print main()

except Exception, e:
    print "Exception: ", type(e)
    print e

