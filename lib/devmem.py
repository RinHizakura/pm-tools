#!/usr/bin/env python

import argparse, ctypes, mmap, os
import os.path as osp


def align_up(x, a):
    return (x + (a - 1)) & ~(a - 1)


def align_down(x, a):
    return x & ~(a - 1)


class DevMem:
    def __init__(self, path="/dev/mem"):
        self.path = path
        if not osp.exists(self.path):
            raise RuntimeError(f"Cannot find {self.path} file")

    def read(self, addr, size, bytestr=True):
        PAGE_SIZE = os.sysconf("SC_PAGE_SIZE")
        PAGE_MASK = PAGE_SIZE - 1
        mapaddr = align_down(addr, PAGE_SIZE)
        offset = addr & PAGE_MASK
        mapsize = size + offset

        mapsize = align_up(mapsize, PAGE_SIZE)

        val = b""
        with open(self.path, "r+b") as f:
            f.truncate(mapsize)

            f.seek(0, os.SEEK_END)
            file_size = f.tell()
            f.seek(0, os.SEEK_SET)

            mem = mmap.mmap(
                f.fileno(),
                length=min(mapsize, file_size),
                flags=mmap.MAP_SHARED,
                prot=mmap.PROT_READ | mmap.PROT_WRITE,
                offset=mapaddr,
            )

            buf = ctypes.addressof(ctypes.c_char.from_buffer(mem, offset))

            if bytestr:
                buf = ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))
                for i in range(size):
                    val += buf[i]
            else:
                # This mode is not expected for a non-interger read
                assert size <= 8
                typ = getattr(ctypes, f"c_uint{size*8}")
                val = ctypes.cast(buf, ctypes.POINTER(typ))[0]

            # Unmap & Release resource
            mem.close()

        return val


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "addr",
        type=lambda x: int(x, 0),
    )
    parser.add_argument(
        "size",
        type=lambda x: int(x, 0),
    )
    args = parser.parse_args()

    return args


if __name__ == "__main__":
    args = get_args()
    addr = args.addr
    size = args.size

    if os.geteuid() != 0:
        exit("Please run script this as root")

    devmem = DevMem()
    m = devmem.read(addr, size)

    for i in range(0, size, 8):
        print(f"{hex(addr + i)} :", end="")
        for j in range(8):
            if i + j >= size:
                break
            data = m[i + j]
            print(hex(data), ",", end="")
        print("")
