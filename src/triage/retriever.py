"""TF-IDF retrieval over local markdown runbooks (the 'RAG' retrieval step)."""
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DEFAULT_DIR = Path(__file__).resolve().parents[2] / "runbooks"


class RunbookRetriever:
    def __init__(self, directory: Path = DEFAULT_DIR) -> None:
        self.names: list[str] = []
        self.texts: list[str] = []
        for p in sorted(Path(directory).glob("*.md")):
            self.names.append(p.stem)
            self.texts.append(p.read_text(encoding="utf-8"))
        if not self.texts:
            raise ValueError(f"No runbooks found in {directory}")
        self.vec = TfidfVectorizer(stop_words="english")
        self.matrix = self.vec.fit_transform(self.texts)

    def search(self, query: str, k: int = 1) -> list[tuple[str, float, str]]:
        sims = cosine_similarity(self.vec.transform([query]), self.matrix)[0]
        order = sims.argsort()[::-1][:k]
        return [(self.names[i], float(sims[i]), self.texts[i]) for i in order]
