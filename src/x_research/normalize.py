from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .models import NormalizedTweet


def _string(value: Any) -> str | None:
    return None if value is None else str(value)


def _datetime_string(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _user_fields(user: Any) -> tuple[str | None, str | None, str | None]:
    if user is None:
        return None, None, None
    return (
        _string(getattr(user, "id_str", getattr(user, "id", None))),
        getattr(user, "username", None),
        getattr(user, "displayname", None),
    )


def normalize_tweet(tweet: Any, captured_at: datetime | None = None) -> NormalizedTweet:
    capture_time = captured_at or datetime.now(UTC)
    author_id, author_username, author_name = _user_fields(getattr(tweet, "user", None))

    reply_user_id, reply_username, _ = _user_fields(getattr(tweet, "inReplyToUser", None))

    quoted = getattr(tweet, "quotedTweet", None)
    quoted_user_id, quoted_username, _ = _user_fields(
        getattr(quoted, "user", None) if quoted is not None else None
    )

    retweeted = getattr(tweet, "retweetedTweet", None)
    retweeted_user_id, retweeted_username, _ = _user_fields(
        getattr(retweeted, "user", None) if retweeted is not None else None
    )

    hashtags = tuple(str(tag) for tag in (getattr(tweet, "hashtags", None) or []))

    return NormalizedTweet(
        tweet_id=_string(getattr(tweet, "id_str", getattr(tweet, "id", None))) or "",
        created_at=_datetime_string(getattr(tweet, "date", None)),
        text=getattr(tweet, "rawContent", "") or "",
        language=getattr(tweet, "lang", None),
        url=getattr(tweet, "url", None),
        author_id=author_id,
        author_username=author_username,
        author_display_name=author_name,
        like_count=getattr(tweet, "likeCount", None),
        retweet_count=getattr(tweet, "retweetCount", None),
        reply_count=getattr(tweet, "replyCount", None),
        quote_count=getattr(tweet, "quoteCount", None),
        view_count=getattr(tweet, "viewCount", None),
        conversation_id=_string(
            getattr(tweet, "conversationIdStr", getattr(tweet, "conversationId", None))
        ),
        reply_to_tweet_id=_string(
            getattr(tweet, "inReplyToTweetIdStr", getattr(tweet, "inReplyToTweetId", None))
        ),
        reply_to_user_id=reply_user_id,
        reply_to_username=reply_username or getattr(tweet, "inReplyToScreenName", None),
        quoted_tweet_id=_string(
            getattr(quoted, "id_str", getattr(quoted, "id", None)) if quoted is not None else None
        ),
        quoted_user_id=quoted_user_id,
        quoted_username=quoted_username,
        retweeted_tweet_id=_string(
            getattr(retweeted, "id_str", getattr(retweeted, "id", None))
            if retweeted is not None
            else None
        ),
        retweeted_user_id=retweeted_user_id,
        retweeted_username=retweeted_username,
        hashtags=hashtags,
        captured_at=capture_time.isoformat(),
    )
