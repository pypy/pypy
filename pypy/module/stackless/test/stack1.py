from stackless_ import *

def f():
    print 'in f'

def g(t):
    print 'in g %s' % t
    schedule()

def main():
    cg = tasklet(g)('test')
    cf = tasklet(f)()
    schedule()
    print 'in main'

if __name__ == '__main__':
    main()
    
