# SPDX-FileCopyrightText: 2025 Federico Beffa <beffa@fbengineering.ch>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from basic_colormath import get_delta_e
from dataclasses import replace
from datetime import date
import mutagen.mp3
from mutagen._file import FileType # pyright: ignore
from pathlib import Path, PosixPath, WindowsPath

import itertools
import os
import re
import typing
import types
import warnings

from .types import (
    AudioFileInaccessibleWarning,
    AEncoderMode,
    AFormat,
    AMarkerColors,
    ASoftware,
    ASoftwareInfo,
    ATrack,
    ATransformation,
    AMarker,
    AMarkerType,
    AEncoder,
    AEncoderMode
)

#########################################################################
# Helper functions

def audio_file_type(audio: FileType) -> AFormat:
    if 'audio/mp3' in audio.mime:
        return AFormat.MP3
    elif 'audio/flac' in audio.mime:
        return AFormat.FLAC
    elif 'audio/mp4' in audio.mime:
        return AFormat.M4A
    else:
        raise NotImplementedError("File format not supported")

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

def file_size(audio: FileType) -> int | None:
    if audio.filename is None:
        s = None
    else:
        try:
            s = os.path.getsize(audio.filename)
        except FileNotFoundError:
            s = None
    return s

def audio_length(audio: FileType | None) -> float | None:
    if (audio is not None and
        hasattr(audio, 'info') and
        hasattr(audio.info, 'length') and
        audio.info is not None
        ):
        return audio.info.length
    else:
        return None

def path_anchor(ancor: Path | None) -> Path:
    if ancor is None:
        match os.name:
            case 'nt':
                return WindowsPath('C:\\')
            case 'posix':
                return PosixPath('/')
            case _:
                raise ValueError(f'OS {os.name} not supported')
    else:
        return ancor

def adjust_location(loc: Path, anchor: Path | None = None, relative: Path | None = None) -> Path:
    loc_rel = loc.relative_to(relative) if relative is not None else loc.relative_to(loc.anchor)
    return path_anchor(anchor) / loc_rel

def ms_to_s(x):
    """Milli-seconds to seconds
    """
    return x/1000

def s_to_ms(x):
    """Seconds to milli-seconds
    """
    return x*1000

def kbps_to_bps(x):
    return x*1000 if x is not None else None

def to_int(x: str | None) -> int:
    if x is not None and x.isnumeric():
        return int(x)
    else:
        return 0

def to_float(x: str | None) -> float | None:
    if x is None:
        return None
    elif x.isnumeric:
        return float(x)
    else:
        ps = x.split('.')
        assert len(ps) == 2, f"Can't convert {x} to a float."
        if ps[0].isnumeric and ps[1].isnumeric:
            return float(x)
        else:
            raise ValueError(f"Can't convert {x} to a float.")

# base64 format: https://datatracker.ietf.org/doc/html/rfc4648.html
def get_leading_base64_part(byte_string: bytes) -> bytes:
    """Base64 leading part of a byte string.
    """
    base64_chars = frozenset(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")

    def is_base64_char(byte_char: int) -> bool:
        return byte_char in base64_chars

    result_bytes = bytearray(itertools.takewhile(is_base64_char, iter(byte_string)))

    return bytes(result_bytes)


def inverse_dict(d: dict) -> dict:
    return {value: key for key, value in d.items()}

###### COLORS ######

def closest_color_perceptual(target_rgb: tuple[int,int,int]) -> AMarkerColors:
    """Given an RGB color, find the closest in the AMarkerColors palette.
    """
    min_delta_e = float('inf')
    closest_color = None

    for color_rgb in AMarkerColors:
        # Calculate Delta E 2000
        delta_e = get_delta_e(target_rgb, color_rgb.value)

        if delta_e < min_delta_e:
            min_delta_e = delta_e
            closest_color = color_rgb
    return closest_color # pyright: ignore[reportReturnType] # will never be None

###### MARKERS AND BEATGRID ######

def mp3_encoder_name_version(encoder: AEncoder) -> tuple[str, list[int]]:
    """Extract encoder name and version from strings like 'LAME 3.100.0+' and 'Lavf58.20.100'

    """
    pattern = r'([a-zA-Z]+)\s*(\d+)\.?(\d+)\.?(\d+)\+?'
    match = re.match(pattern, encoder.text)
    if match:
        name = str(match.group(1))
        # Filter out empty strings from version parts
        version_parts = list(map(int, filter(None, match.groups()[1:])))
        return name, version_parts
    else:
        return encoder.text, []

def mp3_beatgrid_offset(encoder: AEncoder | None) -> float:
    if encoder is None:
        return 0.0
    else:
        name, version = mp3_encoder_name_version(encoder)
        # Verified that this version with '-V0' doesn't shift the beatgrid.
        # Assume that other modes are good as well.
        if name == 'LAME' and version >= [3, 100, 0]:
            return 0.0
        # 'Lavf' is the 'ffmpeg' library which doesn't include and MP3 encoder.
        # It usually links to 'LAME'. Thus the version of 'Lavf' doesn't
        # directly give the encoder version. However, it's reasonable to assume
        # that it will use a version of 'LAME' that was recent at the time of
        # the release of 'ffmpeg' version.

        # Seems that the same delay applies since version 57.83.100.
        # # version around De_Lacy_-_Hideaway
        # elif name == 'Lavf' and version >= [58, 20, 100]:
        #     return -0.016 # between -0.019 and -0.013

        # version around 'The Weekend -- The Todd Terry Project'
        elif name == 'Lavf' and version >= [57, 83, 100]:
            return -0.016
        else:
            # if we don't know the encoder we try the same as ffmpeg
            return -0.016


def beatgrid_offset(at: ATrack, trans: ATransformation) -> float:
    """BeatGrid offset relative to Serato DJ Pro 3.3.2 in seconds.

    dt = t_target - t_serato_dj_pro
    """
    match trans.target:
        case ASoftwareInfo(ASoftware.SERATO_DJ_PRO, _):
            # Serato DJ Pro is currently used as reference.
            return 0.0
        case ASoftwareInfo(ASoftware.REKORDBOX, _):
            match at.aformat:
                case AFormat.M4A:
                    return 0.046
                case AFormat.MP3:
                    return mp3_beatgrid_offset(at.data_source.encoder)
                case _:
                    # LOSSLESS formats are not shifted
                    return 0.0
        case ASoftwareInfo(ASoftware.TRAKTOR, _):
            match at.aformat:
                case AFormat.M4A:
                    return 0.0
                case AFormat.MP3:
                    return 0.0
                case _:
                    # LOSSLESS formats are not shifted
                    return 0.0
        case _:
            raise ValueError(f'{trans.target.software} currently not supported.')

def marker_offset(at: ATrack, trans: ATransformation) -> float:
    """Marker offset relative to Serato DJ Pro 3.3.2 in seconds.

    dt = t_target - t_serato_dj_pro
    """
    # Currently we don't observe difference from beatgrid.
    return beatgrid_offset(at, trans)


def adjust_time(at: ATrack, trans: ATransformation, offset_sign: int) -> ATrack:
    """Adjust the markers and beatgrid time.

    Args:
      at: The audio track information.
      trans: The transformation to be performed.
      offset_sign: -1 -> normalize to ATrack reference ('Serato DJ Pro'). 1 -> adjust normalized time to target.

    Returns:
      The audio track information 'at' with beatgrid and markers timing adjusted.
    """
    m_offset = offset_sign * marker_offset(at, trans)
    new_markers = []
    for m in at.markers:
        new_start = m.start + m_offset
        new_end = (m.end + m_offset) if m.end is not None else None
        new_markers = new_markers + [replace(m, start=new_start, end=new_end)]
    bg_offset = offset_sign * beatgrid_offset(at, trans)
    new_beatgrid = []
    for bg in at.beatgrid:
        new_position = bg.position + bg_offset
        new_beatgrid = new_beatgrid + [replace(bg,position=new_position)]
    return replace(at, markers=new_markers, beatgrid=new_beatgrid)


def adjust_time_to_target(at: ATrack, trans: ATransformation) -> ATrack:
    """Adjust the markers and beatgrid time according to target.
    """
    return adjust_time(at, trans, 1)

def normalize_time(at: ATrack, trans: ATransformation) -> ATrack:
    """Normalize markers and beatgrid time to the reference used by ATrack.

    The reference is 'Serato DJ Pro'.
    """
    return adjust_time(at, trans, -1)
    

def reindex_sdjpro_loops(markers: list[AMarker], trans: ATransformation) -> list[AMarker]:
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
    match trans.source.software:
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
            new_markers = markers
    return new_markers

###### ENCODERS ######

def mp3_endocer_bitrate_mode(mode: mutagen.mp3.BitrateMode) -> AEncoderMode:
    match mode:
        case mutagen.mp3.BitrateMode.CBR:
            return AEncoderMode.CBR
        case mutagen.mp3.BitrateMode.VBR:
            return AEncoderMode.VBR
        case _:
            return AEncoderMode.UNKNOWN


def mp3_encoder(audio: FileType) -> AEncoder | None:
    if audio.info is not None and audio.info.encoder_info != '':
        text = audio.info.encoder_info
        settings = audio.info.encoder_settings
        mode = mp3_endocer_bitrate_mode(audio.info.bitrate_mode)
    elif audio.tags is not None and 'TSSE' in audio.tags.keys():
        text = audio.tags['TSSE'].text[0]
        settings = ''
        mode = mp3_endocer_bitrate_mode(audio.info.bitrate_mode) # pyright: ignore
    else:
        return None
    return AEncoder(text, settings, mode)


def audio_endocer(audio: FileType) -> AEncoder | None:
    ks = audio.tags.keys() if audio.tags is not None else None
    match audio_file_type(audio):
        case AFormat.MP3:
            return mp3_encoder(audio)
        case AFormat.M4A:
            k = '©too'
            return AEncoder(audio.tags[k][0]) if ks is not None and k in ks else None # pyright: ignore
        case AFormat.FLAC:
            if ks is not None and 'ENCODEDBY' in ks:
                k = 'ENCODEDBY'
                return AEncoder(audio.tags[k]) if k in ks else None # pyright: ignore
            elif ks is not None and 'ENCODER' in ks:
                k = 'ENCODER'
                return AEncoder(audio.tags[k]) if k in ks else None # pyright: ignore
            else:
                return None
        case _:
            raise ValueError(f'audio_encoder: file format not supported.')


def maybe_audio(path: Path) -> FileType | None:
    if path.exists() and path.is_file():
        audio = mutagen.File(path, easy=False) # pyright: ignore
        assert isinstance(audio, FileType)
        return audio
    else:
        warnings.warn(
            f"File {path} not found.\n"
            f"For best Cue and beatgrid timing adjustment, djbabel needs access\n"
            f"to the file (for reading).\n"
            f"Further occurrences of similar messages will new be suppressed.",
            AudioFileInaccessibleWarning
        )
        return None

#######################################################################
# Predicates

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

###############################################################################
# Key Maps

# Map the classic musical key into the Camelot one.
CLASSIC2CAMLEOT_KEY_MAP = {
    # Major Keys
    'Cmaj': '8B',
    'C#maj': '3B',
    'Dbmaj': '3B',
    'Dmaj': '10B',
    'Ebmaj': '5B',
    'Emaj': '12B',
    'Fmaj': '7B',
    'F#maj': '2B',
    'Gbmaj': '2B',
    'Gmaj': '9B',
    'Abmaj': '4B',
    'Amaj': '11B',
    'Bbmaj': '6B',
    'Bmaj': '1B',
    # Minor Keys
    'Ami': '8A',
    'Amin': '8A',
    'A#min': '3A',
    'Bbmin': '3A',
    'Bmi': '10A',
    'Bmin': '10A',
    'Cmi': '5A',
    'Cmin': '5A',
    'C#min': '12A',
    'Dbmin': '12A',
    'Dmi': '7A',
    'Dmin': '7A',
    'D#min': '2A',
    'Ebmin': '2A',
    'Emi': '9A',
    'Emin': '9A',
    'Fmi': '4A',
    'Fmin': '4A',
    'F#min': '11A',
    'Gbmin': '11A',
    'Gmi': '6A',
    'Gmin': '6A',
    'G#min': '1A',
    'Abmin': '1A',
}

# Map the classic musical key into the abbreviated one used by Rekordbox.
CLASSIC2ABBREV_KEY_MAP = {
    # Major Keys
    'Cmaj': 'C',
    'C#maj': 'C#',
    'Dbmaj': 'Db',
    'Dmaj': 'D',
    'D#maj': 'D#', # Less common in classic notation but included for completeness
    'Ebmaj': 'Eb',
    'Emaj': 'E',
    'Fmaj': 'F',
    'F#maj': 'F#',
    'Gbmaj': 'Gb',
    'Gmaj': 'G',
    'G#maj': 'G#', # Less common in classic notation but included for completeness
    'Abmaj': 'Ab',
    'Amaj': 'A',
    'A#maj': 'A#', # Less common in classic notation but included for completeness
    'Bbmaj': 'Bb',
    'Bmaj': 'B',
    # Minor Keys (handling both 'min' and 'mi' if you use both in your classic data)
    'Cmin': 'Cm',
    'Cmi': 'Cm',
    'C#min': 'C#m',
    'Dbmin': 'Dbm', # Less common in classic notation but included for completeness
    'Dmin': 'Dm',
    'Dmi': 'Dm',
    'D#min': 'D#m',
    'Ebmin': 'Ebm',
    'Emin': 'Em',
    'Emi': 'Em',
    'Fmin': 'Fm',
    'Fmi': 'Fm',
    'F#min': 'F#m',
    'Gbmin': 'Gbm', # Less common in classic notation but included for completeness
    'Gmin': 'Gm',
    'Gmi': 'Gm',
    'G#min': 'G#m',
    'Abmin': 'Abm',
    'Amin': 'Am',
    'Ami': 'Am',
    'A#min': 'A#m',
    'Bbmin': 'Bbm',
    'Bmin': 'Bm',
    'Bmi': 'Bm',
}

# Traktor uses Open-Key notation
CLASSIC2OPEN_KEY_MAP = {
    # Major Keys
    'Cmaj': '1d',
    'C#maj': '8d',  # Or Dbmaj
    'Dbmaj': '8d',
    'Dmaj': '3d',
    'Ebmaj': '10d',
    'Emaj': '5d',
    'Fmaj': '12d',
    'F#maj': '7d',  # Or Gbmaj
    'Gbmaj': '7d',
    'Gmaj': '2d',
    'Abmaj': '9d',
    'Amaj': '4d',
    'Bbmaj': '11d',
    'Bmaj': '6d',

    # Minor Keys
    'Ami': '1m',    # Relative minor of Cmaj
    'Amin': '1m',
    'A#min': '8m',  # Or Bbmin, Relative minor of Dbmaj
    'Bbmin': '8m',
    'Bmi': '3m',    # Relative minor of Dmaj
    'Bmin': '3m',
    'Cmi': '10m',   # Relative minor of Ebmaj
    'Cmin': '10m',
    'C#min': '5m',  # Relative minor of Emaj
    'Dbmin': '5m',
    'Dmi': '12m',   # Relative minor of Fmaj
    'Dmin': '12m',
    'D#min': '7m',  # Or Ebmin, Relative minor of F#maj
    'Ebmin': '7m',
    'Emi': '2m',    # Relative minor of Gmaj
    'Emin': '2m',
    'Fmi': '9m',    # Relative minor of Abmaj
    'Fmin': '9m',
    'F#min': '4m',  # Relative minor of Amaj
    'Gbmin': '4m',
    'Gmi': '11m',   # Relative minor of Bbmaj
    'Gmin': '11m',
    'G#min': '6m',  # Or Abmin, Relative minor of Bmaj
    'Abmin': '6m',
}

# Open Key (e.g., "1d" for major, "1m" for minor) to Traktor musical_key number
OPEN_KEY2MUSICAL_KEY_MAP = {
    "1d": 1,   "2d": 2,   "3d": 3,   "4d": 4,
    "5d": 5,   "6d": 6,   "7d": 7,   "8d": 8,
    "9d": 9,  "10d": 10, "11d": 11, "12d": 12,

    "1m": 13,  "2m": 14,  "3m": 15,  "4m": 16,
    "5m": 17,  "6m": 18,  "7m": 19,  "8m": 20,
    "9m": 21, "10m": 22, "11m": 23, "12m": 24
}
