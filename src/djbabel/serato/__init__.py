from djbabel.serato.analysis import get_serato_analysis
from djbabel.serato.autotags import get_serato_autotags
from djbabel.serato.beatgrid import get_serato_beatgrid
# from djbabel.serato.markers import get_serato_markers
from djbabel.serato.markers2 import get_serato_markers_v2, CueEntry, BpmLockEntry, LoopEntry, ColorEntry
from djbabel.serato.types import EntryBase
# from djbabel.serato.overview import get_serato_overview
from ..types import ATrack, AMarkerType, AMarker, ABeatGridBPM, ABeatGrid, ADataSource, ALoudness, ASoftware
from .utils import audio_file_type, parse_color, identity

from datetime import date
from mutagen.mp3 import MP3
from mutagen._file import FileType # pyright: ignore
import os
from pathlib import Path
from typing import TypeVar, Callable
import warnings

###########################################################################

map_to_mp3_text_tag = {
    'title' : 'TIT2',
    'artist' : 'TPE1',
    'grouping': 'TPE2',
    'remixer': 'TPE4',
    'composer': 'TCOM',
    'album' : 'TALB',
    'genre' : 'TCON',
    # 'aformat' : 'TFLT', # use audio.mime
    'track_number' : 'TRCK', # may be, e.g. "1/10"
    'disc_number': 'TPOS', # may be, e.g. "1/2"
    'year' : 'TDRC',
    'release_date' : 'TDRL',
    'play_count' : 'TXXX:SERATO_PLAYCOUNT',
    # 'play_count' : 'PCNT', # ID3 standard tag, use Serato one
    'tonality' : 'TKEY',
    'label' : 'TPUB',
    # 'comments' : 'COMM', # special handling
    'track_number' : 'TRCK', # may be, e.g. "1/10"
    'disc_number': 'TPOS', # may be, e.g. "1/2"
    # 'average_bpm' : 'TBPM', # this is rounded, use Serato data instead
    'play_count' : 'TXXX:SERATO_PLAYCOUNT',
    # 'play_count' : 'PCNT', # ID3 standard tag
    'rating': 'POPM', # XXX field .rating!!
}

A = TypeVar('A')
def head(ls: list[A]) -> A | None:
    if len(ls) == 1:
        return ls[0]
    elif len(ls) > 1:
        c = ls[0]
        warnings.warn(f"Multiple ID3 comments, using {c}", UserWarning)
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

def std_tag_text(name: str, tags, f_out: Callable[[str | None]] = identity):
    if name in map_to_mp3_text_tag.keys():
        tag = map_to_mp3_text_tag[name]
        return f_out(head(tags[tag].text)) if tag in tags.keys() else None
    else:
        return None

def std_comments_tag(tags) -> str | None:
    tag = head(list(filter(lambda s: s.startswith('COMM'), tags.keys())))
    return tags[tag].text[0] if tag is not None else None


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


def markers(mkrs: list[EntryBase]) -> list[AMarker]:
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

def release_date(s: str | None):
    return date.fromisoformat(s) if isinstance(s,str) else None
        
###########################################################################

def from_serato(audio: MP3) -> ATrack:

    if audio.tags is not None:
        tags = audio.tags
    else:
        tags = {}

    mkrs: list[EntryBase] = get_serato_markers_v2(audio)

    return ATrack(
        title = std_tag_text('title', tags),
        artist = std_tag_text('artist', tags),
        grouping = std_tag_text('grouping', tags),
        remixer = std_tag_text('remixer', tags),
        composer = std_tag_text('composer', tags),
        album = std_tag_text('album', tags),
        genre = std_tag_text('genre', tags),
        track_number = track_number(std_tag_text('track_number', tags)),
        disc_number = track_number(std_tag_text('disc_number', tags)),
        release_data = release_date(std_tag_text('release_date', tags)),
        play_count = std_tag_text('play_count', tags, to_int),
        tonality = std_tag_text('tonality', tags),
        label = std_tag_text('label', tags),
        comments = std_comments_tag(tags),
        rating = std_tag_text('rating', tags, to_int),
        size = file_size(audio),
        total_time = audio.info.length,
        bit_rate = bitrate(audio),
        sample_rate = samplerate(audio),
        location = location(audio),
        aformat = audio_file_type(audio),
        beatgrid = beatgrid(audio),
        markers = markers(mkrs),
        locked = locked(mkrs),
        color = color(mkrs),
        average_bpm = average_bpm(audio),
        loudness = loudness(audio),
        data_source = data_source(audio),
        trackID = None,
        mix = None,
        date_added = None
    )
