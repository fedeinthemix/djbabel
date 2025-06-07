import struct
from pathlib import Path
from enum import Enum
from io import BytesIO
from typing import BinaryIO
from collections.abc import Generator
from .types import EntryBase
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
# original Rust code licensed uner MPL-2.0 license

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

def create_entry_class(class_name: str, fields: dict[str, type]) -> type[CEntry]:
    def load_method(cls, data):
        return cls(*data)

    class_dict = {
        'FIELDS': tuple(fields.keys()),
        'load': classmethod(load_method),
        '__annotations__': fields
    }
    return type(class_name, (CEntry,), class_dict)

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
    new_class = create_entry_class(name, {'value' : str},)
    created_classes[name] = new_class

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
    bt = (value,)
    match name:
        case b"bgl":
            field = created_classes['BeatgridLocked'].load(bt)
        case b"mis":
            field = created_classes['Missing'].load(bt)
        case b"rev":
            field = created_classes['ReverseOrder'].load(bt)
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
            field = UnknownBooleanField(name, bt)
    return field

def parse_field_u32(name: bytes, value) -> CEntry:
    vt = (value,)
    match name:
        case b"add":
            field = created_classes['DateAdded'].load(vt)
        case b"tme":
            field = created_classes['FileTime'].load(vt)
        # b"lbl" => ???
        # b"fsb" => ???
        # b"tkn" => ???
        # b"dsc" => ???
        case _:
            field = UnknownU32Field(name, vt)
    return field

def parse_field_path(name: bytes, path: Path) -> CEntry:
    pt = (path,)
    match name:
        case b"fil":
            field = created_classes['FilePath'].load(pt)
        case  b"trk":
            field = created_classes['TrackPath'].load(pt)
        case _:
            field = UnknownPathField(name, pt)
    return field

def parse_field_text(name: bytes, text: str) -> CEntry:
    tt = (text,)
    match name:
        case b"add":
            field = created_classes['DateAddedStr'].load(tt)
        case b"alb":
            field = created_classes['Album'].load(tt)
        case b"art":
            field = created_classes['Artist'].load(tt)
        case b"bit":
            field = created_classes['Bitrate'].load(tt)
        case b"bpm":
            field = created_classes['BPM'].load(tt)
        case b"cmp":
            field = created_classes['Composer'].load(tt)
        case b"com":
            field = created_classes['Comment'].load(tt)
        case b"gen":
            field = created_classes['Genre'].load(tt)
        case b"grp":
            field = created_classes['Grouping'].load(tt)
        case b"key":
            field = created_classes['Key'].load(tt)
        case b"lbl":
            field = created_classes['Label'].load(tt)
        case b"len":
            field = created_classes['Length'].load(tt)
        case b"siz":
            field = created_classes['FileSize'].load(tt)
        case b"smp":
            field = created_classes['SampleRate'].load(tt)
        case b"sng":
            field = created_classes['SongTitle'].load(tt)
        case b"typ":
            field = created_classes['FileType'].load(tt)
        case b"tyr":
            field = created_classes['Year'].load(tt)
        case b"vcn":
            field = created_classes['ColumnName'].load(tt)
        case b"vcw":
            field = created_classes['ColumnWidth'].load(tt)
        case b"vrsn":
            field = created_classes['Version'].load(tt)
        case _:
            field = UnknownTextField(name, tt)
    return field

def parse_field_container(name: bytes, fields) -> CEntry:
    match name:
        case b"srt":
            field = created_classes['Sorting'].load(fields)
        case b"trk":
            field =  created_classes['Track'].load(fields)
        case b"vct":
            field =  created_classes['ColumnTitle'].load(fields)
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
    Track = created_classes['Track']
    def get_pp(acc, trk):
        match trk:
            case Track(value=[v]) if isinstance(v, created_classes['TrackPath']):
                return acc + [v.value]
            case _:
                return acc

    return reduce(get_pp, fields, [])
