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


def test_fetch_posts_oauth(monkeypatch):
    monkeypatch.setattr(reddit, "_creds", lambda: ("cid", "secret", "user", "pass"))
    monkeypatch.setattr(reddit, "_get_token", lambda creds: "tok")

    class FakeResp:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {
                "data": {
                    "children": [
                        {
                            "data": {
                                "title": "OAuth hot post",
                                "permalink": "/r/AskReddit/1/x",
                                "subreddit": "AskReddit",
                                "score": 5,
                            }
                        }
                    ]
                }
            }

    monkeypatch.setattr(reddit.requests, "get", lambda *a, **k: FakeResp())

    posts = reddit.fetch_posts()
    assert posts and posts[0]["title"] == "OAuth hot post"
