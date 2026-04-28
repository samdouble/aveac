from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from groove.ffmpeg_runtime import FFmpegInvocation
from groove.operations.input_ref import OperationInput


class AddImageOperation(BaseModel):
    """Overlays an image for a time range using FFmpeg overlay."""

    type: Literal["add_image"]
    input: OperationInput
    image: str
    x: str
    y: str
    start: float
    end: float
    fade_in: float = 0.0
    fade_out: float = 0.0
    name: str | None = None
    id: str = Field(default_factory=lambda: str(uuid4()))
    output: str | None = None

    @model_validator(mode="after")
    def time_range(self) -> "AddImageOperation":
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
                f"Unknown operation id reference in add_image input: {self.input.id!r}"
            )
        return resolved_path

    def build_invocation(
        self, output_dir: Path, input_path: Path | None = None
    ) -> FFmpegInvocation:
        if input_path is None and isinstance(self.input, str):
            input_path = Path(self.input)
        if input_path is None:
            raise ValueError(
                "add_image input uses id reference but no resolved input_path was provided"
            )
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        image_path = Path(self.image)
        if not image_path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")

        output_path = output_dir / f"{input_path.stem}_addimage{input_path.suffix}"
        label = self.name or input_path.name
        print(
            f"[{self.id}] Add image on {label!r} t=[{self.start}, {self.end}) "
            f"at ({self.x}, {self.y}) from {image_path.name!r} "
            f"(fade_in={self.fade_in}, fade_out={self.fade_out})"
        )

        duration = self.end - self.start
        filter_parts = [
            f"[1:v]format=rgba,trim=0:{duration},setpts=PTS-STARTPTS+{self.start}/TB[ol0]"
        ]

        overlay_label = "ol0"
        if self.fade_in > 0:
            filter_parts.append(
                f"[{overlay_label}]fade=t=in:st={self.start}:d={self.fade_in}:alpha=1[ol1]"
            )
            overlay_label = "ol1"
        if self.fade_out > 0:
            fade_out_start = self.end - self.fade_out
            filter_parts.append(
                f"[{overlay_label}]fade=t=out:st={fade_out_start}:d={self.fade_out}:alpha=1[ol2]"
            )
            overlay_label = "ol2"

        filter_parts.append(
            f"[0:v][{overlay_label}]overlay=x={self.x}:y={self.y}:"
            f"enable=between(t\\,{self.start}\\,{self.end})[outv]"
        )

        return FFmpegInvocation(
            command=[
                "ffmpeg",
                "-y",
                "-i",
                str(input_path),
                "-loop",
                "1",
                "-i",
                str(image_path),
                "-filter_complex",
                ";".join(filter_parts),
                "-map",
                "[outv]",
                "-map",
                "0:a?",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "copy",
                str(output_path),
            ],
            output_path=output_path,
        )
