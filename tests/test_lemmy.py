from app.services import lemmy


class FakeResp:
    status_code = 200

    def json(self):
        return {
            "posts": [
                {
                    "post": {
                        "id": 42,
                        "name": "What does 'no cap' mean?",
                        "body": "I keep hearing this phrase.",
                    },
                    "community": {"name": "asklemmy", "title": "Ask Lemmy"},
                    "counts": {"score": 88},
                }
            ]
        }


def test_fetch_posts_parses_lemmy_json(monkeypatch):
    monkeypatch.setattr(lemmy, "fetch", lambda url, timeout, user_agent: FakeResp())

    posts = lemmy.fetch_posts()
    assert len(posts) == 1
    assert posts[0]["title"] == "What does 'no cap' mean?"
    assert posts[0]["url"] == "https://lemmy.world/post/42"
    assert posts[0]["score"] == 88


def test_fetch_posts_all_errors(monkeypatch):
    def fake_fetch(url, timeout, user_agent):
        raise RuntimeError("down")

    monkeypatch.setattr(lemmy, "fetch", fake_fetch)

    try:
        lemmy.fetch_posts()
        assert False, "should raise"
    except RuntimeError as e:
        assert "Lemmy" in str(e)
