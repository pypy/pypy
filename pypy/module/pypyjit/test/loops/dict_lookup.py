def f():
    d = {'x': 1}
    for i in range(10000):
        d['x'] = i
    print d['x']
f()
