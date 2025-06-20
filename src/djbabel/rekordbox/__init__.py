from ..types import APlaylist, ASoftware, ATrack, AFormat, AMarkerType, AMarker, ABeatGridBPM
from ..utils import CLASSIC2ABBREV_KEY_MAP, path_anchor, ms_to_s

from dataclasses import fields, Field, replace
from datetime import date
from functools import reduce
from pathlib import Path
import typing
import types
from urllib.parse import quote, urljoin
import xml.etree.ElementTree as ET

# includes mapping of fields from ATrack to the Rekordbox XML name of
# only those fields whose mapping is not a simple conversion to
# CamelCase. The later are mapped via a function.
REKORDBOX_FIELD_NAMES_MAP = {
    'title' : 'Name',
    # 'artist',
    # 'composer',
    # 'album',
    # 'grouping',
    # 'genre',
    'aformat' : 'kind',
    # 'size',
    # 'total_time',
    # 'disc_number',
    # 'track_number',
    'release_date' : 'Year',
    # 'average_bpm',
    # 'date_added',
    # 'bit_rate',
    # 'sample_rate',
    # 'comments',
    # 'play_count',
    # 'rating',
    # 'location',
    # 'remixer',
    # 'tonality',
    # 'label',
    # 'mix',
    # 'data_source',
    # 'markers',
    # 'beatgrid',
    # 'locked',
    'color' : 'Colour',
    'trackID' : 'TrackID',
    # 'loudness'
}

# Rekordbox mapping from number of start (in the GUI) to the decimal representation of a byte.
REKORDBOX_RATING_MAP = {
    0 : "0",
    1 : "51",
    2 : "102",
    3 : "153",
    4 : "204",
    5 : "255",
}

# Map AMarkerType into the corresponding Rekordbox number
REKORDBOX_MARKERTYPE_MAP = {
    AMarkerType.CUE : "0",
    AMarkerType.FADE_IN : "1",
    AMarkerType.FADE_OUT : "2",
    AMarkerType.CUE_LOAD : "3",
    AMarkerType.LOOP : "4"
}

# Mapping from AFormat to Rekordbox string.
REKORDBOX_AFORMAT_MAP = {
    AFormat.MP3 : 'Mp3-Datei',
    AFormat.FLAC : 'Flac-Datei', # XXX find correct string
    AFormat.M4A : 'Mp4-Datai',  # XXX find correct string
    # AFormat.WAV : 'Wav-Datei',
}
        
def make_or_none_predicate(_type: type):
    """Make a predicate function recognizing the types `_type` or `_type | None`.
    """
    def predicate(field_type):
        t = typing.get_origin(field_type)
        if t is typing.Union or t is types.UnionType:
            args = typing.get_args(field_type)
            return _type in args and (type(None) in args or None in args)
        elif field_type is _type:
            return True
        else:
            return False

    return predicate

is_str_or_none = make_or_none_predicate(str)
is_int_or_none = make_or_none_predicate(int)
is_float_or_none = make_or_none_predicate(float)
is_date_or_none = make_or_none_predicate(date)

def rb_attr_name(s: str) -> str:
    """Convert an ATrack field name (as a string) into the name used by Rekordbox.
    """
    if s in REKORDBOX_FIELD_NAMES_MAP.keys():
        return REKORDBOX_FIELD_NAMES_MAP[s]
    else:
        return ''.join(map(lambda w: w.capitalize(), s.split('_')))

def rb_attr_location(p: Path, ancor:Path | None=None, base_url='file://localhost/') -> str:
    """Convert a root-less Path into a full URL as used by Rekordbox.
    """
    return urljoin(base_url+path_anchor(ancor), quote(p.as_posix()))

def rb_attr_tonality(t: str) -> str:
    """ATrack tonality format (classic) to Rekordbox abbreviated one.
    """
    if t in CLASSIC2ABBREV_KEY_MAP.keys():
        return CLASSIC2ABBREV_KEY_MAP[t]
    else:
        return t

def rb_attr_rating(r: int | None) -> str:
    if isinstance(r, int) and r in REKORDBOX_RATING_MAP.keys():
        return REKORDBOX_RATING_MAP[r]
    else:
        return REKORDBOX_RATING_MAP[0]

def rb_attr_color(c: tuple[int,int,int], source: ASoftware) -> str:
    # Rekordbox colors:
    # Rose(0xFF007F), Red(0xFF0000), Orange(0ｘFFA500), Lemon(0xFFFF00),
    # Green(0x00FF00), Turquoise(0x25FDE9), Blue(0x0000FF), Violet(0x660099)
    RB_DEFAULT_COLOR = '0xFFFF00' # Lemon
    
    if source == ASoftware.REKORDBOX:
        ch = hex(c[0] << 16 + c[1] << 8 + c[2]).upper()
        match ch:
            case '0xFF007F' | '0xFF0000' | '0ｘFFA500' | '0xFFFF00' | '0x00FF00' | '0x25FDE9' | '0x0000FF'  | '0x660099':
                return ch
            case _:
                return RB_DEFAULT_COLOR
    else:
        return RB_DEFAULT_COLOR


def rb_attr(at: ATrack, f: Field, tid: int, ancor: Path | None=None):
    """Convert the ATrack `at` field `f` data into a (name, value) Rekordbox tuple.

    Assign `tid` as the `TrackID` number.
    """
    v = getattr(at, f.name)
    if f.name == 'total_time':
        return [( rb_attr_name(f.name), str(int(v)) if v is not None else "0")]
    elif f.name == 'bit_rate':
        return [( rb_attr_name(f.name), str(int(v/1000)) if v is not None else "0")]
    elif f.name == 'release_date':
        return [( rb_attr_name(f.name), str(v.year) if v is not None else "0")]
    elif f.name == 'location':
        return [( rb_attr_name(f.name), rb_attr_location(v, ancor))]
    elif f.name == 'aformat':
        return [( rb_attr_name(f.name), REKORDBOX_AFORMAT_MAP[v])]
    elif f.name == 'tonality':
        return [( rb_attr_name(f.name), rb_attr_tonality(v))]
    elif f.name == 'color':
        return [( rb_attr_name(f.name), rb_attr_color(v, at.data_source.software))]
    elif f.name == 'rating':
        return [( rb_attr_name(f.name), rb_attr_rating(v))]
    elif f.name == 'trackID':
        return [( rb_attr_name(f.name), str(tid) if v is None else str(v))]
    elif is_str_or_none(f.type):
        return [( rb_attr_name(f.name), v if v is not None else "")]
    elif is_int_or_none(f.type):
        return [( rb_attr_name(f.name), str(v) if v is not None else "0")]
    elif is_float_or_none(f.type):
        return [( rb_attr_name(f.name), str(v) if v is not None else "0")]
    elif is_date_or_none(f.type):
        return [( rb_attr_name(f.name), v.strftime('%Y-%m-%d') if v is not None else "")]
    else:
        return []

def rb_reindex_loops(markers: list[AMarker], software: ASoftware):
    """Reindex Serato DJ Pro loops.

    In Serato loop indexes are independent from cue ones.
    Differently from this, in Rekordbox and Traktor the indexes of
    both types lies in the same namespace (same buttons).
    
    On DJM-S11 you can call up to 16 Hot Cues by pressing the PADS
    (two pages). CDJ-3000 only support 8 Hot Cues.
    
    To accomodate both devices if the number of CUEs + LOOPs <= 8 we
    store the loops at index 8 - (no. LOOPs) to 7.
    
    If CUEs + LOOPs > 8 we store them sequentially, some of them
    will not be usable on CDJ-3000.
    """
    new_markers = []
    match software:
        case ASoftware.SERATO_DJ_PRO:
            # Serato DJ Pro doesn't have FADE-IN/-OUT markers.
            cues = list(filter(
                lambda m: m.kind == AMarkerType.CUE or m.kind == AMarkerType.CUE_LOAD,
                markers))
            loops = list(filter(lambda m: m.kind == AMarkerType.LOOP, markers))
            if len(cues) + len(loops) <= 8:
                i = 8-len(loops)
            else:
                i = len(cues)
            new_markers = cues
            for m in loops:
                new_markers = new_markers + [replace(m, index = i + m.index)]
        case _:
            pass
    return new_markers


def rb_position_mark(m: AMarker) -> ET.Element:
    attrs = {
        'Name'  : m.name,
        'Type'  : REKORDBOX_MARKERTYPE_MAP[m.kind],
        'Start' : str(ms_to_s(m.start)),
        'End'   : str(ms_to_s(m.end))  if m.end is not None else "",
        # rekordbox : Hot Cue A, B, C : "0", "1", "2"; Memory Cue : "-1"
        'Num'   : str(m.index)
    }
    return ET.Element('POSITION_MARK', attrib=attrs)

def rb_tempo(m: ABeatGridBPM, battito: int = 1) -> ET.Element:
    attrs = {
        'Inizio' : str(m.position),
        'Bpm' : str(m.bpm),
        'Metro' : str(m.metro[0]) + '/' + str(m.metro[1]),
        'Battito' : str(battito)
    }
    return ET.Element('TEMPO', attrib=attrs)

def rb_battito(bpms: list[ABeatGridBPM], idx: int, battiti: int = 4):
    """Compute battito in a bar of battiti beats from BPM and position.

    Args:
    -----
      bpms: list of BPMs.
      idx: changes index for which to calculate the battito.
      battiti: beats in a bar.
    """
    battito = 1
    for i, m in enumerate(bpms[:idx]):
        dt = bpms[i+1].position - m.position
        dbeats = m.bpm * dt / 60
        battito = (battito + dbeats) % battiti
    return int(battito)

def to_rekordbox(at: ATrack, tid: int, ancor:Path | None=None) -> ET.Element:
    """Convert an ATrack instance into a Rekordbox XML element.
    """
    fs = fields(at)
    attrs = dict(reduce(lambda acc, f: acc + rb_attr(at, f, tid, ancor),  fs, []))
    trk = ET.Element("TRACK", **attrs)
    for m in rb_reindex_loops(at.markers, at.data_source.software):
        trk.append(rb_position_mark(m))
    for i, m in enumerate(at.beatgrid):
        battito = rb_battito(at.beatgrid, i, m.metro[1])
        trk.append(rb_tempo(m, battito))
    return trk

def to_rekordbox_playlist(playlist: APlaylist, ofile:Path, ancor: Path | None = None) -> None:
    """Generate a RekordBox playlist XML ElementTree.

    Args:
    -----
      playlist: the playlist to convert.
    
      ancor: The path of track files are stored without the ancor
        (root and, on Windows drive). With this parameter it can be
        specified. If None the OS default is used: '/' for POSIX,
        'C:\\' for Windows.

    """
    # XML tree root
    dj_pl = ET.Element('DJ_PLAYLISTS', Version="1.0.0")
    root = ET.ElementTree(dj_pl)
    # PRODUCT sub-element
    prod = ET.Element('PRODUCT', Name="rekordbox", Version="6.6.2", Company="AlphaTheta")
    dj_pl.append(prod)
    # COLLECTION sub-element
    coll = ET.Element('COLLECTION', Entries=str(playlist.entries))
    dj_pl.append(coll)
    # TRACK SUb-sub-elements
    for i, at in enumerate(playlist.tracks):
        e = to_rekordbox(at, i, ancor)
        dj_pl.append(e)
    # PLAYLIST sub-element
    pl = ET.Element('PLAYLISTS')
    dj_pl.append(pl)
    node = ET.Element('NODE', Type="0", Name="ROOT", Count="1")
    pl.append(node)
    # Type: "0" (FOLDER) or "1" (PLAYLIST)
    # KeyType serves for indexing: 0" (Track ID) or "1"(Location)
    # key: TrackID or URL location depending on KeyType.
    node1 = ET.Element('NODE', Name=playlist.name, Type="1", KeyType="0", Entries=str(playlist.entries))
    # can actually specify playlist 'folder' (using Type="0") to
    # categorize them. We should add the possibility to specify a
    # path.
    node.append(node1)
    for i, _ in enumerate(playlist.tracks):
        node1.append(ET.Element('TRACK', Key=str(i)))
    root.write(ofile, "utf-8", True)
    return None
