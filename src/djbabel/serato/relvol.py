from mutagen._file import FileType

from .types import SeratoTags
from .utils import get_serato_metadata, identity

def get_serato_relvol(audio: FileType) -> dict | None:
    # no parser yet
    return get_serato_metadata(SeratoTags.RELVOL, identity, None, identity)(audio)
