import py 

def app_test__isfake(): 
    assert not _isfake(map) 
    assert not _isfake(object) 
    assert not _isfake(_isfake) 

def app_test__isfake_currently_true(): 
    import array
    assert _isfake(array) 

def XXXapp_test__isfake_file(): # only if you are not using --file
    import sys
    assert _isfake(sys.stdout)

