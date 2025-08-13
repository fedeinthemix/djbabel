# SPDX-FileCopyrightText: 2025 Federico Beffa <beffa@fbengineering.ch>
# SPDX-FileCopyrightText: 2019 Jan Holthuis
#
# SPDX-License-Identifier: MIT

from dataclasses import dataclass, fields
import io
import struct
import enum
from typing import ClassVar
from mutagen._file import FileType # pyright: ignore

from ..types import AFormat
from ..utils import audio_file_type

from .types import EntryBase, SeratoTags
from .utils import get_serato_metadata, FMT_VERSION

def get_serato_markers(audio: FileType) -> list[EntryBase] | None:
    match audio_file_type(audio):
        case AFormat.M4A:
            return get_serato_metadata(SeratoTags.MARKERS, parse_m4a)(audio)
        case _:
            return get_serato_metadata(SeratoTags.MARKERS, parse)(audio)

# MP4 format
# ----------
#
# header as MP3
# 4 bytes (start time), 4 bytes (end time), 00 ff ff ff ff 00, 3 bytes (RGB color), 1 byte locked
# 00 ff ff ff 00 (footer)
#
# start/stop  time == ff ff ff ff -> not set, other data not meaninful
#

###############################################################################
# Code below this line adapted from https://github.com/Holzhaus/serato-tags
#
# Copyright 2019 Jan Holthuis
#
# Original code licensed under the MIT License. See LICENSE/MIT.txt

class EntryType(enum.IntEnum):
    INVALID = 0
    CUE = 1
    LOOP = 3


def serato32encode(data: bytes) -> bytes:
    """Encode 3 byte plain text into 4 byte Serato binary format."""
    a, b, c = struct.unpack('BBB', data)
    z = c & 0x7F
    y = ((c >> 7) | (b << 1)) & 0x7F
    x = ((b >> 6) | (a << 2)) & 0x7F
    w = (a >> 5)
    return bytes(bytearray([w, x, y, z]))


def serato32decode(data: bytes) -> bytes:
    """Decode 4 byte Serato binary format into 3 byte plain text."""
    w, x, y, z = struct.unpack('BBBB', data)
    c = (z & 0x7F) | ((y & 0x01) << 7)
    b = ((y & 0x7F) >> 1) | ((x & 0x03) << 6)
    a = ((x & 0x7F) >> 2) | ((w & 0x07) << 5)
    return struct.pack('BBB', a, b, c)


@dataclass
class Entry(EntryBase):
    FMT : ClassVar[str]= '>B4sB4s6s4sB?'
    FMT_M4A : ClassVar[str]= '>4s4s5s4sB?'
    start_position_set : int
    start_position : int | None
    end_position_set : int
    end_position : int | None
    field5 : bytes
    color : bytes
    type : EntryType
    is_locked : bool

    @classmethod
    def load(cls, data):
        info_size = struct.calcsize(cls.FMT)
        info = struct.unpack(cls.FMT, data[:info_size])
        entry_data = []

        start_position_set = None
        end_position_set = None
        for field, value in zip(fields(cls), info):
            if field.name == 'start_position_set':
                assert value in (0x00, 0x7F)
                value = value != 0x7F
                start_position_set = value
            elif field.name == 'end_position_set':
                assert value in (0x00, 0x7F)
                value = value != 0x7F
                end_position_set = value
            elif field.name == 'start_position':
                assert start_position_set is not None
                if start_position_set:
                    value = struct.unpack(
                        '>I', serato32decode(value).rjust(4, b'\x00'))[0]
                else:
                    value = None
            elif field.name == 'end_position':
                assert end_position_set is not None
                if end_position_set:
                    value = struct.unpack(
                        '>I', serato32decode(value).rjust(4, b'\x00'))[0]
                else:
                    value = None
            elif field.name == 'type':
                value = EntryType(value)
            elif field.name == 'color':
                value = serato32decode(value)

            entry_data.append(value)

        return cls(*entry_data)


    @classmethod
    def load_m4a(cls, data):
        info_size = struct.calcsize(cls.FMT_M4A)
        info = struct.unpack(cls.FMT_M4A, data[:info_size])
        entry_data = []

        flds = list(filter(lambda f: not f.name.endswith('_set'), fields(cls)))

        for field, value in zip(flds, info):
            value_set = None
            if field.name == 'start_position':
                if value != b'\xff\xff\xff\xff':
                    value_set = True
                    value = struct.unpack('>I', value)[0]
                else:
                    value_set = False
                    value = None
            elif field.name == 'end_position':
                if value != b'\xff\xff\xff\xff':
                    value_set = True
                    value = struct.unpack('>I', value)[0]
                else:
                    value_set = False
                    value = None
            elif field.name == 'type':
                value = EntryType(value)
            elif field.name == 'color':
                value = value[1:]

            if value_set is None:
                entry_data.append(value)
            else:
                entry_data += [value_set, value]

        return cls(*entry_data)


    def dump(self):
        entry_data = []
        for field in fields(self):
            value = getattr(self, field.name)
            if field.name == 'start_position_set':
                value = 0x7F if not value else 0x00
            elif field.name == 'end_position_set':
                value = 0x7F if not value else 0x00
            if field.name == 'color':
                assert isinstance(value, bytes)
                value = serato32encode(value)
            elif field.name == 'start_position':
                if value is None:
                    value = b'\x7F\x7F\x7F\x7F'
                else:
                    value = serato32encode(struct.pack('>I', value)[1:])
            elif field.name == 'end_position':
                if value is None:
                    value = b'\x7F\x7F\x7F\x7F'
                else:
                    value = serato32encode(struct.pack('>I', value)[1:])
            elif field.name == 'type':
                assert isinstance(value, EntryType)
                value = value.value
            elif field.name == 'color':
                assert isinstance(value, bytes)
                value = serato32encode(value)

            entry_data.append(value)

        return struct.pack(self.FMT, *entry_data)


    def dump_m4a(self):
        entry_data = []

        flds = list(filter(lambda f: not f.name.endswith('_set'), fields(self)))

        for field in flds:
            value = getattr(self, field.name)
            if field.name == 'color':
                value = b'\x00' + value
            elif field.name == 'start_position':
                if value is None:
                    value = b'\xff\xff\xff\xff'
                else:
                    value = struct.pack('>I', value)
            elif field.name == 'end_position':
                if value is None:
                    value = b'\xff\xff\xff\xff'
                else:
                    value = struct.pack('>I', value)
            elif field.name == 'type':
                value = int(value)

            entry_data.append(value)

        return struct.pack(self.FMT_M4A, *entry_data)


@dataclass
class Color(EntryBase):
    FMT : ClassVar[str] = '>4s'
    color : bytes

    @classmethod
    def load(cls, data):
        info_size = struct.calcsize(cls.FMT)
        info = struct.unpack(cls.FMT, data[:info_size])
        color_data = []

        for field, value in zip(fields(cls), info):
            if field.name == 'color':
                value = serato32decode(value)
            color_data.append(value)

        return cls(*color_data)

    @classmethod
    def load_m4a(cls, data):
        info_size = struct.calcsize(cls.FMT)
        info = struct.unpack(cls.FMT, data[:info_size])
        color_data = []

        for field, value in zip(fields(cls), info):
            if field.name == 'color':
                value = value[1:]
            color_data.append(value)

        return cls(*color_data)

    def dump(self):
        color_data = []
        for field in fields(self):
            value = getattr(self, field.name)
            if field.name == 'color':
                value = serato32encode(value)
            color_data.append(value)
        return struct.pack(self.FMT, *color_data)

    def dump_m4a(self):
        color_data = []
        for field in fields(self):
            value = getattr(self, field.name)
            if field.name == 'color':
                value = b'\x00' + value
            color_data.append(value)
        return struct.pack(self.FMT, *color_data)


def parse(data: bytes) -> list[EntryBase]:
    fp = io.BytesIO(data)
    assert struct.unpack(FMT_VERSION, fp.read(2)) == (0x02, 0x05)

    num_entries = struct.unpack('>I', fp.read(4))[0]
    out = []
    for _ in range(num_entries):
        entry_data = fp.read(0x16)
        assert len(entry_data) == 0x16

        entry = Entry.load(entry_data)
        out.append(entry)

    return out  + [Color.load(fp.read())]


def parse_m4a(data: bytes) -> list[EntryBase]:
    fp = io.BytesIO(data)
    assert struct.unpack(FMT_VERSION, fp.read(2)) == (0x02, 0x05)

    num_entries = struct.unpack('>I', fp.read(4))[0]
    out = []
    for _ in range(num_entries):
        entry_data = fp.read(0x13)
        assert len(entry_data) == 0x13

        entry = Entry.load_m4a(entry_data)
        out.append(entry)

    return out  + [Color.load_m4a(fp.read())]


def dump(new_entries : list[Entry | Color]) -> bytes:
    data = struct.pack(FMT_VERSION, 0x02, 0x05)
    num_entries = len(new_entries) - 1
    data += struct.pack('>I', num_entries)
    for entry_data in new_entries:
        data += entry_data.dump()
    return data


def dump_m4a(new_entries : list[Entry | Color]) -> bytes:
    data = struct.pack(FMT_VERSION, 0x02, 0x05)
    num_entries = len(new_entries) - 1
    data += struct.pack('>I', num_entries)
    for entry_data in new_entries:
        data += entry_data.dump_m4a()
    # The last byte is not always '\x00'.
    return data + b'\x00'
