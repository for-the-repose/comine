
def gmap(fn, it):
    ''' Stupid python2 ...'''

    for val in it: yield fn(val)


def yrange(start, end, step = 1):
    while start < end:
        yield start

        start += step
