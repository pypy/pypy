"""
Thunk (a.k.a. lazy objects) in PyPy.
To run on top of the thunk object space with the following command-line:

    py.py -o thunk fibonacci.py

This is a typical Functional Programming Languages demo, computing the
Fibonacci sequence by using an infinite lazy linked list.
"""

try:
    from __pypy__ import thunk    # only available in 'py.py -o thunk'
except ImportError:
    print __doc__
    raise SystemExit(2)

# ____________________________________________________________


class ListNode:
    def __init__(self, head, tail):
        self.head = head   # the first element of the list
        self.tail = tail   # the sublist of all remaining elements


def add_lists(list1, list2):
    """Compute the linked-list equivalent of the Python expression
          [a+b for (a,b) in zip(list1,list2)]
    """
    return ListNode(list1.head + list2.head,
                    thunk(add_lists, list1.tail, list2.tail))


# 1, 1, 2, 3, 5, 8, 13, 21, 34, ...
Fibonacci = ListNode(1, ListNode(1, None))
Fibonacci.tail.tail = thunk(add_lists, Fibonacci, Fibonacci.tail)


if __name__ == '__main__':
    node = Fibonacci
    while True:
        print node.head
        node = node.tail
