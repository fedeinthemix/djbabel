# from djbabel.serato.types import SeratoTags
from djbabel.serato.analysis import get_serato_analysis
from djbabel.serato.autotags import get_serato_autotags
from djbabel.serato.beatgrid import get_serato_beatgrid
# from djbabel.serato.markers import get_serato_markers
from djbabel.serato.markers2 import get_serato_markers_v2, CueEntry, BpmLockEntry, LoopEntry, ColorEntry
# from djbabel.serato.overview import get_serato_overview
from ..types import ATrack, AMarkerType, AMarker, ABeatGridBPM, ABeatGrid, ADataSource, ALoudness, ASoftware
from .utils import audio_file_type, parse_color

from dataclasses import fields
from mutagen.mp3 import MP3
import os
from pathlib import Path
from typing import TypeVar
import warnings


def from_serato_marker2(m):
    """Convert a Serato DJ Pro marker v2 into an AMarker, or Bool (in case of Lock).
    """
    match m:
        case CueEntry(_, index, position, _, color, _, name): # pyright: ignore [reportGeneralTypeIssues]
            return AMarker(name, parse_color(color), position, None, AMarkerType.CUE, index, False)
        case LoopEntry(_, index, start, end, _, _, color, _, locked, name): # pyright: ignore [reportGeneralTypeIssues]
            return AMarker(name, parse_color(color), start, end, AMarkerType.LOOP, index, locked)
        case BpmLockEntry(enabled): # pyright: ignore [reportGeneralTypeIssues]
            return enabled
        # Flip not implemented. They are Serato specific.
        # case djbabel.serato.markers2..FlipEntry():
        case ColorEntry(_, color): # pyright: ignore [reportGeneralTypeIssues]
            return parse_color(color)
        case _:
            return None


def from_serato_beatgrid(bg):
    """Generate a list of ABeatgridBPM from Serato markers.
    """
    if len(bg) < 2:
        return []
    else:
        res = []
        for i in range(1,len(bg)-1): # the last entry is a Footer
            pos = bg[i-1].position
            bpm = bg[i-1].beats_till_next_marker * 60 / (bg[i].position - pos)
            res = res + [ABeatGridBPM(pos, bpm)]
        return res + [ABeatGridBPM(bg[-2].position, bg[-2].bpm)]


def mp3_metadata(audio: MP3, name: str):
    """Construct an ATrack from an MP3 with Serato tags.
    """
    if audio.tags is not None:
        tags = audio.tags
    else:
        tags = {}
    
    map_to_mp3_tag = {
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
        'release_data' : 'TDRL',
        # 'average_bpm' : 'TBPM', # this is rounded, use Serato data instead
        'play_count' : 'TXXX:SERATO_PLAYCOUNT',
        # 'play_count' : 'PCNT', # ID3 standard tag
        'tonality' : 'TKEY',
        'label' : 'TPUB',
        # 'rating': 'POPM', # special handling
        # 'comments' : 'COMM', # special handling
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
    
    match name:
        case n if n in map_to_mp3_tag.keys():
            tag = map_to_mp3_tag[n]
            return head(tags[tag].text) if tag in tags.keys() else None
        case 'comments':
            tag = head(list(filter(lambda s: s.startswith('COMM'), tags.keys())))
            return tags[tag].text[0] if tag is not None else None
        case 'rating':
            tag = head(list(filter(lambda s: s.startswith('POPM'), tags.keys())))
            return tags[tag].rating if tag is not None else None
        case 'size':
            if audio.filename is None:
                s = 0
            else:
                try:
                    s = os.path.getsize(audio.filename)
                except FileNotFoundError:
                    s = None
            return s
        case 'total_time':
            return audio.info.length
        case 'bit_rate':
            return audio.info.bitrate # type: ignore[reportUnknownMemberType]
        case 'sample_rate':
            return float(audio.info.sample_rate) # type: ignore[reportUnknownMemberType]
        case 'location':
            return Path(audio.filename) # type: ignore[reportUnknownMemberType]
        case 'aformat':
            return audio_file_type(audio)
        case 'beatgrid':
            bg = get_serato_beatgrid(audio)
            bpms = from_serato_beatgrid(bg)
            return ABeatGrid(bpms)
        case 'markers':
            mkrs = get_serato_markers_v2(audio)
            cues = filter(lambda e: isinstance(e, CueEntry), mkrs)
            return list(map(from_serato_marker2, cues))
        case 'locked':
            mkrs = get_serato_markers_v2(audio)
            locks = filter(lambda e: isinstance(e, BpmLockEntry), mkrs)
            return head(list(map(from_serato_marker2, locks)))
        case 'color':
            mkrs = get_serato_markers_v2(audio)
            color = filter(lambda e: isinstance(e, ColorEntry), mkrs)
            return head(list(map(from_serato_marker2, color)))
        case 'average_bpm':
            at = get_serato_autotags(audio)
            return at['bpm'] if at is not None else None
        case 'loudness':
            at = get_serato_autotags(audio)
            return ALoudness(at['autogain'], at['gaindb']) if isinstance(at, dict) else None
        case 'data_source':
            an = get_serato_analysis(audio)
            v = an if an is not None else []
            return ADataSource(ASoftware.SERATO_DJ_PRO, v)
        case 'trackID' | 'mix' | 'date_added':
            return None
        case _:
            raise ValueError(f"Unknown tag name {name}")


def from_serato_audio(audio: MP3):
    field_names = list(map(lambda x: x.name, fields(ATrack)))
    ds = dict([(e, mp3_metadata(audio, e)) for e in field_names])
    return ATrack(**ds) # pyright: ignore[reportArgumentType]
