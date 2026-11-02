
from __future__ import annotations


import os
import random
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Sequence, Tuple, TypeVar

from flask import (
    Flask,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from textblob import TextBlob
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from PIL import Image
import cv2
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image as RLImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except Exception:
    mp = None
    MEDIAPIPE_AVAILABLE = False
import base64
import io
import requests
import time
import traceback
import json
import re
try:
    # Optional: load .env automatically if python-dotenv is installed
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # It's okay if dotenv isn't installed; users can set env vars otherwise
    pass

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "emocare.db"
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

# LLM Integration settings (Ollama - local, no API key required)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat").strip()
# Use faster models: llama3.2:1b (fastest), llama3.2:3b (balanced), llama3.2 (7b, slower but better quality)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b").strip()
# Faster models respond quicker - adjust based on your model choice
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "30"))  # seconds - reduce for faster models
LLM_ENABLED = True  # LLM is considered enabled; failures will fall back to rule-based
# Limit response length for faster generation (tokens)
MAX_RESPONSE_TOKENS = int(os.getenv("MAX_RESPONSE_TOKENS", "150"))  # Shorter = faster

F = TypeVar("F", bound=Callable[..., Any])

# Indian Standard Time (IST) is UTC+5:30
IST = timezone(timedelta(hours=5, minutes=30))

def get_ist_now() -> datetime:
    """Get current time in IST."""
    return datetime.now(IST)

def convert_to_ist(dt: datetime) -> datetime:
    """Convert a datetime object to IST timezone."""
    if dt.tzinfo is None:
        # Assume UTC if no timezone info
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST)

def format_ist_time(dt: datetime, format_type: str = "display") -> str:
    """Format datetime in IST for display."""
    ist_dt = convert_to_ist(dt)
    
    if format_type == "display":
        return ist_dt.strftime("%b %d · %H:%M IST")
    elif format_type == "full":
        return ist_dt.strftime("%Y-%m-%d %H:%M:%S IST")
    elif format_type == "time_only":
        return ist_dt.strftime("%H:%M IST")
    elif format_type == "date_only":
        return ist_dt.strftime("%b %d, %Y")
    else:
        return ist_dt.strftime("%b %d · %H:%M IST")

EMOTION_KEYWORDS: Dict[str, Sequence[str]] = {
    "Happiness": [
        "happy", "joy", "joyful", "excited", "thrilled", "elated", "cheerful", 
        "delighted", "pleased", "content", "satisfied", "grateful", "thankful",
        "optimistic", "positive", "upbeat", "wonderful", "amazing", "fantastic", 
        "great", "excellent", "good", "smile", "smiling", "laugh", "laughing", 
        "fun", "enjoy", "enjoying", "love", "loving", "blessed", "ecstatic",
        "glad", "pleased", "proud", "celebrate", "celebration", "victory", "win"
    ],
    "Neutral": [
        "calm", "peaceful", "serene", "tranquil", "relaxed", "comfortable",
        "steady", "balanced", "centered", "grounded", "stable", "okay", "fine",
        "neutral", "normal", "quiet", "still", "gentle", "soft", "mild",
        "moderate", "even", "level", "composed", "collected", "at ease",
        "alright", "decent", "average", "regular", "standard", "typical"
    ],
    "Stress": [
        "stress", "stressed", "pressure", "pressured", "overwhelmed", "busy",
        "rushed", "hurried", "tight", "deadline", "urgent", "demanding",
        "exhausted", "tired", "weary", "drained", "burnt out", "overworked",
        "hectic", "chaotic", "frantic", "intense", "heavy", "burden", "load",
        "swamped", "stretched", "maxed out", "anxious", "anxiety", "worried",
        "worry", "nervous", "tense", "uneasy", "restless", "agitated", "panicked",
        "panic", "fearful", "afraid", "scared", "terrified", "overthinking",
        "burnout", "burned out", "burnt-out", "burned-out"
    ],
    "Anger": [
        "angry", "anger", "mad", "furious", "rage", "enraged", "livid",
        "irritated", "annoyed", "frustrated", "aggravated", "outraged",
        "resentful", "bitter", "hostile", "aggressive", "fuming", "seething",
        "pissed", "fed up", "sick of", "hate", "disgusted", "infuriated",
        "snapped", "explode", "exploded", "blow up", "blown up"
    ],
    "Sadness": [
        "sad", "sadness", "depressed", "depression", "down", "low", "blue",
        "melancholy", "gloomy", "dark", "empty", "hollow", "numb", "hopeless",
        "helpless", "worthless", "useless", "meaningless", "pointless",
        "lonely", "alone", "isolated", "abandoned", "rejected", "unloved",
        "miserable", "awful", "terrible", "horrible", "devastated", "broken",
        "lost", "confused", "disappointed", "discouraged", "defeated", "despair",
        "crying", "tears", "upset", "hurt", "heartbroken", "grief", "grieving"
    ]
}

# Add some additional keywords that indicate being scolded/reprimanded or humiliated
# which often map to stress/sadness states. These are not exhaustive but help
# catch common phrasing like "scolded me" or "yelled at me" (including minor typos).
EXTRA_KEYWORD_MAP = {
    "scold": "Stress",
    "scolded": "Stress",
    "scolding": "Stress",
    "yell": "Stress",
    "yelled": "Stress",
    "yelling": "Stress",
    "shout": "Stress",
    "shouted": "Stress",
    "shouting": "Stress",
    "reprimand": "Stress",
    "reprimanded": "Stress",
    "punish": "Stress",
    "punished": "Stress",
    "humiliat": "Sadness",  # catch 'humiliate' / 'humiliated' stems
    "ashamed": "Sadness",
    "embarrass": "Sadness",
}

EMOTION_COLORS = {
    "Happiness": "#fbbf24",
    "Neutral": "#22d3ee",
    "Stress": "#f97316",
    "Sadness": "#a78bfa",
    "Anger": "#ef4444",
}

ACTIVITY_LIBRARY = {
    "Happiness": [
        {"title": "Capture a gratitude note", "desc": "Anchor the upbeat energy with three specific wins.", "video_query": "gratitude journaling tips"},
        {"title": "Share the light", "desc": "Send a kind message to someone who'd smile hearing from you.", "video_query": "how to write a kind message"},
    ],
    "Neutral": [
        {"title": "Slow breathing reset", "desc": "4-7-8 breathing for two minutes to stay steady.", "video_query": "4 7 8 breathing guide"},
        {"title": "Mindful tea break", "desc": "Sip something warm while noting five gentle sensations.", "video_query": "mindful tea break guided meditation"},
    ],
    "Stress": [
        {"title": "Body scan pause", "desc": "Unclench shoulders, jaw, and hands—release the hidden tension.", "video_query": "body scan meditation for stress"},
        {"title": "Prioritize list", "desc": "Write three tasks only; everything else can wait.", "video_query": "how to prioritize tasks"},
        {"title": "Grounding walk", "desc": "Notice five colors while moving—bring the mind back to the body.", "video_query": "grounding techniques walk"},
        {"title": "Shake it out", "desc": "Two-minute physical shake to move the heat through.", "video_query": "shake it out exercise"},
    ],
    "Sadness": [
        {"title": "Sunlight stretch", "desc": "Step near a window, stretch arms overhead, breathe deeply.", "video_query": "stretching morning routine"},
        {"title": "Micro-joy hunt", "desc": "List one tiny thing that felt kind today—even if it seemed small.", "video_query": "micro joy activities"},
    ],
    "Anger": [
        {
            "title": "60-Second Anger Scan",
            "desc": "You don’t have to “find the exact spot.” Do a quick scan from jaw → neck → shoulders → chest → hands. Notice where the sensation is strongest (tight, hot, heavy, buzzing). Pick the strongest area (even if it’s just “most noticeable”), and silently label it: “This is anger.”",
            "video_query": "body scan for anger reset",
        },
        {
            "title": "Boundary Sentence",
            "desc": "Write 2 lines: (1) “I need…” (what felt crossed) and (2) “I can…” (one safe step you want next—space, a clear boundary, or an honest request). Keep it short and specific to this moment.",
            "video_query": "how to set boundaries journal prompt",
        },
        {
            "title": "Impulse Pause (STOP)",
            "desc": "Right now, do: STOP (Stop) → Take one slow breath → Observe what anger is trying to protect → Proceed with one small action that’s safe for you (drink water, unclench jaw, step away, message later).",
            "video_query": "stop skill emotion regulation anger",
        },
    ],
}

RESPONSE_LIBRARY = {
    "Happiness": [
        "I can feel that lightness from your words. Savor it for a moment—what helped you feel this way today?",
        "Love seeing you in this headspace. Lets anchor it so you can reach for it again later.",
    ],
    "Neutral": [
        "Sounds like youre steadying yourself well. Want to note anything that kept you grounded?",
        "Appreciate this gentle check-in. Even neutral days deserve a quiet celebration.",
    ],
    "Stress": [
        "That sounds like a lot to carry. Lets pick one part to soften or delegate together.",
        "I hear how tight everything feels. A small pause could give your nervous system some room.",
        "Those racing thoughts can feel overwhelming. Lets breathe and name whats actually within your control.",
        "Your frustration makes sense. Lets unpack where its landing in your body and give it an exit.",
    ],
    "Sadness": [
        "Thank you for trusting me with this heaviness. Youre not alone in it, even if it feels that way.",
        "Lets be gentle with today. Is there one kind thing you can offer yourself right now?",
    ],
    "Anger": [
        "I hear how hot and sharp this feels. Anger usually shows up when something important feels crossed—what happened right before it spiked?",
        "That sounds really infuriating. Do you want to vent it out, or do you want help figuring out what to do next?",
    ],
}
RESPONSE_LIBRARY["Default"] = [
    "Im here with you. Tell me a little more so we can unpack it together.",
]


@dataclass
class EmotionInsight:
    emotion: str
    intensity: int
    confidence: float
    keywords: List[str]
    polarity: float


def normalize_emotion(emotion: str | None) -> str:
    """Maps old emotions to the current emotion set.
    
    Maps:
    - Happiness -> Happiness
    - Calm -> Neutral
    - Stress -> Stress
    - Anxiety -> Stress
    - Depression -> Sadness
    - Anger -> Anger
    """
    if not emotion:
        return "Neutral"
    emotion = emotion.strip()
    emotion_map = {
        "Happiness": "Happiness",
        "Sadness": "Sadness",
        "Calm": "Neutral",
        "Neutral": "Neutral",
        "Stress": "Stress",
        "Anxiety": "Stress",
        "Depression": "Sadness",
        "Anger": "Anger",
    }
    return emotion_map.get(emotion, "Neutral")


def analyze_emotion(message: str) -> EmotionInsight:
    """Enhanced text-based emotion analysis with improved accuracy."""
    if not message or not message.strip():
        return EmotionInsight(
            emotion="Neutral",
            intensity=1,
            confidence=0.1,
            keywords=[],
            polarity=0.0
        )
    
    normalized = message.lower().strip()
    keyword_hits = Counter()
    matched_keywords = []
    # Emoji-to-emotion mapping: treat standalone emoji messages as strong signals,
    # and include emoji as a matched keyword when mixed with text.
    # Emoji-to-emotion mapping (includes Anger)
    EMOJI_MAP = {
        "😊": "Happiness", "😄": "Happiness", "😁": "Happiness", "😍": "Happiness", 
        "🤗": "Happiness", "👍": "Happiness", "😃": "Happiness", "😆": "Happiness",
        "😢": "Sadness", "😭": "Sadness", "😞": "Sadness", "😔": "Sadness",
        "😕": "Sadness", "🙁": "Sadness", "😟": "Sadness",  # Worried face -> Sadness (low energy)
        "😠": "Anger", "😡": "Anger", "😤": "Anger", "👎": "Anger",
        "😰": "Stress", "😨": "Stress", "😧": "Stress", "😩": "Stress", 
        "😫": "Stress", "😖": "Stress",  # Tense/worried faces -> Stress (high energy)
        "🙂": "Neutral", "😌": "Neutral", "🤔": "Neutral", "😐": "Neutral",
        "😑": "Neutral", "😶": "Neutral"
    }
    # Find any emoji characters present in the message
    found_emojis = [ch for ch in message if ch in EMOJI_MAP]
    if found_emojis:
        # If the message contains no alphanumeric characters, treat emoji as primary signal
        if not re.search(r"[A-Za-z0-9]", message):
            chosen = EMOJI_MAP.get(found_emojis[0], "Neutral")
            intensity_map = {"Happiness": 3, "Neutral": 2, "Sadness": 4, "Stress": 3, "Anger": 4}
            polarity_map = {"Happiness": 0.6, "Neutral": 0.1, "Sadness": -0.6, "Stress": -0.3, "Anger": -0.65}
            return EmotionInsight(
                emotion=chosen,
                intensity=intensity_map.get(chosen, 3),
                confidence=0.9,
                keywords=[f"emoji_{found_emojis[0]}"],
                polarity=polarity_map.get(chosen, 0.0),
            )
        else:
            # Mixed text+emoji: include the emoji as a matched keyword to influence scoring
            for em in found_emojis:
                matched_keywords.append(f"emoji_{em}")
    
    # Enhanced keyword matching with word boundaries
    for emotion_key, keywords in EMOTION_KEYWORDS.items():
        for keyword in keywords:
            # Use word boundaries for exact matches
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, normalized):
                keyword_hits[emotion_key] += 1
                matched_keywords.append(keyword)
    
    # Sentiment analysis
    try:
        blob = TextBlob(message)
        polarity = float(blob.sentiment.polarity)
        subjectivity = float(blob.sentiment.subjectivity)
    except:
        polarity = 0.0
        subjectivity = 0.5
    
    # Social isolation detection patterns (highest priority for sadness)
    social_patterns = [
        r"\b(?:feel|feeling|am|i'm)\s+(?:so\s+)?(?:lonely|alone|isolated)\b",
        r"\b(?:no\s+one|nobody|noone|no-one)\s+(?:talks?|speaks?|listens?|cares?|understands?)\b",
        r"\b(?:have\s+)?no\s+(?:friends|one\s+to\s+talk\s+to|support)\b",
        r"\b(?:everyone|everybody)\s+(?:left|abandoned|ignores?)\s+me\b",
        r"\b(?:feel|feeling)\s+(?:disconnected|cut\s+off|shut\s+out)\b",
        r"\b(?:can't|cannot)\s+(?:connect|relate)\s+(?:to|with)\s+(?:anyone|people)\b"
    ]
    
    social_isolation_detected = False
    for pattern in social_patterns:
        if re.search(pattern, normalized, re.IGNORECASE):
            social_isolation_detected = True
            matched_keywords.append("social_isolation")
            break

    # High-priority detection: physical harm / abuse phrases (should not be classified as Neutral)
    # Examples: "my parents beat me", "I was beaten", "they hit me", "my parents beated me" (typo)
    abuse_pattern = r"\b(beat|beated|beaten|hit|hitted|abuse|abused|molest|molested|assault|assaulted)\b"
    # direct patterns referencing family or parents performing harm
    family_abuse_pattern = r"\b(my|our|the)\s+(parents|mother|father|parents')\b.*\b(beat|beated|beaten|hit|hitted|abuse|abused)\b"
    if re.search(family_abuse_pattern, normalized, re.IGNORECASE) or re.search(r"\b(i\s+was\s+beaten|i\s+was\s+hit|they\s+beat\s+me|they\s+hit\s+me)\b", normalized, re.IGNORECASE) or re.search(abuse_pattern, normalized, re.IGNORECASE):
        # Treat explicit physical harm statements as high-priority signals -> Stress
        emotion = "Stress"
        intensity = 4
        confidence = 0.9
        matched_keywords.append("physical_harm")
        return EmotionInsight(
            emotion=emotion,
            intensity=intensity,
            confidence=confidence,
            keywords=matched_keywords,
            polarity=polarity,
        )
    # Priority detection for scold/reprimand/yell phrasing
    scold_pattern = r"\b(scold|scolded|scolding|yell|yelled|yelling|shout|shouted|shouting|reprimand|reprimanded|punish|punished)\b"
    
    # Determine emotion and calculate metrics
    # Priority: Check for specific patterns first to avoid confusion
    if social_isolation_detected:
        emotion = "Sadness"
        intensity = max(4, min(5, int(abs(polarity) * 2) + 4))
        confidence = min(1.0, 0.85 + (0.1 if polarity < -0.2 else 0.05))
    elif re.search(scold_pattern, normalized, re.IGNORECASE):
        # scold/reprimand/punish/yell -> Stress
        emotion = "Stress"
        intensity = max(3, int(abs(polarity) * 3) + 2)
        confidence = min(0.9, 0.55 + min(0.35, abs(polarity)))
        matched_keywords.append("scold_or_reprimand")
    elif keyword_hits:
        # Get emotion counts to better distinguish Stress vs Sadness vs Anger
        stress_count = keyword_hits.get("Stress", 0)
        sadness_count = keyword_hits.get("Sadness", 0)
        anger_count = keyword_hits.get("Anger", 0)
        
        # Better disambiguation: check for specific indicators
        # Stress indicators: pressure/overwhelm/anxiety/tension (not anger words)
        stress_specific = re.search(r"\b(pressure|pressured|overwhelmed|anxious|anxiety|tense|nervous|worried|worry|busy|rushed|deadline|urgent|panic|panicked|afraid|scared|terrified|overthinking)\b", normalized, re.IGNORECASE)
        # Sadness indicators: sad, lonely, empty, hopeless, crying, tears, heartbroken, grief
        sadness_specific = re.search(r"\b(sad|sadness|lonely|alone|empty|hollow|hopeless|helpless|worthless|crying|tears|heartbroken|grief|grieving|depressed|depression)\b", normalized, re.IGNORECASE)
        # Anger indicators: angry/mad/frustrated/irritated/rage/hate
        anger_specific = re.search(r"\b(angry|anger|mad|furious|rage|enraged|livid|irritated|annoyed|frustrated|aggravated|outraged|resentful|hostile|aggressive|fuming|seething|pissed|hate|disgusted|infuriated)\b", normalized, re.IGNORECASE)
        
        # If multiple negative states are present, use keyword counts and specific patterns to decide
        if sadness_specific and (stress_specific or anger_specific):
            # If stress keywords significantly outnumber sadness, it's stress
            if stress_specific and stress_count >= sadness_count * 1.5 and stress_count >= max(anger_count, 0) * 1.2:
                emotion = "Stress"
            elif anger_specific and anger_count >= sadness_count * 1.5 and anger_count >= max(stress_count, 0) * 1.2:
                emotion = "Anger"
            elif sadness_count >= max(stress_count, anger_count) * 1.3:
                emotion = "Sadness"
            else:
                # Default to the one with more keyword hits (sadness tends to be under-detected)
                if sadness_count > max(stress_count, anger_count):
                    emotion = "Sadness"
                elif anger_count > stress_count:
                    emotion = "Anger"
                else:
                    emotion = "Stress"
        elif anger_specific and stress_specific:
            # Anger vs Stress: wide "anxiety" vocabulary -> Stress, otherwise Anger
            emotion = "Stress" if stress_count > anger_count else "Anger"
        elif anger_specific:
            emotion = "Anger"
        elif stress_specific:
            emotion = "Stress"
        elif sadness_specific:
            emotion = "Sadness"
        else:
            # Fallback to most common emotion from keywords
            detected_emotion = keyword_hits.most_common(1)[0][0]
            keyword_count = keyword_hits[detected_emotion]
            
            # `detected_emotion` may already be one of our current keys
            # (Happiness/Sadness/Stress/Anger/Neutral). Keep it as-is.
            if detected_emotion in {"Happiness", "Sadness", "Stress", "Neutral", "Anger"}:
                emotion = detected_emotion
            else:
                # Otherwise, map legacy emotions to current system
                emotion_map = {
                    "Happiness": "Happiness",
                    "Calm": "Neutral",
                    "Stress": "Stress",
                    "Anxiety": "Stress",
                    "Depression": "Sadness",
                    "Anger": "Anger",
                }
                emotion = emotion_map.get(detected_emotion, "Neutral")
                keyword_count = keyword_hits.get(emotion, keyword_count)

        # Calculate intensity (1-5 scale)
        if emotion == "Stress":
            final_count = stress_count
        elif emotion == "Sadness":
            final_count = sadness_count
        elif emotion == "Anger":
            final_count = anger_count
        else:
            final_count = keyword_hits.get(emotion, 0)
        base_intensity = min(5, max(1, int(abs(polarity) * 3) + final_count))

        # Adjust for emotion type
        if emotion in {"Stress", "Sadness", "Anger"}:
            intensity = max(3, base_intensity)
        else:
            intensity = max(1, base_intensity)

        # Calculate confidence - boost if we have specific pattern matches
        base_confidence = abs(polarity) * 0.3 + min(final_count / 2, 0.5) + subjectivity * 0.2
        if (emotion == "Stress" and stress_specific) or (emotion == "Sadness" and sadness_specific):
            base_confidence += 0.15  # Boost confidence for specific pattern matches
        confidence = min(1.0, base_confidence)
    else:
        # Fallback to sentiment analysis - map to 4 emotions
        # Better distinction: Very negative -> Sadness, Moderately negative -> Stress
        if polarity > 0.3:
            emotion = "Happiness"
            intensity = min(5, max(2, int(polarity * 4) + 1))
        elif polarity < -0.5:
            # Very negative sentiment -> Sadness (deep negative emotions)
            emotion = "Sadness"
            intensity = min(5, max(3, int(abs(polarity) * 4) + 1))
        elif polarity < -0.25:
            # Moderately negative -> Stress (tension, worry, but not deep sadness)
            emotion = "Stress"
            intensity = min(4, max(2, int(abs(polarity) * 3) + 1))
        elif polarity < -0.1:
            # Slightly negative -> could be Stress (mild tension)
            emotion = "Stress"
            intensity = min(3, max(2, int(abs(polarity) * 2) + 1))
        else:
            emotion = "Neutral"
            intensity = max(1, min(3, 2))

        confidence = min(0.7, abs(polarity) + 0.2)
    
    return EmotionInsight(
        emotion=emotion,
        intensity=intensity,
        confidence=confidence,
        keywords=matched_keywords,
        polarity=polarity
    )


def analyze_image_emotion(image_path: Path) -> EmotionInsight:
    """More robust image emotion analysis using Mediapipe FaceMesh (if available)
    with a cascade-based fallback.

    Strategy:
    - Prefer lightweight OpenCV cascades (face + smile + eyes).
    - Extract mouth contour and compute mouth-aspect ratio and contrast.
    - Use smile cascade detections as a strong happiness signal.
    - Use edge density, brightness, symmetry and eye openness to disambiguate.
    - Log per-image diagnostics to `image_emotion.log` for iterative tuning.
    """
    try:
        img = cv2.imread(str(image_path))
        if img is None:
            return EmotionInsight("Neutral", 2, 0.1, ["image_load_failed"], 0.0)

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        h_img, w_img = gray.shape[:2]

        # If Mediapipe is available, prefer landmark-based analysis for accuracy
        if MEDIAPIPE_AVAILABLE:
            try:
                mp_face_mesh = mp.solutions.face_mesh
                with mp_face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1, refine_landmarks=True) as fm:
                    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    results = fm.process(rgb)
                    if results and results.multi_face_landmarks:
                        lm = results.multi_face_landmarks[0].landmark
                        # helper to get landmark pixel coords
                        def lmk(idx):
                            p = lm[idx]
                            return np.array([p.x * w_img, p.y * h_img])

                        # mouth corners and lips (common FaceMesh indices)
                        left_corner = lmk(61)
                        right_corner = lmk(291)
                        upper_lip = lmk(13)
                        lower_lip = lmk(14)
                        # eye landmarks for openness
                        left_eye_top = lmk(159)
                        left_eye_bottom = lmk(145)
                        right_eye_top = lmk(386)
                        right_eye_bottom = lmk(374)

                        mouth_h = np.linalg.norm(upper_lip - lower_lip)
                        mouth_w = np.linalg.norm(left_corner - right_corner)
                        mouth_aspect = float(mouth_h / (mouth_w + 1e-6))

                        # smile curvature: corners relative to lip center Y (smile -> corners higher)
                        lip_center_y = (upper_lip[1] + lower_lip[1]) / 2.0
                        corners_avg_y = (left_corner[1] + right_corner[1]) / 2.0
                        corner_lift = (lip_center_y - corners_avg_y) / (h_img + 1e-6)

                        # eye openness average (normalized) - fixed calculation
                        left_eye_height = abs(left_eye_top[1] - left_eye_bottom[1])
                        right_eye_height = abs(right_eye_top[1] - right_eye_bottom[1])
                        # Use height difference as measure of openness (larger = more open)
                        left_eye_op = left_eye_height / (h_img + 1e-6)
                        right_eye_op = right_eye_height / (h_img + 1e-6)
                        eye_openness = float((left_eye_op + right_eye_op) / 2.0)

                        # brightness/contrast on face ROI via bounding box of landmarks
                        xs = [p.x for p in lm]
                        ys = [p.y for p in lm]
                        min_x = int(max(0, min(xs) * w_img))
                        max_x = int(min(w_img, max(xs) * w_img))
                        min_y = int(max(0, min(ys) * h_img))
                        max_y = int(min(h_img, max(ys) * h_img))
                        face_roi = gray[min_y:max_y, min_x:max_x] if max_x>min_x and max_y>min_y else gray
                        mean_brightness = float(np.mean(face_roi)) if face_roi.size else float(np.mean(gray))
                        std_brightness = float(np.std(face_roi)) if face_roi.size else float(np.std(gray))

                        # Enhanced emotion detection using landmarks (includes Anger)
                        scores = {k: 0.0 for k in ("Happiness", "Sadness", "Stress", "Anger", "Neutral")}
                        
                        # Happiness: Strong smile indicators
                        if corner_lift > 0.003 and mouth_aspect < 0.55:
                            scores["Happiness"] += 1.5 + min(0.4, corner_lift*150)
                        # Additional happiness signals: wide mouth, raised corners, good brightness
                        if 0.15 < mouth_aspect < 0.5 and corner_lift > 0.001:
                            scores["Happiness"] += 0.5
                        if mean_brightness > 110 and std_brightness > 25 and mouth_aspect < 0.6:
                            scores["Happiness"] += 0.4
                        # Good eye openness combined with positive mouth
                        if eye_openness > 0.8 and mouth_aspect < 0.5 and corner_lift > 0.001:
                            scores["Happiness"] += 0.3
                        
                        # Sadness: downturned mouth + lower energy + dimmer/less contrast face
                        # Key differentiator: negative corner_lift (even slightly) + low eye openness + low brightness/contrast
                        if corner_lift < -0.001:  # Downturned / frown-like mouth
                            scores["Sadness"] += 1.3
                            # If combined with low energy (droopy eyes), very strong sadness signal
                            if eye_openness < 0.82:
                                scores["Sadness"] += 0.7
                        # Closed/neutral mouth with downturned tilt (sad, not tense)
                        if mouth_aspect < 0.18 and corner_lift < 0.001 and eye_openness < 1.0:
                            scores["Sadness"] += 0.8
                        # Very open mouth (yawn-like) can indicate fatigue/sadness (not stress)
                        if mouth_aspect > 1.0 and corner_lift < 0.001 and eye_openness < 0.9:
                            scores["Sadness"] += 0.7
                        # Low brightness and low contrast often indicate sadness (not stress - stress has high contrast)
                        if mean_brightness < 95 and std_brightness < 22:
                            scores["Sadness"] += 0.75
                        # Droopy eyes (low eye_openness) and downturned mouth combination - strong sadness
                        if eye_openness < 0.72 and corner_lift < -0.001:
                            scores["Sadness"] += 0.85
                        # Very low energy overall - sadness, not stress
                        if eye_openness < 0.62 and mean_brightness < 100:
                            scores["Sadness"] += 0.6

                        # Combined emphasis: if brightness/contrast + mouth/eye cues align toward "low energy"
                        if mean_brightness < 98 and std_brightness < 25 and eye_openness < 1.05 and (mouth_aspect < 0.28 or corner_lift < 0.0):
                            scores["Sadness"] += 1.0
                        
                        # Stress: Wide eyes, tense expression, high contrast
                        # Key differentiator: wide eyes (high eye_openness) + high contrast + tense mouth (not downturned)
                        if eye_openness > 1.7:  # Wide eyes - stress/anxiety indicator
                            scores["Stress"] += 1.0
                            # If wide eyes + high contrast, very strong stress signal
                            if std_brightness > 35:
                                scores["Stress"] += 0.5
                        # Tension in mouth (slightly open, neutral corners - not downturned) - stress, not sadness
                        if 0.4 < mouth_aspect < 0.7 and -0.001 < corner_lift < 0.002 and eye_openness > 1.0:
                            scores["Stress"] += 0.8
                        # High contrast can indicate tension/stress (sadness has low contrast)
                        if std_brightness > 35 and mouth_aspect < 0.6 and corner_lift > -0.002:
                            scores["Stress"] += 0.6
                        # Tight lips (low mouth_aspect) with high contrast: Anger vs Stress
                        # - Wide/alert eyes -> Stress
                        # - Normal eyes -> Anger
                        if corner_lift > -0.001 and mouth_aspect < 0.15 and std_brightness > 30:
                            if eye_openness > 1.5:
                                scores["Stress"] += 0.7
                            else:
                                scores["Anger"] += 1.0
                        if std_brightness > 40 and corner_lift > -0.001:
                            if eye_openness > 1.4:
                                scores["Stress"] += 0.5
                            else:
                                scores["Anger"] += 0.5
                        # Moderate tension indicators - alert but not happy
                        if 1.2 < eye_openness < 1.7 and 0.2 < mouth_aspect < 0.5 and -0.001 < corner_lift < 0.001:
                            scores["Stress"] += 0.5
                        # High edge density indicates facial tension - stress, not sadness
                        # (We'll calculate this later, but for now use brightness variance as proxy)
                        if std_brightness > 45 and eye_openness > 1.0:
                            scores["Stress"] += 0.4

                        # Anger: tight/pressed lips + high contrast, without the "wide eyes" anxiety signal
                        if mouth_aspect < 0.12 and std_brightness > 32 and -0.003 < corner_lift < 0.001 and eye_openness < 1.5:
                            scores["Anger"] += 1.1
                        # Angry frown can look like sadness; differentiate by energy/contrast
                        if corner_lift < -0.001 and std_brightness > 32 and eye_openness >= 0.9:
                            scores["Anger"] += 0.5
                        
                        # Neutral: balanced features.
                        # Keep this conservative so Sadness isn't overridden.
                        if mean_brightness > 100 and std_brightness > 18 and eye_openness > 0.95:
                            if 0.1 < mouth_aspect < 0.3 and -0.001 < corner_lift < 0.002 and 1.0 < eye_openness < 1.5:
                                scores["Neutral"] += 0.45
                            if mean_brightness > 105 and 20 < std_brightness < 35:
                                scores["Neutral"] += 0.25
                            # Balanced expression with no strong indicators
                            if 0.08 < mouth_aspect < 0.25 and -0.001 < corner_lift < 0.002 and 0.9 < eye_openness < 1.4:
                                scores["Neutral"] += 0.3
                        
                        # Pick dominant emotion - prioritize negative emotions for accuracy
                        max_score = max(scores.values())
                        candidates = [k for k,v in scores.items() if abs(v-max_score)<1e-9]
                        priority = ["Sadness", "Anger", "Stress", "Happiness", "Neutral"]
                        dominant = None
                        for p in priority:
                            if p in candidates:
                                dominant = p
                                break
                        if dominant is None:
                            dominant = candidates[0] if candidates else "Neutral"
                        intensity = min(5, max(1, int(max_score*5)+1))
                        confidence = float(min(0.98, max(0.2, max_score+0.2)))
                        # write diagnostic
                        try:
                            with open(BASE_DIR / 'image_emotion.log','a',encoding='utf-8') as f:
                                f.write(json.dumps({
                                    'ts': datetime.utcnow().isoformat(),
                                    'file': str(Path(image_path).name),
                                    'method': 'mediapipe',
                                    'mouth_aspect': mouth_aspect,
                                    'corner_lift': corner_lift,
                                    'eye_openness': eye_openness,
                                    'mean_brightness': mean_brightness,
                                    'std_brightness': std_brightness,
                                    'scores': scores,
                                    'prediction': dominant,
                                    'intensity': intensity,
                                    'confidence': confidence,
                                }, ensure_ascii=False) + '\n')
                        except Exception:
                            pass
                        return EmotionInsight(dominant, intensity, confidence, ['landmarks_detected'], 0.0)
            except Exception:
                # If mediapipe processing fails, fall through to cascade pipeline
                pass

        # Attempt to load cascades
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        smile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_smile.xml')
        eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye_tree_eyeglasses.xml')

        if face_cascade.empty():
            return EmotionInsight("Neutral", 2, 0.1, ["cascade_load_failed"], 0.0)

        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60,60))
        if len(faces) == 0:
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=3, minSize=(40,40))
        if len(faces) == 0:
            # no faces -> fallback
            return EmotionInsight("Neutral", 2, 0.2, ["no_face_detected"], 0.0)

        # Use largest face
        x, y, w, h = max(faces, key=lambda r: r[2]*r[3])
        face_roi_color = img[y:y+h, x:x+w]
        face_roi = gray[y:y+h, x:x+w]
        if face_roi.size == 0:
            return EmotionInsight("Neutral", 2, 0.2, ["face_extraction_failed"], 0.0)

        mean_brightness = float(np.mean(face_roi))
        std_brightness = float(np.std(face_roi))

        # Regions (relative boxes)
        eye_box = face_roi[ int(h*0.08): int(h*0.45), int(w*0.12): int(w*0.88) ]
        mouth_box = face_roi[ int(h*0.55): int(h*0.95), int(w*0.18): int(w*0.82) ]

        eye_brightness = float(np.mean(eye_box)) if eye_box.size>0 else mean_brightness
        mouth_brightness = float(np.mean(mouth_box)) if mouth_box.size>0 else mean_brightness
        mouth_contrast = float(np.std(mouth_box)) if mouth_box.size>0 else std_brightness

        # Edge density
        edges = cv2.Canny(face_roi, 50, 150)
        edge_density = float(np.sum(edges>0)) / max(1, (w*h))

        # Symmetry (left-right brightness difference)
        left = face_roi[:, :w//2]
        right = face_roi[:, w//2:]
        symmetry_diff = abs(float(np.mean(left)) - float(np.mean(right))) if left.size and right.size else 0.0

        # Smile detection via cascade (strong signal for happiness)
        smile_detections = []
        try:
            # operate on color ROI for smile detector as it expects full face scale
            smile_detections = smile_cascade.detectMultiScale(
                face_roi,
                scaleFactor=1.7,
                minNeighbors=20,
                minSize=(int(w*0.15), int(h*0.05))
            ) if not smile_cascade.empty() else []
        except Exception:
            smile_detections = []

        smile_count = len(smile_detections)

        # Mouth contour detection (threshold + contours) to estimate openness / curvature - improved
        mouth_aspect = 0.0
        mouth_area = 0
        try:
            mb = mouth_box.copy()
            if mb.size > 0 and mb.shape[0] > 0 and mb.shape[1] > 0:
                mean_mb = float(np.mean(mb))
                # Adaptive threshold to isolate lips/teeth region - improved thresholding
                if mean_mb > 0:
                    threshold_val = int(np.clip(mean_mb - 10, 10, 240))
                    _, thr = cv2.threshold(mb, threshold_val, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                    contours, _ = cv2.findContours(thr, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    if contours:
                        # Filter out very small contours (noise)
                        valid_contours = [c for c in contours if cv2.contourArea(c) > 10]
                        if valid_contours:
                            largest = max(valid_contours, key=cv2.contourArea)
                            x_m, y_m, w_m, h_m = cv2.boundingRect(largest)
                            mouth_area = int(cv2.contourArea(largest))
                            if w_m > 0:
                                mouth_aspect = float(h_m) / float(w_m)
                            else:
                                # Fallback: use aspect ratio of mouth box itself
                                mouth_aspect = float(mb.shape[0]) / max(1.0, float(mb.shape[1]))
                        else:
                            # No valid contours, use default
                            mouth_aspect = float(mb.shape[0]) / max(1.0, float(mb.shape[1])) * 0.3
                    else:
                        # No contours found, use default based on box dimensions
                        mouth_aspect = float(mb.shape[0]) / max(1.0, float(mb.shape[1])) * 0.3
                else:
                    mouth_aspect = 0.3  # Default neutral
            else:
                mouth_aspect = 0.3  # Default neutral
        except Exception as e:
            # Log error but continue with default
            try:
                with open(BASE_DIR / "image_emotion.log", "a", encoding="utf-8") as f:
                    f.write(json.dumps({"ts": datetime.utcnow().isoformat(), "mouth_aspect_error": str(e)}) + "\n")
            except:
                pass
            mouth_aspect = 0.3  # Default neutral

        # Eye openness heuristic: look for eye contours or relative height in eye_box - improved
        eye_openness = 0.0
        try:
            eb = eye_box.copy()
            if eb.size > 0 and eb.shape[0] > 0 and eb.shape[1] > 0:
                # Use adaptive thresholding for better eye detection
                mean_val = float(np.mean(eb))
                if mean_val > 0:
                    _, eth = cv2.threshold(eb, int(np.clip(mean_val - 15, 10, 240)), 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                    eye_cnts, _ = cv2.findContours(eth, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    # approximate openness via average contour height ratio
                    heights = []
                    for c in eye_cnts:
                        _, _, _, hh = cv2.boundingRect(c)
                        if hh > 2:  # Filter out noise
                            heights.append(hh)
                    if heights:
                        eye_openness = float(np.mean(heights)) / max(1.0, float(eb.shape[0]))
                    else:
                        # Fallback: use brightness variance as proxy for eye openness
                        eye_openness = float(np.std(eb)) / max(1.0, float(np.mean(eb)))
                else:
                    eye_openness = 0.5  # Default neutral
            else:
                eye_openness = 0.5  # Default neutral
        except Exception as e:
            # Log error but continue with default
            try:
                with open(BASE_DIR / "image_emotion.log", "a", encoding="utf-8") as f:
                    f.write(json.dumps({"ts": datetime.utcnow().isoformat(), "eye_openness_error": str(e)}) + "\n")
            except:
                pass
            eye_openness = 0.5  # Default neutral

        # Enhanced emotion detection (includes Anger)
        scores = {k: 0.0 for k in ("Happiness", "Sadness", "Stress", "Anger", "Neutral")}

        # Happiness: Strong indicators - smile detections are very reliable
        if smile_count > 0:
            scores["Happiness"] += 1.2 + min(0.3, mouth_aspect * 2)
        # Mouth curvature and brightness for happiness
        if 0.15 < mouth_aspect < 0.55 and mouth_contrast > 20 and mouth_brightness > mean_brightness * 0.92:
            scores["Happiness"] += 0.5
        # Overall positive expression indicators
        if mean_brightness > 125 and std_brightness > 25 and mouth_aspect < 0.55:
            scores["Happiness"] += 0.4
        # Good eye openness combined with positive mouth
        if eye_openness > 1.2 and mouth_aspect < 0.5 and mouth_contrast > 18:
            scores["Happiness"] += 0.3

        # Sadness: low energy + dim/low-contrast + down expression
        if mean_brightness < 105 and std_brightness < 24:
            scores["Sadness"] += 0.85
        # Closed/low-curvature mouth with low contrast (sad, not tense)
        if mouth_contrast < 18 and mouth_aspect < 0.18:
            scores["Sadness"] += 0.65
        # Low edge density indicates reduced facial energy (sadness, not stress)
        if edge_density < 0.08:
            scores["Sadness"] += 0.5
        # Very low eye openness can indicate droopiness/sadness
        if eye_openness < 0.09 and (symmetry_diff > 24 or mean_brightness < 100):
            scores["Sadness"] += 0.9
        # Yawning or very open mouth (fatigue/sadness indicator, not stress)
        if mouth_aspect > 0.95 and smile_count == 0 and mouth_contrast < 20:
            scores["Sadness"] += 0.7
        # Droopy eyes + low mouth openness/contrast
        if eye_openness < 0.75 and mouth_aspect < 0.2 and mouth_contrast < 18:
            scores["Sadness"] += 0.7
        # Very low overall energy
        if eye_openness < 0.6 and mean_brightness < 100 and std_brightness < 26:
            scores["Sadness"] += 0.6

        # Sadness (crying/strained look): low eye openness + moderately open mouth + high mouth contrast
        # This helps match "sad.webp" style images where brightness isn't very low, so earlier
        # "dim face" thresholds don't trigger.
        if (
            eye_openness < 0.55
            and 0.45 < mouth_aspect < 0.85
            and mouth_contrast > 35
            and symmetry_diff < 20
        ):
            scores["Sadness"] += 1.1

        # Combined emphasis: align brightness/contrast with low eye openness
        if mean_brightness < 98 and std_brightness < 26 and eye_openness < 0.95 and mouth_aspect < 0.28:
            scores["Sadness"] += 0.9

        # Stress: Wide eyes, tense expression, high contrast - key differentiators from sadness
        # Wide eyes and tension (anxiety-like) - stress has alert/wide eyes, sadness has droopy eyes
        if eye_openness > 1.8:
            scores["Stress"] += 0.9
            # Wide eyes + high contrast = very strong stress signal
            if std_brightness > 35:
                scores["Stress"] += 0.4
        # Moderate tension in expression (alert, not droopy) - stress
        if 0.35 < mouth_aspect < 0.65 and 20 < mouth_contrast < 35 and symmetry_diff < 20 and eye_openness > 1.0:
            scores["Stress"] += 0.6
        # High contrast can indicate stress/tension (sadness has low contrast)
        if std_brightness > 38 and mouth_aspect < 0.6 and mouth_aspect > 0.2 and eye_openness > 0.8:
            scores["Stress"] += 0.6
        # Edge density indicating tension (stress has more facial tension than sadness)
        if 0.12 < edge_density < 0.20 and symmetry_diff > 15 and eye_openness > 1.0:
            scores["Stress"] += 0.5
        # Tension and high contrast indicators: Anger vs Stress
        # - Wide/alert eyes -> Stress
        # - Normal eyes + tight mouth -> Anger
        if std_brightness > 48 and mouth_contrast > 32 and symmetry_diff > 15:
            if eye_openness > 1.5:
                scores["Stress"] += 0.8
            else:
                scores["Anger"] += 0.9
        # High edge density indicates facial tension (stress, not sadness)
        if edge_density > 0.20 and symmetry_diff > 12:
            scores["Stress"] += 0.7
        # Tight lips (low mouth aspect) with high contrast -> Anger (unless very wide eyes)
        if mouth_aspect < 0.12 and mouth_contrast > 28:
            scores["Anger"] += 1.0
            if eye_openness > 1.7:
                scores["Stress"] += 0.3
        # High edge density + contrast with normal eyes can indicate anger tension
        if edge_density > 0.20 and mouth_contrast > 28 and eye_openness < 1.5:
            scores["Anger"] += 0.6
        # Moderate tension indicators - alert expression (stress)
        if 8 < symmetry_diff < 28 and 20 < std_brightness < 48 and 0.2 < mouth_aspect < 0.5 and eye_openness > 1.0:
            scores["Stress"] += 0.6
        if edge_density > 0.14 and edge_density < 0.20 and eye_openness > 1.0:
            scores["Stress"] += 0.4
        # Alert eyes with moderate contrast - stress, not sadness
        if eye_openness > 1.2 and std_brightness > 25 and std_brightness < 45:
            scores["Stress"] += 0.4

        # Neutral: conservative so sadness wins when cues match sadness
        if mean_brightness > 105 and std_brightness > 18 and eye_openness >= 0.95:
            # Balanced, neutral expression
            if 6 < symmetry_diff < 15 and 105 < mean_brightness < 160 and 18 < std_brightness < 38:
                scores["Neutral"] += 0.45
            # Neutral mouth position
            if smile_count == 0 and 0.08 < mouth_aspect < 0.25 and mean_brightness > 105:
                scores["Neutral"] += 0.35
            # Balanced eye openness
            if 1.1 < eye_openness < 1.6 and mouth_aspect < 0.3:
                scores["Neutral"] += 0.3

        # Normalize and pick dominant - prioritize negative emotions for accuracy
        max_score = max(scores.values())
        # collect candidates with maximum score
        candidates = [k for k, v in scores.items() if abs(v - max_score) < 1e-9]
        # prefer negative emotions in ties (Sadness, Anger, Stress, Happiness, Neutral)
        priority = ["Sadness", "Anger", "Stress", "Happiness", "Neutral"]
        dominant = None
        for p in priority:
            if p in candidates:
                dominant = p
                break
        if dominant is None:
            dominant = candidates[0] if candidates else "Neutral"

        # Enhanced intensity and confidence calculation for better accuracy
        # Intensity scales with emotion strength
        base_intensity = max_score * 5
        intensity = min(5, max(1, int(base_intensity) + 1))
        
        # Confidence improves with stronger signals and multiple indicators
        confidence_base = max_score
        # Boost confidence if we have smile detections or strong landmark signals
        if smile_count > 0:
            confidence_base += 0.15
        if max_score > 0.8:
            confidence_base += 0.1
        
        confidence = float(min(0.98, max(0.3, confidence_base + 0.2)))

        # If no strong signal, prefer Neutral with lower confidence
        if max_score < 0.3:
            dominant = "Neutral"
            intensity = 2
            confidence = max(0.35, confidence - 0.1)

        # Logging diagnostics for tuning
        try:
            log_entry = {
                "ts": datetime.utcnow().isoformat(),
                "file": str(image_path.name),
                "mean_brightness": mean_brightness,
                "std_brightness": std_brightness,
                "mouth_brightness": mouth_brightness,
                "mouth_contrast": mouth_contrast,
                "mouth_aspect": mouth_aspect,
                "mouth_area": mouth_area,
                "smile_count": smile_count,
                "eye_openness": eye_openness,
                "edge_density": edge_density,
                "symmetry_diff": symmetry_diff,
                "scores": scores,
                "prediction": dominant,
                "intensity": intensity,
                "confidence": confidence,
            }
            with open(BASE_DIR / "image_emotion.log", "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

        return EmotionInsight(dominant, intensity, confidence, ["face_detected"], 0.0)

    except Exception as e:
        try:
            with open(BASE_DIR / "image_emotion.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"ts": datetime.utcnow().isoformat(), "error": str(e)}) + "\n")
        except Exception:
            pass
        return EmotionInsight("Neutral", 2, 0.1, ["analysis_error"], 0.0)


def generate_llm_reply(
    insight: EmotionInsight,
    user_message: str,
    history: List[Dict[str, Any]] | None = None,
    user_name: str | None = None,
) -> str | None:
    """
    Call local Ollama API to generate a natural, empathetic reply.
    Returns None if LLM is unavailable or disabled — caller will fall back to rule-based.
    """
    if not LLM_ENABLED:
        return None

    log_path = BASE_DIR / "llm_errors.log"

    try:
        # Build the messages payload using recent history (if available)
        messages_payload = []
        # System prompt with context about detected emotion and optional user name
        uname = user_name.split()[0] if user_name else ""
        name_line = f" The user's name is {uname}." if uname else ""
        system_prompt = (
            f"You are EmoCare, a compassionate mental wellness chatbot.{name_line} "
            f"The user is experiencing {insight.emotion.lower()} (intensity {insight.intensity}/5)."
            " Respond with genuine empathy and warmth. Keep replies conversational and natural."
            " Whenever appropriate, include at least one context-aware, open follow-up question that invites the user to elaborate." 
            " Avoid generic template responses; mirror specific details the user shares and vary your phrasing to sound human." 
            " Offer gentle suggestions only when helpful, and prioritize connection over giving advice."
            " You are not a licensed professional and must not provide medical, diagnostic, or emergency advice."
        )
        messages_payload.append({"role": "system", "content": system_prompt})

        # Attach recent conversation history (map local authors to LLM roles)
        if history:
            # keep only the last N messages to avoid overly long contexts
            last_msgs = history[-12:]
            for m in last_msgs:
                role = "user" if m.get("author") == "user" else "assistant"
                content = m.get("content", "")
                if content:
                    messages_payload.append({"role": role, "content": content})

        # Add the current user message as the final user role
        messages_payload.append({"role": "user", "content": user_message})

        try:
            print(f"[Ollama] Attempting to call {OLLAMA_URL} with model {OLLAMA_MODEL}...")
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "messages": messages_payload,
                    "stream": False,
                    "options": {
                        "num_predict": MAX_RESPONSE_TOKENS,  # Limit response length for speed
                        "temperature": 0.8,  # Keep conversational
                    }
                },
                timeout=LLM_TIMEOUT,
            )
            print(f"[Ollama] Response status: {response.status_code}")
        except requests.exceptions.Timeout:
            error_msg = f"{datetime.utcnow().isoformat()} | timeout (after {LLM_TIMEOUT}s) | URL: {OLLAMA_URL} | Model: {OLLAMA_MODEL}"
            print(f"[Ollama] ERROR: {error_msg}")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(error_msg + "\n")
            return None
        except requests.exceptions.ConnectionError as e:
            error_msg = f"{datetime.utcnow().isoformat()} | connection-error: {str(e)[:500]} | URL: {OLLAMA_URL}"
            print(f"[Ollama] ERROR: {error_msg}")
            print(f"[Ollama] Make sure Ollama is running: ollama serve")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(error_msg + "\n")
            return None
        except requests.exceptions.RequestException as e:
            error_msg = f"{datetime.utcnow().isoformat()} | request-exception: {str(e)[:2000]}"
            print(f"[Ollama] ERROR: {error_msg}")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(error_msg + "\n")
            return None

        status = getattr(response, "status_code", None)
        if status != 200:
            # Log non-success response from Ollama
            try:
                body = response.text[:2000]
            except Exception:
                body = "<no-body>"
            error_msg = f"{datetime.utcnow().isoformat()} | status: {status} | response: {body}"
            print(f"[Ollama] ERROR: {error_msg}")
            print(f"[Ollama] Check if model '{OLLAMA_MODEL}' is pulled: ollama list")
            with open(log_path, "a", encoding="utf-8") as f:
                entry = {
                    "ts": datetime.utcnow().isoformat(),
                    "status": status,
                    "response": body,
                }
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            return None

        try:
            data = response.json()
        except Exception as e:
            # log malformed JSON
            error_msg = f"{datetime.utcnow().isoformat()} | invalid-json-response: {str(e)[:500]}"
            print(f"[Ollama] ERROR: {error_msg}")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(error_msg + "\n")
            return None

        message_obj = data.get("message") or {}
        reply = (message_obj.get("content") or "").strip()
        if not reply:
            error_msg = f"{datetime.utcnow().isoformat()} | empty-reply | response keys: {list(data.keys())}"
            print(f"[Ollama] ERROR: {error_msg}")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(error_msg + "\n")
            return None

        # Ensure LLM reply includes a context-aware follow-up question
        try:
            if "?" not in reply:
                follow = generate_targeted_follow_up(insight, user_message, history, user_name)
                if follow and follow not in reply:
                    reply = reply.rstrip(" .!\"") + ". " + follow
        except Exception:
            pass

        print("LLM reply generated (Ollama)")
        return reply
    except Exception as e:
        # Catch-all logging
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"{datetime.utcnow().isoformat()} | unexpected-exception: {str(e)[:2000]}\n")
                f.write(traceback.format_exc() + "\n")
        except Exception:
            pass
    return None


def generate_targeted_follow_up(insight: EmotionInsight, user_message: str, history: List[Dict[str, Any]] | None = None, user_name: str | None = None) -> str | None:
    """Create a short, context-aware follow-up question based on the user's message and detected emotion.
    Enhanced to be more ChatGPT-like with deeper understanding and natural conversation flow.
    """
    import re
    import random

    txt = (user_message or "").strip()
    if not txt:
        return None
    lower = txt.lower()
    first_name = user_name.split()[0] if user_name else ""

    # Extract context from conversation history for better understanding
    conversation_context = []
    if history:
        for m in history[-5:]:  # Last 5 messages for context
            if m.get("author") == "user":
                conversation_context.append(m.get("content", "").lower())
    
    # Combine current message with recent context for pattern matching
    full_context = " ".join(conversation_context + [lower])
    
    follow_up = None

    # High-signal situation: discipline/punishment at school/teacher
    # Ask for concrete details + safety/appropriateness without being accusatory.
    school_punish = re.search(r"\b(punish|punished|punishment|detention|scold|scolded|reprimand|hit|slap|beat)\b", lower)
    teacher_school = re.search(r"\b(teacher|school|class|principal)\b", lower)
    if school_punish and teacher_school:
        follow_up = "What happened leading up to it, and what kind of punishment was it?"

    # Relationship patterns - more comprehensive
    relationship_patterns = [
        (r"\b(?:love|like|adore|miss|care about|close to)\s+(?:my\s+)?([A-Za-z0-9'\-\s]{2,40})", 
         lambda m: f"What makes {m.group(1).strip().rstrip('.,!?')} so important to you?"),
        (r"\b(?:fight|argue|disagree|conflict)\s+(?:with|about)\s+([A-Za-z0-9'\-\s]{2,40})",
         lambda m: f"Can you help me understand what happened with {m.group(1).strip().rstrip('.,!?')}?"),
        (r"\b(?:my\s+)?(?:mom|dad|mother|father|parent|sister|brother|friend|partner|spouse|boyfriend|girlfriend|husband|wife|boss|colleague)\b",
         lambda m: "How has this relationship been affecting you lately?"),
    ]
    
    for pattern, handler in relationship_patterns:
        match = re.search(pattern, lower)
        if match:
            follow_up = handler(match)
            break

    # Work/School patterns - more detailed
    if not follow_up:
        work_patterns = [
            (r"\b(?:work|job|career|office|boss|colleague|team)\b", 
             "What's been the most challenging part of work recently?"),
            (r"\b(?:school|university|college|exam|test|assignment|project|deadline|grade)\b",
             "How has school been weighing on you?"),
            (r"\b(?:stressed|overwhelmed|pressure|deadline|behind)\b.*?\b(?:work|job|school|project)\b",
             "What would help you feel more in control right now?"),
        ]
        for pattern, response in work_patterns:
            if re.search(pattern, lower):
                follow_up = response
                break

    # Emotional state patterns - deeper understanding
    if not follow_up:
        emotion_patterns = [
            (r"\b(?:don't know|not sure|confused|unsure|can't decide|stuck|lost|uncertain)\b",
             "What would help you feel more clear about this?"),
            (r"\b(?:scared|afraid|worried|anxious|nervous|fear)\b",
             "What's the worst-case scenario you're imagining, and how likely do you think it really is?"),
            (r"\b(?:tired|exhausted|drained|burned out|worn out)\b",
             "What's been draining your energy the most?"),
            (r"\b(?:angry|mad|furious|frustrated|annoyed)\b",
             "What do you think is really underneath that anger?"),
            (r"\b(?:sad|down|depressed|hopeless|empty|numb)\b",
             "How long have you been feeling this way?"),
            (r"\b(?:happy|joy|excited|grateful|blessed|lucky)\b",
             "I love hearing that! What's contributing to this positive feeling?"),
        ]
        for pattern, response in emotion_patterns:
            if re.search(pattern, lower):
                follow_up = response
                break

    # Situation-specific patterns - more context-aware
    if not follow_up:
        situation_patterns = [
            (r"\b(?:happened|occurred|went down|took place)\b",
             "Walk me through what happened step by step?"),
            (r"\b(?:said|told|asked|responded|replied)\b",
             "How did that make you feel when they said that?"),
            (r"\b(?:can't|cannot|unable|struggling|difficulty)\b",
             "What do you think is getting in the way?"),
            (r"\b(?:want|need|wish|hope|desire)\b",
             "What would it look like if you got what you want?"),
            (r"\b(?:always|never|every time|constantly)\b",
             "Has this always been the case, or is this something new?"),
        ]
        for pattern, response in situation_patterns:
            if re.search(pattern, lower):
                follow_up = response
                break

    # Context-aware follow-ups based on conversation history
    if not follow_up and history and len(conversation_context) > 0:
        # Check if user is continuing a previous topic
        if any(word in full_context for word in ["still", "again", "same", "continue", "keep"]):
            follow_up = "It sounds like this is an ongoing situation. What's changed since we last talked about it?"
        # Check if user is introducing something new
        elif any(word in lower for word in ["new", "recently", "just", "today", "now"]):
            follow_up = "This seems like something recent. What triggered this feeling?"

    # Emotion-specific intelligent follow-ups - 5 emotions: Happiness, Sadness, Stress, Anger, Neutral
    if not follow_up:
        if insight.emotion == "Sadness":
            follow_ups = [
                "What's one small thing that used to bring you joy, even if it feels distant now?",
                "When did you first notice these feelings starting?",
                "Is there someone in your life you feel comfortable talking to about this?",
                "What would a good day look like for you right now?",
            ]
            follow_up = random.choice(follow_ups)
        elif insight.emotion == "Stress":
            follow_ups = [
                "What's the biggest source of stress for you right now?",
                "What would need to change for you to feel less overwhelmed?",
                "Is there anything you can delegate or set aside temporarily?",
                "What's one thing you could do right now to reduce this stress?",
                "What's the specific worry that's been on your mind?",
                "Can you identify what's triggering this right now?",
                "What would help you feel more grounded in this moment?",
                "What do you think is really underneath this?",
            ]
            follow_up = random.choice(follow_ups)
        elif insight.emotion == "Anger":
            follow_ups = [
                "What happened right before this anger spiked?",
                "What do you wish they understood about how this felt for you?",
                "Is this anger protecting something for you (like fairness, respect, or safety)?",
                "If you could act on one thing safely right now, what would it be?",
            ]
            follow_up = random.choice(follow_ups)
        elif insight.emotion in ("Happiness", "Neutral"):
            follow_ups = [
                "What's contributing to this positive feeling?",
                "How can you hold onto this feeling?",
                "What would help you experience more moments like this?",
                "I'm so glad to hear this! What's been going well for you?",
            ]
            follow_up = random.choice(follow_ups)

    # Question responses - more engaging
    if not follow_up and txt.endswith("?"):
        follow_ups = [
            "That's a thoughtful question. What's your gut feeling about it?",
            "What do you think might be the answer?",
            "Let's explore that together. What are your thoughts so far?",
            f"I'd love to help you think through that, {first_name}. What's your initial instinct?" if first_name else "I'd love to help you think through that. What's your initial instinct?",
        ]
        follow_up = random.choice(follow_ups)

    # Short, intense messages - dig deeper
    if not follow_up and len(txt.split()) <= 5 and (txt.endswith("!") or insight.intensity >= 4):
        follow_ups = [
            "I can sense the intensity in your words. Can you tell me more about what's happening?",
            "That sounds really significant. What's going on?",
            f"{first_name}, help me understand what led to this feeling?" if first_name else "Help me understand what led to this feeling?",
            "There's clearly something important here. What's the full story?",
        ]
        follow_up = random.choice(follow_ups)

    # Default intelligent follow-ups - more varied and natural
    if not follow_up:
        if first_name:
            follow_ups = [
                f"{first_name}, can you help me understand more about what's going on?",
                f"What else is on your mind, {first_name}?",
                f"{first_name}, what would be most helpful for me to know right now?",
                f"Tell me more about what you're experiencing, {first_name}.",
                f"{first_name}, what's the deeper story here?",
                f"How has this been affecting you, {first_name}?",
            ]
        else:
            follow_ups = [
                "Can you help me understand more about what's going on?",
                "What else is on your mind?",
                "What would be most helpful for me to know right now?",
                "Tell me more about what you're experiencing.",
                "What's the deeper story here?",
                "How has this been affecting you?",
                "What's really at the heart of what you're feeling?",
            ]
        follow_up = random.choice(follow_ups)

    return follow_up


def craft_reply(insight: EmotionInsight, user_message: str, history: List[Dict[str, Any]] | None = None, user_name: str | None = None) -> str:
    # Ollama is text-only here (we don't send images). For image/camera events we
    # skip the LLM and rely on our emotion-based rule replies to guarantee responses.
    user_message = user_message or ""
    media_event = (
        user_message.startswith("📎") or user_message.startswith("📷") or
        "Detected facial emotion" in user_message or
        "user shared a camera" in user_message or
        "user shared a image" in user_message
    )

    # Try LLM first if enabled; fall back to rule-based if LLM unavailable or skipped
    if LLM_ENABLED and not media_event:
        llm_reply = generate_llm_reply(insight, user_message, history, user_name=user_name)
        if llm_reply:
            return llm_reply
    
    # Rule-based fallback: generates warm, ChatGPT-like replies using context-aware matching
    import re
    import string

    txt = user_message.strip()
    lower = txt.lower()
    
    # Extract user's first name for light personalization (avoid repeating too often)
    first_name = (user_name.split()[0] if user_name else "").strip()
    
    # Extract conversation context and history patterns - enhanced for better understanding
    conversation_depth = len(history) if history else 0
    recent_user_messages = []
    recent_emotions = []
    recent_assistant_messages = []
    conversation_topics = set()
    
    if history:
        for m in history[-15:]:  # Look at last 15 messages for better context
            if m.get("author") == "user":
                content = m.get("content", "").strip()
                recent_user_messages.append(content)
                # Extract topics (simple keyword extraction)
                words = content.lower().split()
                for word in words:
                    if len(word) > 4 and word not in ("that", "this", "with", "from", "have", "been", "just", "really"):
                        conversation_topics.add(word)
            elif m.get("author") == "assistant":
                recent_assistant_messages.append(m.get("content", "").strip())
            if m.get("emotion"):
                recent_emotions.append(m.get("emotion"))
    
    # Detect if this is a repeated emotion (pattern recognition)
    is_repeated_emotion = len(recent_emotions) > 0 and recent_emotions[-1] == insight.emotion
    
    # Detect conversation continuity - check if user is responding to assistant's question
    is_response_to_question = False
    if recent_assistant_messages and recent_assistant_messages[-1]:
        last_assistant = recent_assistant_messages[-1].lower()
        if "?" in last_assistant:
            is_response_to_question = True
    
    # Extract specific details from user's message
    mirror = None
    
    # Try patterns: "I am X", "I'm X", "I feel X", "I just X"
    patterns = [
        r"\b(?:i am|i'm|im)\s+([^.?!]{1,80})",
        r"\bi\s+(?:feel|felt)\s+(?:like|that\s+)?([^.?!]{1,80})",
        r"\b(?:i just|just)\s+([^.?!]{1,80})",
        r"\bi\s+(?:can't|cannot|can't|don't|don't)\s+([^.?!]{1,80})",
    ]
    
    for pattern in patterns:
        m = re.search(pattern, lower)
        if m:
            mirror = m.group(1).strip()
            break
    
    # If no specific pattern match, extract key subject - enhanced extraction
    if not mirror:
        # Find nouns, verbs, and important descriptive words
        words = txt.split()
        important_words = []
        skip_words = {"that", "this", "have", "really", "just", "been", "with", "from", "about", "when", "where", "what", "how", "why", "the", "a", "an", "is", "are", "was", "were", "am", "be"}
        for w in words[:20]:  # First 20 words for better context
            w_clean = w.strip(string.punctuation).lower()
            if len(w_clean) > 2 and w_clean not in skip_words:
                important_words.append(w_clean)
        if important_words:
            mirror = " ".join(important_words[:7])  # More context

    # ----------------------------
    # Intent detection (no LLM)
    # ----------------------------
    is_question = txt.endswith("?") or bool(re.search(r"\b(why|how|what|should|can|could|would)\b", lower))
    wants_advice = bool(re.search(r"\b(what should i do|what do i do|help me|any advice|how do i|what can i do)\b", lower))
    venting = bool(re.search(r"\b(i just need|just needed|needed to say|vent|get this off my chest)\b", lower))

    # ----------------------------
    # Opening (less template-y)
    # ----------------------------
    greeting = None
    if insight.emotion == "Sadness" and insight.intensity >= 4:
        greeting = random.choice([
            "That sounds really heavy.",
            "I'm really sorry you're carrying that.",
            "I'm glad you told me—this matters.",
        ])
    elif insight.emotion == "Stress" and insight.intensity >= 3:
        greeting = random.choice([
            "That sounds stressful.",
            "I can see why that would make you feel on edge.",
            "Okay—let's take this one step at a time.",
            "I hear how frustrating that is.",
            "That would make a lot of people feel this way.",
        ])
    elif insight.emotion == "Anger" and insight.intensity >= 3:
        greeting = random.choice([
            "I can hear how hot that anger is.",
            "That sounds really intense—and totally valid to feel.",
            "Okay, I’m with you. Let’s slow the intensity down together.",
        ])
    elif insight.emotion in ("Happiness", "Neutral") and insight.intensity >= 3:
        greeting = random.choice([
            "That’s genuinely nice to hear.",
            "I’m glad you’re feeling that.",
            "Love that for you.",
        ])
    else:
        greeting = random.choice([
            "I’m here with you.",
            "Thanks for sharing that with me.",
            "Got it—tell me more.",
        ])
    
    # High intensity + sadness = extra empathetic
    if insight.emotion == "Sadness" and insight.intensity >= 4:
        greetings = [
            f"I can feel how heavy this is, {first_name}," if first_name else "I can feel how heavy this is,",
            f"{first_name}, that sounds incredibly difficult." if first_name else "That sounds incredibly difficult.",
            "Thank you for letting me in — this takes real courage.",
        ]
        greeting = random.choice(greetings)
    
    # Repeated emotion — acknowledge the pattern
    elif is_repeated_emotion and len(recent_emotions) >= 2:
        greetings = [
            f"I'm noticing this has been coming up for you, {first_name}." if first_name else "I'm noticing this pattern coming up.",
            f"It sounds like this has been with you for a bit, {first_name}." if first_name else "This feels like it's been sitting with you.",
            "I see you're navigating this again — I'm here with you.",
        ]
        greeting = random.choice(greetings)
    
    # Happiness/positive — celebrate with them
    elif insight.emotion in ("Happiness", "Neutral") and insight.intensity >= 3:
        greetings = [
            f"{first_name}, I love seeing you in this space!" if first_name else "I love seeing you in this space!",
            f"That's wonderful, {first_name}." if first_name else "That's wonderful.",
            "This is beautiful — I want to help you hold onto this.",
        ]
        greeting = random.choice(greetings)
    
    # Stress — grounding approach
    elif insight.emotion == "Stress":
        greetings = [
            f"{first_name}, let's slow this down together." if first_name else "Let me help you slow this down.",
            "I'm right here — we can work through this.",
            f"That's a lot, {first_name}." if first_name else "That's a lot.",
            f"{first_name}, I hear the frustration." if first_name else "I hear the frustration.",
        ]
        greeting = random.choice(greetings)
    
    # Default caring opener
    else:
        greetings = [
            f"{first_name}, I'm here for this." if first_name else "I'm here with you.",
            f"I see you, {first_name}." if first_name else "I see what you're sharing.",
            "Thanks for opening up to me.",
        ]
        greeting = random.choice(greetings)
    
    # ----------------------------
    # Reflection (mirror, but natural)
    # ----------------------------
    reflection = ""
    if mirror:
        mirror_clean = mirror.strip().rstrip(".?!")[:100]  # More context
        if mirror_clean:
            reflection_styles = [
                f"It sounds like {mirror_clean}.",
                f"From what you’re saying, {mirror_clean}.",
                f"Okay—{mirror_clean}.",
                f"I’m hearing: {mirror_clean}.",
            ]
            reflection = random.choice(reflection_styles)
    
    # ============================================
    # CONTEXTUAL CALLBACK - Reference their story - Enhanced
    # ============================================
    callback = None
    if history and len(recent_user_messages) >= 2:
        # Check multiple previous messages for better continuity
        for i in range(2, min(5, len(recent_user_messages) + 1)):
            prev_msg = recent_user_messages[-i] if i <= len(recent_user_messages) else None
            if prev_msg:
                prev_clean = prev_msg.strip()
                # avoid echoing the same message and require some length
                if len(prev_clean) > 8 and prev_clean.lower() != user_message.lower():
                    # Extract meaningful content
                    prev_snippet_words = prev_clean.split()[0:10]
                    prev_display = " ".join(prev_snippet_words)
                    prev_display = re.sub(r"^(i\s+am|i'm|i am|i'm|i feel|feeling|i\s+think|i\s+believe)\s+", "", prev_display, flags=re.I).strip()
                    prev_display = prev_display.rstrip(" .?!")
                    if prev_display and len(prev_display) > 4:
                        # More natural callback based on emotion and context - 4 emotions
                        if insight.emotion in ("Sadness", "Stress"):
                            tails = [
                                " — how has that been sitting with you?",
                                " — is that still on your mind?",
                                " — has anything changed since then?",
                                " — has that situation resolved?",
                            ]
                            tail = random.choice(tails)
                        elif insight.emotion in ("Happiness", "Neutral"):
                            tails = [
                                " — are you still feeling that way?",
                                " — has that positive feeling continued?",
                                " — what's been keeping that good energy going?",
                            ]
                            tail = random.choice(tails)
                        else:
                            tail = " — how has that been for you?"
                        callback = f"You mentioned {prev_display}...{tail}"
                        break
    
    # If responding to a question, acknowledge the response
    if is_response_to_question and not callback:
        acknowledgment = None
        if insight.emotion in ("Sadness", "Stress"):
            acknowledgments = [
                "Thank you for sharing that with me.",
                "I appreciate you opening up about that.",
                "That helps me understand better.",
            ]
        elif insight.emotion in ("Happiness", "Neutral"):
            acknowledgments = [
                "I'm so glad to hear that!",
                "That's wonderful to know!",
                "I love hearing that!",
            ]
        else:
            acknowledgments = [
                "Thanks for telling me that.",
                "I understand.",
                "That makes sense.",
            ]
        callback = random.choice(acknowledgments)
    
    # ----------------------------
    # One strong follow-up question (avoid multiple questions)
    # ----------------------------
    follow_up = generate_targeted_follow_up(insight, user_message, history, user_name)

    # If user asked a direct question, prioritize answering style question
    if is_question and not wants_advice and not venting:
        # Keep follow-up but make it clarifying
        follow_up = follow_up or "What part are you most unsure about?"

    
    # ----------------------------
    # Light suggestion only when user wants advice or intensity is high
    # ----------------------------
    suggestion = None
    if insight.emotion == "Stress":
        suggestions = [
            f"A quick grounding moment: name 3 things you can see, {first_name}." if first_name else "A quick grounding: name 3 things you can see right now.",
            "Even 2 minutes of deep breathing can shift things.",
            "What's one thing you could set aside for now?",
            "One small action beats a thousand worried thoughts.",
            "What's one thing you can control in this situation?",
            "Your body is responding to perceived threat. Can you ground yourself — feet on floor, hands on something?",
        ]
        if wants_advice or insight.intensity >= 4:
            suggestion = random.choice(suggestions)
    
    elif insight.emotion == "Depression":
        suggestions = [
            f"{first_name}, sometimes the first step is just speaking it out loud. You did that. That matters." if first_name else "Sometimes the first step is just speaking it out loud. You did. That matters.",
            "You are worthy of kindness, especially your own.",
            "This feeling is not permanent, even though it feels heavy right now.",
            "One tiny act of self-care: what would that look like for you?",
            "Is there one person you trust enough to tell them you're struggling?",
        ]
        if wants_advice or insight.intensity >= 4:
            suggestion = random.choice(suggestions)
    
    elif insight.emotion == "Anger":
        suggestions = [
            "That energy has something to teach you — what is it asking for?",
            "Can you channel this into something creative or physical?",
        ]
        if wants_advice or insight.intensity >= 4:
            suggestion = random.choice(suggestions)
    
    # ----------------------------
    # Assemble (tight, ChatGPT-like)
    # ----------------------------
    segments = []
    
    # Build reply in natural conversation order
    if greeting:
        segments.append(greeting)
    
    if reflection:
        segments.append(reflection)
    
    if callback:
        segments.append(callback)
    
    # Include exactly one follow-up question
    if follow_up:
        # ensure it's a question
        fu = follow_up.strip()
        if not fu.endswith("?"):
            fu = fu.rstrip(".!") + "?"
        segments.append(fu)
    
    # Add suggestion only when useful (already gated above)
    if suggestion:
        segments.append(suggestion)
    
    # Deduplicate nearly-identical segments while preserving order
    uniq_segments: List[str] = []
    seen_keys: set = set()
    for seg in segments:
        key = re.sub(r"\s+", " ", seg.strip().lower())
        if key and key not in seen_keys:
            seen_keys.add(key)
            uniq_segments.append(seg)
    
    # Join with proper punctuation and spacing - more natural flow
    if len(uniq_segments) == 0:
        # Fallback if somehow no segments
        if first_name:
            reply = f"{first_name}, I'm here to listen. What's on your mind?"
        else:
            reply = "I'm here to listen. What's on your mind?"
    elif len(uniq_segments) == 1:
        reply = uniq_segments[0]
    else:
        # Join segments naturally
        reply_parts = []
        for i, seg in enumerate(uniq_segments):
            seg_clean = seg.strip()
            if i == 0:
                reply_parts.append(seg_clean)
            else:
                # Add natural connectors
                prev_ends_with_punct = reply_parts[-1].endswith((".", "!", "?"))
                if prev_ends_with_punct:
                    reply_parts.append(seg_clean)
                else:
                    # Add comma or period if needed
                    if seg_clean[0].isupper() and not seg_clean.startswith(("I ", "What", "How", "When", "Where", "Why")):
                        reply_parts[-1] = reply_parts[-1].rstrip(".,!?") + ". " + seg_clean
                    else:
                        reply_parts.append(seg_clean)
        reply = " ".join(reply_parts)
    
    # Ensure proper ending - but preserve question marks
    if reply and not reply.endswith((".", "?", "!", '"')):
        # If last segment was a question, keep it; otherwise add period
        if follow_up and reply.endswith(follow_up.rstrip(".,!?")):
            if not reply.endswith("?"):
                reply = reply.rstrip(".,!") + "?"
        else:
            reply += "."
    
    # Final cleanup - remove double spaces and fix punctuation
    reply = re.sub(r"\s+", " ", reply)
    reply = re.sub(r"\.\s*\.", ".", reply)
    reply = re.sub(r"\?\s*\?", "?", reply)
    reply = reply.strip()
    
    return reply


def get_or_create_today_conversation(user_id: int) -> int:
    # Get current IST date
    ist_now = get_ist_now()
    today_ist = ist_now.date().isoformat()
    
    row = g.db.execute(
        """
        SELECT id FROM conversations
        WHERE user_id = ? AND date(created_at, '+05:30') = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (user_id, today_ist),
    ).fetchone()
    if row:
        return int(row["id"])

    cursor = g.db.execute("INSERT INTO conversations (user_id) VALUES (?)", (user_id,))
    g.db.commit()
    return int(cursor.lastrowid)


def log_message(conversation_id: int, author: str, content: str, emotion: str | None, intensity: int | None, image_path: str | None = None, detection_source: str = "text") -> None:
    # Store the current time in UTC for consistency
    current_utc = datetime.now(timezone.utc)
    
    g.db.execute(
        """
        INSERT INTO messages (conversation_id, author, content, emotion, intensity, image_path, detection_source, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (conversation_id, author, content, emotion, intensity, image_path, detection_source, current_utc.isoformat()),
    )
    if emotion:
        g.db.execute("UPDATE conversations SET dominant_emotion = ? WHERE id = ?", (emotion, conversation_id))
    g.db.commit()


def fetch_chat_messages(user_id: int, limit: int | None = None) -> List[Dict[str, Any]]:
    sql = """
        SELECT m.id, m.author, m.content, m.emotion, m.intensity, m.created_at, m.image_path, m.detection_source
        FROM messages m
        JOIN conversations c ON c.id = m.conversation_id
        WHERE c.user_id = ?
        ORDER BY m.created_at ASC
    """
    params: Tuple[Any, ...] = (user_id,)
    if limit:
        sql += " LIMIT ?"
        params = params + (limit,)
    rows = g.db.execute(sql, params).fetchall()
    formatted = []
    
    for row in rows:
        # Parse the stored datetime (assuming it's in UTC or local time)
        if isinstance(row["created_at"], str):
            timestamp = datetime.fromisoformat(row["created_at"])
        else:
            timestamp = row["created_at"]
        
        # If no timezone info, assume UTC
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        
        # Convert to IST
        ist_timestamp = convert_to_ist(timestamp)
        
        # Convert Row to dict for safe access
        row_dict = dict(row)
        image_path = row_dict.get("image_path")
        
        # Extract just the filename from the path
        image_filename = None
        if image_path:
            # Handle both Windows (\) and Unix (/) path separators
            image_filename = image_path.replace("\\", "/").split("/")[-1]
        
        formatted.append({
            "id": row_dict.get("id"),
            "author": row_dict["author"],
            "display_author": "You" if row_dict["author"] == "user" else "EmoCare",
            "content": row_dict["content"],
            "emotion": normalize_emotion(row_dict.get("emotion") or "Neutral"),
            "intensity": row_dict.get("intensity"),
            "image_path": image_path,
            "image_filename": image_filename,
            "detection_source": row_dict.get("detection_source", "text"),
            "created_at": ist_timestamp.isoformat(),
            "display_time": format_ist_time(ist_timestamp, "display"),
            "time_only": format_ist_time(ist_timestamp, "time_only"),
            "full_time": format_ist_time(ist_timestamp, "full")
        })
    
    return formatted


def fetch_messages_for_conversation(conversation_id: int, limit: int | None = None) -> List[Dict[str, Any]]:
    """Fetch messages for a specific conversation in chronological order with IST timezone."""
    sql = """
        SELECT m.id, m.author, m.content, m.emotion, m.intensity, m.created_at, m.image_path, m.detection_source
        FROM messages m
        WHERE m.conversation_id = ?
        ORDER BY m.created_at ASC
    """
    params: Tuple[Any, ...] = (conversation_id,)
    if limit:
        sql += " LIMIT ?"
        params = params + (limit,)
    rows = g.db.execute(sql, params).fetchall()
    formatted = []
    
    for row in rows:
        # Parse and convert timestamp to IST
        if isinstance(row["created_at"], str):
            timestamp = datetime.fromisoformat(row["created_at"])
        else:
            timestamp = row["created_at"]
        
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        
        ist_timestamp = convert_to_ist(timestamp)
        
        row_dict = dict(row)
        image_path = row_dict.get("image_path")
        image_filename = None
        if image_path:
            image_filename = image_path.replace("\\", "/").split("/")[-1]
        
        formatted.append({
            "id": row_dict.get("id"),
            "author": row_dict["author"],
            "display_author": "You" if row_dict["author"] == "user" else "EmoCare",
            "content": row_dict["content"],
            "emotion": normalize_emotion(row_dict.get("emotion") or "Neutral"),
            "intensity": row_dict.get("intensity"),
            "image_path": image_path,
            "image_filename": image_filename,
            "detection_source": row_dict.get("detection_source", "text"),
            "created_at": ist_timestamp.isoformat(),
            "display_time": format_ist_time(ist_timestamp, "display"),
            "time_only": format_ist_time(ist_timestamp, "time_only"),
            "full_time": format_ist_time(ist_timestamp, "full")
        })
    
    return formatted


def fetch_recent_conversations(user_id: int, limit: int = 3) -> List[Dict[str, Any]]:
    rows = g.db.execute(
        """
        SELECT id, dominant_emotion, created_at,
               (
                 SELECT content FROM messages
                 WHERE conversation_id = conversations.id
                 ORDER BY messages.created_at DESC
                 LIMIT 1
               ) AS summary
        FROM conversations
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()
    
    results = []
    for row in rows:
        if isinstance(row["created_at"], str):
            timestamp = datetime.fromisoformat(row["created_at"])
        else:
            timestamp = row["created_at"]
        
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        
        ist_timestamp = convert_to_ist(timestamp)
        
        results.append({
            "title": f"Check-in {format_ist_time(ist_timestamp, 'time_only')}",
            "mood": normalize_emotion(row["dominant_emotion"] or "Neutral"),
            "time": format_ist_time(ist_timestamp, "date_only"),
            "summary": row["summary"] or "",
            "full_time": format_ist_time(ist_timestamp, "full")
        })
    
    return results


def _tokenize_for_search(text: str) -> List[str]:
    import re
    text = (text or "").lower()
    # words + numbers, keep simple
    tokens = re.findall(r"[a-z0-9']{2,}", text)
    stop = {
        "the","a","an","and","or","but","if","then","so","to","of","in","on","at","for","from","with","as","is","are","was","were",
        "i","im","i'm","me","my","you","your","we","they","he","she","it","this","that","these","those","been","being","have","has","had",
        "do","does","did","not","no","yes","just","really","very","can","could","should","would"
    }
    return [t for t in tokens if t not in stop and len(t) > 2]


def build_trigger_map(user_id: int) -> Dict[str, Any]:
    """Build a simple local 'trigger map' from user chats + journal (no external APIs)."""
    try:
        # Pull recent content
        msg_rows = g.db.execute(
            """
            SELECT m.content, m.emotion
            FROM messages m
            JOIN conversations c ON c.id = m.conversation_id
            WHERE c.user_id = ? AND m.author = 'user'
            ORDER BY m.created_at DESC
            LIMIT 600
            """,
            (user_id,),
        ).fetchall()
        journal_rows = g.db.execute(
            """
            SELECT title, content, emotion
            FROM journal_entries
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 200
            """,
            (user_id,),
        ).fetchall()

        # Buckets
        # Normalize old labels to the current set
        negative = {"Sadness", "Stress", "Anger"}
        pos = {"Happiness", "Neutral"}

        trigger_counts: Counter = Counter()
        help_counts: Counter = Counter()
        by_emotion: Dict[str, Counter] = {e: Counter() for e in ["Happiness", "Sadness", "Stress", "Anger", "Neutral"]}

        def add_text(emotion: str, text: str):
            emotion = normalize_emotion(emotion)
            toks = _tokenize_for_search(text)
            if not toks:
                return
            by_emotion.setdefault(emotion, Counter()).update(toks)
            if emotion in negative:
                trigger_counts.update(toks)
            elif emotion in pos:
                help_counts.update(toks)

        for r in msg_rows:
            add_text((r["emotion"] or "Neutral"), (r["content"] or ""))
        for r in journal_rows:
            combined = ((r["title"] or "") + " " + (r["content"] or "")).strip()
            add_text((r["emotion"] or "Neutral"), combined)

        # Convert to lists
        top_triggers = [{"word": w, "count": int(c)} for w, c in trigger_counts.most_common(12)]
        top_helpers = [{"word": w, "count": int(c)} for w, c in help_counts.most_common(12)]
        per_emotion = {
            e: [{"word": w, "count": int(c)} for w, c in by_emotion.get(e, Counter()).most_common(8)]
            for e in ["Anger", "Stress", "Sadness", "Neutral", "Happiness"]
        }

        return {
            "top_triggers": top_triggers,
            "top_helpers": top_helpers,
            "per_emotion": per_emotion,
        }
    except Exception:
        return {"top_triggers": [], "top_helpers": [], "per_emotion": {}}


def auto_save_conversation_to_journal(user_id: int, conversation_id: int) -> None:
    """Create a lightweight journal recap from a conversation (best-effort, no AI)."""
    try:
        # avoid spamming: only one auto-save per conversation
        existing = g.db.execute(
            "SELECT id FROM journal_entries WHERE user_id = ? AND title = ? LIMIT 1",
            (user_id, f"Chat recap #{conversation_id}"),
        ).fetchone()
        if existing:
            return

        msgs = fetch_messages_for_conversation(conversation_id, limit=12)
        # keep only user-authored content for recap
        user_lines = []
        for m in msgs:
            if m.get("author") == "user":
                c = (m.get("content") or "").strip()
                if c:
                    user_lines.append(f"- {c}")
        if not user_lines:
            return

        recap = "\n".join(user_lines[-8:])
        snapshot = latest_user_snapshot(user_id)
        emotion = snapshot.get("emotion", "")
        mood_rating = snapshot.get("intensity")

        g.db.execute(
            "INSERT INTO journal_entries (user_id, title, content, emotion, mood_rating) VALUES (?, ?, ?, ?, ?)",
            (user_id, f"Chat recap #{conversation_id}", recap, emotion, int(mood_rating) if mood_rating else None),
        )
        g.db.commit()
    except Exception:
        # best-effort; never break chat
        try:
            g.db.rollback()
        except Exception:
            pass


def generate_conversation_insights(user_id: int, conversation_id: int) -> Dict[str, Any]:
    """Simple local insights about the current conversation (no external APIs)."""
    try:
        msgs = fetch_messages_for_conversation(conversation_id, limit=30)
        emotions = [m.get("emotion") for m in msgs if m.get("emotion")]
        intensity = [m.get("intensity") for m in msgs if m.get("intensity")]
        top_emotion = None
        if emotions:
            try:
                top_emotion = Counter(emotions).most_common(1)[0][0]
            except Exception:
                top_emotion = emotions[-1]

        avg_intensity = None
        ints = [i for i in intensity if isinstance(i, int)]
        if ints:
            avg_intensity = round(sum(ints) / len(ints), 1)

        return {
            "top_emotion": normalize_emotion(top_emotion or "Neutral"),
            "avg_intensity": avg_intensity if avg_intensity is not None else 0,
            "message_count": len(msgs),
        }
    except Exception:
        return {"top_emotion": "Neutral", "avg_intensity": 0, "message_count": 0}


def generate_quick_replies(user_id: int, messages: List[Dict[str, Any]]) -> List[str]:
    """Generate short quick-reply suggestions based on last detected emotion."""
    try:
        last_emotion = None
        for m in reversed(messages or []):
            if m.get("author") == "user" and m.get("emotion"):
                last_emotion = m.get("emotion")
                break
        last_emotion = normalize_emotion(last_emotion or latest_user_snapshot(user_id).get("emotion", "Neutral"))

        bank = {
            "Anger": [
                "What happened exactly?",
                "What do you wish they understood?",
                "What would help right now—space, fairness, an apology?",
            ],
            "Stress": [
                "What’s the biggest pressure right now?",
                "What’s the next smallest step?",
                "What can wait until later?",
            ],
            "Sadness": [
                "What’s been hardest today?",
                "What would feel a little gentler right now?",
                "Who feels safest to talk to?",
            ],
            "Happiness": [
                "What made today better?",
                "How can we repeat this tomorrow?",
                "Want to set a small goal to keep the momentum?",
            ],
            "Neutral": [
                "What are you thinking about?",
                "What would you like to focus on today?",
                "Anything you want to plan for?",
            ],
        }
        return bank.get(last_emotion, bank["Neutral"])[:3]
    except Exception:
        return []


def latest_user_snapshot(user_id: int) -> Dict[str, Any]:
    row = g.db.execute(
        """
        SELECT m.emotion, m.intensity, m.created_at, m.content
        FROM messages AS m
        JOIN conversations c ON c.id = m.conversation_id
        WHERE c.user_id = ? AND m.author = 'user'
        ORDER BY m.created_at DESC
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()
    if not row:
        return {
            "emotion": normalize_emotion("Neutral"),
            "intensity": 2,
            "summary": "No logs yet today—share how youre doing to unlock insights.",
        }
    emotion = normalize_emotion(row["emotion"] or "Neutral")
    intensity = row["intensity"] or 2
    snippet = row["content"][:120] + ("…" if len(row["content"]) > 120 else "")
    summary = f"Latest emotion: {emotion} at {intensity}/5. You said: '{snippet}'"
    return {"emotion": emotion, "intensity": intensity, "summary": summary}


def suggested_activities(emotion: str | None) -> List[Dict[str, str]]:
    emotion = normalize_emotion(emotion)
    if emotion in ACTIVITY_LIBRARY:
        pool = ACTIVITY_LIBRARY[emotion]
    else:
        pool = ACTIVITY_LIBRARY["Neutral"]
    suggestions = pool[:3]
    results: List[Dict[str, str]] = []
    for item in suggestions:
        if isinstance(item, dict):
            title = item.get("title") or item.get("name") or ""
            subtitle = item.get("subtitle") or item.get("desc") or item.get("description") or ""
            entry: Dict[str, str] = {"title": title, "subtitle": subtitle}
            if "video_query" in item and item.get("video_query"):
                entry["video_query"] = item.get("video_query")
            results.append(entry)
        elif isinstance(item, (list, tuple)):
            # legacy tuple/list format: (title, subtitle)
            title = item[0] if len(item) > 0 else ""
            subtitle = item[1] if len(item) > 1 else ""
            results.append({"title": title, "subtitle": subtitle})
        else:
            # fallback: stringify
            results.append({"title": str(item), "subtitle": ""})
    return results


def generate_emotion_chart_images(user_id: int) -> Tuple[io.BytesIO, io.BytesIO]:
    """Generate emotion chart images for PDF embedding.
    
    Returns a tuple of (line_chart_image, pie_chart_image) as BytesIO objects.
    """
    # Get chart data
    ist_today = get_ist_now().date()
    days = [ist_today - timedelta(days=i) for i in range(6, -1, -1)]
    labels = [d.strftime("%a") for d in days]
    dataset_template = {emotion: [0 for _ in days] for emotion in EMOTION_COLORS}

    # Query database
    rows = g.db.execute(
        """
        SELECT date(m.created_at, '+05:30') AS day, m.emotion, COUNT(*) AS total
        FROM messages m
        JOIN conversations c ON c.id = m.conversation_id
        WHERE c.user_id = ? AND m.author = 'user'
          AND day >= date('now', '+05:30', '-6 day')
        GROUP BY day, m.emotion
        """,
        (user_id,),
    ).fetchall()
    
    day_index = {d.isoformat(): idx for idx, d in enumerate(days)}
    distribution: Counter[str] = Counter()
    
    for row in rows:
        day = row["day"]
        emotion = normalize_emotion(row["emotion"] or "Neutral")
        if day in day_index and emotion in dataset_template:
            dataset_template[emotion][day_index[day]] = row["total"]
            distribution[emotion] += row["total"]

    # Create line chart (emotion timeline)
    fig_line, ax_line = plt.subplots(figsize=(8, 4), dpi=100)
    fig_line.patch.set_facecolor('white')
    
    for emotion, values in dataset_template.items():
        if sum(values) > 0:  # Only plot emotions with data
            ax_line.plot(labels, values, marker='o', label=emotion, 
                        color=EMOTION_COLORS[emotion], linewidth=2, markersize=6)
    
    ax_line.set_xlabel('Day', fontsize=11, fontweight='bold')
    ax_line.set_ylabel('Count', fontsize=11, fontweight='bold')
    ax_line.set_title('Weekly Emotion Timeline', fontsize=13, fontweight='bold', pad=15)
    ax_line.legend(loc='best', fontsize=9)
    ax_line.grid(True, alpha=0.3, linestyle='--')
    ax_line.set_ylim(bottom=0)
    fig_line.tight_layout()
    
    # Save to BytesIO
    line_chart_bytes = io.BytesIO()
    fig_line.savefig(line_chart_bytes, format='png', dpi=100, bbox_inches='tight')
    line_chart_bytes.seek(0)
    plt.close(fig_line)
    
    # Create pie chart (emotion distribution)
    fig_pie, ax_pie = plt.subplots(figsize=(6, 4), dpi=100)
    fig_pie.patch.set_facecolor('white')
    
    distribution_labels = list(distribution.keys()) or list(EMOTION_COLORS.keys())
    distribution_data = [distribution[label] for label in distribution_labels] or [1] * len(distribution_labels)
    distribution_colors = [EMOTION_COLORS.get(label, "#94a3b8") for label in distribution_labels]
    
    # Filter out emotions with no data
    filtered_labels = []
    filtered_data = []
    filtered_colors = []
    for label, data, color in zip(distribution_labels, distribution_data, distribution_colors):
        if data > 0:
            filtered_labels.append(label)
            filtered_data.append(data)
            filtered_colors.append(color)
    
    if filtered_data:
        wedges, texts, autotexts = ax_pie.pie(filtered_data, labels=filtered_labels, colors=filtered_colors,
                                               autopct='%1.1f%%', startangle=90, textprops={'fontsize': 10})
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
    
    ax_pie.set_title('Emotion Distribution', fontsize=13, fontweight='bold', pad=15)
    fig_pie.tight_layout()
    
    # Save to BytesIO
    pie_chart_bytes = io.BytesIO()
    fig_pie.savefig(pie_chart_bytes, format='png', dpi=100, bbox_inches='tight')
    pie_chart_bytes.seek(0)
    plt.close(fig_pie)
    
    return line_chart_bytes, pie_chart_bytes


def weekly_chart_payload(user_id: int) -> Dict[str, Any]:
    # Get IST today and calculate the last 7 days
    ist_today = get_ist_now().date()
    days = [ist_today - timedelta(days=i) for i in range(6, -1, -1)]
    labels = [d.strftime("%a") for d in days]
    dataset_template = {emotion: [0 for _ in days] for emotion in EMOTION_COLORS}

    # Use IST offset (+05:30) for date calculation
    rows = g.db.execute(
        """
        SELECT date(m.created_at, '+05:30') AS day, m.emotion, COUNT(*) AS total
        FROM messages m
        JOIN conversations c ON c.id = m.conversation_id
        WHERE c.user_id = ? AND m.author = 'user'
          AND day >= date('now', '+05:30', '-6 day')
        GROUP BY day, m.emotion
        """,
        (user_id,),
    ).fetchall()
    day_index = {d.isoformat(): idx for idx, d in enumerate(days)}
    distribution: Counter[str] = Counter()
    for row in rows:
        day = row["day"]
        emotion = normalize_emotion(row["emotion"] or "Neutral")
        if day in day_index and emotion in dataset_template:
            dataset_template[emotion][day_index[day]] = row["total"]
            distribution[emotion] += row["total"]

    datasets = [
        {
            "label": emotion,
            "data": values,
            "borderColor": EMOTION_COLORS[emotion],
            "backgroundColor": EMOTION_COLORS[emotion],
            "tension": 0.4,
            "fill": False,
        }
        for emotion, values in dataset_template.items()
    ]

    distribution_labels = list(distribution.keys()) or list(EMOTION_COLORS.keys())
    distribution_data = [distribution[label] for label in distribution_labels] or [1] * len(distribution_labels)
    distribution_colors = [EMOTION_COLORS.get(label, "#94a3b8") for label in distribution_labels]

    return {
        "timeline": {"labels": labels, "datasets": datasets},
        "distribution": {
            "labels": distribution_labels,
            "data": distribution_data,
            "colors": distribution_colors,
        },
    }


def summarize_day(user_id: int, target_day: date) -> Dict[str, Any]:
    rows = g.db.execute(
        """
        SELECT m.emotion, m.intensity, m.content, m.created_at, m.detection_source, m.image_path
        FROM messages m
        JOIN conversations c ON c.id = m.conversation_id
        WHERE c.user_id = ? AND m.author = 'user'
          AND date(m.created_at, '+05:30') = ?
        """,
        (user_id, target_day.isoformat()),
    ).fetchall()
    if not rows:
        return {
            "entry_count": 0,
            "top_emotion": "No data",
            "avg_intensity": 0,
            "highlights": [],
        }

    # Convert rows to dicts for safe access
    rows_dict = [dict(row) for row in rows]
    emotion_counts = Counter(normalize_emotion(row.get("emotion") or "Neutral") for row in rows_dict)
    top_emotion, _ = emotion_counts.most_common(1)[0]
    avg_intensity = sum((row.get("intensity") or 0) for row in rows_dict) / len(rows_dict)
    text_count = sum(1 for row in rows_dict if row.get("detection_source") == "text")
    image_count = sum(1 for row in rows_dict if row.get("detection_source") in ("image", "camera"))
    highlights = []
    for row in rows_dict[:3]:
        source_tag = "📷" if row.get("detection_source") == "camera" else "📎" if row.get("detection_source") == "image" else ""
        snippet = row.get("content", "")[:100] + ("" if len(row.get("content", "")) > 100 else "")
        highlights.append(f"{source_tag} {row.get('emotion') or 'Emotion'} - {snippet}")

    return {
        "entry_count": len(rows),
        "top_emotion": top_emotion,
        "avg_intensity": round(avg_intensity, 2),
        "highlights": highlights,
        "text_count": text_count,
        "image_count": image_count,
    }


def _build_classic_template(doc: SimpleDocTemplate, summary: Dict[str, Any], target_day: date, user_id: int) -> List:
    """Classic template - clean and traditional."""
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'],
        fontSize=24, textColor=colors.HexColor('#2c3e50'), spaceAfter=6,
        alignment=TA_CENTER, fontName='Helvetica-Bold')
    heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'],
        fontSize=14, textColor=colors.HexColor('#34495e'), spaceAfter=10,
        spaceBefore=12, fontName='Helvetica-Bold')
    normal_style = ParagraphStyle('CustomNormal', parent=styles['BodyText'],
        fontSize=11, textColor=colors.HexColor('#2c3e50'), spaceAfter=8, alignment=TA_LEFT)
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'],
        fontSize=10, textColor=colors.HexColor('#7f8c8d'), alignment=TA_CENTER, spaceAfter=12)
    
    elements.append(Paragraph("📊 EmoCare Daily Reflection", title_style))
    elements.append(Paragraph(f"<b>{target_day.strftime('%B %d, %Y')}</b>", subtitle_style))
    elements.append(Spacer(1, 0.2*inch))
    
    if summary["entry_count"] == 0:
        elements.append(Paragraph("No entries logged today. Consider sharing a feeling to unlock insights.", normal_style))
    else:
        summary_data = [
            ["Metric", "Value"],
            ["Total Entries", str(summary['entry_count'])],
            ["Text Messages", str(summary.get('text_count', 0))],
            ["Images/Camera", str(summary.get('image_count', 0))],
            ["Dominant Emotion", summary['top_emotion']],
            ["Average Intensity", f"{summary['avg_intensity']}/5"],
        ]
        summary_table = Table(summary_data, colWidths=[2.5*inch, 2.5*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 11),
            ('PADDINGTOP', (0, 1), (-1, -1), 8),
            ('PADDINGBOTTOM', (0, 1), (-1, -1), 8),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 0.2*inch))
        elements.append(Paragraph("✨ Highlights", heading_style))
        for highlight in summary["highlights"]:
            elements.append(Paragraph(f"• {highlight}", normal_style))
        elements.append(Spacer(1, 0.3*inch))
        elements.append(Paragraph("📈 Weekly Emotion Analytics", heading_style))
        try:
            line_chart_bytes, pie_chart_bytes = generate_emotion_chart_images(user_id)
            elements.append(RLImage(line_chart_bytes, width=6.5*inch, height=3*inch))
            elements.append(Spacer(1, 0.15*inch))
            elements.append(RLImage(pie_chart_bytes, width=5*inch, height=3*inch))
        except Exception:
            elements.append(Paragraph("<i>Charts could not be generated at this time.</i>", normal_style))
        elements.append(Spacer(1, 0.2*inch))
        suggestion_style = ParagraphStyle('Suggestion', parent=styles['Normal'],
            fontSize=11, textColor=colors.HexColor('#e74c3c'), spaceAfter=8,
            alignment=TA_CENTER, fontName='Helvetica-Oblique')
        elements.append(Paragraph("💝 Gentle suggestion: show yourself the same kindness you offer others.", suggestion_style))
    
    elements.append(Spacer(1, 0.3*inch))
    footer_style = ParagraphStyle('Footer', parent=styles['Normal'],
        fontSize=8, textColor=colors.HexColor('#95a5a6'), alignment=TA_CENTER)
    elements.append(Paragraph("EmoCare - Your Mental Health Companion", footer_style))
    return elements


def _build_modern_template(doc: SimpleDocTemplate, summary: Dict[str, Any], target_day: date, user_id: int) -> List:
    """Modern template - sleek and contemporary."""
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('ModernTitle', parent=styles['Heading1'],
        fontSize=28, textColor=colors.HexColor('#1a1a1a'), spaceAfter=8,
        alignment=TA_CENTER, fontName='Helvetica-Bold', leading=32)
    heading_style = ParagraphStyle('ModernHeading', parent=styles['Heading2'],
        fontSize=16, textColor=colors.HexColor('#4a5568'), spaceAfter=12,
        spaceBefore=16, fontName='Helvetica-Bold')
    normal_style = ParagraphStyle('ModernNormal', parent=styles['BodyText'],
        fontSize=11, textColor=colors.HexColor('#2d3748'), spaceAfter=10, alignment=TA_LEFT, leading=16)
    
    # Modern header with accent
    header_table = Table([[""]], colWidths=[6.5*inch], rowHeights=[0.15*inch])
    header_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea'))]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.3*inch))
    
    elements.append(Paragraph("Daily Wellness Report", title_style))
    elements.append(Paragraph(f"{target_day.strftime('%B %d, %Y')}", 
        ParagraphStyle('Date', parent=styles['Normal'], fontSize=12, textColor=colors.HexColor('#718096'),
        alignment=TA_CENTER, spaceAfter=20)))
    
    if summary["entry_count"] > 0:
        # Stats in cards layout
        stats_data = [
            [f"<b>{summary['entry_count']}</b><br/><font size=9 color='#718096'>Entries</font>",
             f"<b>{summary['top_emotion']}</b><br/><font size=9 color='#718096'>Dominant</font>",
             f"<b>{summary['avg_intensity']}/5</b><br/><font size=9 color='#718096'>Intensity</font>"]
        ]
        stats_table = Table(stats_data, colWidths=[2*inch, 2*inch, 2*inch])
        stats_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f7fafc')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('LEFTPADDING', (0, 0), (-1, -1), 15),
            ('RIGHTPADDING', (0, 0), (-1, -1), 15),
            ('TOPPADDING', (0, 0), (-1, -1), 20),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
        ]))
        elements.append(stats_table)
        elements.append(Spacer(1, 0.3*inch))
        elements.append(Paragraph("Key Insights", heading_style))
        for highlight in summary["highlights"]:
            elements.append(Paragraph(f"→ {highlight}", normal_style))
        try:
            line_chart_bytes, pie_chart_bytes = generate_emotion_chart_images(user_id)
            elements.append(Spacer(1, 0.3*inch))
            elements.append(RLImage(line_chart_bytes, width=6.5*inch, height=3*inch))
            elements.append(Spacer(1, 0.2*inch))
            elements.append(RLImage(pie_chart_bytes, width=5*inch, height=3*inch))
        except Exception:
            pass
    
    return elements


def _build_minimalist_template(doc: SimpleDocTemplate, summary: Dict[str, Any], target_day: date, user_id: int) -> List:
    """Minimalist template - clean and simple."""
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('MinTitle', parent=styles['Heading1'],
        fontSize=22, textColor=colors.black, spaceAfter=4, alignment=TA_CENTER, fontName='Helvetica')
    normal_style = ParagraphStyle('MinNormal', parent=styles['BodyText'],
        fontSize=10, textColor=colors.HexColor('#333'), spaceAfter=6, alignment=TA_LEFT, leading=14)
    
    elements.append(Spacer(1, 0.5*inch))
    elements.append(Paragraph("EmoCare", title_style))
    elements.append(Paragraph(target_day.strftime('%B %d, %Y'), 
        ParagraphStyle('MinDate', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#666'),
        alignment=TA_CENTER, spaceAfter=20)))
    
    if summary["entry_count"] > 0:
        for highlight in summary["highlights"]:
            elements.append(Paragraph(highlight, normal_style))
            elements.append(Spacer(1, 0.15*inch))
    
    elements.append(Spacer(1, 0.4*inch))
    return elements


def _build_professional_template(doc: SimpleDocTemplate, summary: Dict[str, Any], target_day: date, user_id: int) -> List:
    """Professional template - business-like format."""
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('ProfTitle', parent=styles['Heading1'],
        fontSize=20, textColor=colors.HexColor('#1e3a8a'), spaceAfter=10,
        alignment=TA_LEFT, fontName='Helvetica-Bold')
    heading_style = ParagraphStyle('ProfHeading', parent=styles['Heading2'],
        fontSize=13, textColor=colors.HexColor('#1e40af'), spaceAfter=8,
        spaceBefore=12, fontName='Helvetica-Bold')
    normal_style = ParagraphStyle('ProfNormal', parent=styles['BodyText'],
        fontSize=10, textColor=colors.HexColor('#1f2937'), spaceAfter=6, alignment=TA_JUSTIFY)
    
    elements.append(Paragraph("EMOCARE - WELLNESS REPORT", title_style))
    elements.append(Paragraph(f"Date: {target_day.strftime('%B %d, %Y')}", 
        ParagraphStyle('ProfDate', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#4b5563'))))
    elements.append(Spacer(1, 0.3*inch))
    
    if summary["entry_count"] > 0:
        summary_data = [
            ["Metric", "Value"],
            ["Total Entries", str(summary['entry_count'])],
            ["Dominant Emotion", summary['top_emotion']],
            ["Average Intensity", f"{summary['avg_intensity']}/5"],
        ]
        summary_table = Table(summary_data, colWidths=[3*inch, 3*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#93c5fd')),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 0.2*inch))
        elements.append(Paragraph("SUMMARY", heading_style))
        for highlight in summary["highlights"]:
            elements.append(Paragraph(f"• {highlight}", normal_style))
    
    return elements


def _build_colorful_template(doc: SimpleDocTemplate, summary: Dict[str, Any], target_day: date, user_id: int) -> List:
    """Colorful template - vibrant and energetic."""
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('ColorTitle', parent=styles['Heading1'],
        fontSize=26, textColor=colors.HexColor('#e91e63'), spaceAfter=8,
        alignment=TA_CENTER, fontName='Helvetica-Bold')
    heading_style = ParagraphStyle('ColorHeading', parent=styles['Heading2'],
        fontSize=15, textColor=colors.HexColor('#9c27b0'), spaceAfter=10,
        spaceBefore=14, fontName='Helvetica-Bold')
    normal_style = ParagraphStyle('ColorNormal', parent=styles['BodyText'],
        fontSize=11, textColor=colors.HexColor('#424242'), spaceAfter=8, alignment=TA_LEFT)
    
    # Colorful header
    header_table = Table([[""]], colWidths=[6.5*inch], rowHeights=[0.3*inch])
    header_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ff6b6b'))]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.2*inch))
    
    elements.append(Paragraph("✨ Your Day in Colors ✨", title_style))
    elements.append(Paragraph(f"<b>{target_day.strftime('%B %d, %Y')}</b>", 
        ParagraphStyle('ColorDate', parent=styles['Normal'], fontSize=12, textColor=colors.HexColor('#ff9800'),
        alignment=TA_CENTER, spaceAfter=20)))
    
    if summary["entry_count"] > 0:
        # Colorful stats
        stats_colors = [colors.HexColor('#ff6b6b'), colors.HexColor('#4ecdc4'), colors.HexColor('#ffe66d')]
        stats_data = [
            [f"<b>{summary['entry_count']}</b><br/>Entries",
             f"<b>{summary['top_emotion']}</b><br/>Emotion",
             f"<b>{summary['avg_intensity']}/5</b><br/>Intensity"]
        ]
        stats_table = Table(stats_data, colWidths=[2.15*inch, 2.15*inch, 2.15*inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), stats_colors[0]),
            ('BACKGROUND', (1, 0), (1, 0), stats_colors[1]),
            ('BACKGROUND', (2, 0), (2, 0), stats_colors[2]),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 15),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
        ]))
        elements.append(stats_table)
        elements.append(Spacer(1, 0.3*inch))
        elements.append(Paragraph("🎯 Highlights", heading_style))
        for highlight in summary["highlights"]:
            elements.append(Paragraph(f"🎨 {highlight}", normal_style))
    
    return elements


def _build_elegant_template(doc: SimpleDocTemplate, summary: Dict[str, Any], target_day: date, user_id: int) -> List:
    """Elegant template - refined and sophisticated."""
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('ElegantTitle', parent=styles['Heading1'],
        fontSize=24, textColor=colors.HexColor('#2c1810'), spaceAfter=6,
        alignment=TA_CENTER, fontName='Helvetica-Bold')
    heading_style = ParagraphStyle('ElegantHeading', parent=styles['Heading2'],
        fontSize=13, textColor=colors.HexColor('#5d4037'), spaceAfter=10,
        spaceBefore=14, fontName='Helvetica')
    normal_style = ParagraphStyle('ElegantNormal', parent=styles['BodyText'],
        fontSize=10, textColor=colors.HexColor('#3e2723'), spaceAfter=8, alignment=TA_JUSTIFY, leading=15)
    
    elements.append(Spacer(1, 0.4*inch))
    elements.append(Paragraph("EmoCare Wellness Report", title_style))
    elements.append(Paragraph("─" * 40, ParagraphStyle('Line', parent=styles['Normal'],
        fontSize=8, textColor=colors.HexColor('#8d6e63'), alignment=TA_CENTER, spaceAfter=8)))
    elements.append(Paragraph(f"{target_day.strftime('%B %d, %Y')}", 
        ParagraphStyle('ElegantDate', parent=styles['Normal'], fontSize=11, textColor=colors.HexColor('#6d4c41'),
        alignment=TA_CENTER, spaceAfter=25, fontName='Helvetica')))
    
    if summary["entry_count"] > 0:
        summary_data = [
            ["Total Entries", str(summary['entry_count'])],
            ["Dominant Emotion", summary['top_emotion']],
            ["Average Intensity", f"{summary['avg_intensity']}/5"],
        ]
        summary_table = Table(summary_data, colWidths=[3.25*inch, 3.25*inch])
        summary_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d7ccc8')),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 0.25*inch))
        elements.append(Paragraph("Insights", heading_style))
        for highlight in summary["highlights"]:
            elements.append(Paragraph(f"• {highlight}", normal_style))
    
    elements.append(Spacer(1, 0.4*inch))
    return elements


def _build_creative_template(doc: SimpleDocTemplate, summary: Dict[str, Any], target_day: date, user_id: int) -> List:
    """Creative template - artistic and expressive."""
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('CreativeTitle', parent=styles['Heading1'],
        fontSize=30, textColor=colors.HexColor('#ff5722'), spaceAfter=10,
        alignment=TA_CENTER, fontName='Helvetica-Bold')
    heading_style = ParagraphStyle('CreativeHeading', parent=styles['Heading2'],
        fontSize=16, textColor=colors.HexColor('#ff9800'), spaceAfter=12,
        spaceBefore=16, fontName='Helvetica-Bold')
    normal_style = ParagraphStyle('CreativeNormal', parent=styles['BodyText'],
        fontSize=11, textColor=colors.HexColor('#37474f'), spaceAfter=10, alignment=TA_LEFT)
    
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph("🎨 CREATIVE REFLECTION 🎨", title_style))
    elements.append(Paragraph(f"{target_day.strftime('%B %d, %Y')}", 
        ParagraphStyle('CreativeDate', parent=styles['Normal'], fontSize=14, textColor=colors.HexColor('#607d8b'),
        alignment=TA_CENTER, spaceAfter=25)))
    
    if summary["entry_count"] > 0:
        # Creative stats display
        elements.append(Paragraph(f"<b>{summary['entry_count']}</b> moments captured", 
            ParagraphStyle('Stat', parent=styles['Normal'], fontSize=13, textColor=colors.HexColor('#e64a19'),
            alignment=TA_CENTER, spaceAfter=15)))
        elements.append(Paragraph(f"Dominant emotion: <b>{summary['top_emotion']}</b>", 
            ParagraphStyle('Stat', parent=styles['Normal'], fontSize=13, textColor=colors.HexColor('#ff6f00'),
            alignment=TA_CENTER, spaceAfter=25)))
        elements.append(Paragraph("Your Story", heading_style))
        for highlight in summary["highlights"]:
            elements.append(Paragraph(f"✨ {highlight}", normal_style))
            elements.append(Spacer(1, 0.1*inch))
    
    return elements


def _build_tech_template(doc: SimpleDocTemplate, summary: Dict[str, Any], target_day: date, user_id: int) -> List:
    """Tech template - futuristic and data-driven."""
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('TechTitle', parent=styles['Heading1'],
        fontSize=22, textColor=colors.HexColor('#00d4ff'), spaceAfter=8,
        alignment=TA_CENTER, fontName='Helvetica-Bold')
    heading_style = ParagraphStyle('TechHeading', parent=styles['Heading2'],
        fontSize=13, textColor=colors.HexColor('#00ff88'), spaceAfter=10,
        spaceBefore=12, fontName='Helvetica-Bold')
    normal_style = ParagraphStyle('TechNormal', parent=styles['BodyText'],
        fontSize=10, textColor=colors.HexColor('#b0bec5'), spaceAfter=6, alignment=TA_LEFT)
    
    # Dark header
    header_table = Table([[""]], colWidths=[6.5*inch], rowHeights=[0.2*inch])
    header_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0a1929'))]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.2*inch))
    
    elements.append(Paragraph("[EMOCARE] DAILY REPORT", title_style))
    elements.append(Paragraph(f">> {target_day.strftime('%Y-%m-%d')}", 
        ParagraphStyle('TechDate', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#64ffda'),
        alignment=TA_CENTER, spaceAfter=20)))
    
    if summary["entry_count"] > 0:
        # Tech-style stats
        stats_data = [
            ["ENTRIES:", str(summary['entry_count'])],
            ["EMOTION:", summary['top_emotion'].upper()],
            ["INTENSITY:", f"{summary['avg_intensity']}/5"],
        ]
        stats_table = Table(stats_data, colWidths=[2.5*inch, 4*inch])
        stats_table.setStyle(TableStyle([
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#00ff88')),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.white),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#1a237e')),
        ]))
        elements.append(stats_table)
        elements.append(Spacer(1, 0.2*inch))
        elements.append(Paragraph("[INSIGHTS]", heading_style))
        for highlight in summary["highlights"]:
            elements.append(Paragraph(f"> {highlight}", normal_style))
    
    return elements


def _build_nature_template(doc: SimpleDocTemplate, summary: Dict[str, Any], target_day: date, user_id: int) -> List:
    """Nature template - organic and calming."""
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('NatureTitle', parent=styles['Heading1'],
        fontSize=26, textColor=colors.HexColor('#2e7d32'), spaceAfter=8,
        alignment=TA_CENTER, fontName='Helvetica-Bold')
    heading_style = ParagraphStyle('NatureHeading', parent=styles['Heading2'],
        fontSize=14, textColor=colors.HexColor('#388e3c'), spaceAfter=10,
        spaceBefore=14, fontName='Helvetica-Bold')
    normal_style = ParagraphStyle('NatureNormal', parent=styles['BodyText'],
        fontSize=11, textColor=colors.HexColor('#1b5e20'), spaceAfter=8, alignment=TA_LEFT)
    
    # Green header
    header_table = Table([[""]], colWidths=[6.5*inch], rowHeights=[0.25*inch])
    header_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#66bb6a'))]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.2*inch))
    
    elements.append(Paragraph("🌿 Daily Wellness Journey 🌿", title_style))
    elements.append(Paragraph(f"{target_day.strftime('%B %d, %Y')}", 
        ParagraphStyle('NatureDate', parent=styles['Normal'], fontSize=12, textColor=colors.HexColor('#4caf50'),
        alignment=TA_CENTER, spaceAfter=20)))
    
    if summary["entry_count"] > 0:
        summary_data = [
            [f"<b>{summary['entry_count']}</b> Reflections",
             f"<b>{summary['top_emotion']}</b> Emotion",
             f"<b>{summary['avg_intensity']}/5</b> Intensity"]
        ]
        stats_table = Table(summary_data, colWidths=[2.15*inch, 2.15*inch, 2.15*inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#c8e6c9')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1b5e20')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ]))
        elements.append(stats_table)
        elements.append(Spacer(1, 0.3*inch))
        elements.append(Paragraph("🌸 Insights", heading_style))
        for highlight in summary["highlights"]:
            elements.append(Paragraph(f"🌱 {highlight}", normal_style))
    
    return elements


def _build_zen_template(doc: SimpleDocTemplate, summary: Dict[str, Any], target_day: date, user_id: int) -> List:
    """Zen template - peaceful and mindful."""
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('ZenTitle', parent=styles['Heading1'],
        fontSize=20, textColor=colors.HexColor('#5d4037'), spaceAfter=6,
        alignment=TA_CENTER, fontName='Helvetica')
    heading_style = ParagraphStyle('ZenHeading', parent=styles['Heading2'],
        fontSize=12, textColor=colors.HexColor('#6d4c41'), spaceAfter=8,
        spaceBefore=12, fontName='Helvetica')
    normal_style = ParagraphStyle('ZenNormal', parent=styles['BodyText'],
        fontSize=10, textColor=colors.HexColor('#3e2723'), spaceAfter=6, alignment=TA_LEFT, leading=16)
    
    elements.append(Spacer(1, 0.6*inch))
    elements.append(Paragraph("mindful reflection", title_style))
    elements.append(Spacer(1, 0.1*inch))
    elements.append(Paragraph("─" * 30, ParagraphStyle('Line', parent=styles['Normal'],
        fontSize=6, textColor=colors.HexColor('#a1887f'), alignment=TA_CENTER, spaceAfter=6)))
    elements.append(Paragraph(target_day.strftime('%B %d, %Y'), 
        ParagraphStyle('ZenDate', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#8d6e63'),
        alignment=TA_CENTER, spaceAfter=30)))
    
    if summary["entry_count"] > 0:
        elements.append(Paragraph("observations", heading_style))
        for highlight in summary["highlights"]:
            elements.append(Paragraph(highlight, normal_style))
            elements.append(Spacer(1, 0.15*inch))
        elements.append(Spacer(1, 0.3*inch))
        elements.append(Paragraph(f"{summary['entry_count']} moments · {summary['top_emotion']} · intensity {summary['avg_intensity']}/5", 
            ParagraphStyle('ZenFooter', parent=styles['Normal'], fontSize=8, textColor=colors.HexColor('#a1887f'),
            alignment=TA_CENTER)))
    
    elements.append(Spacer(1, 0.5*inch))
    return elements


def build_daily_report(user_id: int, target_day: date) -> Tuple[Dict[str, Any], Path]:
    summary = summarize_day(user_id, target_day)
    report_path = REPORTS_DIR / f"{target_day.isoformat()}_user-{user_id}.pdf"
    
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create PDF document
    doc = SimpleDocTemplate(
        str(report_path),
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch,
    )
    
    # Container for PDF elements
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#34495e'),
        spaceAfter=10,
        spaceBefore=12,
        fontName='Helvetica-Bold',
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['BodyText'],
        fontSize=11,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=8,
        alignment=TA_LEFT,
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#7f8c8d'),
        alignment=TA_CENTER,
        spaceAfter=12,
    )
    
    # Title
    title = Paragraph("📊 EmoCare Daily Reflection", title_style)
    elements.append(title)
    
    # Date subtitle
    date_para = Paragraph(f"<b>{target_day.strftime('%B %d, %Y')}</b>", subtitle_style)
    elements.append(date_para)
    elements.append(Spacer(1, 0.2*inch))
    
    if summary["entry_count"] == 0:
        # No entries message
        no_entries = Paragraph(
            "No entries logged today. Consider sharing a feeling to unlock insights.",
            normal_style
        )
        elements.append(no_entries)
    else:
        # Summary Statistics Table
        summary_data = [
            ["Metric", "Value"],
            ["Total Entries", str(summary['entry_count'])],
            ["Text Messages", str(summary.get('text_count', 0))],
            ["Images/Camera", str(summary.get('image_count', 0))],
            ["Dominant Emotion", summary['top_emotion']],
            ["Average Intensity", f"{summary['avg_intensity']}/5"],
        ]
        
        summary_table = Table(summary_data, colWidths=[2.5*inch, 2.5*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 11),
            ('PADDINGTOP', (0, 1), (-1, -1), 8),
            ('PADDINGBOTTOM', (0, 1), (-1, -1), 8),
        ]))
        
        elements.append(summary_table)
        elements.append(Spacer(1, 0.2*inch))
        
        # Highlights Section
        highlights_heading = Paragraph("✨ Highlights", heading_style)
        elements.append(highlights_heading)
        
        for highlight in summary["highlights"]:
            highlight_para = Paragraph(f"• {highlight}", normal_style)
            elements.append(highlight_para)
        
        elements.append(Spacer(1, 0.3*inch))
        
        # Add Charts Section
        charts_heading = Paragraph("📈 Weekly Emotion Analytics", heading_style)
        elements.append(charts_heading)
        
        try:
            line_chart_bytes, pie_chart_bytes = generate_emotion_chart_images(user_id)
            
            # Add line chart
            line_img = RLImage(line_chart_bytes, width=6.5*inch, height=3*inch)
            elements.append(line_img)
            elements.append(Spacer(1, 0.15*inch))
            
            # Add pie chart
            pie_img = RLImage(pie_chart_bytes, width=5*inch, height=3*inch)
            elements.append(pie_img)
        except Exception as e:
            # If chart generation fails, continue without charts
            chart_error = Paragraph(f"<i>Charts could not be generated at this time.</i>", normal_style)
            elements.append(chart_error)
        
        elements.append(Spacer(1, 0.2*inch))
        
        # Gentle suggestion
        suggestion_style = ParagraphStyle(
            'Suggestion',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#e74c3c'),
            spaceAfter=8,
            alignment=TA_CENTER,
            fontName='Helvetica-Oblique',
        )
        suggestion = Paragraph(
            "💝 Gentle suggestion: show yourself the same kindness you offer others.",
            suggestion_style
        )
        elements.append(suggestion)
    
    # Footer
    elements.append(Spacer(1, 0.3*inch))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#95a5a6'),
        alignment=TA_CENTER,
    )
    footer = Paragraph("EmoCare - Your Mental Health Companion", footer_style)
    elements.append(footer)
    
    # Build PDF
    doc.build(elements)
    return summary, report_path


def calculate_achievements(user_id: int) -> Dict[str, Any]:
    """Calculate user achievements and badges."""
    # Get user stats
    row = g.db.execute(
        """
        SELECT COUNT(*) as count
        FROM messages m
        JOIN conversations c ON c.id = m.conversation_id
        WHERE c.user_id = ? AND m.author = 'user'
        """,
        (user_id,),
    ).fetchone()
    total_messages = dict(row)["count"] if row else 0
    
    # Calculate streak
    rows = g.db.execute(
        """
        SELECT DISTINCT date(m.created_at, 'localtime') as day
        FROM messages m
        JOIN conversations c ON c.id = m.conversation_id
        WHERE c.user_id = ? AND m.author = 'user'
        ORDER BY day DESC
        LIMIT 30
        """,
        (user_id,),
    ).fetchall()
    
    streak = 0
    today = date.today()
    for i, row in enumerate(rows):
        row_dict = dict(row)
        day_str = row_dict.get("day")
        if day_str:
            day = date.fromisoformat(day_str) if isinstance(day_str, str) else day_str
            expected_date = today - timedelta(days=i)
            if day == expected_date:
                streak += 1
            else:
                break
    
    achievements = []
    if total_messages >= 1:
        achievements.append({"name": "First Step", "icon": "🌱", "description": "Logged your first emotion"})
    if total_messages >= 10:
        achievements.append({"name": "Consistent", "icon": "📝", "description": "Logged 10 emotions"})
    if total_messages >= 50:
        achievements.append({"name": "Dedicated", "icon": "💪", "description": "Logged 50 emotions"})
    if total_messages >= 100:
        achievements.append({"name": "Master", "icon": "🏆", "description": "Logged 100 emotions"})
    if streak >= 3:
        achievements.append({"name": "On Fire", "icon": "🔥", "description": f"{streak} day streak"})
    if streak >= 7:
        achievements.append({"name": "Week Warrior", "icon": "⭐", "description": "7 day streak"})
    if streak >= 30:
        achievements.append({"name": "Month Master", "icon": "👑", "description": "30 day streak"})
    
    return {
        "total_messages": total_messages,
        "current_streak": streak,
        "achievements": achievements,
        "level": min(10, total_messages // 10 + 1),
    }


def generate_ai_insights(user_id: int) -> Dict[str, Any]:
    """Generate AI-powered insights and patterns."""
    rows = g.db.execute(
        """
        SELECT m.emotion, m.intensity, m.created_at, m.detection_source
        FROM messages m
        JOIN conversations c ON c.id = m.conversation_id
        WHERE c.user_id = ? AND m.author = 'user'
        ORDER BY m.created_at DESC
        LIMIT 50
        """,
        (user_id,),
    ).fetchall()
    
    if not rows:
        return {
            "insights": [],
            "patterns": [],
            "recommendations": [],
        }
    
    rows_dict = [dict(row) for row in rows]
    emotion_counts = Counter(normalize_emotion(row.get("emotion", "Neutral")) for row in rows_dict)
    most_common = emotion_counts.most_common(3)
    
    # Calculate time-based patterns
    weekday_emotions = defaultdict(Counter)
    for row in rows_dict:
        timestamp = datetime.fromisoformat(row["created_at"]) if isinstance(row["created_at"], str) else row["created_at"]
        if isinstance(timestamp, datetime):
            weekday = timestamp.strftime("%A")
            weekday_emotions[weekday][normalize_emotion(row.get("emotion", "Neutral"))] += 1
    
    insights = []
    patterns = []
    recommendations = []
    
    if most_common:
        top_emotion, count = most_common[0]
        insights.append({
            "title": f"Your dominant emotion is {top_emotion}",
            "description": f"You've experienced {top_emotion} {count} times recently. This suggests it's a significant part of your emotional landscape.",
            "icon": "🎯",
        })
    
    # Pattern detection
    if weekday_emotions:
        worst_day = max(weekday_emotions.items(), key=lambda x: sum(x[1].values()))
        patterns.append({
            "title": f"{worst_day[0]}s are challenging",
            "description": f"You tend to log more emotions on {worst_day[0]}s. Consider planning self-care activities for these days.",
            "icon": "📅",
        })
    
    # Recommendations
    if most_common:
        top_emotion = most_common[0][0]
        if top_emotion in ["Stress", "Anxiety"]:
            recommendations.append({
                "title": "Try breathing exercises",
                "description": "Your patterns show elevated stress. Daily breathing exercises can help regulate your nervous system.",
                "icon": "🧘",
            })
        elif top_emotion == "Depression":
            recommendations.append({
                "title": "Consider morning sunlight",
                "description": "Natural light exposure in the morning can help improve mood and energy levels.",
                "icon": "☀️",
            })
    
    return {
        "insights": insights,
        "patterns": patterns,
        "recommendations": recommendations,
        "total_entries": len(rows_dict),
    }


def generate_mood_calendar(user_id: int) -> Dict[str, Any]:
    """Generate mood calendar data for the current month."""
    today = date.today()
    first_day = today.replace(day=1)
    last_day = (first_day + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    
    rows = g.db.execute(
        """
        SELECT date(m.created_at, 'localtime') as day, m.emotion, m.intensity
        FROM messages m
        JOIN conversations c ON c.id = m.conversation_id
        WHERE c.user_id = ? AND m.author = 'user'
          AND day >= ? AND day <= ?
        """,
        (user_id, first_day.isoformat(), last_day.isoformat()),
    ).fetchall()
    
    # Build calendar_data as a mapping day->list of recorded emotions for that day.
    # Each day entry will include 'entries' (list of {emotion,intensity}), a
    # dominant emotion (highest intensity) and a count.
    calendar_data = {}
    for row in rows:
        row_dict = dict(row)
        day = row_dict.get("day")
        emotion = normalize_emotion(row_dict.get("emotion", "Neutral"))
        intensity = row_dict.get("intensity", 2)
        if not day:
            continue

        if day not in calendar_data:
            calendar_data[day] = {
                "entries": [{"emotion": emotion, "intensity": intensity}],
                "dominant": emotion,
                "intensity": intensity,
                "count": 1,
            }
        else:
            calendar_data[day]["entries"].append({"emotion": emotion, "intensity": intensity})
            calendar_data[day]["count"] += 1
            # update dominant if this entry has higher intensity
            if intensity > calendar_data[day]["intensity"]:
                calendar_data[day]["dominant"] = emotion
                calendar_data[day]["intensity"] = intensity
    
    return {
        "calendar_data": calendar_data,
        "month": today.strftime("%B %Y"),
        "first_day": first_day,
        "last_day": last_day,
    }


def get_user_streaks(user_id: int) -> Dict[str, Any]:
    """Get user's current streaks."""
    rows = g.db.execute(
        "SELECT streak_type, current_streak, longest_streak, last_activity_date FROM streaks WHERE user_id = ?",
        (user_id,)
    ).fetchall()
    streaks = {}
    for row in rows:
        streaks[row["streak_type"]] = dict(row)
    return streaks

def update_streak(user_id: int, streak_type: str) -> None:
    """Update user streak for a given activity type."""
    today = date.today()
    row = g.db.execute(
        "SELECT * FROM streaks WHERE user_id = ? AND streak_type = ?",
        (user_id, streak_type)
    ).fetchone()
    
    if row:
        last_date = datetime.fromisoformat(row["last_activity_date"]).date() if row["last_activity_date"] else None
        if last_date == today:
            return  # Already updated today
        elif last_date == today - timedelta(days=1):
            # Continue streak
            new_streak = row["current_streak"] + 1
            longest = max(new_streak, row["longest_streak"])
            g.db.execute(
                "UPDATE streaks SET current_streak = ?, longest_streak = ?, last_activity_date = ? WHERE user_id = ? AND streak_type = ?",
                (new_streak, longest, today, user_id, streak_type)
            )
        else:
            # Reset streak
            g.db.execute(
                "UPDATE streaks SET current_streak = 1, last_activity_date = ? WHERE user_id = ? AND streak_type = ?",
                (today, user_id, streak_type)
            )
    else:
        # Create new streak
        g.db.execute(
            "INSERT INTO streaks (user_id, streak_type, current_streak, longest_streak, last_activity_date) VALUES (?, ?, 1, 1, ?)",
            (user_id, streak_type, today)
        )
    g.db.commit()

def check_achievements(user_id: int, achievement_type: str) -> None:
    """Check and unlock achievements."""
    # Check if already unlocked
    existing = g.db.execute(
        "SELECT id FROM achievements WHERE user_id = ? AND achievement_type = ?",
        (user_id, achievement_type)
    ).fetchone()
    if existing:
        return
    
    achievement_names = {
        "first_chat": "First Chat",
        "week_streak": "Week Warrior",
        "month_streak": "Monthly Master",
        "goal_completed": "Goal Achiever",
        "journal_entry": "Journal Keeper",
        "breathing_session": "Mindful Moment",
    }
    
    name = achievement_names.get(achievement_type, "Achievement Unlocked")
    g.db.execute(
        "INSERT INTO achievements (user_id, achievement_type, achievement_name) VALUES (?, ?, ?)",
        (user_id, achievement_type, name)
    )
    g.db.commit()

def grouped_history(user_id: int) -> List[Dict[str, Any]]:
    rows = fetch_chat_messages(user_id)
    history_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        timestamp = datetime.fromisoformat(row["created_at"]) if isinstance(row["created_at"], str) else row["created_at"]
        day_key = timestamp.strftime("%Y-%m-%d") if isinstance(timestamp, datetime) else "Unknown"
        history_map[day_key].append(
            {
                "id": row.get("id"),
                "time": timestamp.strftime("%H:%M") if isinstance(timestamp, datetime) else "",
                "author": row["author"].title(),
                "content": row["content"],
                "emotion": normalize_emotion(row["emotion"] or "Neutral"),
                "image_filename": row.get("image_filename"),
                "detection_source": row.get("detection_source", "text"),
            }
        )
    grouped = []
    for day in sorted(history_map.keys(), reverse=True):
        grouped.append({"day": day, "messages": history_map[day]})
    return grouped


def get_user_preferences(user_id: int) -> Dict[str, Any]:
    """Get user preferences or return defaults."""
    cursor = g.db.execute(
        "SELECT * FROM user_preferences WHERE user_id = ?",
        (user_id,)
    )
    row = cursor.fetchone()
    if row:
        return dict(row)
    # Return defaults
    return {
        "daily_checkin_reminders": True,
        "goal_reminders": True,
        "weekly_report_emails": False,
        "theme": "Auto",
        "language": "English",
        "default_report_template": "classic"
    }


def save_user_preferences(user_id: int, preferences: Dict[str, Any]) -> None:
    """Save user preferences."""
    cursor = g.db.execute(
        "SELECT id FROM user_preferences WHERE user_id = ?",
        (user_id,)
    )
    exists = cursor.fetchone()
    
    if exists:
        # Update existing preferences
        g.db.execute(
            """UPDATE user_preferences SET
                daily_checkin_reminders = ?,
                goal_reminders = ?,
                weekly_report_emails = ?,
                theme = ?,
                language = ?,
                default_report_template = ?,
                updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?""",
            (
                preferences.get("daily_checkin_reminders", True),
                preferences.get("goal_reminders", True),
                preferences.get("weekly_report_emails", False),
                preferences.get("theme", "Auto"),
                preferences.get("language", "English"),
                preferences.get("default_report_template", "classic"),
                user_id
            )
        )
    else:
        # Insert new preferences
        g.db.execute(
            """INSERT INTO user_preferences
                (user_id, daily_checkin_reminders, goal_reminders, weekly_report_emails,
                 theme, language, default_report_template)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                preferences.get("daily_checkin_reminders", True),
                preferences.get("goal_reminders", True),
                preferences.get("weekly_report_emails", False),
                preferences.get("theme", "Auto"),
                preferences.get("language", "English"),
                preferences.get("default_report_template", "classic")
            )
        )
    g.db.commit()


def export_user_data(user_id: int) -> Dict[str, Any]:
    """Export all user data for backup."""
    data = {
        "user_id": user_id,
        "export_date": datetime.now().isoformat(),
        "messages": [],
        "journal_entries": [],
        "goals": [],
        "achievements": [],
        "streaks": [],
        "preferences": get_user_preferences(user_id)
    }
    
    # Export messages
    messages = fetch_chat_messages(user_id)
    data["messages"] = [dict(m) for m in messages]
    
    # Export journal entries
    journal_rows = g.db.execute(
        "SELECT * FROM journal_entries WHERE user_id = ?",
        (user_id,)
    ).fetchall()
    data["journal_entries"] = [dict(row) for row in journal_rows]
    
    # Export goals
    goals_rows = g.db.execute(
        "SELECT * FROM goals WHERE user_id = ?",
        (user_id,)
    ).fetchall()
    data["goals"] = [dict(row) for row in goals_rows]
    
    # Export achievements
    achievements_rows = g.db.execute(
        "SELECT * FROM achievements WHERE user_id = ?",
        (user_id,)
    ).fetchall()
    data["achievements"] = [dict(row) for row in achievements_rows]
    
    # Export streaks
    streaks_rows = g.db.execute(
        "SELECT * FROM streaks WHERE user_id = ?",
        (user_id,)
    ).fetchall()
    data["streaks"] = [dict(row) for row in streaks_rows]
    
    return data


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("EMOCARE_SECRET_KEY", "super-secret-dev-key")

    @app.before_request
    def before_request() -> None:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row

    @app.teardown_appcontext
    def close_connection(_: Any) -> None:
        db = getattr(g, "db", None)
        if db is not None:
            db.close()

    with app.app_context():
        init_db()

    def login_required(view: F) -> F:
        @wraps(view)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            if "user_id" not in session:
                flash("Please log in to continue.", "error")
                return redirect(url_for("login"))
            return view(*args, **kwargs)

        return wrapped  # type: ignore[return-value]

    def render_app_template(template_name: str, **context: Any) -> str:
        return render_template(template_name, user_name=session.get("user_name"), **context)

    @app.route("/", methods=["GET", "POST"])
    def login() -> str:
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")

            if not email or not password:
                flash("Please enter both email and password.", "error")
            else:
                user = query_user(email)
                if user and check_password_hash(user["password"], password):
                    session.clear()
                    session["user_id"] = user["id"]
                    session["user_name"] = user["full_name"]
                    flash(f"Welcome back, {user['full_name']}!", "success")
                    return redirect(url_for("dashboard"))
                flash("Invalid credentials. Try again or sign up.", "error")

        return render_template("login.html")

    @app.route("/signup", methods=["GET", "POST"])
    def signup() -> str:
        if request.method == "POST":
            full_name = request.form.get("full_name", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            confirm_password = request.form.get("confirm_password", "")

            if not full_name or not email or not password:
                flash("Every field is required.", "error")
            elif password != confirm_password:
                flash("Passwords do not match.", "error")
            elif query_user(email):
                flash("An account with that email already exists.", "error")
            else:
                hashed_password = generate_password_hash(password)
                g.db.execute(
                    "INSERT INTO users (full_name, email, password) VALUES (?, ?, ?)",
                    (full_name, email, hashed_password),
                )
                g.db.commit()
                flash("Account created! Please log in.", "success")
                return redirect(url_for("login"))

        return render_template("signup.html")

    @app.route("/dashboard")
    @login_required
    def dashboard() -> str:
        user_id = session["user_id"]
        snapshot = latest_user_snapshot(user_id)
        chart_payload = weekly_chart_payload(user_id)
        recent_convos = fetch_recent_conversations(user_id)
        activities = suggested_activities(snapshot.get("emotion"))
        report_summary, report_path = build_daily_report(user_id, date.today())
        report_download_url = url_for("download_report", report_date=date.today().isoformat())
        context = {
            "today_summary": snapshot["summary"],
            "chart_payload": chart_payload,
            "activity_suggestions": activities,
            "recent_conversations": recent_convos,
            "report_summary": report_summary,
            "report_file": report_path.name,
            "report_download_url": report_download_url,
        }
        return render_app_template("dashboard.html", **context)

    @app.route("/charts")
    @login_required
    def charts() -> str:
        user_id = session["user_id"]
        chart_payload = weekly_chart_payload(user_id)
        distribution_pairs = list(
            zip(chart_payload["distribution"]["labels"], chart_payload["distribution"]["data"])
        )
        return render_app_template(
            "charts.html",
            chart_payload=chart_payload,
            distribution_pairs=distribution_pairs,
        )

    @app.route("/reports", methods=["GET", "POST"])
    @login_required
    def reports() -> str:
        user_id = session["user_id"]
        if request.method == "POST":
            date_raw = request.form.get("report_date", "")
            try:
                target_day = date.fromisoformat(date_raw)
            except ValueError:
                flash("Invalid date format.", "error")
                target_day = date.today()
        else:
            target_day = date.today()
        summary, report_path = build_daily_report(user_id, target_day)
        download_url = url_for("download_report", report_date=target_day.isoformat())
        return render_app_template(
            "reports.html",
            summary=summary,
            target_day=target_day,
            report_file=report_path.name,
            download_url=download_url,
        )

    @app.route("/reports/download/<report_date>")
    @login_required
    def download_report(report_date: str):
        user_id = session["user_id"]
        try:
            target_day = date.fromisoformat(report_date)
        except ValueError:
            abort(404)
        _, report_path = build_daily_report(user_id, target_day)
        if not report_path.exists():
            abort(404)
        return send_file(report_path, as_attachment=True, download_name=report_path.name)

    @app.route("/activities")
    @login_required
    def activities() -> str:
        user_id = session["user_id"]
        snapshot = latest_user_snapshot(user_id)
        activities_list = suggested_activities(snapshot.get("emotion"))
        return render_app_template("activities.html", activities=activities_list, current_emotion=snapshot.get("emotion"))

    @app.route("/history")
    @login_required
    def history() -> str:
        user_id = session["user_id"]
        grouped = grouped_history(user_id)
        return render_app_template("history.html", grouped_history=grouped)

    @app.route("/chat", methods=["GET", "POST"])
    @login_required
    def chat() -> str:
        user_id = session["user_id"]
        analysis_display = None
        # Always have a conversation id available (GET + POST) to avoid UnboundLocalError
        conversation_id = get_or_create_today_conversation(user_id)
        if request.method == "POST":
            user_message = request.form.get("message", "").strip()
            image_file = request.files.get("image")
            camera_data = request.form.get("camera_image")
            insight = None
            image_path = None
            detection_source = "text"
            
            # Handle camera snapshot (base64 image) - improved error handling
            if camera_data and camera_data.strip():
                try:
                    # Handle base64 data URL
                    if "," in camera_data:
                        header, encoded = camera_data.split(",", 1)
                    else:
                        encoded = camera_data
                    
                    # Validate base64 data
                    if not encoded or len(encoded) < 100:
                        flash("Invalid image data. Please try capturing again.", "error")
                        messages = fetch_chat_messages(user_id)
                        return render_app_template("chat.html", messages=messages, analysis=None)
                    
                    try:
                        image_data = base64.b64decode(encoded)
                    except Exception as decode_err:
                        flash("Failed to decode image. Please try capturing again.", "error")
                        messages = fetch_chat_messages(user_id)
                        return render_app_template("chat.html", messages=messages, analysis=None)
                    
                    if len(image_data) < 1000:  # Too small to be a valid image
                        flash("Image data too small. Please try capturing again.", "error")
                        messages = fetch_chat_messages(user_id)
                        return render_app_template("chat.html", messages=messages, analysis=None)
                    
                    try:
                        img = Image.open(io.BytesIO(image_data))
                        # Convert to RGB if necessary (for JPEG)
                        if img.mode != "RGB":
                            img = img.convert("RGB")
                        
                        # Validate image dimensions
                        if img.size[0] < 50 or img.size[1] < 50:
                            flash("Image too small. Please capture a clearer image.", "error")
                            messages = fetch_chat_messages(user_id)
                            return render_app_template("chat.html", messages=messages, analysis=None)
                        
                        filename = f"camera_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                        image_path = UPLOADS_DIR / filename
                        img.save(image_path, "JPEG", quality=85)
                        
                        # Analyze emotion with error handling
                        try:
                            insight = analyze_image_emotion(image_path)
                            # Validate insight
                            if not insight or insight.confidence < 0.1:
                                # Fallback to text analysis if image analysis fails
                                insight = analyze_emotion("Camera snapshot shared")
                        except Exception as analysis_err:
                            # Fallback to text analysis
                            insight = analyze_emotion("Camera snapshot shared")
                            try:
                                with open(BASE_DIR / "image_emotion.log", "a", encoding="utf-8") as f:
                                    f.write(json.dumps({"ts": datetime.utcnow().isoformat(), "analysis_error": str(analysis_err)}) + "\n")
                            except:
                                pass
                        
                        detection_source = "camera"
                        content_msg = "📷 Camera snapshot shared"
                    except Exception as img_err:
                        flash(f"Failed to process image: {str(img_err)}", "error")
                        messages = fetch_chat_messages(user_id)
                        return render_app_template("chat.html", messages=messages, analysis=None)
                except Exception as e:
                    import traceback
                    print(f"Camera image processing error: {e}")
                    print(traceback.format_exc())
                    flash(f"Could not process camera image: {str(e)}", "error")
                    messages = fetch_chat_messages(user_id)
                    return render_app_template("chat.html", messages=messages, analysis=analysis_display)
            
            # Handle file upload
            elif image_file and image_file.filename:
                try:
                    filename = secure_filename(f"{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{image_file.filename}")
                    image_path = UPLOADS_DIR / filename
                    image_file.save(image_path)
                    insight = analyze_image_emotion(image_path)
                    detection_source = "image"
                    content_msg = f"📎 Image uploaded: {image_file.filename}"
                except Exception as e:
                    flash("Could not process uploaded image.", "error")
                    messages = fetch_chat_messages(user_id)
                    return render_app_template("chat.html", messages=messages, analysis=analysis_display)
            
            # Handle text message
            elif user_message:
                insight = analyze_emotion(user_message)
                content_msg = user_message
            else:
                flash("Please share a message, image, or camera snapshot.", "error")
                messages = fetch_chat_messages(user_id)
                return render_app_template("chat.html", messages=messages, analysis=analysis_display)
            
            if insight:
                log_message(conversation_id, "user", content_msg, insight.emotion, insight.intensity, str(image_path) if image_path else None, detection_source)
                # Update chat streak
                update_streak(user_id, "chat")
                # Check for first chat achievement
                if not g.db.execute("SELECT id FROM achievements WHERE user_id = ? AND achievement_type = 'first_chat'", (user_id,)).fetchone():
                    check_achievements(user_id, "first_chat")
                # Provide recent conversation history to the reply generator for better context
                recent_history = fetch_messages_for_conversation(conversation_id, limit=10)
                user_name = session.get("user_name", "")
                # For image/camera events, give the reply generator a richer seed so Ollama can respond
                # meaningfully even without direct text from the user.
                seed_message = content_msg
                if detection_source in ("image", "camera"):
                    seed_message = (
                        f"{content_msg}\n\n"
                        f"(Context: user shared a {detection_source}. Detected facial emotion: {insight.emotion} "
                        f"at {insight.intensity}/5, confidence {insight.confidence:.2f}.)"
                    )
                reply = craft_reply(insight, seed_message, history=recent_history, user_name=user_name)
                log_message(conversation_id, "assistant", reply, insight.emotion, insight.intensity, None, detection_source)
                analysis_display = insight
                flash("Reflection saved.", "success")
                
                # Auto-save conversation to journal after meaningful exchange
                if len(fetch_messages_for_conversation(conversation_id)) >= 6:
                    auto_save_conversation_to_journal(user_id, conversation_id)
        
        messages = fetch_chat_messages(user_id)
        
        # Generate conversation insights (mind-blowing feature)
        conversation_insights = generate_conversation_insights(user_id, conversation_id)
        
        # Generate quick reply suggestions
        quick_replies = generate_quick_replies(user_id, messages)
        
        return render_app_template(
            "chat.html", 
            messages=messages, 
            analysis=analysis_display,
            conversation_insights=conversation_insights,
            quick_replies=quick_replies
        )

    @app.route("/uploads/<filename>")
    @login_required
    def serve_image(filename: str):
        """Serve uploaded images securely."""
        image_path = UPLOADS_DIR / secure_filename(filename)
        if image_path.exists() and image_path.is_file():
            return send_file(image_path, mimetype="image/jpeg")
        abort(404)

    @app.route("/chat/delete/<int:message_id>", methods=["POST"])
    @login_required
    def delete_message(message_id: int):
        """Delete a message and its associated image file."""
        user_id = session["user_id"]
        
        # Verify the message belongs to the user
        row = g.db.execute(
            """
            SELECT m.image_path, m.conversation_id
            FROM messages m
            JOIN conversations c ON c.id = m.conversation_id
            WHERE m.id = ? AND c.user_id = ?
            """,
            (message_id, user_id),
        ).fetchone()
        
        if not row:
            flash("Message not found or you don't have permission to delete it.", "error")
            return redirect(url_for("chat"))
        
        # Delete associated image file if it exists
        image_path = row["image_path"]
        if image_path:
            try:
                img_file = Path(image_path)
                if img_file.exists() and img_file.is_file():
                    img_file.unlink()
            except Exception as e:
                print(f"Error deleting image file: {e}")
        
        # Delete the message from database
        g.db.execute("DELETE FROM messages WHERE id = ?", (message_id,))
        g.db.commit()
        
        flash("Message deleted successfully.", "success")
        return redirect(url_for("chat"))

    @app.route("/history/delete/<int:message_id>", methods=["POST"])
    @login_required
    def delete_history_message(message_id: int):
        """Delete a message from history page."""
        user_id = session["user_id"]
        
        # Verify the message belongs to the user
        row = g.db.execute(
            """
            SELECT m.image_path, m.conversation_id
            FROM messages m
            JOIN conversations c ON c.id = m.conversation_id
            WHERE m.id = ? AND c.user_id = ?
            """,
            (message_id, user_id),
        ).fetchone()
        
        if not row:
            flash("Message not found or you don't have permission to delete it.", "error")
            return redirect(url_for("history"))
        
        # Delete associated image file if it exists
        image_path = row["image_path"]
        if image_path:
            try:
                img_file = Path(image_path)
                if img_file.exists() and img_file.is_file():
                    img_file.unlink()
            except Exception as e:
                print(f"Error deleting image file: {e}")
        
        # Delete the message from database
        g.db.execute("DELETE FROM messages WHERE id = ?", (message_id,))
        g.db.commit()
        
        flash("Message deleted successfully.", "success")
        return redirect(url_for("history"))

    @app.route("/chat/clear", methods=["POST"])
    @login_required
    def clear_all_chat():
        """Delete all conversations and messages for the user."""
        user_id = session["user_id"]
        
        # Get all image paths before deleting
        rows = g.db.execute(
            """
            SELECT m.image_path
            FROM messages m
            JOIN conversations c ON c.id = m.conversation_id
            WHERE c.user_id = ?
            """,
            (user_id,),
        ).fetchall()
        
        # Delete all image files
        for row in rows:
            image_path = row["image_path"]
            if image_path:
                try:
                    img_file = Path(image_path)
                    if img_file.exists() and img_file.is_file():
                        img_file.unlink()
                except Exception as e:
                    print(f"Error deleting image file: {e}")
        
        # Delete all messages and conversations
        g.db.execute(
            """
            DELETE FROM messages
            WHERE conversation_id IN (
                SELECT id FROM conversations WHERE user_id = ?
            )
            """,
            (user_id,),
        )
        g.db.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
        g.db.commit()
        
        flash("All conversations cleared successfully.", "success")
        return redirect(url_for("chat"))

    @app.route("/calendar")
    @login_required
    def calendar() -> str:
        """Mood calendar view."""
        user_id = session["user_id"]
        calendar_data = generate_mood_calendar(user_id)
        return render_app_template("calendar.html", calendar_data=calendar_data)

    @app.route("/games")
    @login_required
    def games() -> str:
        """Games area with emotion-themed puzzles."""
        user_id = session["user_id"]
        snapshot = latest_user_snapshot(user_id)
        current_emotion = normalize_emotion(snapshot.get("emotion", "Neutral"))
        return render_app_template("games.html", current_emotion=current_emotion)

    @app.route("/journal", methods=["GET", "POST"])
    @login_required
    def journal() -> str:
        """Journal entries for users."""
        user_id = session["user_id"]
        if request.method == "POST":
            action = request.form.get("action")
            if action == "create":
                title = request.form.get("title", "").strip()
                content = request.form.get("content", "").strip()
                emotion = request.form.get("emotion", "")
                mood_rating = request.form.get("mood_rating")
                if content:
                    g.db.execute(
                        "INSERT INTO journal_entries (user_id, title, content, emotion, mood_rating) VALUES (?, ?, ?, ?, ?)",
                        (user_id, title, content, emotion, int(mood_rating) if mood_rating else None)
                    )
                    g.db.commit()
                    update_streak(user_id, "journal")
                    check_achievements(user_id, "journal_entry")
                    flash("Journal entry saved!", "success")
            elif action == "delete":
                entry_id = request.form.get("entry_id")
                g.db.execute("DELETE FROM journal_entries WHERE id = ? AND user_id = ?", (entry_id, user_id))
                g.db.commit()
                flash("Entry deleted!", "success")
        
        entries = g.db.execute(
            "SELECT * FROM journal_entries WHERE user_id = ? ORDER BY created_at DESC LIMIT 50",
            (user_id,)
        ).fetchall()
        normalized_entries = []
        for row in entries:
            d = dict(row)
            d["emotion"] = normalize_emotion(d.get("emotion") or "Neutral")
            normalized_entries.append(d)
        return render_app_template("journal.html", entries=normalized_entries)

    @app.route("/goals", methods=["GET", "POST"])
    @login_required
    def goals() -> str:
        """Goals and achievements."""
        user_id = session["user_id"]
        if request.method == "POST":
            action = request.form.get("action")
            if action == "create":
                title = request.form.get("title", "").strip()
                description = request.form.get("description", "").strip()
                category = request.form.get("category", "")
                target_date = request.form.get("target_date")
                if title:
                    g.db.execute(
                        "INSERT INTO goals (user_id, title, description, category, target_date) VALUES (?, ?, ?, ?, ?)",
                        (user_id, title, description, category, target_date if target_date else None)
                    )
                    g.db.commit()
                    flash("Goal created!", "success")
            elif action == "complete":
                goal_id = request.form.get("goal_id")
                g.db.execute("UPDATE goals SET completed = 1 WHERE id = ? AND user_id = ?", (goal_id, user_id))
                g.db.commit()
                check_achievements(user_id, "goal_completed")
                flash("Goal completed! 🎉", "success")
            elif action == "delete":
                goal_id = request.form.get("goal_id")
                g.db.execute("DELETE FROM goals WHERE id = ? AND user_id = ?", (goal_id, user_id))
                g.db.commit()
                flash("Goal deleted!", "success")
        
        goals_list = g.db.execute(
            "SELECT * FROM goals WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        ).fetchall()
        achievements = g.db.execute(
            "SELECT * FROM achievements WHERE user_id = ? ORDER BY unlocked_at DESC",
            (user_id,)
        ).fetchall()
        streaks = get_user_streaks(user_id)
        return render_app_template(
            "goals.html",
            goals=[dict(row) for row in goals_list],
            achievements=[dict(row) for row in achievements],
            streaks=streaks
        )

    @app.route("/breathing", methods=["GET", "POST"])
    @login_required
    def breathing() -> str:
        """Breathing exercises and meditation."""
        user_id = session["user_id"]
        if request.method == "POST":
            duration = int(request.form.get("duration", 60))
            exercise_type = request.form.get("type", "box")
            # Log breathing session
            update_streak(user_id, "breathing")
            flash("Great job! Keep up the mindfulness practice.", "success")
        return render_app_template("breathing.html")

    @app.route("/music", methods=["GET", "POST"])
    @login_required
    def music() -> str:
        """Music recommendations based on mood."""
        user_id = session["user_id"]
        snapshot = latest_user_snapshot(user_id)
        current_emotion = normalize_emotion(snapshot.get("emotion", "Neutral"))
        
        music_library = {
            "Happiness": [
                {"name": "Happy", "artist": "Pharrell Williams", "platform": "Spotify/YouTube"},
                {"name": "Can't Stop the Feeling", "artist": "Justin Timberlake", "platform": "Spotify/YouTube"},
                {"name": "Walking on Sunshine", "artist": "Katrina & The Waves", "platform": "Spotify/YouTube"},
            ],
            "Neutral": [
                {"name": "Weightless", "artist": "Marconi Union", "platform": "Spotify/YouTube"},
                {"name": "Strawberry Swing", "artist": "Coldplay", "platform": "Spotify/YouTube"},
                {"name": "Watermark", "artist": "Enya", "platform": "Spotify/YouTube"},
            ],
            "Stress": [
                {"name": "Gymnopédie No. 1", "artist": "Erik Satie", "platform": "Spotify/YouTube"},
                {"name": "Clair de Lune", "artist": "Claude Debussy", "platform": "Spotify/YouTube"},
                {"name": "The Sound of Silence", "artist": "Simon & Garfunkel", "platform": "Spotify/YouTube"},
                {"name": "Weightless", "artist": "Marconi Union", "platform": "Spotify/YouTube"},
                {"name": "Let It Be", "artist": "The Beatles", "platform": "Spotify/YouTube"},
            ],
            "Sadness": [
                {"name": "Fix You", "artist": "Coldplay", "platform": "Spotify/YouTube"},
                {"name": "Bridge Over Troubled Water", "artist": "Simon & Garfunkel", "platform": "Spotify/YouTube"},
                {"name": "Lean on Me", "artist": "Bill Withers", "platform": "Spotify/YouTube"},
                {"name": "Don't Worry Be Happy", "artist": "Bobby McFerrin", "platform": "Spotify/YouTube"},
                {"name": "Three Little Birds", "artist": "Bob Marley", "platform": "Spotify/YouTube"},
            ],
        }
        
        # Fallback to Neutral playlist if current_emotion key is missing (e.g., legacy data)
        recommendations = music_library.get(current_emotion, music_library["Neutral"])
        return render_app_template("music.html", recommendations=recommendations, current_emotion=current_emotion)

    @app.route("/logout")
    def logout() -> str:
        session.clear()
        flash("See you soon!", "info")
        return redirect(url_for("login"))

    return app


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                dominant_emotion TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                author TEXT NOT NULL,
                content TEXT NOT NULL,
                emotion TEXT,
                intensity INTEGER,
                image_path TEXT,
                detection_source TEXT DEFAULT 'text',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(conversation_id) REFERENCES conversations(id)
            );

            CREATE TABLE IF NOT EXISTS journal_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT,
                content TEXT NOT NULL,
                emotion TEXT,
                mood_rating INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                category TEXT,
                target_date DATE,
                completed BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                achievement_type TEXT NOT NULL,
                achievement_name TEXT NOT NULL,
                unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS streaks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                streak_type TEXT NOT NULL,
                current_streak INTEGER DEFAULT 0,
                longest_streak INTEGER DEFAULT 0,
                last_activity_date DATE,
                FOREIGN KEY(user_id) REFERENCES users(id),
                UNIQUE(user_id, streak_type)
            );

            CREATE TABLE IF NOT EXISTS music_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                emotion TEXT NOT NULL,
                track_name TEXT NOT NULL,
                artist TEXT,
                platform TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                daily_checkin_reminders BOOLEAN DEFAULT 1,
                goal_reminders BOOLEAN DEFAULT 1,
                weekly_report_emails BOOLEAN DEFAULT 0,
                theme TEXT DEFAULT 'Auto',
                language TEXT DEFAULT 'English',
                default_report_template TEXT DEFAULT 'classic',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            """
        )
        conn.commit()
        
        # Migrate existing tables to add new columns if they don't exist
        migrate_db(conn)


def migrate_db(conn: sqlite3.Connection) -> None:
    """Add new columns to existing tables if they don't exist."""
    cursor = conn.cursor()
    
    # Check if image_path column exists in messages table
    try:
        cursor.execute("SELECT image_path FROM messages LIMIT 1")
    except sqlite3.OperationalError:
        # Column doesn't exist, add it
        try:
            cursor.execute("ALTER TABLE messages ADD COLUMN image_path TEXT")
        except sqlite3.OperationalError:
            pass  # Column might already exist
    
    # Check if detection_source column exists in messages table
    try:
        cursor.execute("SELECT detection_source FROM messages LIMIT 1")
    except sqlite3.OperationalError:
        # Column doesn't exist, add it
        try:
            cursor.execute("ALTER TABLE messages ADD COLUMN detection_source TEXT DEFAULT 'text'")
        except sqlite3.OperationalError:
            pass  # Column might already exist
    
    # Create user_preferences table if it doesn't exist
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                daily_checkin_reminders BOOLEAN DEFAULT 1,
                goal_reminders BOOLEAN DEFAULT 1,
                weekly_report_emails BOOLEAN DEFAULT 0,
                theme TEXT DEFAULT 'Auto',
                language TEXT DEFAULT 'English',
                default_report_template TEXT DEFAULT 'classic',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
    except sqlite3.OperationalError:
        pass  # Table might already exist
    
    conn.commit()


def query_user(email: str) -> sqlite3.Row | None:
    cursor = g.db.execute("SELECT * FROM users WHERE email = ?", (email,))
    return cursor.fetchone()


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
