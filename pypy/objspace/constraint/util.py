
def sort(l):
    """in place merge sort"""
    _sort(l, 0, len(l) - 1)

def _sort(l, low, high):
    if low >= high: return
    mid = (low + high) / 2
    _sort(l, low, mid)
    _sort(l, mid + 1, high)
    stop_low = mid
    start_high = mid + 1
    while low <= stop_low and start_high <= high:
        if l[low] < l[start_high]:
            low += 1
        else:
            t = l[start_high]
            k = start_high - 1
            while k >= low:
                l[k+1] = l[k]
                k -= 1
            l[low] = t
            low += 1
            stop_low += 1
            start_high += 1


def reverse(l):
    """reverse the content of a vector"""
    length = len(l)
    mid = length / 2
    max = length - 1
    idx = 0
    while idx < mid:
        antidx = max-idx
        l[idx], l[antidx] = l[antidx], l[idx]
        idx += 1
