from dbc import ContractAspect, ContractError
ContractAspect()
from  contract_stack import Stack

def run():
    """This is an example of how contracts work
    """
    print "*"*30
    print "Creating an empty stack (max_size = 3)"
    stack = Stack(3)

    try:
        print "Empty stack, pop() should fail"
        stack.pop()
    except ContractError, excpt:
        print "\t failed with %s, (OK)" % excpt
    else:
        print "\t did not failed, (XXX)"

    print "\n\n\n"
    stack.push(1)
    print "push 1 done"
    stack.push(2)
    print "push 2 done"
    stack.push(3)
    print "push 3 done"
        
    try:
        print "The stack is full, push() should fail"
        stack.push(4)
    except ContractError, excpt:
        print "\t failed with %s, (OK)" % excpt
    else:
        print "\t did not failed, (XXX)"

    print "\n\n\n"



if __name__ == '__main__':
    run()
