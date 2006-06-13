from stackless import coroutine

d = {}

def f():
    print 'in f'

def g(coro,t):
    print 'in g %s' % t
    coro.switch()

def main():
    cm = coroutine.getcurrent()
    d[cm] = 'main'
    cf = coroutine()
    d[cf] = 'f'
    print 'cf:',cf
    cf.bind(f)
    cg = coroutine()
    d[cg] = 'g'
    print 'cg:',cg
    cg.bind(g,cf,'test')
    cg.switch()
    print 'back in main'
    print d

if __name__ == '__main__':
    main()
