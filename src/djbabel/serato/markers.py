# -*- coding: utf-8 -*-
import io
import struct
import enum
from mutagen._file import FileType

from .types import SeratoTags
from .utils import get_serato_metadata, FMT_VERSION

def get_serato_markers(audio: FileType) -> dict | None:
    return get_serato_metadata(SeratoTags.MARKERS, parse)(audio)

# XXXX --- 'parse' fails on M4A files, needs special handling

# MP4 format
# ----------
#
# header as MP3
# 4 bytes (start time), 4 bytes (end time), 00 ff ff ff ff 00, 3 bytes (RGB color), 1 byte color
# 00 ff ff ff 00 (footer)
#
# start/stop  time == ff ff ff ff -> not set, other data not meaninful
#
    
###############################################################################
# Code from https://github.com/Holzhaus/serato-tags with minor modifications.
#
# Copyright 2019 Jan Holthuis
#
# original code licensed under the MIT License

class EntryType(enum.IntEnum):
    INVALID = 0
    CUE = 1
    LOOP = 3


def serato32encode(data):
    """Encode 3 byte plain text into 4 byte Serato binary format."""
    a, b, c = struct.unpack('BBB', data)
    z = c & 0x7F
    y = ((c >> 7) | (b << 1)) & 0x7F
    x = ((b >> 6) | (a << 2)) & 0x7F
    w = (a >> 5)
    return bytes(bytearray([w, x, y, z]))


def serato32decode(data):
    """Decode 4 byte Serato binary format into 3 byte plain text."""
    w, x, y, z = struct.unpack('BBBB', data)
    c = (z & 0x7F) | ((y & 0x01) << 7)
    b = ((y & 0x7F) >> 1) | ((x & 0x03) << 6)
    a = ((x & 0x7F) >> 2) | ((w & 0x07) << 5)
    return struct.pack('BBB', a, b, c)


class Entry(object):
    FMT = '>B4sB4s6s4sBB'
    FIELDS = ('start_position_set', 'start_position', 'end_position_set',
              'end_position', 'field5', 'color', 'type', 'is_locked')

    def __init__(self, *args):
        assert len(args) == len(self.FIELDS)
        for field, value in zip(self.FIELDS, args):
            setattr(self, field, value)

    def __repr__(self):
        return '{name}({data})'.format(
            name=self.__class__.__name__,
            data=', '.join('{}={!r}'.format(name, getattr(self, name))
                           for name in self.FIELDS))

    @classmethod
    def load(cls, data):
        info_size = struct.calcsize(cls.FMT)
        info = struct.unpack(cls.FMT, data[:info_size])
        entry_data = []

        start_position_set = None
        end_position_set = None
        for field, value in zip(cls.FIELDS, info):
            if field == 'start_position_set':
                assert value in (0x00, 0x7F)
                value = value != 0x7F
                start_position_set = value
            elif field == 'end_position_set':
                assert value in (0x00, 0x7F)
                value = value != 0x7F
                end_position_set = value
            elif field == 'start_position':
                assert start_position_set is not None
                if start_position_set:
                    value = struct.unpack(
                        '>I', serato32decode(value).rjust(4, b'\x00'))[0]
                else:
                    value = None
            elif field == 'end_position':
                assert end_position_set is not None
                if end_position_set:
                    value = struct.unpack(
                        '>I', serato32decode(value).rjust(4, b'\x00'))[0]
                else:
                    value = None
            elif field == 'color':
                value = serato32decode(value)
            elif field == 'type':
                value = EntryType(value)
            entry_data.append(value)

        return cls(*entry_data)

    def dump(self):
        entry_data = []
        for field in self.FIELDS:
            value = getattr(self, field)
            if field == 'start_position_set':
                value = 0x7F if not value else 0x00
            elif field == 'end_position_set':
                value = 0x7F if not value else 0x00
            elif field == 'color':
                value = serato32encode(value)
            elif field == 'start_position':
                if value is None:
                    value = 0x7F7F7F7F
                else:
                    value = serato32encode(struct.pack('>I', value)[1:])
            elif field == 'end_position':
                if value is None:
                    value = 0x7F7F7F7F
                else:
                    value = serato32encode(struct.pack('>I', value)[1:])
            elif field == 'type':
                value = int(value)
            entry_data.append(value)
        return struct.pack(self.FMT, *entry_data)


class Color(Entry):
    FMT = '>4s'
    FIELDS = ('color',)


def parse(data: bytes):
    fp = io.BytesIO(data)
    assert struct.unpack(FMT_VERSION, fp.read(2)) == (0x02, 0x05)

    num_entries = struct.unpack('>I', fp.read(4))[0]
    for i in range(num_entries):
        entry_data = fp.read(0x16)
        assert len(entry_data) == 0x16

        entry = Entry.load(entry_data)
        yield entry

    yield Color.load(fp.read())


def dump(new_entries):
    data = struct.pack(FMT_VERSION, 0x02, 0x05)
    num_entries = len(new_entries) - 1
    data += struct.pack('>I', num_entries)
    for entry_data in new_entries:
        data += entry_data.dump()
    return data
