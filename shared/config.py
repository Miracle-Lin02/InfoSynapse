# -*- coding: utf-8 -*-
"""
Shared configuration constants for InfoSynapse application.
"""

# Data file paths
KB_PATH = "data/hdu_knowledge_base.json"
USER_PROFILE_PATH = "data/user_profiles.json"
CAREER_FEEDBACK_PATH = "data/career_feedback.json"

# Default scoring weights for recommendations
DEFAULT_WEIGHTS = {
    "INTEREST_NAME_WEIGHT": 30.0,
    "INTEREST_DESC_WEIGHT": 18.0,
    "TAG_MATCH_WEIGHT": 12.0,
    "KB_BASE_SCORE": 6.0,
    "SOURCE_GITHUB_BONUS": 5.0,
    "SOURCE_KB_BONUS": 2.0,
    "GITHUB_STAR_WEIGHT_FACTOR": 6.0,
    "GITHUB_STAR_MAX_BONUS": 40.0,
    "RANDOM_TIE_BREAKER": 1.5,
}

# Application configuration
CONFIG = {
    "RECOMMEND_MAX_ITEMS": 12,
    "GITHUB_FETCH_PER_TOPIC": 30,
    "GITHUB_PICK_TOTAL": 8,
}
CONFIG.update(DEFAULT_WEIGHTS)
