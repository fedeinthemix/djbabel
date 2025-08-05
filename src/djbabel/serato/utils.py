import base64
from mutagen.mp4 import MP4FreeForm
from mutagen._file import FileType       # pyright: ignore
from mutagen.id3 import GEOB, TXXX, RVA2 # pyright: ignore
import struct
from typing import Callable

from ..serato.types import EntryBase, SeratoTags
from ..types import AFormat
from ..utils import audio_file_type

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
    'comments' : 'COMM', # special handling for reading
    'rating': 'POPM', # XXX field .rating!!
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
    'comments' : 'COMMENT',
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
    'comments': '©cmt',
}

map_to_aformat = {
    AFormat.MP3 : map_to_mp3_text_tag,
    AFormat.FLAC : map_to_flac_text_tag,
    AFormat.M4A : map_to_mp4_tag,
}


###################################################################

def identity(x):
    return x

def is_list_of_one_str(data):
    return isinstance(data, list) and (len(data) == 1) and isinstance(data[0], str)

def is_list_of_one_mp4freeform(data):
    return isinstance(data, list) and (len(data) == 1) and isinstance(data[0], MP4FreeForm)


def get_tags(audio: FileType):
    if audio.tags is not None:
        tags = audio.tags
    else:
        tags = {}
    return tags

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

def maybe_metadata(audio, tag_name):
    if audio.tags is not None and tag_name in audio.tags.keys():
        data = audio.tags[tag_name]
        if is_list_of_one_str(data):
            return bytes(data[0], 'utf-8')
        elif is_list_of_one_mp4freeform(data):
            return bytes(data[0])
        elif isinstance(data, GEOB):
            return data.data # pyright: ignore
        elif isinstance(data, TXXX):
            return data.text # pyright: ignore
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

def get_serato_metadata(stag: SeratoTags,
                        parser: Callable[[bytes], list[EntryBase]]):
    def get_metadata(audio: FileType) -> list[EntryBase] | None:
        data = serato_metadata(audio, stag)
        if data != None:
            return parser(data)
        else:
            return None

    return get_metadata


def parse_color(data: bytes) -> tuple[int, int, int]:
    r, g, b = struct.unpack('BBB', data)
    return (r, g, b)

def pack_color(color: tuple[int, int, int]) -> bytes:
    data = struct.pack('BBB', *color)
    return data

###############################################################################

FMT_VERSION = 'BB'

def readbytes(fp):
    for x in iter(lambda: fp.read(1), b''):
        if x == b'\00':
            break
        yield x
