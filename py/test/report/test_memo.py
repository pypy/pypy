import py 

datadir = py.test.config.tmpdir 

#def test_equal_should_raise():
#    check.equal(1,2)

#class MyUnit(collect.Auto, collect.Unit):
#    def execute(self, runner):
#        try:        
#
def test_memoreporter():
    reporter = py.test.MemoReporter()
    p = datadir.join('memoimport.py')
    p.write('raise IOError') 
    collector = py.test.collect.Module(p) 
    #main(collector=collector, reporter=reporter)
    #collect_errors = reporter.getlist(collect.Error)
    #assert len(collect_errors) == 1
    ##print collect_errors

if __name__=='__main__':
    test.main()
