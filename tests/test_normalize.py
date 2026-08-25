from datetime import UTC, datetime
from types import SimpleNamespace as Object

from x_research.normalize import normalize_tweet


def user(user_id: str, username: str):
    return Object(
        id_str=user_id,
        username=username,
        displayname=username.title(),
    )


def test_normalizes_reply_quote_and_retweet_fields():
    quoted = Object(id_str="300", user=user("30", "citada"))
    retweeted = Object(id_str="400", user=user("40", "original"))
    tweet = Object(
        id_str="200",
        date=datetime(2026, 7, 19, 18, 30, tzinfo=UTC),
        user=user("20", "autora"),
        lang="es",
        rawContent="Texto de prueba",
        replyCount=3,
        retweetCount=4,
        likeCount=5,
        quoteCount=6,
        viewCount=7,
        conversationIdStr="100",
        inReplyToTweetIdStr="100",
        inReplyToUser=user("10", "raiz"),
        inReplyToScreenName="raiz",
        quotedTweet=quoted,
        retweetedTweet=retweeted,
        hashtags=["Argentina", "Mundial2026"],
        url="https://x.com/autora/status/200",
    )

    result = normalize_tweet(tweet, captured_at=datetime(2026, 8, 23, tzinfo=UTC))

    assert result.tweet_id == "200"
    assert result.author_username == "autora"
    assert result.reply_to_tweet_id == "100"
    assert result.reply_to_username == "raiz"
    assert result.quoted_tweet_id == "300"
    assert result.quoted_username == "citada"
    assert result.retweeted_tweet_id == "400"
    assert result.hashtags == ("Argentina", "Mundial2026")
