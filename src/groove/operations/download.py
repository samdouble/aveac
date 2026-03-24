from typing import Literal
from uuid import uuid4

import yt_dlp
from pydantic import BaseModel, Field, HttpUrl, field_validator


class DownloadOperation(BaseModel):
    type: Literal["download"]
    url: HttpUrl
    name: str | None = None
    id: str = Field(default_factory=lambda: str(uuid4()))

    @field_validator("url")
    @classmethod
    def must_be_youtube(cls, v: HttpUrl) -> HttpUrl:
        host = v.host or ""
        if not any(h in host for h in ("youtube.com", "youtu.be")):
            raise ValueError(f"URL must be a YouTube link, got: {v}")
        return v

    def run(self) -> None:
        label = self.name or str(self.url)
        print(f"[{self.id}] Starting download: {label}")
        ydl_opts = {
            "format": "bestvideo+bestaudio/best",
            "merge_output_format": "mp4",
            "outtmpl": "/downloads/%(title)s.%(ext)s",
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(str(self.url), download=False)
            print(f"[{self.id}] Downloading: {info['title']}")
            ydl.download([str(self.url)])
        print(f"[{self.id}] Done.")
