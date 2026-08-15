"""Convert image files into panel-ready BMP files."""

from typing import TYPE_CHECKING

from PIL.Image import open as open_image
from returns.result import safe

from eink.convert import ImageConverter

if TYPE_CHECKING:
    from pathlib import Path


@safe
def main(src: Path, dest: Path | None, *, dither: bool) -> None:
    """Convert an image file and save the panel-ready BMP."""
    _dest = dest if dest is not None else src.with_suffix(".bmp")

    with open_image(src) as source:
        converted = ImageConverter().convert(source, dither=dither).unwrap()

    converted.save(_dest, format="BMP")
