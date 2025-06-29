from .analysis import get_serato_analysis
from .autotags import get_serato_autotags
from .beatgrid import get_serato_beatgrid
# from djbabel.serato.markers import get_serato_markers
from .markers2 import get_serato_markers_v2, CueEntry, BpmLockEntry, LoopEntry, ColorEntry
from .types import EntryBase
# from djbabel.serato.overview import get_serato_overview
from ..types import ATrack, AMarkerType, AMarker, ABeatGridBPM, ADataSource, ALoudness, ASoftware, AFormat, APlaylist
from .utils import audio_file_type, parse_color, identity
from ..utils import path_anchor, get_leading_base64_part, closest_color_perceptual, ms_to_s, audio_endocer
from .crate import take_fields, get_track_paths

import base64
from collections.abc import Callable
from datetime import date
import io
import mutagen
from mutagen.mp4 import MP4FreeForm, AtomDataType
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

# there can multiple tags with the same key, e.g., for multiple authors
# case INSENSITIVE
# https://xiph.org/vorbis/doc/v-comment.html
map_to_flac_text_tag = {
    ## stadnard defined
    'title' : 'title',
    'artist' : 'artist',
    'album' : 'album',
    'grouping': 'grouping',
    'mix' : 'version',
    'composer': 'composer',
    'genre' : 'genre',
    'release_date' : 'date',
    'label' : 'organization',
    'track_number' : 'tracknumber', # may be, e.g. "1/10"
    ## community defined
    'disc_number': 'discnumber', # may be, e.g. "1/2"
    'remixer': 'remixer',
    # 'comments' : 'COMMENT', # special handling
    'rating': 'rating', # XXX field .rating!!
    ## other
    'tonality' : 'initialkey',
    # 'average_bpm' : 'BPM', # this is rounded, use Serato data instead
    'play_count' : 'serato_playcount',
    # 'play_count' : 'PLAY_COUNT', # use Serato one
}

map_to_mp4_tag = {
    'title': '©nam',       # common name for title
    'artist': '©ART',      # common name for artist
    'album': '©alb',       # common name for album
    'grouping': '©grp',     # common name for grouping
    'composer': '©wrt',     # common name for composer (writer)
    'genre': '©gen',       # common name for genre
    'year': '©day',        # common name for year/creation date
    'release_date': '©day', # often also uses ©day, or custom tag for more specific date
    'label': '©lab',       # not a standard MP4 tag, often custom or using '©too' (encoder)
    'track_number': 'trkn', # track number, often stores 'track/total' as a tuple
    'disc_number': 'disk',  # disc number, often stores 'disc/total' as a tuple
    'remixer': '©rem',     # not a standard MP4 tag, often custom or using '©too'
    'rating': 'rtng',      # rating (e.g., 0-100)
    # 'play_count': 'pcnt',   # play count (specific to Apple/iTunes)
    'play_count': '----:com.serato.dj:playcount', # used by Serato
    # 'tonality': '©key',    # not a standard MP4 tag, often custom (e.g., 'key')
    'tonality' : '----:com.apple.iTunes:initialkey', # used by Serato
    # 'comments': '©cmt',   # comments
}

map_to_aformat = {
    AFormat.MP3 : map_to_mp3_text_tag,
    AFormat.FLAC : map_to_flac_text_tag,
    AFormat.M4A : map_to_mp4_tag,
}

###########################################################################
# Helpers

A = TypeVar('A')
def head(ls: list[A]) -> A | None:
    if len(ls) == 1:
        return ls[0]
    elif len(ls) > 1:
        c = ls[0]
        warnings.warn(f"Multiple entries {ls}. Using {c}", UserWarning)
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

def parse_m4a_play_count(data: MP4FreeForm) -> int:
    ds = get_leading_base64_part(bytes(data))
    if len(ds) % 4 == 1:
        padding = b'B=='
    else:
        padding = b'=' * (-len(ds) % 4)
    payload = base64.b64decode(ds + padding)
    # first convert to int, otherwise we get a byte string.
    return int(payload[:payload.index(b'\x00')])

def parse_flac_m4a_tag_value(tags: dict[str, Any], tag: str) -> str | None:
    vs = tags[tag]
    if len(vs) > 0:
        v = vs[0]
        if isinstance(v, str):
            return ','.join(vs)
        # Serato play_count
        elif tag == map_to_mp4_tag['play_count'] and isinstance(v, MP4FreeForm) and v.FORMAT_TEXT ==  AtomDataType.UTF8:
            try:
                pc = parse_m4a_play_count(v)
            except Exception as _:
                warnings.warn("Failed to decode Serato play_count. Using 0")
                pc = 0
            return str(pc)
        # Serato initialkey
        elif isinstance(v, MP4FreeForm) and v.FORMAT_TEXT ==  AtomDataType.UTF8:
            return v.decode('UTF-8')
            # return ','.join(list(map(lambda x: x.decode('UTF-8'), vs)))
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
    aformat = audio_file_type(audio)
    tag_map = map_to_aformat[aformat]

    match aformat:
        case AFormat.MP3:
            if name in tag_map.keys():
                tag = tag_map[name]
                # .text field in not of type str
                return f_out(str(head(tags[tag].text))) if tag in tags.keys() else None
            else:
                return None

        # FLAC metadate tag keys are case insensitive
        case AFormat.FLAC:
            if name in tag_map.keys():
                tag = tag_map[name]
                tag_keys = tags.keys()
                if tag.lower() in tag_keys:
                    return f_out(parse_flac_m4a_tag_value(tags, tag))
                else:
                    return None
            else:
                return None

        # M4A metadate tag keys are case sensitive
        case AFormat.M4A:
            if name in tag_map.keys():
                tag = tag_map[name]
                tag_keys = tags.keys()
                if tag in tag_keys:
                    return f_out(parse_flac_m4a_tag_value(tags, tag))
                else:
                    return None
            else:
                return None

        case _:
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

def file_size(audio: FileType) -> int:
    if audio.filename is None:
        s = 0
    else:
        try:
            s = os.path.getsize(audio.filename)
        except FileNotFoundError:
            s = 0
    return s


def beatgrid(audio: FileType) -> list[ABeatGridBPM]:
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
    return bpms

# Markers2 are used at least since Serato DJ Pro 2.3 (2019)
def get_markers(mkrs: list[EntryBase]) -> list[AMarker]:
    def from_serato(m: EntryBase) -> AMarker:
        match m:
            case CueEntry(_, index, position, _, color, _, name): # pyright: ignore [reportGeneralTypeIssues]
                color_rbg = parse_color(color)
                return AMarker(name, closest_color_perceptual(color_rbg), ms_to_s(position), None, AMarkerType.CUE, index, False)
            case LoopEntry(_, index, start, end, _, _, color, _, locked, name): # pyright: ignore [reportGeneralTypeIssues]
                color_rbg = parse_color(color)
                return AMarker(name, closest_color_perceptual(color_rbg), ms_to_s(start), ms_to_s(end), AMarkerType.LOOP, index, locked)
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

def average_bpm(audio: FileType) -> float | None:
    at = get_serato_autotags(audio)
    return at['bpm'] if at is not None else None

def loudness(audio: FileType) -> ALoudness | None:
    at = get_serato_autotags(audio)
    return ALoudness(at['autogain'], at['gaindb']) if isinstance(at, dict) else None

def data_source(audio: FileType) -> ADataSource:
    an = get_serato_analysis(audio)
    v = an if an is not None else []
    enc = audio_endocer(audio)
    return ADataSource(ASoftware.SERATO_DJ_PRO, v, enc)

def location(audio: FileType) -> Path:
    if audio.filename is not None:
        return Path(audio.filename)
    else:
        raise ValueError("Required file path is missing")

def bitrate(audio: FileType) -> int:
    if audio.info is not None and audio.info.bitrate is not None:
        return audio.info.bitrate
    else:
        raise ValueError(f"No bitrate info for file {audio.filename}.")

def samplerate(audio: FileType) -> int:
    if audio.info is not None and audio.info.sample_rate is not None:
        return audio.info.sample_rate
    else:
        raise ValueError(f"No sample_rate info for file {audio.filename}.")

###########################################################################

def from_serato(audio: FileType) -> ATrack:

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
        release_date = release_date(audio),
        play_count = std_tag_text('play_count', audio, to_int),
        tonality = std_tag_text('tonality', audio),
        label = std_tag_text('label', audio),
        comments = std_comments_tag(audio),
        rating = std_tag_text('rating', audio, to_int),
        size = file_size(audio),
        total_time = audio.info.length, # pyright: ignore
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

def read_serato_playlist(crate: Path, anchor: Path | None = None, relative: Path | None = None) -> APlaylist:
    """Read a Serato DJ Pro Crate.

    Args:
    -----
      crate: Crate path
      anchor: Path anchor to add to the track paths in the crate
    """
    with open(crate, "rb") as f:
        data = f.read()

    fp = io.BytesIO(data)
    paths = get_track_paths(take_fields(fp))
    audios = []
    for p in paths:
        pr = p.relative_to(relative) if relative is not None else p
        a = mutagen.File(path_anchor(anchor) / pr, easy=False) # pyright: ignore
        if a is None:
            print(f'File {p} could not be read.')
        else:
            audios = audios + [a]
    name = crate.stem
    atrks = list(map(from_serato, audios))
    return APlaylist(name, atrks)
