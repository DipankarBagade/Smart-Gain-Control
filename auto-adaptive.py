import sounddevice as sd
import numpy as np
import time
from collections import deque
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from ctypes import POINTER, cast
from comtypes import CLSCTX_ALL

# CONFIGURATION
SAMPLE_RATE = 44100
CHUNK = 2048                      # faster + continuous capture
SMOOTHING = 0.2                   # stronger response
MIN_VOLUME, MAX_VOLUME = 0.2, 0.95
ROLLING_WINDOW = 40               # adaptive learning window (sec)
CALC_INTERVAL = 4                 # recalc thresholds every 4 sec
NOISE_STABILITY = 0.4             # ignore tiny fluctuations

# System Volume Control
devices = AudioUtilities.GetSpeakers()
interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
volume_interface = cast(interface, POINTER(IAudioEndpointVolume))

def get_volume():
    return volume_interface.GetMasterVolumeLevelScalar()

def set_volume(v):
    volume_interface.SetMasterVolumeLevelScalar(
        float(np.clip(v, MIN_VOLUME, MAX_VOLUME)), None
    )

# Noise Measurement
stream = sd.InputStream(channels=1, samplerate=SAMPLE_RATE,
                        blocksize=CHUNK, dtype='float32')
stream.start()

def measure_db():
    block, _ = stream.read(CHUNK)
    rms = np.sqrt(np.mean(np.square(block)))
    db = 20 * np.log10(rms + 1e-7)

    # smoother scaling range for real-world noise
    db_norm = np.interp(db, [-80, -10], [0, 100])
    return db_norm

# Rolling Auto-Calibration 
noise_history = deque(maxlen=int(ROLLING_WINDOW * SAMPLE_RATE / CHUNK))
low_thresh, high_thresh = 35, 65
last_recalc = time.time()

def update_thresholds():
    global low_thresh, high_thresh
    arr = np.array(noise_history)
    avg = np.mean(arr)
    std = np.std(arr)

    low_thresh = max(5, avg - std)
    high_thresh = min(95, avg + std)

# Smart Volume Logic
def compute_volume(noise_level):
    current = get_volume()

    if noise_level > high_thresh + NOISE_STABILITY:
        desired = current + 0.08
    elif noise_level < low_thresh - NOISE_STABILITY:
        desired = current - 0.08
    else:
        return current  # no change

    return current + SMOOTHING * (desired - current)

# Main Loop
print("Smart Gain Control — Auto Adaptive Running…")
print("Ctrl+C to stop\n")

try:
    while True:
        noise = measure_db()
        noise_history.append(noise)

        if time.time() - last_recalc > CALC_INTERVAL:
            update_thresholds()
            last_recalc = time.time()

        new_vol = compute_volume(noise)
        set_volume(new_vol)

        print(f"\rNoise: {noise:5.1f} | Low: {low_thresh:5.1f} | "
              f"High: {high_thresh:5.1f} | Vol: {new_vol*100:5.1f}%",
              end="", flush=True)

        time.sleep(0.1)

except KeyboardInterrupt:
    print("\n Stopped Smart Gain Control")
    stream.stop()
    stream.close()
