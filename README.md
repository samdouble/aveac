# Groove on a Real Train

FFmpeg is a great tool for video and audio processing, but its command-line interface can be daunting if you're aiming to do non-tri

## Usage

From the root of the repository, run:

```sh
docker compose up --build
```

### Configuration

#### Operations

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

##### Suno extend

```yaml
- type: "suno_extend"
  input: "/output/audio-vocals.mp3"
  output: "audio-extended.mp3"
```
