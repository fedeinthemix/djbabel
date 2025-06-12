from mutagen._file import FileType

from .types import SeratoTags
from .utils import get_serato_metadata

def get_serato_analysis(audio: FileType) -> list | None:
    return get_serato_metadata(SeratoTags.ANALYSIS, parse)(audio)

def parse(b: bytes):
    v = []
    for n in range(0, len(b)):
        v = v + [b[n]]
    return v
