from datetime import date, datetime
from pathlib import Path, PurePath
import warnings
import xml.etree.ElementTree as ET

from ..types import ABeatGridBPM, ADataSource, AFormat, ALoudness, AMarker, APlaylist, ASoftware, ATrack
from .utils import TRAKTOR_MARKERTYPE_MAP, TRAKTOR_MARKERTYPE_MAP, is_album_tag_attr, is_entry_tag_attr, is_tempo_tag_attr, is_info_tag_attr, traktor_attr_name, is_musical_key_attr
from ..utils import CLASSIC2OPEN_KEY_MAP, OPEN_KEY2MUSICAL_KEY_MAP, inverse_dict, ms_to_s, to_int, to_float, path_anchor

###################################################################

########## Helpers ######################

def get_tag_attr(fn: str, tag: ET.Element) -> str | None:
    tn = traktor_attr_name(fn)
    match tn:
        case None:
            return None
        case 'BITRATE':
            v = tag.get(tn)
            return v if v != "-1" else None
        case _:
            return tag.get(tn)


def make_get_subtag(xpath: str):
    def get_subtag(fn: str, entry: ET.Element) -> str | None:
        tag = entry.find(xpath)
        if tag is not None:
            return get_tag_attr(fn, tag)
        else:
            return None

    return get_subtag


def to_date(d: str | None) -> date | None:
    if d is None:
        return d
    else:
        return datetime.strptime(d, "%Y/%m/%d").date()


def to_bool(l: str | None) -> bool:
    if l == "0":
        return False
    elif l == "1":
        return True
    else:
        return False


def aformat_from_path(p: Path) -> AFormat:
    match p.suffix.lower():
        case '.mp3':
            return AFormat.MP3
        case '.flac':
            return AFormat.FLAC
        case '.m4a' | '.aac' | '.mp4':
            return AFormat.M4A
        case _:
            raise ValueError(f"Audio format of {p} is not supported.")

########## ALBUM ######################

get_album_subtag = make_get_subtag('./ALBUM')

########## MODIFICATION_INFO ######################

# get_modification_info_subtag = make_get_subtag('./MODIFICATION_INFO')

########## INFO ######################

get_info_subtag = make_get_subtag('./INFO')

########## TEMPO ######################

get_tempo_subtag = make_get_subtag('./TEMPO')

########## LOCATION ######################

def get_location(entry: ET.Element) -> Path:
    loc = entry.find('./LOCATION')
    assert loc is not None, "location tag missing"

    vol = loc.get('VOLUME')
    d = loc.get('DIR')
    name = loc.get('FILE')

    if vol is None or d is None or name is None:
        raise ValueError(f"Incomplete location information.")
    else:
        d = Path(d.replace('/:', '/'))

    return Path(vol) / d / name


def adjust_location(loc: Path, anchor: Path | None = None, relative: Path | None = None) -> Path:
    loc_rel = loc.relative_to(relative) if relative is not None else loc.relative_to(loc.anchor)
    return path_anchor(anchor) / loc_rel


########## LOUDNESS ######################

def get_loudness(entry: ET.Element):
    ldns = entry.find('./LOUDNESS')
    if ldns is None:
        return None
    else:
        perc_db = ldns.get('PERCEIVED_DB')
        if perc_db is None:
            return None
        else:
            return ALoudness(
                autogain=float(perc_db),
                gain_db=0.0
            )


########## MUSICAL_KEY ######################

get_musical_key_subtag = make_get_subtag('./MUSICAL_KEY')

def musical_key_to_classic_key(mk: str | None) -> str | None:
    if mk is None:
        return None
    elif mk.isnumeric():
        ok = inverse_dict(OPEN_KEY2MUSICAL_KEY_MAP)[int(mk)]
        return inverse_dict(CLASSIC2OPEN_KEY_MAP)[ok]
    else:
        warnings.warn(f"Can't convert key {mk} to Classical key.")
        return None

########## CUE_V2 ######################

def get_cue_v2_beatgrid(entry: ET.Element) -> list[ABeatGridBPM]:
    mkrs = entry.findall('./CUE_V2[@TYPE="4"]')
    out = []
    for m in mkrs:
        pos = m.get('START')
        assert pos is not None
        grid = m.find('./GRID')
        assert grid is not None
        bpm = grid.get('BPM')
        assert bpm is not None
        out += [ABeatGridBPM(
            position = ms_to_s(float(pos)),
            bpm = float(bpm),
        )]
    return out


def get_cue_v2_cues(entry: ET.Element) -> list[AMarker]:
    mkrs = entry.findall('./CUE_V2[@TYPE!="4"]')
    out = []
    for m in mkrs:
        name = m.get('NAME')
        assert name is not None
        start = m.get('START')
        assert start is not None
        length = m.get('LEN')
        assert length is not None
        kind = m.get('TYPE')
        assert kind is not None
        idx = m.get('HOTCUE')
        assert idx is not None
        out += [AMarker(
            name = name,
            color = None,
            start = ms_to_s(float(start)),
            end = ms_to_s(float(start) + float(length)) if float(length) != 0.0 else None,
            kind = inverse_dict(TRAKTOR_MARKERTYPE_MAP)[kind],
            index = int(idx),
            locked = False,
        )]
    return out


########## MAIN ######################

def get_str_attr(fn: str, entry: ET.Element) -> str | None:
    if is_entry_tag_attr(fn):
        return get_tag_attr(fn, entry)
    elif is_album_tag_attr(fn):
        return get_album_subtag(fn, entry)
    elif is_info_tag_attr(fn):
        return get_info_subtag(fn, entry)
    elif is_tempo_tag_attr(fn):
        return get_tempo_subtag(fn, entry)
    elif is_musical_key_attr(fn):
        return get_musical_key_subtag(fn, entry)
    else:
        return None


def from_traktor(entry: ET.Element, nml_version: int, anchor: Path | None = None, relative: Path | None = None) -> ATrack:

    return ATrack(
        title = get_str_attr('title', entry),
        artist = get_str_attr('artist', entry),
        grouping = get_str_attr('grouping', entry),
        remixer = get_str_attr('remixer', entry),
        composer = get_str_attr('composer', entry),
        album = get_str_attr('album', entry),
        genre = get_str_attr('genre', entry),
        track_number = to_int(get_str_attr('track_number', entry)),
        disc_number = to_int(get_str_attr('disc_number', entry)),
        release_date = to_date(get_str_attr('release_date', entry)),
        play_count = to_int(get_str_attr('play_count', entry)),
        tonality = musical_key_to_classic_key(get_str_attr('tonality', entry)),
        label = get_str_attr('label', entry),
        comments = get_str_attr('comments', entry),
        rating = to_int(get_str_attr('rating', entry)),
        # Traktor gives an integer in kbytes. However, Rekordbox
        # expects the numberof octets. For the moment we omit this
        # piece of information. In the future we may get the accurate
        # value from the file directly.
        size = None, # to_int(get_str_attr('size', entry)) * 1000,
        total_time = to_float(get_str_attr('total_time', entry)),
        bit_rate = to_int(get_str_attr('bit_rate', entry)),
        sample_rate = to_float(get_str_attr('sample_rate', entry)),
        location = adjust_location(get_location(entry), anchor, relative),
        aformat = aformat_from_path(get_location(entry)),
        beatgrid = get_cue_v2_beatgrid(entry),
        markers = get_cue_v2_cues(entry),
        locked = to_bool(get_str_attr('locked', entry)),
        color = None, # XXX extract track color
        average_bpm = to_float(get_str_attr('average_bpm', entry)),
        loudness = get_loudness(entry),
        data_source = ADataSource(ASoftware.TRAKTOR, [nml_version], None),
        trackID = None, # XXX use AUDIO_ID?
        mix = None,
        date_added = to_date(get_str_attr('date_added', entry))
    )


def find_collection_entry(col: ET.Element, key: str | None) -> ET.Element | None:
    if key is None:
        return None
    else:
        out = None
        for element in col.iter('ENTRY'):
            loc = element.find('./LOCATION')
            if loc is None:
                continue

            vol = loc.get('VOLUME')
            d = loc.get('DIR')
            name = loc.get('FILE')

            if not any(e is None for e in [vol, d, name]) and key == (vol + d + name): # pyright: ignore
                out = element
                break
        return out


def read_traktor_playlist(nml_file: Path, name: str | None, anchor: Path | None = None, relative: Path | None = None) -> APlaylist:

    root = ET.parse(nml_file).getroot()
    nml_version = root.get('VERSION')
    if nml_version is not None:
        nml_version = int(nml_version)
    else:
        raise ValueError(f"NML file has not VERSION information.")

    # find playlist
    pls = root.findall('.//NODE[@TYPE="PLAYLIST"]')
    pl_name = nml_file.stem if name is None else name
    
    pl = list(filter(lambda pl: pl.attrib['NAME'] == pl_name, pls))
    if len(pl) == 0:
        raise ValueError(f'Playlist {pl_name} not found.')
    elif len(pl) > 1:
        raise ValueError(f'More than 1 playlist named {pl_name}!')
    else:
        pl = pl[0]

    # entries
    entries = pl.find('./PLAYLIST[@TYPE="LIST"]')
    if entries is not None:
        entries = entries.get('ENTRIES')
        assert entries is not None
        entries = int(entries)
    else:
        raise ValueError(f"Can't find ENTRIES in playlist {pl_name}: Corrupted file.")
        
    # lookup entry in collection
    col = root.find('COLLECTION')
    if col is None:
        raise ValueError(f'No COLLECTION in playlist {pl_name}: Corrupted file.')

    ats = []
    for t in pl.findall('./PLAYLIST/ENTRY/PRIMARYKEY'):
        k = t.get('KEY')
        e = find_collection_entry(col, k)
        if e is not None:
            at = from_traktor(e, nml_version, anchor, relative)
            ats += [at]

    apl = APlaylist(pl_name, ats)
    if apl.entries != entries:
        warnings.warn(f"Couldn't find all files in playlist {pl_name}.")
        
    return apl
