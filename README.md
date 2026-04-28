[![CI](https://github.com/samdouble/groove-on-a-real-train/actions/workflows/checks.yml/badge.svg)](https://github.com/samdouble/groove-on-a-real-train/actions/workflows/checks.yml)
[![Coverage Status](https://coveralls.io/repos/samdouble/groove-on-a-real-train/badge.svg?branch=master&service=github)](https://coveralls.io/github/samdouble/groove-on-a-real-train?branch=master)

# AVEaC

FFmpeg is a great tool for video and audio processing, but its command-line interface can be daunting if you're aiming to do non-tri

[![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=fff)](https://www.python.org/)
[![uv](https://img.shields.io/badge/uv-261230.svg?logo=uv&logoColor=#de5fe9)](https://docs.astral.sh/uv/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=fff)](https://www.docker.com/)

## Usage

From the root of the repository, run:

```sh
docker compose up --build
```

### Configuration

#### Operations

##### Add image

```yaml
- type: "add_image"
  input: { id: "intro-cut" } # or "/output/somevideo.mp4"
  image: "/app/src/assets/images/logo.png"
  x: "(W-w)/2"
  y: "80"
  start: 1.0
  end: 4.5
  fade_in: 0.5
  fade_out: 0.5
  output: "somevideo-imaged.mp4"
```

##### Add text

```yaml
- type: "add_text"
  input: { id: "intro-cut" } # or "/output/somevideo.mp4"
  text: "Hello"
  fontfile: "/app/src/assets/fonts/Michland Script.otf"
  x: "(w-text_w)/2"
  y: "80"
  start: 1.0
  end: 4.5
  fade_in: 0.5
  fade_out: 0.5
  fontsize: 42
  fontcolor: "yellow"
  output: "somevideo-titled.mp4"
```

##### Concatenate

```yaml
- type: "concatenate"
  inputs:
    - "/output/part1.mp4"
    - { id: "intro-title-card" }
    - "/output/part3.mp4"
  mode: "reencode" # default; safer when stream parameters differ
  output: "merged.mp4"
```

##### Convert

```yaml
- type: "convert"
  input: "/output/somevideo.mp4"
  output_format: "mp3"
  output: "audio.mp3"

```

##### Cut

```yaml
- type: "cut"
  input: "/output/tor-vs-car-game-recap.mp3"
  start: "00:00:00"
  end: "00:00:05"
  output: "audio-cut.mp3"
```

##### Download

```yaml
- type: "download"
  url: "https://www.youtube.com/watch?v=dinyOvO2EEo"
  output: "audio.mp3"
```

##### Extract voice

```yaml
- type: "extract_voice"
  input: "/output/audio.mp3"
  target: "vocals"
  output: "audio-vocals.mp3"
```
