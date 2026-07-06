"""Two functions that reference each other but nothing live calls.
A reference-counter sees each 'used' and misses both. Reachability does not."""

def ping(n):
    return pong(n - 1) if n > 0 else "done"

def pong(n):
    return ping(n - 1) if n > 0 else "done"
