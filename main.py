import yt_dlp

URL = "https://www.youtube.com/watch?v=dinyOvO2EEo"

ydl_opts = {
    "format": "bestvideo+bestaudio/best",
    "merge_output_format": "mp4",
}

def main():
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(URL, download=False)
        print(f"Downloading: {info['title']}")
        ydl.download([URL])
    print("Download complete!")


if __name__ == "__main__":
    main()
