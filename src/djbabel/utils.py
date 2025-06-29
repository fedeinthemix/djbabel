from basic_colormath import get_delta_e
from dataclasses import replace
from mutagen._file import FileType # pyright: ignore
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath

import itertools
import os

from .types import AFormat, AMarkerColors, ASoftware, ASoftwareInfo, ATrack, ATransformation

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

def path_anchor(ancor: Path | None) -> PurePath:
    if ancor is None:
        match os.name:
            case 'nt':
                return PureWindowsPath('C:\\')
            case 'posix':
                return PurePosixPath('/')
            case _:
                raise ValueError(f'OS {os.name} not supported')
    else:
        return ancor

def ms_to_s(x):
    """Milli-seconds to seconds
    """
    return x/1000

def s_to_ms(x):
    """Seconds to milli-seconds
    """
    return x*1000

# base64 format: https://datatracker.ietf.org/doc/html/rfc4648.html
def get_leading_base64_part(byte_string: bytes) -> bytes:
    """Base64 leading part of a byte string.
    """
    base64_chars = frozenset(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")

    def is_base64_char(byte_char: int) -> bool:
        return byte_char in base64_chars

    result_bytes = bytearray(itertools.takewhile(is_base64_char, iter(byte_string)))

    return bytes(result_bytes)


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
                    # Files encoded with 'lame -V0' are NOT shifted
                    return 0.0
                case _:
                    # LOSSLESS formats are not shifted
                    return 0.0
        case _:
            raise ValueError(f'{trans.target.software} currently not supported.')

def adjust_time(at: ATrack, trans: ATransformation) -> ATrack:
    """Adjust the markers and beatgrid time according to target.
    """
    offset = beatgrid_offset(at, trans)
    new_markers = []
    for m in at.markers:
        new_start = m.start + offset
        new_end = (m.end + offset) if m.end is not None else None
        new_markers = new_markers + [replace(m, start=new_start, end=new_end)]
    new_beatgrid = []
    for bg in at.beatgrid:
        new_position = bg.position + offset
        new_beatgrid = new_beatgrid + [replace(bg,position=new_position)]
    return replace(at, markers=new_markers, beatgrid=new_beatgrid)

def mp3_encoder(audio: FileType) -> str | None:
    if audio.info is not None and audio.info.encoder_info != '':
        return audio.info.encoder_info
    elif audio.tags is not None and 'TSSE' in audio.tags.keys():
        return audio.tags['TSSE'].text[0]
    else:
        return None

def audio_endocer(audio: FileType) -> str | None:
    ks = audio.tags.keys() if audio.tags is not None else None
    match audio_file_type(audio):
        case AFormat.MP3:
            return mp3_encoder(audio)
        case AFormat.M4A:
            k = '©too'
            return audio.tags[k][0] if ks is not None and k in ks else None # pyright: ignore
        case AFormat.FLAC:
            if ks is not None and 'ENCODEDBY' in ks:
                k = 'ENCODEDBY'
                return audio.tags[k] if k in ks else None # pyright: ignore
            elif ks is not None and 'ENCODER' in ks:
                k = 'ENCODER'
                return audio.tags[k] if k in ks else None # pyright: ignore
            else:
                return None
        case _:
            raise ValueError(f'audio_encoder: file format not supported.')

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
