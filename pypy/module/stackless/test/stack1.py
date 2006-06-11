from stackless_ import *

def f():
    print 'in f', getcurrent()

def g(t):
    print 'in g %s' % t , getcurrent()
    schedule()

def main():
    cg = tasklet(g)('test')
    cf = tasklet(f)()
    run()
    print 'in main', getcurrent()

if __name__ == '__main__':
    main()
    
