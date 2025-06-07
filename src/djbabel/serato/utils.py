import base64
from mutagen.mp4 import MP4FreeForm
from mutagen._file import FileType
from mutagen.id3 import GEOB, TXXX, RVA2

from djbabel.serato.types import SeratoTags
from ..types import AFormat

###################################################################

def identity(x):
    return x

def is_list_of_one_str(data):
    return isinstance(data, list) and (len(data) == 1) and isinstance(data[0], str)

def is_list_of_one_mp4freeform(data):
    return isinstance(data, list) and (len(data) == 1) and isinstance(data[0], MP4FreeForm)

# def is_id3_geob(data):
#     return isinstance(data, GEOB)

###################################################################

def parse_serato_envelope(data: bytes, prefix: bytes) -> bytes:
    """
    Parses the Serato Markers2 envelope found in FLAC/M4A metadata.
    
    Parameters:
        data (bytes): Raw binary tag data (base64 encoded).
        
    Returns:
        bytes: Extracted 'Serato Markers2' payload suitable for parsing.
        
    Raises:
        ValueError: If 'Serato Markers2' cannot be found.
    """

    try:
        b64data = data.replace(b'\n', b'')
        padding = b'A==' if len(b64data) % 4 == 1 else (b'=' * (-len(b64data) % 4))
        decoded = base64.b64decode(b64data + padding)
    except Exception as e:
        raise ValueError(f"Base64 decoding failed: {e}")

    mkr = prefix + b'\x00'
    marker_offset = decoded.find(mkr) + len(mkr)
    if marker_offset == -1:
        raise ValueError(f"{prefix} marker not found in decoded envelope")

    return decoded[marker_offset:]

def audio_file_type(audio: FileType) -> AFormat:
    if 'audio/mp3' in audio.mime:
        return AFormat.MP3
    elif 'audio/flac' in audio.mime:
        return AFormat.FLAC
    elif 'audio/mp4' in audio.mime:
        return AFormat.M4A
    else:
        raise NotImplementedError("File format not supported")

def maybe_metadata(audio, tag_name):
    if tag_name in audio.tags.keys():
        data = audio.tags[tag_name]
        if is_list_of_one_str(data):
            return bytes(data[0], 'utf-8')
        elif is_list_of_one_mp4freeform(data):
            return bytes(data[0])
        elif isinstance(data, GEOB):
            return data.data
        elif isinstance(data, TXXX):
            return data.text
        elif isinstance(data, RVA2):
            return data
        else:
            raise NotImplementedError('Unexpected audio metadata type')
    else:
        return None

def serato_tag_name(tag: SeratoTags, fmt: AFormat):
    return tag.value.names[fmt]

def serato_tag_marker(tag: SeratoTags):
    return tag.value.marker

def serato_metadata(audio: FileType, stag: SeratoTags) -> bytes | None:
    """Audio file Serato metadata content.
    """
    ty = audio_file_type(audio)
    tag_name = serato_tag_name(stag, ty)
    env_marker = serato_tag_marker(stag)
    if ty in [AFormat.MP3, AFormat.FLAC, AFormat.M4A]:
        data = maybe_metadata(audio, tag_name)
    else:
        print('File type not supported.')
        data = None
    if ty in [AFormat.FLAC, AFormat.M4A] and isinstance(data, bytes):
        return parse_serato_envelope(data, env_marker)
    else:
        return data

def get_serato_metadata(stag: SeratoTags, parser, keys: list[str] | None = None, f_out = list):
    def get_metadata(audio: FileType) -> dict | None:
        data = serato_metadata(audio, stag)
        if data != None:
            if keys == None:
                return {stag.name.lower() : f_out(parser(data))}
            else:
                return dict(zip(keys, f_out(parser(data))))
        else:
            return None

    return get_metadata

###############################################################################
# Code from https://github.com/Holzhaus/serato-tags
#
# Copyright 2019 Jan Holthuis
#
# original code licensed under the MIT License

FMT_VERSION = 'BB'

def readbytes(fp):
    for x in iter(lambda: fp.read(1), b''):
        if x == b'\00':
            break
        yield x
