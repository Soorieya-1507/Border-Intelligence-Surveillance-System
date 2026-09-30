import os
import subprocess

def download_video(url, output_path):
    print(f"Downloading {url} to {output_path}...")
    # Get the best video format (mp4) up to 720p to save space
    cmd = [
        "yt-dlp",
        "-f", "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "-o", output_path,
        url
    ]
    subprocess.run(cmd, check=True)
    print("Download complete.")

if __name__ == "__main__":
    os.makedirs("data/samples", exist_ok=True)
    # A generic test video: Oxford Town Centre or similar street CCTV view
    # A well-known 4K pedestrian walking sample (creative commons)
    # E.g. "Free Stock Footage of people walking" or traffic
    # URL: https://www.youtube.com/watch?v=1EiC9bvVGnk is a generic 4K walking video (London street)
    # Another standard is MOT16-04 or MOT17. Let's use a standard MOT sequence from YouTube or similar.
    # We will use this generic one: https://www.youtube.com/watch?v=MNn9qKG2AMQ (People Walking)
    sample_url = "https://www.youtube.com/watch?v=MNn9qKG2AMQ" 
    target = "data/samples/test_video.mp4"
    
    if not os.path.exists(target):
        try:
            download_video(sample_url, target)
        except Exception as e:
            print(f"Failed to download from YouTube: {e}")
            print("Falling back to a direct MP4 link...")
            fallback_url = "https://github.com/intel-iot-devkit/sample-videos/raw/master/people-detection.mp4"
            import urllib.request
            urllib.request.urlretrieve(fallback_url, target)
            print("Fallback download complete.")
    else:
        print(f"{target} already exists.")
