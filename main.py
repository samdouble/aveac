import yaml
import yt_dlp

CONFIG_PATH = "/app/config.yaml"


def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def main():
    config = load_config(CONFIG_PATH)
    url = config["url"]
    ydl_opts = {
        **config.get("yt_dlp", {}),
        "outtmpl": "/downloads/%(title)s.%(ext)s",
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        print(f"Downloading: {info['title']}")
        ydl.download([url])

    print("Download complete!")


if __name__ == "__main__":
    main()
