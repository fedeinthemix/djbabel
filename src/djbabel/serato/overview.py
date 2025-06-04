# -*- coding: utf-8 -*-
import struct
import io
from PIL import Image
from PIL import ImageColor
from mutagen._file import FileType

from .types import SeratoTags
from .utils import get_serato_metadata, FMT_VERSION

def get_serato_overview(audio: FileType) -> dict | None:
    return get_serato_metadata(SeratoTags.OVERVIEW,
                               parse,
                               [SeratoTags.OVERVIEW.name.lower()],
                               lambda x: [draw_waveform(x)])(audio)

###############################################################################
# Code from https://github.com/Holzhaus/serato-tags with minor modifications.
#
# Copyright 2019 Jan Holthuis
#
# original code licensed under the MIT License

def parse(data: bytes):
    fp = io.BytesIO(data)
    version = struct.unpack(FMT_VERSION, fp.read(2))
    assert version == (0x01, 0x05)

    for x in iter(lambda: fp.read(16), b''):
        assert len(x) == 16
        yield bytearray(x)


def draw_waveform(data):
    img = Image.new('RGB', (240, 16), "black")
    pixels = img.load()

    for i in range(img.size[0]):
        rowdata = next(data)
        factor = (len([x for x in rowdata if x < 0x80]) / len(rowdata))

        for j, value in enumerate(rowdata):
            # The algorithm to derive the colors from the data has no real
            # mathematical background and was found by experimenting with
            # different values.
            color = 'hsl({hue:.2f}, {saturation:d}%, {luminance:.2f}%)'.format(
                hue=(factor * 1.5 * 360) % 360,
                saturation=40,
                luminance=(value / 0xFF) * 100,
            )
            pixels[i, j] = ImageColor.getrgb(color)

    return img
