"""Learning Activities for Dutch Trainer"""

from app.activities.base import AbstractActivity
from app.activities.word_activity import WordActivity
from app.activities.sentence_activity import SentenceActivity
from app.activities.verb_tense import VerbTenseActivity
from app.activities.preposition_activity import PrepositionActivity

__all__ = [
    "AbstractActivity",
    "WordActivity",
    "SentenceActivity",
    "VerbTenseActivity",
    "PrepositionActivity",
]
