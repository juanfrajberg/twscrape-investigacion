from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class NormalizedTweet:
    tweet_id: str
    created_at: str | None
    text: str
    language: str | None
    url: str | None

    author_id: str | None
    author_username: str | None
    author_display_name: str | None

    like_count: int | None
    retweet_count: int | None
    reply_count: int | None
    quote_count: int | None
    view_count: int | None

    conversation_id: str | None
    reply_to_tweet_id: str | None
    reply_to_user_id: str | None
    reply_to_username: str | None
    quoted_tweet_id: str | None
    quoted_user_id: str | None
    quoted_username: str | None
    retweeted_tweet_id: str | None
    retweeted_user_id: str | None
    retweeted_username: str | None

    hashtags: tuple[str, ...]
    captured_at: str
    source_provider: str = "twscrape"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["hashtags"] = list(self.hashtags)
        return data
