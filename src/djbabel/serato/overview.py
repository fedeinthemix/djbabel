# SPDX-FileCopyrightText: 2025 Federico Beffa <beffa@fbengineering.ch>
# SPDX-FileCopyrightText: 2019 Jan Holthuis
#
# SPDX-License-Identifier: MIT

from dataclasses import dataclass
import struct
import io
from PIL import Image
from PIL import ImageColor
from typing import Iterator
from mutagen._file import FileType # pyright: ignore

from .types import EntryBase, SeratoTags
from .utils import get_serato_metadata, FMT_VERSION

###############################################################################

@dataclass
class Overview(EntryBase):
    img : Image.Image


def get_serato_overview(audio: FileType) -> Overview | None:
    ov = get_serato_metadata(SeratoTags.OVERVIEW, lambda x: draw_waveform(parse(x)))(audio)
    if ov is None:
        return None
    else:
        assert len(ov) == 1, f"Unexpected overview data {ov}"
        assert isinstance(ov[0], Overview)
        return ov[0]

###############################################################################
# Code below this line adapted from https://github.com/Holzhaus/serato-tags
#
# Copyright 2019 Jan Holthuis
#
# Original code licensed under the MIT License. See LICENSE/MIT.txt

def parse(data: bytes) -> Iterator[bytearray]:
    fp = io.BytesIO(data)
    version = struct.unpack(FMT_VERSION, fp.read(2))
    assert version == (0x01, 0x05)

    for x in iter(lambda: fp.read(16), b''):
        assert len(x) == 16
        yield bytearray(x)


def draw_waveform(data) -> list[EntryBase]:
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
            assert pixels is not None, "Enpty image"
            pixels[i, j] = ImageColor.getrgb(color)

    return [Overview(img)]
