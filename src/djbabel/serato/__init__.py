from djbabel.serato.analysis import get_serato_analysis
from djbabel.serato.autotags import get_serato_autotags
from djbabel.serato.beatgrid import get_serato_beatgrid
# from djbabel.serato.markers import get_serato_markers
from djbabel.serato.markers2 import get_serato_markers_v2, CueEntry, BpmLockEntry, LoopEntry, ColorEntry
from djbabel.serato.types import EntryBase
# from djbabel.serato.overview import get_serato_overview
from ..types import ATrack, AMarkerType, AMarker, ABeatGridBPM, ABeatGrid, ADataSource, ALoudness, ASoftware, AFormat
from .utils import audio_file_type, parse_color, identity

from collections.abc import Callable
from datetime import date
from functools import reduce
from mutagen.mp3 import MP3
from mutagen._file import FileType # pyright: ignore
import os
from pathlib import Path
from typing import TypeVar, Any
import warnings

###########################################################################

# https://mutagen-specs.readthedocs.io/en/latest/id3/id3v2.4.0-frames.html
map_to_mp3_text_tag = {
    'title' : 'TIT2',
    'artist' : 'TPE1',
    'album' : 'TALB',
    'grouping': 'TIT1',
    'composer': 'TCOM',
    'genre' : 'TCON',
    # 'aformat' : 'TFLT', # use audio.mime
    'year' : 'TDRC',
    'release_date' : 'TDRL',
    'label' : 'TPUB',
    'track_number' : 'TRCK', # may be, e.g. "1/10"
    'disc_number': 'TPOS', # may be, e.g. "1/2"
    'remixer': 'TPE4',
    # 'comments' : 'COMM', # special handling
    'rating': 'POPM', # XXX field .rating!!
    'play_count' : 'TXXX:SERATO_PLAYCOUNT',
    # 'play_count' : 'PCNT', # ID3 standard tag, use Serato one
    'tonality' : 'TKEY',
    # 'average_bpm' : 'TBPM', # this is rounded, use Serato data instead
    'play_count' : 'TXXX:SERATO_PLAYCOUNT',
    # 'play_count' : 'PCNT', # ID3 standard tag
}

# the can multiple tags with the same key, e.g., for multiple authors
# case INSENSITIVE
# https://xiph.org/vorbis/doc/v-comment.html
map_to_flac_text_tag = {
    ## stadnard defined
    'title' : 'TITLE',
    'artist' : 'ARTIST',
    'album' : 'ALBUM',
    'grouping': 'GROUPING',
    'mix' : 'VERSION',
    'composer': 'COMPOSER',
    'genre' : 'GENRE',
    'release_date' : 'DATE',
    'label' : 'ORGANIZATION',
    'track_number' : 'TRACKNUMBER', # may be, e.g. "1/10"

    ## community defined
    'disc_number': 'DISCNUMBER', # may be, e.g. "1/2"
    'remixer': 'REMIXER',
    # 'comments' : 'COMMENT', # special handling
    'rating': 'RATING', # XXX field .rating!!

    ## other
    'tonality' : 'initialkey',
    # 'average_bpm' : 'BPM', # this is rounded, use Serato data instead
    'play_count' : 'serato_playcount',
    # 'play_count' : 'PLAY_COUNT', # use Serato one
}

###########################################################################
# Helpers

A = TypeVar('A')
def head(ls: list[A]) -> A | None:
    if len(ls) == 1:
        return ls[0]
    elif len(ls) > 1:
        c = ls[0]
        warnings.warn(f"Multiple comments, using {c}", UserWarning)
        return c
    else:
        return None

def to_int(x) -> int:
    if x is not None and x.isnumeric():
        return int(x)
    else:
        return 0

def track_number(s: str | None) -> int | None:
    if isinstance(s, str):
        parts = s.split('/')
        if parts:
            try:
                return int(parts[0])
            except ValueError:
                return None
        else:
            return None
    else:
        return None

###########################################################################
# metadata from standard tags

def get_tags(audio: FileType):
    if audio.tags is not None:
        tags = audio.tags
    else:
        tags = {}
    return tags

def std_tag_text(name: str, audio: FileType, f_out: Callable[[str | None],Any] = identity):

    tags = get_tags(audio)

    match audio_file_type(audio):
        case AFormat.MP3:
            tag_map = map_to_mp3_text_tag
            if name in tag_map.keys():
                tag = tag_map[name]
                return f_out(str(head(tags[tag].text))) if tag in tags.keys() else None
            else:
                return None

        case AFormat.FLAC:
            tag_map = map_to_flac_text_tag
            if name in tag_map.keys():
                tag = tag_map[name].lower()
                tag_keys = tags.keys()
                if tag in tag_keys and len(tag_keys) > 1:
                    return f_out(head(tags[tag]))
                elif tag in tag_keys and len(tag_keys) > 1:
                    return f_out(reduce(lambda acc, e: acc + ', ' + e, tags[tag], ''))
                else:
                    return None
            else:
                return None

        case _:
            tag_map = {}
            return None


def std_comments_tag(audio: FileType) -> str | None:
    tags = get_tags(audio)

    match audio_file_type(audio):
        case AFormat.MP3:
            tag = head(list(filter(lambda s: s.startswith('COMM'), tags.keys())))
            return tags[tag].text[0] if tag is not None else None
        case AFormat.FLAC:
            return std_tag_text('comments', audio)
        case _:
            return None


def release_date(audio: FileType):
    s = std_tag_text('release_date', audio)
    if s is None:
        # try with year
        y = std_tag_text('year', audio)
        if isinstance(y, str) and y.isnumeric():
            return date.fromisoformat(y + '-01-01')
        else:
            return None
    elif s.isnumeric():
        return date.fromisoformat(s + '-01-01')
    else:
        return date.fromisoformat(s)

###########################################################################
# other metadata

def file_size(audio: MP3) -> int:
    if audio.filename is None:
        s = 0
    else:
        try:
            s = os.path.getsize(audio.filename)
        except FileNotFoundError:
            s = 0
    return s


def beatgrid(audio: MP3) -> ABeatGrid:
    def from_serato(bg: list) -> list[ABeatGridBPM]:
        if len(bg) < 2:
            return []
        else:
            res = []
            for i in range(1,len(bg)-1): # the last entry is a Footer
                pos = bg[i-1].position
                bpm = bg[i-1].beats_till_next_marker * 60 / (bg[i].position - pos)
                res = res + [ABeatGridBPM(pos, bpm)]
            return res + [ABeatGridBPM(bg[-2].position, bg[-2].bpm)]

    bg = get_serato_beatgrid(audio)
    bpms = from_serato(bg) if bg is not None else []
    return ABeatGrid(bpms)


def get_markers(mkrs: list[EntryBase]) -> list[AMarker]:
    def from_serato(m: EntryBase) -> AMarker:
        match m:
            case CueEntry(_, index, position, _, color, _, name): # pyright: ignore [reportGeneralTypeIssues]
                return AMarker(name, parse_color(color), position, None, AMarkerType.CUE, index, False)
            case LoopEntry(_, index, start, end, _, _, color, _, locked, name): # pyright: ignore [reportGeneralTypeIssues]
                return AMarker(name, parse_color(color), start, end, AMarkerType.LOOP, index, locked)
            # Flip not implemented. They are Serato specific.
            # case djbabel.serato.markers2..FlipEntry():
            case _:
                raise ValueError(f"Marker of unexpected type {m}")

    cues = filter(lambda e: isinstance(e, CueEntry) or isinstance(e, LoopEntry), mkrs)
    return list(map(from_serato, cues))


def locked(mkrs: list[EntryBase]) -> bool:
    def from_serato(m: EntryBase) -> bool:
        match m:
            case BpmLockEntry(enabled): # pyright: ignore [reportGeneralTypeIssues]
                return enabled
            case _:
                return False

    locks = filter(lambda e: isinstance(e, BpmLockEntry), mkrs)
    e = head(list(map(from_serato, locks)))
    return e if e is not None else False


def color(mkrs: list[EntryBase]) -> tuple[int, int, int] | None:
    def from_serato(m: EntryBase) -> tuple[int, int, int] | None:
        match m:
            case ColorEntry(_, color): # pyright: ignore [reportGeneralTypeIssues]
                return parse_color(color)
            case _:
                return None

    color = filter(lambda e: isinstance(e, ColorEntry), mkrs)
    return head(list(map(from_serato, color)))

def average_bpm(audio: MP3) -> float | None:
    at = get_serato_autotags(audio)
    return at['bpm'] if at is not None else None

def loudness(audio: MP3) -> ALoudness | None:
    at = get_serato_autotags(audio)
    return ALoudness(at['autogain'], at['gaindb']) if isinstance(at, dict) else None

def data_source(audio: MP3) -> ADataSource:
    an = get_serato_analysis(audio)
    v = an if an is not None else []
    return ADataSource(ASoftware.SERATO_DJ_PRO, v)

def location(audio: FileType) -> Path:
    if audio.filename is not None:
        return Path(audio.filename)
    else:
        raise ValueError("Required file path is missing")

def bitrate(audio) -> int:
    if audio.info is not None and audio.info.bitrate is not None:
        return audio.info.bitrate
    else:
        raise ValueError(f"No bitrate info for file {audio.filename}.")

def samplerate(audio) -> int:
    if audio.info is not None and audio.info.sample_rate is not None:
        return audio.info.sample_rate
    else:
        raise ValueError(f"No sample_rate info for file {audio.filename}.")

###########################################################################

def from_serato(audio: MP3) -> ATrack:

    mkrs: list[EntryBase] = get_serato_markers_v2(audio)

    return ATrack(
        title = std_tag_text('title', audio),
        artist = std_tag_text('artist', audio),
        grouping = std_tag_text('grouping', audio),
        remixer = std_tag_text('remixer', audio),
        composer = std_tag_text('composer', audio),
        album = std_tag_text('album', audio),
        genre = std_tag_text('genre', audio),
        track_number = track_number(std_tag_text('track_number', audio)),
        disc_number = track_number(std_tag_text('disc_number', audio)),
        release_data = release_date(audio),
        play_count = std_tag_text('play_count', audio, to_int),
        tonality = std_tag_text('tonality', audio),
        label = std_tag_text('label', audio),
        comments = std_comments_tag(audio),
        rating = std_tag_text('rating', audio, to_int),
        size = file_size(audio),
        total_time = audio.info.length,
        bit_rate = bitrate(audio),
        sample_rate = samplerate(audio),
        location = location(audio),
        aformat = audio_file_type(audio),
        beatgrid = beatgrid(audio),
        markers = get_markers(mkrs),
        locked = locked(mkrs),
        color = color(mkrs),
        average_bpm = average_bpm(audio),
        loudness = loudness(audio),
        data_source = data_source(audio),
        trackID = None,
        mix = None,
        date_added = None
    )
