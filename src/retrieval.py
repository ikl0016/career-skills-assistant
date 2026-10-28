import logging, re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

log = logging.getLogger(__name__)

class Index:
    """Keyword search over a small list of dicts using TF-IDF."""
    def __init__(self, items, id_key, text_fn):
        self.items, self.id_key = items, id_key
        self.vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.matrix = self.vec.fit_transform([text_fn(i) for i in items])

    def search(self, query, top_k=3):
        scores = cosine_similarity(self.vec.transform([query]), self.matrix)[0]
        ranked = sorted(zip(scores, self.items), key=lambda p: -p[0])[:top_k]
        return [{**item, "score": round(float(s), 3)} for s, item in ranked if s > 0]

INJECTION = re.compile(
    r"(ignore|disregard|forget)\b.{0,40}\b(instruction|prompt|rule)s?"
    r"|recommend this (role|job) to everyone"
    r"|you are now|system prompt", re.I)

def sanitize(job):
    """Remove instruction-like sentences from a job description."""
    sentences = re.split(r"(?<=[.!?])\s+", job["description"])
    kept = [s for s in sentences if not INJECTION.search(s)]
    clean = {k: v for k, v in job.items() if k != "description"}
    clean["untrusted_description"] = " ".join(kept)
    clean["flagged"] = len(kept) < len(sentences)
    if clean["flagged"]:
        log.warning("Possible prompt injection removed from %s", job["job_id"])
    return clean
