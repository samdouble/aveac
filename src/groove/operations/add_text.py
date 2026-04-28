import re
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

from groove.ffmpeg_command_builder import FFmpegCommandBuilder
from groove.ffmpeg_runtime import FFmpegInvocation
from groove.operations.input_ref import OperationInput


def _escape_filter_path(p: Path) -> str:
    s = p.resolve().as_posix()
    s = s.replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
    s = s.replace(" ", r"\ ")
    return s


def _write_textfile(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _build_alpha_expr(start: float, end: float, fade_in: float, fade_out: float) -> str | None:
    if fade_in <= 0 and fade_out <= 0:
        return None
    if fade_in > 0 and fade_out > 0:
        return (
            f"if(lt(t\\,{start})\\,0\\,"
            f"if(lt(t\\,{start + fade_in})\\,(t-{start})/{fade_in}\\,"
            f"if(lt(t\\,{end - fade_out})\\,1\\,"
            f"if(lt(t\\,{end})\\,({end}-t)/{fade_out}\\,0))))"
        )
    if fade_in > 0:
        return (
            f"if(lt(t\\,{start})\\,0\\,"
            f"if(lt(t\\,{start + fade_in})\\,(t-{start})/{fade_in}\\,1))"
        )
    return (
        f"if(lt(t\\,{start})\\,0\\,"
        f"if(lt(t\\,{end - fade_out})\\,1\\,"
        f"if(lt(t\\,{end})\\,({end}-t)/{fade_out}\\,0)))"
    )


class AddTextOperation(BaseModel):
    """Overlays a line of text for a time range using FFmpeg drawtext."""

    type: Literal["add_text"]
    input: OperationInput
    text: str
    fontfile: str
    x: str
    y: str
    start: float
    end: float
    fade_in: float = 0.0
    fade_out: float = 0.0
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
        if self.fade_in < 0:
            msg = "fade_in must be >= 0"
            raise ValueError(msg)
        if self.fade_out < 0:
            msg = "fade_out must be >= 0"
            raise ValueError(msg)
        duration = self.end - self.start
        if self.fade_in + self.fade_out > duration:
            msg = "fade_in + fade_out must be <= (end - start)"
            raise ValueError(msg)
        return self

    def resolve_input_path(self, results_by_id: dict[str, Path]) -> Path:
        if isinstance(self.input, str):
            return Path(self.input)
        resolved_path = results_by_id.get(self.input.id)
        if resolved_path is None:
            raise ValueError(
                f"Unknown operation id reference in add_text input: {self.input.id!r}"
            )
        return resolved_path

    def build_invocation(
        self, output_dir: Path, input_path: Path | None = None
    ) -> FFmpegInvocation:
        if input_path is None and isinstance(self.input, str):
            input_path = Path(self.input)
        if input_path is None:
            raise ValueError(
                "add_text input uses id reference but no resolved input_path was provided"
            )
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
            f"at ({self.x}, {self.y}) {self.text!r} "
            f"(fade_in={self.fade_in}, fade_out={self.fade_out})"
        )

        drawtext_opts = [
            f"fontfile={_escape_filter_path(font_path)}",
            f"textfile={_escape_filter_path(textfile_path)}",
            f"fontsize={self.fontsize}",
            f"fontcolor={self.fontcolor}",
            f"x={self.x}",
            f"y={self.y}",
            f"enable=between(t\\,{self.start}\\,{self.end})",
        ]
        alpha_expr = _build_alpha_expr(self.start, self.end, self.fade_in, self.fade_out)
        if alpha_expr is not None:
            drawtext_opts.append(f"alpha={alpha_expr}")
        ff = "drawtext=" + ":".join(drawtext_opts)

        command = (
            FFmpegCommandBuilder()
            .add_input(input_path)
            .set_video_filter(ff)
            .set_video_codec("libx264")
            .set_pixel_format("yuv420p")
            .set_audio_codec("copy")
            .set_output(output_path)
            .build()
        )
        return FFmpegInvocation(
            command=command,
            output_path=output_path,
            cleanup_paths=[textfile_path],
        )
