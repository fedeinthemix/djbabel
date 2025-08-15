# SPDX-FileCopyrightText: 2025 Federico Beffa <beffa@fbengineering.ch>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import struct
from io import BytesIO
from typing import BinaryIO

from .read import (
    CEntry,
    CrateFieldKind,
    Album,
    Artist,
    BPM,
    BeatgridLocked,
    Bitrate,
    Comment,
    Composer,
    DateAdded,
    DateAddedStr,
    FilePath,
    FileSize,
    FileTime,
    FileType,
    Genre,
    Grouping,
    Key,
    Label,
    Length,
    Missing,
    SampleRate,
    SongTitle,
    Track,
    Version,
    Year,
    Sorting,
    ReverseOrder,
    ColumnTitle,
    ColumnName,
    ColumnWidth,
    TrackPath
)

#################################################################

def dump_field_desc(fp: BinaryIO, desc: bytes) -> int:
    data = struct.pack('>4s', desc)
    return fp.write(data)

def dump_field_length(fp: BinaryIO, length: int) -> int:
    data = struct.pack('>I', length)
    return fp.write(data)

def dump_bool(fp: BinaryIO, data: bool) -> int:
    b = struct.pack('?', data)
    l = dump_field_length(fp, len(b))
    return fp.write(b) + l

def dump_u16_text(fp: BinaryIO, content: str) -> int:
    data = content.encode('utf-16be', errors='replace')
    l = dump_field_length(fp, len(data))
    return fp.write(data) + l

def dump_u16(fp: BinaryIO, content: str) -> int:
    data = struct.pack('>H', content)
    l = dump_field_length(fp, len(data))
    return fp.write(data) + l

def dump_u32(fp: BinaryIO, content: str) -> int:
    data = struct.pack('>I', content)
    l = dump_field_length(fp, len(data))
    return fp.write(data) + l

############################################################

def field_type(data: CEntry) -> bytes:
    match data:
        case BeatgridLocked(_) | Missing(_) | ReverseOrder(_):
            return CrateFieldKind.FIELD_BOOL.value
        case DateAdded(_) | FileTime(_):
            return CrateFieldKind.FIELD_U32.value
        case FilePath(_) | TrackPath(_):
            return CrateFieldKind.FIELD_PATH.value
        case Sorting(_) | ColumnTitle(_) | Track(_):
            return CrateFieldKind.FIELD_CONTAINER.value
        case _:
            return CrateFieldKind.FIELD_TEXT.value


def field_name(data: CEntry) -> bytes:
    match data:
        case BeatgridLocked(_):
            return b"bgl"
        case Missing(_):
            return b"mis"
        case ReverseOrder(_):
            return b"rev"
        case DateAdded(_):
            return b"add"
        case FileTime(_):
            return b"tme"
        case FilePath(_):
            return b"fil"
        case TrackPath(_):
            return b"trk"
        case DateAddedStr(_):
             return b"add"
        case Album(_):
             return b"alb"
        case Artist(_):
             return b"art"
        case Bitrate(_):
             return b"bit"
        case BPM(_):
             return b"bpm"
        case Composer(_):
             return b"cmp"
        case Comment(_):
             return b"com"
        case Genre(_):
             return b"gen"
        case Grouping(_):
             return b"grp"
        case Key(_):
             return b"key"
        case Label(_):
             return b"lbl"
        case Length(_):
             return b"len"
        case FileSize(_):
             return b"siz"
        case SampleRate(_):
             return b"smp"
        case SongTitle(_):
             return b"sng"
        case FileType(_):
             return b"typ"
        case Year(_):
             return b"tyr"
        case ColumnName(_):
             return b"vcn"
        case ColumnWidth(_):
             return b"vcw"
        case Version(_):
             return b"vrsn"
        case Sorting(_):
             return b"srt"
        case Track(_):
             return b"trk"
        case ColumnTitle(_):
             return b"vct"
        case _:
            raise ValueError(f"field_name: invalid data {data}")


def dump_field_content(fp: BinaryIO, f_name: bytes, f_type: bytes, content: str) -> int:
    match f_type:
        case CrateFieldKind.FIELD_BOOL.value:
            return dump_bool(fp, bool(content))
        case CrateFieldKind.FIELD_U32.value:
            return dump_u32(fp, content)
        case CrateFieldKind.FIELD_PATH.value:
            return dump_u16_text(fp, str(content))
        case CrateFieldKind.FIELD_TEXT.value:
            return dump_u16_text(fp, content)
        case CrateFieldKind.FIELD_CONTAINER.value | CrateFieldKind.FIELD_CONTAINER_R.value:
            return dump_field_desc(fp, f_name)
        case _:
            raise ValueError(f"dump_field_content: unknown desc {f_type} {f_name}")


def write_field(fp: BinaryIO, data: CEntry) -> int:
    """Transform a CEntry into the binary Serato DJ Pro Crate format.

    Args:
       BinaryIO: A bynary stream to write into.
       CEntry: The class entry to convert.

    Returns:
       int: Number of bytes written.
    """
    f_type = field_type(data)
    f_name = field_name(data)
    content = data.value # pyright: ignore

    # 'vsrn' is an exception
    if f_name == b'vrsn':
        dc = dump_field_desc(fp, f_name)
        cc = dump_field_content(fp, f_name, CrateFieldKind.FIELD_TEXT.value, content)
        return dc + cc
    else:
        desc = f_type + f_name
        match f_type:
            case CrateFieldKind.FIELD_CONTAINER.value:
                dc = dump_field_desc(fp, desc)
                fp_container = BytesIO()
                write_fields(fp_container, content)
                container = fp_container.getvalue()
                # fp.seek(0, io.SEEK_END) # fp should already be at the end
                lc = dump_field_length(fp, len(container))
                return fp.write(container) + lc + dc
            case _:
                dc = dump_field_desc(fp, desc)
                cc = dump_field_content(fp, f_name, f_type, content)
                return dc + cc


def write_fields(fp: BinaryIO, data: list[CEntry]) -> int:
    """Transform a list of CEntry into the binary Serato DJ Pro Crate format.

    Args:
       BinaryIO: A bynary stream to write into.
       list[CEntry]: The list of entries to convert.

    Returns:
       int: Number of bytes written.
    """
    b = 0 # number of bytes written
    for d in data:
        b += write_field(fp, d)
    return b
