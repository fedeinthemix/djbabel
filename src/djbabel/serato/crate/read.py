# SPDX-FileCopyrightText: 2025 Federico Beffa <beffa@fbengineering.ch>
# SPDX-FileCopyrightText: 2024 Jan Holthuis <jan.holthuis@rub.de>
#
# SPDX-License-Identifier: MPL-2.0

"""Manipulate Serato DJ Pro Crates

A Crate consists of a list of header names and width, followed by the
list of track paths. The full information is extracted with the help
of the function 'take_fields'.  From the result of 'take_fields', the
track list (paths) can be extracted with 'get_track_paths'.
"""

from dataclasses import make_dataclass, dataclass
import struct
from pathlib import Path
from enum import Enum
from io import BytesIO
from typing import BinaryIO
from collections.abc import Generator
from ..types import EntryBase
from functools import reduce

class CrateFieldKind(Enum):
    FIELD_BOOL = b'b'
    FIELD_CONTAINER = b'o'
    FIELD_CONTAINER_R = b'r'
    FIELD_PATH = b'p'
    FIELD_TEXT = b't'
    FIELD_U16 = b's'
    FIELD_U32 = b'u'

#################################################################
# Code based on https://github.com/Holzhaus/triseratops/tree/main
#
# original Rust code licensed uner MPL-2.0 license.
# See LICENSES/MPL-2.0.txt

class CEntry(EntryBase):
    pass

class Unknown(CEntry):
    FIELDS = ('field_type', 'name', 'content')

class UnknownBooleanField(CEntry):
    FIELDS = ('name', 'value')

class UnknownContainerField(CEntry):
    FIELDS = ('name', 'fields')

class UnknownContainerRField(CEntry):
    FIELDS = ('name', 'fields')

class UnknownPathField(CEntry):
    FIELDS = ('name', 'path')

class UnknownU16Field(CEntry):
    FIELDS = ('name', 'value')

class UnknownU32Field(CEntry):
    FIELDS = ('name', 'value')

class UnknownTextField(CEntry):
    FIELDS = ('name', 'text')

############################################################

def create_entry_dataclass(class_name: str, fields: dict[str, type]) -> type[CEntry]:
    fields_list = list(fields.items())

    new_class = make_dataclass(
        class_name,
        fields_list,
        bases=(CEntry,),
    )
    return new_class

created_classes = {} # store dynamically created classes

class_names = {
    # // Library
    'Album': str,
    'Artist': str,
    'BPM': str,
    'BeatgridLocked': bool,
    'Bitrate': str,
    'Comment': str,
    'Composer': str,
    'DateAdded': bytes,
    'DateAddedStr': str,
    'FilePath': Path,
    'FileSize': str,
    'FileTime': bytes,
    'FileType': str,
    'Genre': str,
    'Grouping': str,
    'Key': str,
    'Label': str,
    'Length': str,
    'Missing': bool,
    'SampleRate': str,
    'SongTitle': str,
    'Track': list,
    'Version': str,
    'Year': str,
    # Crates
    'Sorting': list,
    'ReverseOrder': bool,
    'ColumnTitle': list,
    'ColumnName': str,
    'ColumnWidth': str,
    'TrackPath': Path,
}

for name in class_names:
    new_class = create_entry_dataclass(name, {'value' : class_names[name]})
    created_classes[name] = new_class

Album = created_classes['Album']
Artist = created_classes['Artist']
BPM = created_classes['BPM']
BeatgridLocked = created_classes['BeatgridLocked']
Bitrate = created_classes['Bitrate']
Comment = created_classes['Comment']
Composer = created_classes['Composer']
DateAdded = created_classes['DateAdded']
DateAddedStr = created_classes['DateAddedStr']
FilePath = created_classes['FilePath']
FileSize = created_classes['FileSize']
FileTime = created_classes['FileTime']
FileType = created_classes['FileType']
Genre = created_classes['Genre']
Grouping = created_classes['Grouping']
Key = created_classes['Key']
Label = created_classes['Label']
Length = created_classes['Length']
Missing = created_classes['Missing']
SampleRate = created_classes['SampleRate']
SongTitle = created_classes['SongTitle']
Track = created_classes['Track']
Version = created_classes['Version']
Year = created_classes['Year']
Sorting = created_classes['Sorting']
ReverseOrder = created_classes['ReverseOrder']
ColumnTitle = created_classes['ColumnTitle']
ColumnName = created_classes['ColumnName']
ColumnWidth = created_classes['ColumnWidth']
TrackPath = created_classes['TrackPath']

############################################################

def take_field_length(fp: BinaryIO) -> int:
    data, = struct.unpack('>I', fp.read(4))
    return data

def parse_bool(fp: BinaryIO) -> Generator[bool, None, None]:
    data, = struct.unpack('?', fp.read(1))
    yield data

def take_field_desc(fp: BinaryIO) -> Generator[bytes, None, None]:
    raw = fp.read(4)
    l = len(raw)
    if l < 4:
        data = b''
    else:
        data, = struct.unpack('>4s', raw)
    yield data

def take_u16_text(fp: BinaryIO) -> Generator[str, None, None]:
    data = fp.read().decode('utf-16be', errors='replace')
    yield data

def take_u16(fp: BinaryIO) -> Generator[int, None, None]:
    data, = struct.unpack('>H', fp.read(2))
    yield data

def take_u32(fp: BinaryIO) -> Generator[int, None, None]:
    data, = struct.unpack('>I', fp.read(4))
    yield data

def take_field_content(fp: BinaryIO) -> Generator[bytes, None, None]:
    length = take_field_length(fp)
    data = fp.read(length)
    yield data

def take_field_type(desc: bytes) -> bytes:
    return desc[0:1]
    
def take_field_name(desc: bytes) -> bytes:
    return desc[1:4]

############################################################

def parse_field_bool(name: bytes, value: bool) -> CEntry:
    match name:
        case b"bgl":
            field = BeatgridLocked(value)
        case b"mis":
            field = Missing(value)
        case b"rev":
            field = ReverseOrder(value)
        # b"crt" => ???
        # b"hrt" => ???
        # b"iro" => ???
        # b"itu" => ???
        # b"krk" => ???
        # b"ovc" => ???
        # b"ply" => ???
        # b"uns" => ???
        # b"wlb" => ???
        # b"wll" => ???
        case _:
            field = UnknownBooleanField(name, value)
    return field

def parse_field_u32(name: bytes, value) -> CEntry:
    match name:
        case b"add":
            field = DateAdded(value)
        case b"tme":
            field = FileTime(value)
        # b"lbl" => ???
        # b"fsb" => ???
        # b"tkn" => ???
        # b"dsc" => ???
        case _:
            field = UnknownU32Field(name, value)
    return field

def parse_field_path(name: bytes, path: Path) -> CEntry:
    match name:
        case b"fil":
            field = FilePath(path)
        case  b"trk":
            field = TrackPath(path)
        case _:
            field = UnknownPathField(name, path)
    return field

def parse_field_text(name: bytes, text: str) -> CEntry:
    match name:
        case b"add":
            field = DateAddedStr(text)
        case b"alb":
            field = Album(text)
        case b"art":
            field = Artist(text)
        case b"bit":
            field = Bitrate(text)
        case b"bpm":
            field = BPM(text)
        case b"cmp":
            field = Composer(text)
        case b"com":
            field = Comment(text)
        case b"gen":
            field = Genre(text)
        case b"grp":
            field = Grouping(text)
        case b"key":
            field = Key(text)
        case b"lbl":
            field = Label(text)
        case b"len":
            field = Length(text)
        case b"siz":
            field = FileSize(text)
        case b"smp":
            field = SampleRate(text)
        case b"sng":
            field = SongTitle(text)
        case b"typ":
            field = FileType(text)
        case b"tyr":
            field = Year(text)
        case b"vcn":
            field = ColumnName(text)
        case b"vcw":
            field = ColumnWidth(text)
        case b"vrsn":
            field = Version(text)
        case _:
            field = UnknownTextField(name, text)
    return field

def parse_field_container(name: bytes, fields) -> CEntry:
    match name:
        case b"srt":
            field = Sorting(*fields)
        case b"trk":
            field =  Track(*fields)
        case b"vct":
            field =  ColumnTitle(*fields)
        case _:
            field = UnknownContainerField(name, fields)
    return field

def parse_field(content: BinaryIO, name: bytes, field_type: bytes) -> CEntry:
    match field_type:
        case CrateFieldKind.FIELD_BOOL.value:
            value = next(parse_bool(content))
            field = parse_field_bool(name, value)
            return field
        case CrateFieldKind.FIELD_U16.value:
            value = next(take_u16(content))
            field = UnknownU16Field(name, value)
            # b"bav": ???
            return field
        case CrateFieldKind.FIELD_U32.value:
            value = next(take_u32(content))
            field = parse_field_u32(name, value)
            return field
        case CrateFieldKind.FIELD_PATH.value:
            path = next(take_u16_text(content))
            path = Path(path)
            field = parse_field_path(name, path)
            return field
        case CrateFieldKind.FIELD_TEXT.value:
            text = next(take_u16_text(content))
            field = parse_field_text(name, text)
            return field
        case CrateFieldKind.FIELD_CONTAINER.value:
            fields = take_fields(content)
            field = parse_field_container(name, (fields,))
            return field
        case CrateFieldKind.FIELD_CONTAINER_R.value:
            fields = take_fields(content)
            field = UnknownContainerRField(name, fields)
            return field
        case _:
            return Unknown(field_type, name, content)


def parse_field_desc(desc: bytes, content: BinaryIO) -> CEntry:
    match desc:
        # Special case: `vrsn` is a text field but begins with `v`
        case b"vrsn":
            return parse_field(content, desc, CrateFieldKind.FIELD_TEXT.value)
        case _:
            typ = take_field_type(desc)
            name = take_field_name(desc)
            return parse_field(content, name, typ)


def take_field(fp: BinaryIO) -> CEntry | None:
    desc = next(take_field_desc(fp))
    if len(desc) < 4:
        field = None
    else:
        content = next(take_field_content(fp))
        fp_content = BytesIO(content)
        field = parse_field_desc(desc, fp_content)
    return field

def take_fields(fp: BinaryIO) -> list[CEntry]:
    parsed_fields = []
    while field := take_field(fp):
        if field == None:
            break
        else:
            parsed_fields.append(field)
    return parsed_fields

#################################################################

def get_track_paths(fields: list[CEntry]) -> list[Path]:
    def get_pp(acc, trk):
        match trk:
            case Track(value=[v]) if isinstance(v, TrackPath):
                return acc + [v.value]
            case _:
                return acc

    return reduce(get_pp, fields, [])
