#!/usr/bin/env python
import io
import struct
import typing as t
from dataclasses import dataclass
from functools import cached_property


@dataclass
class Header:
    signature: bytes
    version: int
    entries_number: int


@dataclass
class Entry:
    ctime_seconds: int
    ctime_nanoseconds: int
    mtime_seconds: int
    mtime_nanoseconds: int
    dev: int
    ino: int
    mode: int
    uid: int
    gid: int
    file_size: int  # 40 bytes
    sha1: bytes  # +20 bytes
    flags: int  # +2 bytes
    file_path: bytes  # null-terminated


@dataclass
class GitIndex:
    _fp: t.BinaryIO

    def read_struct(self, format: str) -> tuple[t.Any, ...]:
        return struct.unpack(format, self._fp.read(struct.calcsize(format)))

    def __post_init__(self) -> None:
        self.header = Header(*self.read_struct('>4s2I'))
        assert self.header.signature == b'DIRC'
        assert self.header.version == 2

    @cached_property
    def entries(self) -> list[Entry]:
        rv = []
        for _ in range(self.header.entries_number):
            entrysize = self._fp.tell()
            # В struct нету null-terminated strings
            unpacked = self.read_struct('>10I20sH')
            # путь всегда заканчивается null-byte
            buf = io.BytesIO()
            while (c := self._fp.read(1)) and c != b'\0':
                buf.write(c)
            entry = Entry(*unpacked, buf.getvalue())
            entrysize -= self._fp.tell()
            # размер entry кратен 8: file path добивается null-байтами
            self._fp.seek(entrysize % 8, 1)
            rv.append(entry)
        return rv

    def __iter__(self) -> t.Iterator[Entry]:
        return iter(self.entries)


if __name__ == '__main__':
    import sys

    with open(sys.argv[1], 'rb') as fp:
        index = GitIndex(fp)
        for entry in index:
            print(entry)
        print('=' * 40)
        for entry in index.entries:
            print(entry.sha1.hex())
