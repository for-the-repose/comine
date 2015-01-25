
def gmap(fn, it):
    ''' Stupid python2 ...'''

    for val in it: yield fn(val)


def yrange(start, end, step = 1):
    while start < end:
        yield start

        start += step

def find(it, key, fn = lambda x: x, end = None):
    for some in it:
        if key == fn(some): return some

    return end
