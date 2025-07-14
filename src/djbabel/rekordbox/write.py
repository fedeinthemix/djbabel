from ..types import APlaylist, ASoftware, ATrack, AFormat, AMarkerType, AMarker, ABeatGridBPM, AMarkerColors, ATransformation
from ..utils import CLASSIC2ABBREV_KEY_MAP, adjust_time, is_str_or_none, is_int_or_none, is_float_or_none, is_date_or_none, reindex_sdjpro_loops

from dataclasses import fields, Field, replace
from datetime import date
from functools import reduce
from math import ceil
from pathlib import Path
from urllib.parse import quote, urljoin
import xml.etree.ElementTree as ET

#######################################################################
# Mappings

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
    AFormat.MP3 : 'MP3 File',
    AFormat.FLAC : 'FLAC File',
    AFormat.M4A : 'MP4 File',
    # AFormat.WAV : 'WAV FILE',
}

#######################################################################
# Main functions

##### Attributes ##########

def rb_attr_name(s: str) -> str:
    """Convert an ATrack field name (as a string) into the name used by Rekordbox.
    """
    if s in REKORDBOX_FIELD_NAMES_MAP.keys():
        return REKORDBOX_FIELD_NAMES_MAP[s]
    else:
        return ''.join(map(lambda w: w.capitalize(), s.split('_')))

def rb_attr_location(p: Path, base_url='file://localhost/') -> str:
    """Convert a root-less Path into a full URL as used by Rekordbox.
    """
    return urljoin(base_url, quote(p.as_posix()))

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
        ch = '0x' + f"{c[0]:02x}{c[1]:02x}{c[2]:02x}".upper()
        match ch:
            case '0xFF007F' | '0xFF0000' | '0xFFA500' | '0xFFFF00' | '0x00FF00' | '0x25FDE9' | '0x0000FF'  | '0x660099':
                return ch
            case _:
                return RB_DEFAULT_COLOR
    else:
        return RB_DEFAULT_COLOR


def rb_attr(at: ATrack, f: Field, tid: int):
    """Convert the ATrack `at` field `f` data into a (name, value) Rekordbox tuple.

    Assign `tid` as the `TrackID` number.
    """
    v = getattr(at, f.name)
    if f.name == 'total_time':
        return [( rb_attr_name(f.name), str(ceil(v)) if v is not None else "0")]
    elif f.name == 'bit_rate':
        return [( rb_attr_name(f.name), str(int(v/1000)) if v is not None else "0")]
    elif f.name == 'release_date':
        return [( rb_attr_name(f.name), str(v.year) if v is not None else "0")]
    elif f.name == 'location':
        return [( rb_attr_name(f.name), rb_attr_location(v))]
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
        return [( rb_attr_name(f.name), v.strftime('%Y-%m-%d') if v is not None else date.today().strftime('%Y-%m-%d'))]
    else:
        return []

##### Markers ##########

def rb_marker_color(c: AMarkerColors) -> tuple[int,int,int]:
    match c:
        case AMarkerColors.RED:
            return (230, 40, 40)
        case AMarkerColors.RED_ORANGE:
            return (224, 100, 27)
        case AMarkerColors.ORANGE:
            return (224, 100, 27)
        case AMarkerColors.YELLOW:
            return (180, 190, 4)
        case AMarkerColors.LIME_gREEN:
            return (165, 225, 22)
        case AMarkerColors.DARK_GREEN:
            return (40, 226, 20)
        case AMarkerColors.BRIGHT_GREEN:
            return (40, 226, 20)
        case AMarkerColors.LIGHT_GREEN:
            return (16, 177, 118)
        case AMarkerColors.TEAL:
            return (16, 177, 118)
        case AMarkerColors.CYAN:
            return (31, 163, 146)
        case AMarkerColors.SKY_BLUE:
            return (80, 180, 255)
        case AMarkerColors.BLUE:
            return (48, 90, 255)
        case AMarkerColors.DARK_BLUE:
            return (48, 90, 255)
        case AMarkerColors.VIOLET:
            return (180, 50, 255)
        case AMarkerColors.MAGENTA:
            return (222, 68, 207)
        case AMarkerColors.HOT_PING:
            return (255, 18, 123)

def rb_position_mark(m: AMarker) -> ET.Element:
    attrs = {
        'Name'  : m.name,
        'Type'  : REKORDBOX_MARKERTYPE_MAP[m.kind],
        'Start' : str(m.start),
        'End'   : str(m.end)  if m.end is not None else "",
        # rekordbox : Hot Cue A, B, C : "0", "1", "2"; Memory Cue : "-1"
        'Num'   : str(m.index)
    }
    if m.color is not None:
        r, g, b = rb_marker_color(m.color)
        colors = {
            'Red' : str(r),
            'Green' : str(g),
            'Blue' : str(b)
        }
        attrs.update(colors)

    return ET.Element('POSITION_MARK', attrib=attrs)

##### BeatGrid ##########

def rb_tempo(m: ABeatGridBPM, battito: int = 1) -> ET.Element:
    attrs = {
        'Inizio' : str(m.position),
        'Bpm' : str(m.bpm),
        'Metro' : str(m.metro[0]) + '/' + str(m.metro[1]),
        'Battito' : str(battito)
    }
    return ET.Element('TEMPO', attrib=attrs)

def rb_battito(bpms: list[ABeatGridBPM], idx: int):
    """Compute battito in a bar of battiti beats from BPM and position.

    Args:
    -----
      bpms: list of BPMs.
      idx: changes index for which to calculate the battito.
    """
    # metro is fixed for an entire track.
    metro = bpms[0].metro[1] if len(bpms) > 0 else 4
    battito = 0
    for i, m in enumerate(bpms[:idx]):
        dt = bpms[i+1].position - m.position
        dbeats = m.bpm * dt / 60
        battito += dbeats
    return 1 + round(battito) % metro

##### Min ##########

def to_rekordbox(at: ATrack, tid: int, trans: ATransformation) -> ET.Element:
    """Convert an ATrack instance into a Rekordbox XML element.

    The time of markers and beatgrid is adjusted to reflect the shift
    in absolute time between the various programs.

    """
    fs = fields(at)
    attrs = dict(reduce(lambda acc, f: acc + rb_attr(at, f, tid),  fs, []))
    trk = ET.Element("TRACK", **attrs)
    new_at = adjust_time(at, trans)
    for m in reindex_sdjpro_loops(new_at.markers, trans):
        trk.append(rb_position_mark(m))
    for i, m in enumerate(new_at.beatgrid):
        battito = rb_battito(new_at.beatgrid, i)
        trk.append(rb_tempo(m, battito))
    return trk

def to_rekordbox_playlist(playlist: APlaylist, ofile:Path, trans: ATransformation) -> None:
    """Generate a RekordBox playlist XML file.

    Args:
    -----
      playlist: the playlist to convert.
      ofile: output file name.
      trans: information about the source and target format.
    """
    # XML tree root
    dj_pl = ET.Element('DJ_PLAYLISTS', Version="1.0.0")
    root = ET.ElementTree(dj_pl)
    # PRODUCT sub-element
    ver = '.'.join(map(str,trans.target.version))
    prod = ET.Element('PRODUCT', Name="rekordbox", Version=ver, Company="AlphaTheta")
    dj_pl.append(prod)
    # COLLECTION sub-element
    coll = ET.Element('COLLECTION', Entries=str(playlist.entries))
    dj_pl.append(coll)
    # TRACK SUb-sub-elements
    for i, at in enumerate(playlist.tracks):
        e = to_rekordbox(at, i, trans)
        coll.append(e)
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
