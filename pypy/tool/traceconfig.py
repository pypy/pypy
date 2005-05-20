""" Trace object space configuration options - set with __pytrace__=1
in py.py """

config = {
    # An optional filename to use for trace output.  None is stdout
    "output_filename" : None,

    # Some internal interpreter code is written at applevel - by default
    # it is a good idea to hide this.
    "show_hidden_applevel" : False,

    # Many operations call back into the object space
    "recursive_operations" : False,
    
    # Show the bytecode or just the operations
    "show_bytecode" : True,

    # Indentor string used for output
    "indentor" : '  ',

    # Show wrapped values in bytecode
    "show_wrapped_consts_bytecode" : True

}
