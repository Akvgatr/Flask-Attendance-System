import os, random
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write
import librosa
import speech_recognition as sr

BASE_DIR = os.path.dirname(__file__)
SAMPLES_DIR = os.path.join(BASE_DIR, "Voice_samples")
os.makedirs(SAMPLES_DIR, exist_ok=True)

WORDS = [
    "machine", "learning", "data", "science", "python", "flask",
    "student", "teacher", "voice", "recognition", "system", "database",
    "model", "feature", "classroom", "attendance", "speech", "verify"
]

# -----------------------
# Phrase generator
# -----------------------
def get_random_phrase(n=6):
    return " ".join(random.sample(WORDS, n))

# -----------------------
# Recording helper (PCM WAV)
# -----------------------
def record_audio(filename, duration=5, fs=16000):
    """Record microphone audio as proper 16-bit PCM WAV."""
    print("Recording...")
    audio = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype="int16")
    sd.wait()
    write(filename, fs, audio)
    print("Saved:", filename)

# -----------------------
# Features (MFCC)
# -----------------------
def extract_features(path):
    y, sr = librosa.load(path, sr=16000)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    return np.mean(mfcc.T, axis=0)

# -----------------------
# Speech presence check
# -----------------------
def has_speech(y, threshold=1e-5):
    """Check if audio has enough energy to be considered speech."""
    energy = float(np.mean(y**2))
    print(f"Energy={energy:.6f}")
    return energy > threshold

# -----------------------
# Transcription
# -----------------------
def transcribe(path):
    r = sr.Recognizer()
    with sr.AudioFile(path) as source:
        audio = r.record(source)
    try:
        return r.recognize_google(audio).lower()
    except sr.UnknownValueError:
        return ""
    except sr.RequestError:
        return ""

# -----------------------
# Registration
# -----------------------
def register_student(student_id, phrase, duration=5, fs=16000):
    wav_path = os.path.join(SAMPLES_DIR, f"{student_id}_registered.wav")
    feat_path = os.path.join(SAMPLES_DIR, f"{student_id}_features.npy")

    print(f"Expected phrase (register): {phrase}")
    record_audio(wav_path, duration=duration, fs=fs)

    features = extract_features(wav_path)
    np.save(feat_path, features)

    return {"ok": True, "message": f"Voice registered with phrase: '{phrase}'"}

# -----------------------
# Verification
# -----------------------
def verify_student(student_id, phrase, duration=8, fs=16000, threshold=0.75):
    feat_path = os.path.join(SAMPLES_DIR, f"{student_id}_features.npy")
    if not os.path.exists(feat_path):
        return {"ok": False, "message": "No registered voice found"}

    registered_features = np.load(feat_path)

    login_wav = os.path.join(SAMPLES_DIR, f"{student_id}_login.wav")
    print(f"Expected phrase (verify): {phrase}")
    record_audio(login_wav, duration=duration, fs=fs)

    # --- Step 1: Ensure speech is present
    y, sr = librosa.load(login_wav, sr=16000)
    if not has_speech(y):
        return {"ok": False, "message": "No speech detected"}

    # --- Step 2: Extract features + similarity
    features = extract_features(login_wav)
    sim = float(
        np.dot(registered_features, features) /
        (np.linalg.norm(registered_features) * np.linalg.norm(features))
    )
    print(f"Similarity={sim:.4f}")

    # --- Step 3: Transcribe and check phrase
    spoken_text = transcribe(login_wav)
    print(f"Recognized text: '{spoken_text}'")

    if phrase.lower() not in spoken_text:
        return {
            "ok": False,
            "similarity": sim,
            "expected_phrase": phrase,
            "spoken": spoken_text,
            "message": "Phrase mismatch"
        }

    # --- Final decision
    return {
        "ok": bool(sim > threshold),
        "similarity": sim,
        "expected_phrase": phrase,
        "spoken": spoken_text,
        "message": "Verification passed" if sim > threshold else "Verification failed"
    }
