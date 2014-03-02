
from sys import stdout

def log(lev, string):
    if lev < 8: stdout.write(string + '\n')
