import re
import subprocess
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


def _escape_filter_path(p: Path) -> str:
    s = p.resolve().as_posix()
    s = s.replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
    s = s.replace(" ", r"\ ")  # spaces in paths would otherwise split the filter
    return s


def _write_textfile(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


class AddTextOperation(BaseModel):
    """Overlays a line of text for a time range using FFmpeg drawtext."""

    type: Literal["add_text"]
    input: str
    text: str
    fontfile: str
    x: str
    y: str
    start: float
    end: float
    fontsize: int = 32
    fontcolor: str = "white"
    name: str | None = None
    id: str = Field(default_factory=lambda: str(uuid4()))
    output: str | None = None

    @field_validator("text", mode="after")
    @classmethod
    def text_single_line(cls, v: str) -> str:
        if "\n" in v or "\r" in v:
            msg = "text must be a single line (no newlines) for the drawtext filter"
            raise ValueError(msg)
        return v

    @field_validator("fontcolor", mode="after")
    @classmethod
    def fontcolor_safe(cls, v: str) -> str:
        t = v.strip()
        if not t:
            msg = "fontcolor must be non-empty"
            raise ValueError(msg)
        if re.search(r"[:'\\\n\r]", t):
            msg = "fontcolor may not contain :, backslash, quotes, or newlines"
            raise ValueError(msg)
        return t

    @model_validator(mode="after")
    def time_range(self) -> "AddTextOperation":
        if self.start < 0:
            msg = "start must be >= 0"
            raise ValueError(msg)
        if self.end <= self.start:
            msg = f"end ({self.end}) must be > start ({self.start})"
            raise ValueError(msg)
        return self

    def run(self, output_dir: Path) -> Path:
        input_path = Path(self.input)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        font_path = Path(self.fontfile)
        if not font_path.exists():
            raise FileNotFoundError(f"Font file not found: {font_path}")

        output_path = output_dir / f"{input_path.stem}_addtext{input_path.suffix}"
        textfile_path = output_dir / f"{self.id}.txt"
        _write_textfile(textfile_path, self.text)

        label = self.name or input_path.name
        print(
            f"[{self.id}] Add text on {label!r} t=[{self.start}, {self.end}) "
            f"at ({self.x}, {self.y}) {self.text!r}"
        )

        ff = "drawtext=" + ":".join(
            [
                f"fontfile={_escape_filter_path(font_path)}",
                f"textfile={_escape_filter_path(textfile_path)}",
                f"fontsize={self.fontsize}",
                f"fontcolor={self.fontcolor}",
                f"x={self.x}",
                f"y={self.y}",
                f"enable=between(t\\,{self.start}\\,{self.end})",
            ]
        )

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(input_path),
                "-vf",
                ff,
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "copy",
                str(output_path),
            ],
            check=True,
        )
        textfile_path.unlink(missing_ok=True)
        print(f"[{self.id}] Done → {output_path.name}")
        return output_path
