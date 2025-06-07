import struct
import base64
import io
from mutagen._file import FileType

from .types import SeratoTags, EntryBase
from .utils import get_serato_metadata, FMT_VERSION, readbytes

def get_serato_markers_v2(audio: FileType) -> dict | None:
    return get_serato_metadata(SeratoTags.MARKERS2, parse)(audio)

###############################################################################
# Code from https://github.com/Holzhaus/serato-tags
#
# Copyright 2019 Jan Holthuis
#
# original code licensed under the MIT License

class Entry(EntryBase):
    pass


class UnknownEntry(Entry):
    NAME = None
    FIELDS = ('data',)

    @classmethod
    def load(cls, data):
        return cls(data)

    def dump(self):
        return self.data


class BpmLockEntry(Entry):
    NAME = 'BPMLOCK'
    FIELDS = ('enabled',)
    FMT = '?'

    @classmethod
    def load(cls, data):
        return cls(*struct.unpack(cls.FMT, data))

    def dump(self):
        return struct.pack(self.FMT, *(getattr(self, f) for f in self.FIELDS))


class ColorEntry(Entry):
    NAME = 'COLOR'
    FMT = 'c3s'
    FIELDS = ('field1', 'color',)

    @classmethod
    def load(cls, data):
        return cls(*struct.unpack(cls.FMT, data))

    def dump(self):
        return struct.pack(self.FMT, *(getattr(self, f) for f in self.FIELDS))


class CueEntry(Entry):
    NAME = 'CUE'
    FMT = '>cBIc3s2s'
    FIELDS = ('field1', 'index', 'position', 'field4', 'color', 'field6',
              'name',)

    @classmethod
    def load(cls, data):
        info_size = struct.calcsize(cls.FMT)
        info = struct.unpack(cls.FMT, data[:info_size])
        name, nullbyte, other = data[info_size:].partition(b'\x00')
        assert nullbyte == b'\x00'
        assert other == b''
        return cls(*info, name.decode('utf-8'))

    def dump(self):
        struct_fields = self.FIELDS[:-1]
        return b''.join((
            struct.pack(self.FMT, *(getattr(self, f) for f in struct_fields)),
            self.name.encode('utf-8'),
            b'\x00',
        ))


class LoopEntry(Entry):
    NAME = 'LOOP'
    FMT = '>cBII4s4sB?'
    FIELDS = ('field1', 'index', 'startposition', 'endposition', 'field5',
              'field6', 'color', 'locked', 'name',)

    @classmethod
    def load(cls, data):
        info_size = struct.calcsize(cls.FMT)
        info = struct.unpack(cls.FMT, data[:info_size])
        name, nullbyte, other = data[info_size:].partition(b'\x00')
        assert nullbyte == b'\x00'
        assert other == b''
        return cls(*info, name.decode('utf-8'))

    def dump(self):
        struct_fields = self.FIELDS[:-1]
        return b''.join((
            struct.pack(self.FMT, *(getattr(self, f) for f in struct_fields)),
            self.name.encode('utf-8'),
            b'\x00',
        ))


class FlipEntry(Entry):
    NAME = 'FLIP'
    FMT1 = 'cB?'
    FMT2 = '>BI'
    FMT3 = '>BI16s'
    FIELDS = ('field1', 'index', 'enabled', 'name', 'loop', 'num_actions',
              'actions')

    @classmethod
    def load(cls, data):
        info1_size = struct.calcsize(cls.FMT1)
        info1 = struct.unpack(cls.FMT1, data[:info1_size])
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

def parse(data):
    versionlen = struct.calcsize(FMT_VERSION)
    version = struct.unpack(FMT_VERSION, data[:versionlen])
    assert version == (0x01, 0x01)

    b64data = data[versionlen:data.index(b'\x00', versionlen)].replace(b'\n', b'')
    padding = b'A==' if len(b64data) % 4 == 1 else (b'=' * (-len(b64data) % 4))
    payload = base64.b64decode(b64data + padding)
    fp = io.BytesIO(payload)
    assert struct.unpack(FMT_VERSION, fp.read(2)) == (0x01, 0x01)
    while True:
        entry_name = b''.join(readbytes(fp)).decode('utf-8')
        if not entry_name:
            break
        entry_len = struct.unpack('>I', fp.read(4))[0]
        assert entry_len > 0

        entry_type = get_entry_type(entry_name)
        yield entry_type.load(fp.read(entry_len))
