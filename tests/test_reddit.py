from app.services import reddit


class FakeResp:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def test_fetch_posts_parses_reddit_json(monkeypatch):
    payload = {
        "data": {
            "children": [
                {
                    "data": {
                        "title": "What does 'hit the sack' mean?",
                        "selftext": "I heard this phrase.",
                        "permalink": "/r/EnglishLearning/comments/abc/x/",
                        "subreddit": "EnglishLearning",
                        "score": 100,
                    }
                }
            ]
        }
    }

    def fake_fetch(url, timeout, user_agent):
        return FakeResp(200, payload)

    monkeypatch.setattr(reddit, "fetch", fake_fetch)

    posts = reddit.fetch_posts()
    assert len(posts) == 1
    assert posts[0]["title"] == "What does 'hit the sack' mean?"
    assert posts[0]["url"].startswith("https://www.reddit.com")


def test_fetch_posts_all_errors(monkeypatch):
    def fake_fetch(url, timeout, user_agent):
        raise RuntimeError("network down")

    monkeypatch.setattr(reddit, "fetch", fake_fetch)

    try:
        reddit.fetch_posts()
        assert False, "should raise"
    except RuntimeError as e:
        assert "Reddit" in str(e)
