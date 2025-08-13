import base64
from datetime import date
import io
import mutagen
import mutagen.id3
from mutagen.id3 import Frame, GEOB, Encoding # pyright: ignore
from mutagen.mp4 import AtomDataType, MP4FreeForm
from mutagen._file import FileType # pyright: ignore
from pathlib import Path
import struct
from typing import Literal
import warnings

from .analysis import Analysis
from .autotags import dump as dump_autotags, AutoTags
from .beatgrid import NonTerminalBeatgridMarker, TerminalBeatgridMarker, Footer
from .markers import EntryType, Entry, Color
from .markers import dump as dump_markers
from .markers import dump_m4a as dump_markers_m4a
from .markers2 import BpmLockEntry, ColorEntry, CueEntry, LoopEntry
from ..types import (
    AFormat,
    AMarker,
    AMarkerColors,
    AMarkerType,
    ATrack,
    ATransformation,
    APlaylist,
)
from .types import SeratoTags
from ..utils import s_to_ms, audio_file_type
from .utils import (
    pack_color,
    FMT_VERSION,
    serato_tag_marker,
    get_tags,
    map_to_aformat
)
from .crate.write import (
    write_fields,
    Version,
    Sorting,
    ColumnName,
    ColumnTitle,
    ColumnWidth,
    ReverseOrder,
    Track,
    TrackPath,
)

#########################################################################

###### Analysis ######

def to_serato_analysis(at: ATrack) -> Analysis:
    """Convert to the low-level Serato DJ Pro tag representation.
    """
    match at.aformat:
        case AFormat.MP3:
            return Analysis([2, 1])
        case AFormat.FLAC | AFormat.M4A:
            # In sime files we saw a last digit of 100.
            return Analysis([0, 1, 0])
        case _:
            raise ValueError(f"to_serato_analysis: file format not supported {at.aformat}.")


def dump_serato_analysis(an: Analysis) -> bytes:
    """Convert the low-level Serato DJ Pro tag representation to the tag bytes.
    """
    return bytes(an.version)

###### Autotags ######

def to_serato_autotags(at: ATrack) -> AutoTags | None:
    """Convert to the low-level Serato DJ Pro tag representation.
    """
    if at.average_bpm is None or at.loudness is None:
        return None
    else:
        return AutoTags(at.average_bpm, at.loudness.autogain, at.loudness.gain_db)


def dump_serato_autotags(ag: AutoTags) -> bytes:
    """Convert the low-level Serato DJ Pro tag representation to the tag bytes.
    """
    assert ag is not None, "dump_serato_autotags: Autotags is None."
    return dump_autotags(ag)

###### Markers2 ######

def to_serato_markers_v2(at: ATrack) -> list[CueEntry | LoopEntry | ColorEntry | BpmLockEntry]:
    """Convert to the low-level Serato DJ Pro tag representation.
    """
    def to_serato(m: AMarker | tuple[int,int,int] | bool) -> CueEntry | LoopEntry | ColorEntry | BpmLockEntry:
        default_color = AMarkerColors.BLUE.value
        match m:
            case AMarker(name, color, start, end, AMarkerType.CUE, index, locked) | AMarker(name, color, start, end, AMarkerType.CUE_LOAD, index, locked):
                c = pack_color(color.value) if color is not None else pack_color(default_color)
                return CueEntry(b'\x00', index, round(s_to_ms(start)), b'\x00', c, b'\x00\x00', name)
            case AMarker(name, color, start, end, AMarkerType.LOOP, index, locked):
                c = pack_color(color.value) if color is not None else pack_color(default_color)
                return LoopEntry(b'\x00', index, round(s_to_ms(start)), round(s_to_ms(end)), b'\xff\xff\xff\xff', b'\x00', c, b'\x00', locked, name)
            case (_, _, _):
                return ColorEntry(b'\x00', pack_color(m))
            case v if isinstance(v, bool):
                return BpmLockEntry(v)
            case _:
                raise ValueError(f"{m} can't be converted to a Serato Marker2")

    if at.color is None:
        track_color = (255, 255, 255) # default Serato DJ Pro track color
    else:
        track_color = at.color
    m2s = [track_color] + at.markers + [at.locked]
    return list(map(to_serato, m2s))


def insert_newlines(data: bytes, period:int = 72) -> bytes:
    if len(data) <= 72:
        return data
    else:
        byte_list = list(data)
        modified_list = []
        for i, byte_char in enumerate(byte_list):
            modified_list.append(byte_char)
            if (i + 1) % period == 0 and (i + 1) < len(byte_list):
                modified_list.append(ord(b'\n'))
        return bytes(modified_list)


def remove_b64padding(data: bytes) -> bytes:
    return data.replace(b'A=', b'').replace(b'=', b'')


def dump_serato_markers_v2(entries: list[ColorEntry | CueEntry | LoopEntry | BpmLockEntry]) -> bytes:
    """Convert the low-level Serato DJ Pro tag representation to the tag bytes.
    """
    null = struct.pack('B', 0x00)
    oneone = struct.pack(FMT_VERSION, 0x01, 0x01)
    data = io.BytesIO()

    # start bytes
    data.write(oneone)

    for entry in entries:
        # entry name
        entry_name = entry.NAME.encode('utf-8')     
        data.write(entry_name + null)
        # length
        payload = entry.dump()
        data.write(struct.pack('>I', len(payload)))
        # data
        data.write(payload)

    b64data = base64.b64encode(data.getvalue() + null)
    # Serato seems to remove b64 encoding padding.
    b64data = remove_b64padding(b64data)

    # If the content is very long, a linefeed character is
    # inserted into the base64 string every 72 bytes.
    b64data = insert_newlines(b64data, 72)
    b64data_len = len(b64data)

    # The b64data written by Serato seems to have a minium length of
    # 470 bytes. If it's shorter, it's null padded. (2 bytes header excluded)
    padding = b'\x00' * (468 - b64data_len) if b64data_len < 468 else b''

    return oneone + b64data + padding

###### Markers ######

def markers_dummies(af: AFormat) -> bytes:
    if af != AFormat.M4A:
        return b'\x00\x7f\x7f\x7f\x7f\x7f'
    else:
        return b'\x00\xff\xff\xff\xff\xff'

def to_serato_markers(at: ATrack) -> list[Entry | Color]:
    """Convert to the low-level Serato DJ Pro tag representation.
    """
    # FLAC files don't use MARKERS
    if at.aformat == AFormat.FLAC:
        return []

    def to_serato(m: AMarker | tuple[int,int,int] | bool) -> tuple[int, Entry | Color] | tuple[None, None]:
        default_color = AMarkerColors.BLUE.value
        match m:
            case (AMarker(_, color, start, end, AMarkerType.CUE, index, locked)
                  | AMarker(_, color, start, end, AMarkerType.CUE_LOAD, index, locked)):
                c = pack_color(color.value) if color is not None else pack_color(default_color)
                if index < 5:
                    return (index,
                            Entry(True,
                                  round(s_to_ms(start)),
                                  False,
                                  None,
                                  markers_dummies(at.aformat),
                                  c,
                                  EntryType.CUE,
                                  locked))
                else:
                    return (None, None)
            case AMarker(_, color, start, end, AMarkerType.LOOP, index, locked):
                c = pack_color(color.value) if color is not None else pack_color(default_color)
                if index < 9:
                    return (5 + index,
                            Entry(True,
                                  round(s_to_ms(start)),
                                  True,
                                  round(s_to_ms(end)),
                                  markers_dummies(at.aformat),
                                  c,
                                  EntryType.LOOP,
                                  locked))
                else:
                    return (None, None)
            case (_, _, _):
                return (14, Color(pack_color(m)))
            case _:
                raise ValueError(f"{m} can't be converted to a Serato Marker")

    if at.color is None:
        track_color = (255, 255, 255) # default Serato DJ Pro track color
    else:
        track_color = at.color

    # initialize with empty data
    out = [
        Entry(False,
              None,
              False,
              None,
              markers_dummies(at.aformat),
              b'\x00\x00\x00',
              EntryType.INVALID,
              False)
    ] * 5 + [
        Entry(False,
              None,
              False,
              None,
              markers_dummies(at.aformat),
              b'\x00\x00\x00',
              EntryType.LOOP,
              False)
    ] * 9 + [
        Color(b'\x00\x00\x00')
    ]
    for m in at.markers + [track_color]:
        index, entry = to_serato(m)
        if entry is not None and index is not None:
            out[index] = entry

    return out


def dump_serato_markers(entries: list[Color | Entry], af: AFormat) -> bytes:
    """Convert the low-level Serato DJ Pro tag representation to the tag bytes.
    """
    match af:
        case AFormat.MP3:
            return dump_markers(entries)
        case AFormat.M4A:
            return dump_markers_m4a(entries)
        case AFormat.FLAC:
            warnings.warn(f"dump_serato_markers: FLAC files don't use markers!")
            return b''
        case _:
            raise ValueError(f"dump_serato_markers: file format {af} not supported")

###### Beatgrid ######

# The meaning of the footer is uncelar. We found:

# 2 M4A tracks with a footer of 65
# - blow-go.m4a
# - supergirl.m4a
# But 1 M4a track with a footer of 109
# - 2-01-Paid_in_Full.m4a

# 1 FLAC file with a footer of 0
# - MARRS-Pump_up_the_volume.flac

# 2 MP3 files with a footer of 116
# - The_Todd_Terry_Project_-_Weekend.mp3
# - De_Lacy_-_Hideaway_(Deep_Dish_Remix).mp3

# For the moment we set the footer based on the most common value we
# observed for each audio format.
def beatgrid_footer(at: ATrack) -> Footer:
    match at.aformat:
        case AFormat.MP3:
            return Footer(116)
        case AFormat.FLAC:
            return Footer(0)
        case AFormat.M4A:
            return Footer(65)
        case _:
            raise ValueError(f"to_serato_beatgrid: file_format {at.aformat} not supported.")


def to_serato_beatgrid(at: ATrack) -> list[NonTerminalBeatgridMarker | TerminalBeatgridMarker | Footer]:
    """Convert to the low-level Serato DJ Pro tag representation.
    """
    out = []
    for i, entry in enumerate(at.beatgrid[:-1]):
        dt = at.beatgrid[i+1].position - entry.position
        beats = round(entry.bpm * dt / 60)
        out.append(NonTerminalBeatgridMarker(entry.position, beats))
    if len(at.beatgrid) > 0:
        term_bg = at.beatgrid[-1]
        out.append(TerminalBeatgridMarker(term_bg.position, term_bg.bpm))
    out.append(beatgrid_footer(at))
    return out
        
    
def dump_serato_beatgrid(bg: list[NonTerminalBeatgridMarker | TerminalBeatgridMarker | Footer]) -> bytes:
    """Convert the low-level Serato DJ Pro tag representation to the tag bytes.
    """
    data = io.BytesIO()

    # header bytes
    data.write(struct.pack(FMT_VERSION, 0x01, 0x00))

    # length
    num_markers = len(bg) - 1 # discard footer
    data.write(struct.pack('>I', num_markers))

    # entries
    for i, entry in enumerate(bg):
        match entry:
            case TerminalBeatgridMarker(position, bpm):
                # The last entry is Footer
                assert i == num_markers - 1, f"dump_serato_beatgrid: TerminalBeatgridMarker in non-final position.\nWrong beatgrid markers order!"
                data.write(struct.pack('>f', position))
                data.write(struct.pack('>f', bpm))
            case NonTerminalBeatgridMarker(position, beats_till_next_marker):
                assert i < num_markers - 1, f"dump_serato_beatgrid: NonTerminalBeatgridMarker in final position.\nWrong beatgrid markers order!"
                data.write(struct.pack('>f', position))
                data.write(struct.pack('>I', beats_till_next_marker))
            case Footer(unknown):
                assert i == num_markers, f"dump_serato_beatgrid: Footer in non-final position.\nWrong beatgrid markers order!"
                data.write(struct.pack('B', unknown))
            case _:
                raise ValueError(f"dump_serato_beatgrid: Unexpected entry {entry}")

    return insert_newlines(data.getvalue())

###### Envelope ######

def envelope_padding_min_len(stag: SeratoTags) -> int:
    match stag:
        case SeratoTags.MARKERS2:
            return 515
        case _:
            return 0


def add_envelope(data: bytes, stag: SeratoTags) -> bytes:
    """Add envelope bytes used in FLAC and M4A files.
    """
    env_marker = serato_tag_marker(stag)
    prefix = b'application/octet-stream\x00\x00' + env_marker + b'\x00'

    if stag == SeratoTags.AUTOTAGS or stag == SeratoTags.BEATGRID:
        data_trimmed = remove_b64padding(data + b'\x00')
    else:
        data_trimmed = remove_b64padding(data)

    min_len = envelope_padding_min_len(stag)
    data_trimmed_len = len(data_trimmed)
    padding = b'\x00' * (min_len - data_trimmed_len) if data_trimmed_len < min_len else b''
    b64data = base64.b64encode(prefix + data_trimmed + padding)
    return remove_b64padding(insert_newlines(b64data))

#########################################################################
###### handle overwrite ######

Action = Literal["continue", "break", "process"]


def ask_to_overwrite(tag: str, path: Path) -> str:
    while True:
        overwrite = input(f'{path}: Overwrite tag {tag} (y/[n]/Y/N)? ')
        if overwrite not in ['y', 'n', 'Y', 'N']:
            print(f"Please answer 'n' for NO, 'y' for YES, 'N' for NO to all, or 'Y' for YES to all.\n")
        else:
            return overwrite


def handle_existing_tag(tag: str, tags: dict, overwrite: str, location: Path) -> tuple[Action, str]:
    if tag in tags and overwrite != 'Y':
        if overwrite == 'N':
            return "break", overwrite
        else:
            ow = ask_to_overwrite(tag, location)
            if ow in ['Y', 'N']:
                overwrite = ow
            if ow not in ['y', 'Y']:
                return "continue", overwrite
    return "process", overwrite

#########################################################################

def is_m4afreeform(tag: str) -> bool:
    return tag.startswith('----:')


def format_m4a_std_tag(tag: str, value: str | int | date) -> list[MP4FreeForm] | list[str] | list[int]:
    if is_m4afreeform(tag): # tonality
        return [MP4FreeForm(str(value).encode('utf-8'), dataformat=AtomDataType.UTF8)]
    elif isinstance(value, int):
        return [str(value)]
    elif isinstance(value, date):
        return [value.strftime('%Y-%m-%d')]
    else:
        return [value]


def format_mp3_std_tag(tag: str, value: int | str | date) -> Frame:
    match value:
        case int(v):
            text = str(value)
        case date(year=_, month=_, day=_):
            text = value.strftime('%Y-%m-%d')
        case str(v):
            text = v
        case _:
            raise ValueError(f"format_mp3_std_tag: unexpected tag {tag} value {value}.")

    FrameClass = getattr(mutagen.id3, tag)
    if tag == 'COMM':
        desc = "ID3v1 Comment"
        return FrameClass(encoding=3, desc=desc, lang="eng", text=text)
    else:
        return FrameClass(encoding=3, text=text)


def format_flac_std_tag(tag: str, value: int | str | date) -> list[str]:
    match value:
        case int(v):
            return [str(value)]
        case date(year=_, month=_, day=_):
            return [value.strftime('%Y-%m-%d')]
        case str(v):
            return [v]
        case _:
            raise ValueError(f"format_mp3_std_tag: unexpected tag {tag} value {value}.")


def format_std_tags(field_name: str, tag: str, value, aformat: AFormat) -> Frame | list[str] | list[MP4FreeForm] | list[int] | None:
    match aformat:
        case AFormat.MP3:
            return format_mp3_std_tag(tag, value)
        case AFormat.FLAC:
            return format_flac_std_tag(tag, value)
        case AFormat.M4A:
            # track number has to be written as a tuple
            # [(track_number, total_tracks)]
            #
            # XXX for the moment we omit it
            if not (field_name in ['track_number', 'disc_number']):
                return format_m4a_std_tag(tag, value)
            else:
                return None
        case _:
            raise ValueError(f"format_std_tags: File format {aformat} not supported")


def add_std_tags(at: ATrack, audio: FileType, overwrite: str) -> tuple[FileType, str]:
    tags = get_tags(audio)
    tag_map = map_to_aformat[at.aformat]

    for field_name in ['title', 'artist', 'grouping', 'remixer', 'composer', 'album', 'genre', 'track_number', 'disc_number', 'tonality', 'label', 'release_date', 'comments' ]:
        tag = tag_map[field_name]

        action, overwrite = handle_existing_tag(tag, tags, overwrite, at.location)
        match action:
            case 'break':
                break
            case 'continue':
                continue

        v = getattr(at, field_name)
        if v is None:
            continue

        tag_value = format_std_tags(field_name, tag, v, at.aformat)
        if tag_value is not None:
            audio[tag] = tag_value
    return audio, overwrite


def split_tag_name(tag: str) -> tuple[str, str, str]:
    tag_parts = tag.split(':')
    if len(tag_parts) == 3:
        return tag_parts[0], tag_parts[1], tag_parts[2]
    elif len(tag_parts) == 2:
        return tag_parts[0], tag_parts[1], ""
    elif len(tag_parts) == 1:
        return tag_parts[0], "", ""
    else:
        raise ValueError(f"split_tag_name: unexpected tag {tag}")


def add_serato_tag(at, audio, overwrite, stag, to_low, dump):
    tag = stag.value.names[at.aformat]
    low = to_low(at)
    if low != [] and low is not None:
        data = dump(low)
        match at.aformat:
            case AFormat.MP3:
                _, tag_desc, _ = split_tag_name(tag)
                frame = GEOB(encoding=Encoding.UTF8,
                             mime="application/octet-stream",
                             desc=tag_desc,
                             data=data)
                audio.tags.add(frame)
            case AFormat.FLAC:
                audio[tag] = add_envelope(data, stag).decode('ascii')
            case AFormat.M4A:
                audio[tag] = MP4FreeForm(data=add_envelope(data, stag))
            case _:
                raise ValueError(f"add_serato_markers: file format {at.aformat} not supported")            
    return audio, overwrite

#########################################################################
#### Main ####

def to_serato(at: ATrack, trans: ATransformation, overwrite: str = 'n') -> str:
    """Convert an ATrack instance into 'Serato DJ Pro' metadata.

    The metadta is written to the tags expected by Serato in the audio
    file specified by the 'location' attribute of the ATrack instance.

    Args:
      at: The ATrack instance.
      trans: ATransformation instance specifying the configuration.

    Returns:
      The overwrite state ('n', 'N', 'y', 'Y').
    """

    audio = mutagen.File(at.location, easy=False) # pyright: ignore
    if audio is None:
        warnings.warn(f"to_serato: file {at.location} not accessible")
        return overwrite

    try:
        audio, overwrite = add_std_tags(at, audio, overwrite)

        # XXX play_count (tag 'TXXX:SERATO_PLAYCOUNT'): encoding not
        # reverse engineered.

        audio, overwrite = add_serato_tag(at, audio, overwrite,
                                          SeratoTags.MARKERS,
                                          to_serato_markers,
                                          lambda es: dump_serato_markers(es, at.aformat))
        audio, overwrite = add_serato_tag(at, audio, overwrite,
                                          SeratoTags.MARKERS2,
                                          to_serato_markers_v2,
                                          dump_serato_markers_v2)
        audio, overwrite = add_serato_tag(at, audio, overwrite,
                                          SeratoTags.BEATGRID,
                                          to_serato_beatgrid,
                                          dump_serato_beatgrid)
        audio, overwrite = add_serato_tag(at, audio, overwrite,
                                          SeratoTags.ANALYSIS,
                                          to_serato_analysis,
                                          dump_serato_analysis)
        audio, overwrite = add_serato_tag(at, audio, overwrite,
                                          SeratoTags.AUTOTAGS,
                                          to_serato_autotags,
                                          dump_serato_autotags)
    finally:
        audio.save()
    return overwrite


def to_serato_playlist(playlist: APlaylist, ofile: Path, trans: ATransformation, overwrite: str = 'n') -> None:
    """Generate a Serato DJ Pro Crate playlist and write tags to audio files.

    Args:
    -----
      playlist: the playlist to convert.
      ofile: output file name.
      trans: information about the source and target format.
    """
    # header
    crate = [
        Version(value='1.0/Serato ScratchLive Crate'),
        Sorting(value=[ColumnName(value='#'), ReverseOrder(value=False)]),
        ColumnTitle(value=[ColumnName(value='playCount'), ColumnWidth(value='0')]),
        ColumnTitle(value=[ColumnName(value='artist'), ColumnWidth(value='0')]),
        ColumnTitle(value=[ColumnName(value='song'), ColumnWidth(value='0')]),
        ColumnTitle(value=[ColumnName(value='bpm'), ColumnWidth(value='0')]),
        ColumnTitle(value=[ColumnName(value='key'), ColumnWidth(value='0')]),
        ColumnTitle(value=[ColumnName(value='album'), ColumnWidth(value='0')]),
        ColumnTitle(value=[ColumnName(value='length'), ColumnWidth(value='0')]),
        ColumnTitle(value=[ColumnName(value='comment'), ColumnWidth(value='0')]),
    ]

    for at in playlist.tracks:
        # write tags to audio file
        overwrite = to_serato(at, trans, overwrite)
        # In Crates, Serato removes the drive and root components
        p = at.location.relative_to(at.location.anchor)
        crate.append(Track([TrackPath(p)]))

    with open(ofile, "wb") as f:
        write_fields(f, crate)

    return None
