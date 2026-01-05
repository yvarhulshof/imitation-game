"""Configuration settings for the backend."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (parent of backend/)
project_root = Path(__file__).parent.parent.parent
load_dotenv(project_root / ".env")

# LLM Configuration - accept either GEMINI_API_KEY or GOOGLE_API_KEY
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.0-flash")
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "10"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "2"))

# AI Behavior Configuration
CHAT_POLL_INTERVAL = float(os.getenv("CHAT_POLL_INTERVAL", "5"))
MAX_NOTES_TOKENS = int(os.getenv("MAX_NOTES_TOKENS", "2000"))
AI_CHAT_STAGGER_MIN = float(os.getenv("AI_CHAT_STAGGER_MIN", "0.5"))
AI_CHAT_STAGGER_MAX = float(os.getenv("AI_CHAT_STAGGER_MAX", "1.0"))

# Notes Storage
NOTES_STORAGE_DIR = os.getenv("NOTES_STORAGE_DIR", "data/ai_notes")
