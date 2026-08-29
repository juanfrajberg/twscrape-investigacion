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

    author_description: str | None = None
    author_created_at: str | None = None
    author_location: str | None = None
    author_followers_count: int | None = None
    author_following_count: int | None = None
    author_statuses_count: int | None = None
    author_favourites_count: int | None = None
    author_listed_count: int | None = None
    author_media_count: int | None = None
    author_protected: bool | None = None
    author_verified: bool | None = None
    author_blue: bool | None = None
    author_blue_type: str | None = None
    author_profile_image_url: str | None = None

    cashtags: tuple[str, ...] = ()
    mentioned_user_ids: tuple[str, ...] = ()
    mentioned_usernames: tuple[str, ...] = ()
    links: tuple[str, ...] = ()
    media: tuple[dict[str, Any], ...] = ()
    source_label: str | None = None
    possibly_sensitive: bool | None = None
    place_full_name: str | None = None
    place_country: str | None = None
    place_country_code: str | None = None
    longitude: float | None = None
    latitude: float | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        for field_name in (
            "hashtags",
            "cashtags",
            "mentioned_user_ids",
            "mentioned_usernames",
            "links",
            "media",
        ):
            data[field_name] = list(data[field_name])
        return data
