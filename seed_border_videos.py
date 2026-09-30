import os
import urllib.request

VIDEOS = {
    "border_post_alpha.mp4": "https://github.com/intel-iot-devkit/sample-videos/raw/master/people-detection.mp4",
    "border_road_vehicle.mp4": "https://raw.githubusercontent.com/intel-iot-devkit/sample-videos/master/car-detection.mp4",
    "checkpost_gate.mp4": "https://raw.githubusercontent.com/intel-iot-devkit/sample-videos/master/driver-desolation-detection.mp4"
}

def seed_videos():
    target_dir = os.path.join(os.path.dirname(__file__), "data/samples")
    os.makedirs(target_dir, exist_ok=True)
    
    for filename, url in VIDEOS.items():
        filepath = os.path.join(target_dir, filename)
        if not os.path.exists(filepath):
            print(f"Downloading sample video: {filename} from {url}...")
            try:
                urllib.request.urlretrieve(url, filepath)
                print(f"Successfully downloaded {filename}")
            except Exception as e:
                print(f"Failed to download {filename}: {e}")
        else:
            print(f"Sample video {filename} already exists.")

if __name__ == "__main__":
    seed_videos()
