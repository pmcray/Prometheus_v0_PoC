def reverse_string(s):
    # inefficient reversal
    r = ''
    for i in range(len(s) - 1, -1, -1):
        r += s[i]
    return r