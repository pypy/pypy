import stackless
if hasattr(stackless,'coroutine'):
    import stackless_ as stackless

def f():
    print 'in f', stackless.getcurrent()

def g(t):
    print 'in g %s' % t , stackless.getcurrent()
    stackless.schedule()

def main():
    cg = stackless.tasklet(g)('test')
    cf = stackless.tasklet(f)()
    stackless.run()
    print 'in main', stackless.getcurrent()

if __name__ == '__main__':
    main()
    
