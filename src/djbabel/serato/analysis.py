from mutagen._file import FileType

from .types import SeratoTags
from .utils import get_serato_metadata

def get_serato_analysis(audio: FileType) -> dict | None:
    # no parser yet
    return get_serato_metadata(SeratoTags.ANALYSIS, lambda x: x, None, bytes)(audio)
