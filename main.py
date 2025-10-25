import sounddevice as sd
import numpy as np
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from ctypes import POINTER, cast
from comtypes import CLSCTX_ALL

SAMPLE_RATE = 44100
OFFSET_DB = 100
SCALE = 1.2
BASE_GAIN = 50  
MIN_VOL, MAX_VOL = 0.2, 0.9
SMOOTHING = 0.1 

devices = AudioUtilities.GetSpeakers()
interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
volume_iface = cast(interface, POINTER(IAudioEndpointVolume))

def get_sys_vol():
    return volume_iface.GetMasterVolumeLevelScalar()

def set_sys_vol(v):
    v = float(np.clip(v, MIN_VOL, MAX_VOL))
    volume_iface.SetMasterVolumeLevelScalar(v, None)

def suggest_gain(db, base_gain=BASE_GAIN):
    if db > 65:
        adj = min((db - 65) * 1, 30)
    elif db < 50:
        adj = max((db - 50) * 1, -30)
    else:
        adj = 0
    return round(base_gain + adj, 1)


def audio_callback(indata, frames, time_info, status):
    if status:
        print(status)

    rms = np.sqrt(np.mean(indata**2))
    db_raw = 20 * np.log10(rms + 1e-6)
    db = (db_raw + OFFSET_DB) * SCALE

    gain_suggestion = suggest_gain(db)
    target_vol = np.clip(gain_suggestion / 100.0, MIN_VOL, MAX_VOL)

    current = get_sys_vol()
    new_vol = current + SMOOTHING * (target_vol - current)
    set_sys_vol(new_vol)

    print(f"Noise: {db:6.2f} dB → Suggested Vol: {gain_suggestion:5.1f}% | "
          f"Applied: {new_vol*100:5.1f}%")

if __name__ == "__main__":
    print("🎧 Smart Gain Control Active — Press Ctrl+C to stop\n")
    try:
        with sd.InputStream(callback=audio_callback, channels=1, samplerate=SAMPLE_RATE):
            while True:
                sd.sleep(200)  # runs indefinitely
    except KeyboardInterrupt:
        print("\n Stopped Smart Gain Control.")
