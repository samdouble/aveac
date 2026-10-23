from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from groove.ffmpeg_runtime import FFmpegInvocation


class ConvertOperation(BaseModel):
    type: Literal["convert"]
    input: str
    name: str | None = None
    id: str = Field(default_factory=lambda: str(uuid4()))
    output_format: Literal["mp3"] = "mp3"
    audio_bitrate: str = "192k"
    output: str | None = None

    def build_invocation(self, output_dir: Path) -> FFmpegInvocation:
        input_path = Path(self.input)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        output_path = output_dir / input_path.with_suffix(f".{self.output_format}").name
        label = self.name or input_path.name
        print(f"[{self.id}] Converting: {label} -> {output_path.name}")
        return FFmpegInvocation(
            command=[
                "ffmpeg",
                "-y",
                "-i",
                str(input_path),
                "-vn",
                "-ar",
                "48000",
                "-ac",
                "1",
                "-f",
                self.output_format,
                "-b:a",
                self.audio_bitrate,
                str(output_path),
            ],
            output_path=output_path,
        )
