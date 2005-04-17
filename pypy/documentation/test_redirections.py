
import py 
redir = py.magic.autopath().dirpath('redirections') 

def checkexist(path):
    assert path.new(ext='.txt').check(file=1) 
   
def test_eval(): 
    d = eval(redir.read()) 
    return d

def test_redirections(): 
    d = test_eval() 
    for newname in d.values(): 
        yield checkexist, redir.dirpath(newname) 

def test_navlist(): 
    assert eval(redir.dirpath('navlist').read())
