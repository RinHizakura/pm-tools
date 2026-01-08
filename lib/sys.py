def read_f(path, quiet=False):
    try:
        f = open(path, "r")
        r = f.read()
        f.close()
    except Exception as exc:
        if not quiet:
            print(f"read({path}) fail: {exc}")
        return None
    return r


def write_f(path, val, quiet=False):
    try:
        f = open(path, "w")
        w = f.write(val)
        f.close()
    except Exception as exc:
        if not quiet:
            print(f"write({path}, {val}) fail: {exc}")
        return None
    return w
