# SPDX-FileCopyrightText: 2025 Federico Beffa <beffa@fbengineering.ch>
# SPDX-FileCopyrightText: 2019 Jan Holthuis
#
# SPDX-License-Identifier: MIT

import struct
import base64
from dataclasses import dataclass, fields
import io
from mutagen._file import FileType # pyright: ignore
from typing import ClassVar

from .types import SeratoTags, EntryBase
from .utils import get_serato_metadata, FMT_VERSION, readbytes

def get_serato_markers_v2(audio: FileType) -> list[EntryBase]:
    m = get_serato_metadata(SeratoTags.MARKERS2, parse)(audio)
    return m if isinstance(m, list) else []

###############################################################################
# Code below this line adapted from https://github.com/Holzhaus/serato-tags
#
# Copyright 2019 Jan Holthuis
#
# Original code licensed under the MIT License. See LICENSE/MIT.txt

@dataclass
class UnknownEntry(EntryBase):
    NAME : ClassVar[None] = None
    data : bytes

    @classmethod
    def load(cls, data):
        return cls(data)

    def dump(self):
        return self.data

@dataclass
class BpmLockEntry(EntryBase):
    NAME : ClassVar[str] = 'BPMLOCK'
    FMT : ClassVar[str] = '?'
    enabled : bool

    @classmethod
    def load(cls, data):
        return cls(*struct.unpack(cls.FMT, data))

    def dump(self):
        return struct.pack(self.FMT, *(getattr(self, f.name) for f in fields(self)))


@dataclass
class ColorEntry(EntryBase):
    NAME : ClassVar[str] = 'COLOR'
    FMT : ClassVar[str] = 'c3s'
    field1 : bytes
    color : bytes

    @classmethod
    def load(cls, data):
        return cls(*struct.unpack(cls.FMT, data))

    def dump(self):
        return struct.pack(self.FMT, *(getattr(self, f.name) for f in fields(self)))


@dataclass
class CueEntry(EntryBase):
    NAME : ClassVar[str] = 'CUE'
    FMT : ClassVar[str] = '>cBIc3s2s'
    field1 : bytes
    index : int
    position : int
    field4 : bytes
    color : bytes
    field6 : bytes
    name : str

    @classmethod
    def load(cls, data):
        info_size = struct.calcsize(cls.FMT)
        info = struct.unpack(cls.FMT, data[:info_size])
        assert len(info) == 6
        name, nullbyte, other = data[info_size:].partition(b'\x00')
        assert nullbyte == b'\x00'
        assert other == b''
        return cls(*info, name.decode('utf-8'))

    def dump(self):
        struct_fields = fields(self)[:-1]
        return b''.join((
            struct.pack(self.FMT, *(getattr(self, f.name) for f in struct_fields)),
            self.name.encode('utf-8'),
            b'\x00',
        ))


@dataclass
class LoopEntry(EntryBase):
    NAME : ClassVar[str] = 'LOOP'
    FMT : ClassVar[str] = '>cBII4sc3sc?'
    field1 : bytes
    index : int
    startposition : int
    endposition : int
    field5 : bytes
    field6 : bytes
    color  : bytes
    field8 : bytes
    locked : bool
    name : str


    @classmethod
    def load(cls, data):
        info_size = struct.calcsize(cls.FMT)
        info = struct.unpack(cls.FMT, data[:info_size])
        assert len(info) == 9
        name, nullbyte, other = data[info_size:].partition(b'\x00')
        assert nullbyte == b'\x00'
        assert other == b''
        return cls(*info, name.decode('utf-8'))

    def dump(self):
        struct_fields = fields(self)[:-1]
        return b''.join((
            struct.pack(self.FMT, *(getattr(self, f.name) for f in struct_fields)),
            self.name.encode('utf-8'),
            b'\x00',
        ))


@dataclass
class FlipEntry(EntryBase):
    NAME : ClassVar[str] = 'FLIP'
    FMT1 : ClassVar[str] = 'cB?'
    FMT2 : ClassVar[str] = '>BI'
    FMT3 : ClassVar[str] = '>BI16s'
    field1 : bytes
    index : int
    enabled : bool
    name : str
    loop : int
    num_actions : int
    actions : list


    @classmethod
    def load(cls, data):
        info1_size = struct.calcsize(cls.FMT1)
        info1 = struct.unpack(cls.FMT1, data[:info1_size])
        assert len(info1) == 3
        name, nullbyte, other = data[info1_size:].partition(b'\x00')
        assert nullbyte == b'\x00'

        info2_size = struct.calcsize(cls.FMT2)
        loop, num_actions = struct.unpack(cls.FMT2, other[:info2_size])
        action_data = other[info2_size:]
        actions = []
        for _ in range(num_actions):
            type_id, size = struct.unpack(cls.FMT2, action_data[:info2_size])
            action_data = action_data[info2_size:]
            if type_id == 0:
                payload = struct.unpack('>dd', action_data[:size])
                actions.append(("JUMP", *payload))
            elif type_id == 1:
                payload = struct.unpack('>ddd', action_data[:size])
                actions.append(("CENSOR", *payload))
            action_data = action_data[size:]
        assert action_data == b''

        return cls(*info1, name.decode('utf-8'), loop, num_actions, actions)

    def dump(self):
        raise NotImplementedError('FLIP entry dumps are not implemented!')


def get_entry_type(entry_name):
    entry_type = UnknownEntry
    for entry_cls in (BpmLockEntry, ColorEntry, CueEntry, LoopEntry, FlipEntry):
        if entry_cls.NAME == entry_name:
            entry_type = entry_cls
            break
    return entry_type

def parse(data: bytes) -> list[EntryBase]:
    versionlen = struct.calcsize(FMT_VERSION)
    version = struct.unpack(FMT_VERSION, data[:versionlen])
    assert version == (0x01, 0x01)

    b64data = data[versionlen:data.index(b'\x00', versionlen)].replace(b'\n', b'')
    padding = b'A==' if len(b64data) % 4 == 1 else (b'=' * (-len(b64data) % 4))
    payload = base64.b64decode(b64data + padding)
    fp = io.BytesIO(payload)
    assert struct.unpack(FMT_VERSION, fp.read(2)) == (0x01, 0x01)
    out = []
    while True:
        entry_name = b''.join(readbytes(fp)).decode('utf-8')
        if not entry_name:
            break
        entry_len = struct.unpack('>I', fp.read(4))[0]
        assert entry_len > 0

        entry_type = get_entry_type(entry_name)
        out += [entry_type.load(fp.read(entry_len))]
    return out
