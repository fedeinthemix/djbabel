# SPDX-FileCopyrightText: 2025 Federico Beffa <beffa@fbengineering.ch>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import binascii
from datetime import date, datetime
import os
from pathlib import Path
import struct
from urllib.parse import urlparse
from urllib.request import url2pathname
import warnings
import xml.etree.ElementTree as ET

from ..types import (
    ABeatGridBPM,
    ADataSource,
    AMarker,
    APlaylist,
    ASoftware,
    ATrack,
    ATransformation
)

from .types import RBPlaylistKeyType

from ..utils import (
    adjust_location,
    aformat_from_path,
    audio_endocer,
    audio_file_type,
    audio_length,
    closest_color_perceptual,
    file_size,
    kbps_to_bps,
    inverse_dict,
    maybe_audio,
    normalize_time,
    to_float,
    to_int,
    CLASSIC2ABBREV_KEY_MAP
)

from .utils import (
    rb_attr_name,
    REKORDBOX_MARKERTYPE_MAP
)

###### Helpers ####################################################

def to_date(d: str | None) -> date | None:
    if d is None:
        return d
    elif len(d) == 4:
        return datetime.strptime(d, "%Y").date()
    else:
        return datetime.strptime(d, "%Y-%m-%d").date()


def get_rb_location(entry: ET.Element) -> Path:
    """Converts a file:// URL to a Path object.
    """
    url = entry.get('Location')
    assert url is not None, "get_rb_location: location is mandatory"
    parsed_url = urlparse(url)
    if parsed_url.scheme != 'file':
        raise ValueError("get_rb_location: URL scheme must be 'file'")
    path_str = url2pathname(parsed_url.path)
    # On Windows, if the path starts with a slash, it needs to be removed
    # unless it's part of a UNC path (e.g., //host/share)
    if os.name == 'nt' and path_str.startswith('/') and not path_str.startswith('//'):
        path_str = path_str[1:]
    return Path(path_str)


def get_tag_attr(fn: str, element: ET.Element) -> str | None:
    tn = rb_attr_name(fn)
    v = element.get(tn)
    return v if v != '' else None


def get_color(element: ET.Element) -> tuple[int,int,int] | None:
    c = get_tag_attr('color', element)
    if c is not None and c.startswith('0x') and len(c) == 8:
        return struct.unpack('BBB',binascii.unhexlify(c[2:]))
    else:
        return None


def get_beatgrid(element: ET.Element) -> list[ABeatGridBPM]:
    bg = []
    for tempo in element.findall('TEMPO'):
        bpm = to_float(tempo.get('Bpm'))
        assert bpm is not None
        position = to_float(tempo.get('Inizio'))
        assert position is not None
        metro_str = tempo.get('Metro')
        assert metro_str is not None
        b, m = metro_str.split('/')
        if b.isnumeric() and m.isnumeric():
            bg.append(ABeatGridBPM(position, bpm, (to_int(b), to_int(m))))
        else:
            bg.append(ABeatGridBPM(position, bpm))
    return bg


def get_markers(element: ET.Element) -> list[AMarker]:
    mks = []
    for pm in element.findall('POSITION_MARK'):
        name = pm.get('Name')
        assert name is not None
        ty = pm.get('Type')
        assert ty is not None
        kind = inverse_dict(REKORDBOX_MARKERTYPE_MAP)[ty]
        start = to_float(pm.get('Start'))
        assert start is not None
        end_str = pm.get('End')
        end = to_float(end_str) if end_str != '' else None
        index = to_int(pm.get('Num'))
        red = to_int(pm.get('Red'))
        green = to_int(pm.get('Green'))
        blue = to_int(pm.get('Blue'))
        color = closest_color_perceptual((red, green, blue))

        mks.append(AMarker(name, color, start, end, kind, index, False))

    return mks


def get_tonality(element: ET.Element) -> str | None:
    """Rekordbox abbreviated tonality to ATrack format (classic) one.
    """
    t = get_tag_attr('tonality', element)
    a2c = inverse_dict(CLASSIC2ABBREV_KEY_MAP)
    if t is None:
        return None
    elif t in a2c.keys():
        return a2c[t]
    else:
        warnings.warn(f"get_tonality: Tonality {t} is not in the expected abbreviated format.")
        return t


###### Main #######################################################

def from_rekordbox(entry: ET.Element, rb_version: list[int], anchor: Path | None = None, relative: Path | None = None) -> ATrack:

    location = adjust_location(get_rb_location(entry), anchor, relative)
    audio = maybe_audio(location)

    return ATrack(
        title = get_tag_attr('title', entry),
        artist = get_tag_attr('artist', entry),
        grouping = get_tag_attr('grouping', entry),
        remixer = get_tag_attr('remixer', entry),
        composer = get_tag_attr('composer', entry),
        album = get_tag_attr('album', entry),
        genre = get_tag_attr('genre', entry),
        track_number = to_int(get_tag_attr('track_number', entry)),
        disc_number = to_int(get_tag_attr('disc_number', entry)),
        release_date = to_date(get_tag_attr('release_date', entry)),
        play_count = to_int(get_tag_attr('play_count', entry)),
        tonality = get_tonality(entry),
        label = get_tag_attr('label', entry),
        comments = get_tag_attr('comments', entry),
        rating = to_int(get_tag_attr('rating', entry)),
        size = file_size(audio) if audio is not None else None,
        total_time = audio_length(audio),
        bit_rate = kbps_to_bps(to_int(get_tag_attr('bit_rate', entry))),
        sample_rate = to_float(get_tag_attr('sample_rate', entry)),
        location = location,
        aformat = audio_file_type(audio) if audio is not None else aformat_from_path(location),
        beatgrid = get_beatgrid(entry),
        markers = get_markers(entry),
        locked = False, # no 'locked' entry
        color = get_color(entry),
        average_bpm = to_float(get_tag_attr('average_bpm', entry)),
        loudness = None, # no 'loudness' entry
        data_source = ADataSource(ASoftware.REKORDBOX,
                                  rb_version,
                                  audio_endocer(audio) if audio is not None else None),
        trackID = None,
        mix = get_tag_attr('mix', entry),
        date_added = to_date(get_tag_attr('date_added', entry))
    )


def get_playlist_key_type(pl: ET.Element) -> RBPlaylistKeyType:
    key_type = pl.get('KeyType')
    match key_type:
        case "0":
            return RBPlaylistKeyType.TRACK_ID
        case "1":
            return RBPlaylistKeyType.LOCATION
        case _:
            raise ValueError(f"get_playlist_key_type: Unspecified playlist type {key_type}")


def get_element_key(element: ET.Element, key_type: RBPlaylistKeyType) -> str | None:
    match key_type:
        case RBPlaylistKeyType.TRACK_ID:
            return element.get('TrackID')
        case RBPlaylistKeyType.LOCATION:
            return element.get('Location')

def find_collection_entry(col: ET.Element, key: str | None, key_type: RBPlaylistKeyType) -> ET.Element | None:
    if key is None:
        return None
    else:
        out = None
        for element in col.iter('TRACK'):
            el_key = get_element_key(element, key_type)
            if el_key != key:
                continue
            else:
                out = element
                break
        return out


def read_rekordbox_playlist(rb_file: Path, name: str | None, trans: ATransformation, anchor: Path | None = None, relative: Path | None = None) -> APlaylist:

    root = ET.parse(rb_file).getroot()
    prod = root.find('PRODUCT')
    if prod is not None:
        v = prod.attrib['Version']
        rb_version = list(map(int, v.split('.')))
    else:
        raise ValueError(f"XML file has not PRODUCT information.")

    # find playlist
    pls = root.findall('.//NODE[@Type="1"]')
    pl_name = rb_file.stem if name is None else name

    pl = list(filter(lambda pl: pl.attrib['Name'] == pl_name, pls))
    if len(pl) == 0:
        raise ValueError(f'Playlist {pl_name} not found.')
    elif len(pl) > 1:
        raise ValueError(f'More than 1 playlist named {pl_name}!')
    else:
        pl = pl[0]

    # number of entries
    entries = pl.get('Entries')
    assert entries is not None
    entries = int(entries)

    # key type
    key_type = get_playlist_key_type(pl)

    # lookup entry in collection
    col = root.find('COLLECTION')
    if col is None:
        raise ValueError(f'No COLLECTION in playlist {pl_name}: Corrupted file.')

    ats = []
    for t in pl.findall('./TRACK'):
        k = t.get('Key')
        e = find_collection_entry(col, k, key_type)
        if e is not None:
            at = from_rekordbox(e, rb_version, anchor, relative)
            ats.append(normalize_time(at, trans))

    apl = APlaylist(pl_name, ats)
    if apl.entries != entries:
        warnings.warn(f"Couldn't find all files in playlist {pl_name}.")

    return apl
