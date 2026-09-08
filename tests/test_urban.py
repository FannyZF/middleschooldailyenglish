from app.services import urban


class FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_fetch_entries_parses_ud(monkeypatch):
    payload = {
        "list": [
            {
                "word": "hit the sack",
                "definition": "to go to bed",
                "example": "I'm tired, time to hit the sack.",
                "permalink": "https://hit.urbanup.com/1",
                "thumbs_up": 42,
            }
        ]
    }

    def fake_fetch(url, timeout, user_agent):
        return FakeResp(payload)

    monkeypatch.setattr(urban, "fetch", fake_fetch)

    entries = urban.fetch_entries(limit=2)
    assert len(entries) >= 1
    assert entries[0]["title"] == "hit the sack"
    assert entries[0]["subreddit"] == "Urban Dictionary"


def test_autocomplete_parses_terms(monkeypatch):
    payload = {"result": [{"term": "lowkey"}, {"term": "low key"}, {"term": "***x!!"}]}

    def fake_fetch(url, timeout, user_agent):
        return FakeResp(payload)

    monkeypatch.setattr(urban, "fetch", fake_fetch)

    terms = urban._autocomplete_terms("lo", max_out=10)
    assert terms == ["lowkey", "low key"]  # 乱码被过滤
    assert all(urban._WORDY.match(t) for t in terms)


def test_curated_wordlist_is_large_and_unique():
    words = [s.strip().lower() for s in urban.COMMON_SLANG if s.strip()]
    assert len(words) >= 500
    assert len(set(words)) >= 500
