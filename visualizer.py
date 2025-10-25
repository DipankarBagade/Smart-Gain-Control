import sounddevice as sd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# === CONFIG ===
duration = 0.2         # window per frame (seconds)
samplerate = 44100
OFFSET_DB = 100
SCALE = 1.2
BASE_GAIN = 50

# === Buffers ===
history_len = 100
db_values = [40] * history_len
gain_values = [BASE_GAIN] * history_len

# === Gain Logic ===
def suggest_gain(db, base_gain=BASE_GAIN):
    if db > 65:
        adj = min((db - 65) * 1, 30)
    elif db < 50:
        adj = max((db - 50) * 1, -30)
    else:
        adj = 0
    return base_gain + adj

# === Audio Processing ===
latest_db = 40  # global shared variable

def audio_callback(indata, frames, time, status):
    global latest_db
    if status:
        print(status)
    rms = np.sqrt(np.mean(indata**2))
    db_raw = 20 * np.log10(rms + 1e-6)
    db = (db_raw + OFFSET_DB) * SCALE
    latest_db = db

# === Setup Microphone Stream ===
stream = sd.InputStream(callback=audio_callback, channels=1, samplerate=samplerate)
stream.start()

# === Plot Setup ===
fig, ax1 = plt.subplots(figsize=(8, 4))
ax2 = ax1.twinx()
x = np.arange(history_len)

line1, = ax1.plot(x, db_values, label='Noise Level (dB)', color='tab:blue', lw=2)
line2, = ax2.plot(x, gain_values, label='Suggested Gain (%)', color='tab:orange', lw=2)

ax1.set_ylim(30, 90)
ax1.set_ylabel("Noise Level (dB)")
ax2.set_ylim(20, 100)
ax2.set_ylabel("Gain (%)")
plt.title("🎧 Smart Gain Control — Real-Time Visualization")
plt.grid(True)

# === Combine Legends ===
lines = [line1, line2]
labels = [line.get_label() for line in lines]
plt.legend(lines, labels, loc="upper right")

# === Animation Update ===
def update(frame):
    db = latest_db
    gain = suggest_gain(db)

    db_values.append(db)
    gain_values.append(gain)
    db_values.pop(0)
    gain_values.pop(0)

    line1.set_ydata(db_values)
    line2.set_ydata(gain_values)

    print(f"Noise: {db:.2f} dB | Gain: {gain:.1f}%")  # Debug print

    return line1, line2

ani = animation.FuncAnimation(fig, update, interval=duration * 1000, blit=True)
plt.tight_layout()
plt.show()

# === Cleanup on exit ===
stream.stop()
stream.close()
