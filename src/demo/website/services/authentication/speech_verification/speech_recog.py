import os
import random
import numpy as np
import soundfile as sf
import sounddevice as sd
import torch
from numpy.linalg import norm
from scipy.io.wavfile import write
from pyannote.audio import Model

# ---------- paths ----------
BASE_DIR = os.path.dirname(__file__)
SAMPLES_DIR = os.path.join(BASE_DIR, "Voice_samples")
os.makedirs(SAMPLES_DIR, exist_ok=True)

# ---------- lazy model cache ----------
_MODEL = None
def _get_model():
    global _MODEL
    if _MODEL is None:
        # If your env needs a HF token, set env var HUGGINGFACE_TOKEN and use: os.getenv("HUGGINGFACE_TOKEN")
        _MODEL = Model.from_pretrained("pyannote/embedding", use_auth_token=None)
    return _MODEL

# ---------- helpers ----------
_PHRASES = [
    "Artificial intelligence is the future.",
    "The quick brown fox jumps over the lazy dog.",
    "Today is a beautiful day.",
    "I love learning new things.",
    "Technology is evolving rapidly."
]

def get_random_phrase():
    return random.choice(_PHRASES)

def record_audio_wav(path, duration=4, fs=16000):
    """Records mono audio to `path`."""
    audio = sd.rec(int(duration * fs), samplerate=fs, channels=1)
    sd.wait()
    write(path, fs, audio)  # writes 16-bit PCM WAV

def embed_wav(path):
    """Returns an embedding vector for the given WAV file path."""
    model = _get_model()
    wav, sr = sf.read(path)
    wav_t = torch.tensor(wav, dtype=torch.float32).unsqueeze(0)
    with torch.no_grad():
        emb = model({"waveform": wav_t, "sample_rate": sr}).numpy().squeeze()
    return emb

# ---------- main callable ----------
def verify_student(student_id: str, threshold: float = 0.75, duration: int = 4, fs: int = 16000):
    """
    1) Prompts the user with a random phrase,
    2) Records voice, computes embedding,
    3) Compares with stored registration embedding: {student_id}_embedding.npy in Voice_samples/.

    Returns:
        dict: {"ok": bool, "similarity": float, "phrase": str, "message": str, "login_wav": path}
    """
    phrase = get_random_phrase()
    login_wav = os.path.join(SAMPLES_DIR, f"{student_id}_login.wav")
    reg_npy   = os.path.join(SAMPLES_DIR, f"{student_id}_embedding.npy")

    # Record
    try:
        record_audio_wav(login_wav, duration=duration, fs=fs)
    except Exception as e:
        return {"ok": False, "similarity": 0.0, "phrase": phrase, "message": f"Mic error: {e}", "login_wav": login_wav}

    # Load registered embedding
    if not os.path.exists(reg_npy):
        return {"ok": False, "similarity": 0.0, "phrase": phrase,
                "message": "No registered voice found. Please register first.", "login_wav": login_wav}

    try:
        stored_emb = np.load(reg_npy).squeeze()
        login_emb  = embed_wav(login_wav).squeeze()
    except Exception as e:
        return {"ok": False, "similarity": 0.0, "phrase": phrase, "message": f"Embedding error: {e}", "login_wav": login_wav}

    # Cosine similarity
    denom = (norm(stored_emb) * norm(login_emb))
    sim = float(np.dot(stored_emb, login_emb) / denom) if denom else 0.0
    ok = sim > threshold
    msg = "Voice Verified: Login Successful." if ok else "Voice Mismatch: Login Denied."

    return {"ok": ok, "similarity": sim, "phrase": phrase, "message": msg, "login_wav": login_wav}

def register_student(student_id: str, duration: int = 4, fs: int = 16000):
    """Records a clean sample and stores {student_id}_embedding.npy under Voice_samples/."""
    reg_wav = os.path.join(SAMPLES_DIR, f"{student_id}_register.wav")
    reg_npy = os.path.join(SAMPLES_DIR, f"{student_id}_embedding.npy")
    record_audio_wav(reg_wav, duration=duration, fs=fs)
    emb = embed_wav(reg_wav)
    np.save(reg_npy, emb)
    return {"ok": True, "message": "Registration voice saved.", "register_wav": reg_wav, "embedding": reg_npy}
