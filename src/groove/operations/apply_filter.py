import subprocess
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

FILTERS_DIR = Path("/app/src/groove/filters")


class ApplyFilterOperation(BaseModel):
    type: Literal["apply_filter"]
    input: str
    filter: Literal["gta5wasted"]
    timestamp: float
    name: str | None = None
    id: str = Field(default_factory=lambda: str(uuid4()))
    output: str | None = None

    def run(self, output_dir: Path) -> Path:
        input_path = Path(self.input)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        output_path = output_dir / f"{input_path.stem}_{self.filter}{input_path.suffix}"
        label = self.name or input_path.name
        print(f"[{self.id}] Applying {self.filter} to: {label} at t={self.timestamp}s")

        match self.filter:
            case "gta5wasted":
                self._apply_gta5wasted(input_path, output_path)

        print(f"[{self.id}] Done → {output_path.name}")
        return output_path

    def _apply_gta5wasted(self, input_path: Path, output_path: Path) -> None:
        t1 = self.timestamp
        t2 = t1 + 3.0
        gta_offset = t1 + 3.0
        filter_video = FILTERS_DIR / "gta5Wasted" / "video.mp4"

        filter_complex = (
            f"[0:v]trim=0:{t1},setpts=PTS-STARTPTS[0v0];"
            f"[0:a]atrim=0:{t1},asetpts=PTS-STARTPTS[0a0];"
            f"[0:v]trim={t1}:{t2},setpts=PTS-STARTPTS[0v1];"
            f"[0:a]atrim={t1}:{t2},asetpts=PTS-STARTPTS[0a1];"
            f"[0v1]setpts=2.0*PTS[0v1a];"
            f"[0v1a]eq=contrast=1.5:saturation=0[0v1b];"
            f"[0v1b]colorchannelmixer=0.9:0:0:0:0:1.2:0:0[0v1c];"
            f"[0a1]atempo=0.5[0a1a];"
            f"[0a1a]volume=0[0a1b];"
            f"[0:v]trim={t2},setpts=PTS-STARTPTS[0v2];"
            f"[0:a]atrim={t2},asetpts=PTS-STARTPTS[0a2];"
            f"[0v2]setpts=3.0*PTS[0v2a];"
            f"[0v2a]eq=contrast=2.5:saturation=0[0v2c];"
            f"[0a2]volume=0[0a2a];"
            f"[0v0][0a0][0v1c][0a1b][0v2c][0a2a]concat=n=3:v=1:a=1[v0out][a0out];"
            f"[v0out]fps=fps=30[v0out];"
            f"[1:v]fps=fps=30[1va];"
            f"[1va][v0out]scale2ref=iw:ih[1vb][v0out];"
            f"[1vb]colorkey=0x00ff00:0.3:0.7[1vc];"
            f"[1vc]colorchannelmixer=1:0:0:0:0:0:0:0[ckout];"
            f"[v0out][ckout]overlay=x=(main_w-overlay_w)/2:y=(main_h-overlay_h)/2:shortest=1[outv];"
            f"[1:a]adelay=8500|8500[1aa];"
            f"[a0out][1aa]amix[outa]"
        )

        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", str(input_path),
                "-itsoffset", str(gta_offset),
                "-i", str(filter_video),
                "-filter_complex", filter_complex,
                "-map", "[outv]",
                "-map", "[outa]",
                str(output_path),
            ],
            check=True,
        )
