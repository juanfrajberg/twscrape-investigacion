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


def _media_entries(tweet: Any) -> tuple[dict[str, Any], ...]:
    media = getattr(tweet, "media", None)
    if media is None:
        return ()

    entries: list[dict[str, Any]] = []
    for photo in getattr(media, "photos", None) or []:
        entries.append({"type": "photo", "url": getattr(photo, "url", None)})
    for video in getattr(media, "videos", None) or []:
        variants = getattr(video, "variants", None) or []
        best_variant = max(
            variants,
            key=lambda item: getattr(item, "bitrate", 0) or 0,
            default=None,
        )
        entries.append(
            {
                "type": "video",
                "thumbnail_url": getattr(video, "thumbnailUrl", None),
                "url": getattr(best_variant, "url", None),
                "duration_ms": getattr(video, "duration", None),
                "views": getattr(video, "views", None),
            }
        )
    for animated in getattr(media, "animated", None) or []:
        entries.append(
            {
                "type": "animated_gif",
                "thumbnail_url": getattr(animated, "thumbnailUrl", None),
                "url": getattr(animated, "videoUrl", None),
            }
        )
    return tuple(entries)


def normalize_tweet(tweet: Any, captured_at: datetime | None = None) -> NormalizedTweet:
    capture_time = captured_at or datetime.now(UTC)
    author = getattr(tweet, "user", None)
    author_id, author_username, author_name = _user_fields(author)

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
    cashtags = tuple(str(tag) for tag in (getattr(tweet, "cashtags", None) or []))
    mentioned_users = getattr(tweet, "mentionedUsers", None) or []
    mentioned_user_ids = tuple(
        value
        for user in mentioned_users
        if (value := _string(getattr(user, "id_str", getattr(user, "id", None))))
    )
    mentioned_usernames = tuple(
        str(username)
        for user in mentioned_users
        if (username := getattr(user, "username", None))
    )
    links = tuple(
        str(url)
        for link in (getattr(tweet, "links", None) or [])
        if (url := getattr(link, "url", None))
    )
    place = getattr(tweet, "place", None)
    coordinates = getattr(tweet, "coordinates", None)

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
        author_description=getattr(author, "rawDescription", None),
        author_created_at=_datetime_string(getattr(author, "created", None)),
        author_location=getattr(author, "location", None),
        author_followers_count=getattr(author, "followersCount", None),
        author_following_count=getattr(author, "friendsCount", None),
        author_statuses_count=getattr(author, "statusesCount", None),
        author_favourites_count=getattr(author, "favouritesCount", None),
        author_listed_count=getattr(author, "listedCount", None),
        author_media_count=getattr(author, "mediaCount", None),
        author_protected=getattr(author, "protected", None),
        author_verified=getattr(author, "verified", None),
        author_blue=getattr(author, "blue", None),
        author_blue_type=getattr(author, "blueType", None),
        author_profile_image_url=getattr(author, "profileImageUrl", None),
        cashtags=cashtags,
        mentioned_user_ids=mentioned_user_ids,
        mentioned_usernames=mentioned_usernames,
        links=links,
        media=_media_entries(tweet),
        source_label=getattr(tweet, "sourceLabel", None),
        possibly_sensitive=getattr(tweet, "possibly_sensitive", None),
        place_full_name=getattr(place, "fullName", None),
        place_country=getattr(place, "country", None),
        place_country_code=getattr(place, "countryCode", None),
        longitude=getattr(coordinates, "longitude", None),
        latitude=getattr(coordinates, "latitude", None),
    )
