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
