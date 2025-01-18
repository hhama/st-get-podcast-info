import datetime
import re

from dateutil.parser import parse
import feedparser
import streamlit as st

from podcast_dict import RSS_URL


def duration_to_seconds(duration: str) -> int:
    time_data = [int(x) for x in duration.split(":")]
    if len(time_data) == 3:
        return time_data[2] + time_data[1] * 60 + time_data[0] * 3600
    elif len(time_data) == 2:
        return time_data[1] + time_data[0] * 60
    else:
        raise ValueError("durationのフォーマットが不正です")


def get_date_from_entry(entry: feedparser.util.FeedParserDict) -> datetime.datetime:
    return parse(entry.published).date()


def get_podcast_duration(
    d: feedparser.util.FeedParserDict,
    from_date: datetime.datetime,
    to_date: datetime.datetime,
) -> tuple[str, str]:
    tz_jst = datetime.timezone(datetime.timedelta(hours=9))

    from_datetime = datetime.datetime.combine(
        from_date, datetime.time(0, 0, 0, 0)
    ).replace(tzinfo=tz_jst)
    to_datetime = datetime.datetime.combine(
        to_date, datetime.time(23, 59, 59, 0)
    ).replace(tzinfo=tz_jst)

    all_seconds = 0
    topic_num = 0
    for entry in reversed(d.entries):
        the_date = parse(entry.published)
        if from_datetime <= the_date <= to_datetime:
            all_seconds += duration_to_seconds(entry.itunes_duration)
            topic_num += 1

    hour, mod_sec = divmod(all_seconds, 3600)
    min, sec = divmod(mod_sec, 60)

    all_secondsx1_25 = int(all_seconds / 1.3)
    hour2, mod_sec2 = divmod(all_secondsx1_25, 3600)
    min2, sec2 = divmod(mod_sec2, 60)

    return (
        f"{hour:02d}:{min:02d}:{sec:02d} (全{topic_num}話)",
        f"{hour2:02d}:{min2:02d}:{sec2:02d}",
    )


def grep_and_get_title(
    idx: int, entry: feedparser.util.FeedParserDict, keyword: str
) -> str:
    if not keyword:
        return ""

    the_date = parse(entry.published).strftime("%Y-%m-%d")
    podcast_info = f"{idx}: {the_date} {entry.title}"

    if (
        keyword in podcast_info
        or (hasattr(entry, "content") and keyword in entry.content[0].value)
        or (hasattr(entry, "description") and keyword in entry.description)
    ):
        return podcast_info

    return ""


def get_title(idx: int, entry: feedparser.util.FeedParserDict) -> str:
    the_date = parse(entry.published).strftime("%Y-%m-%d")
    return f"{idx}: {the_date} {entry.title}"


def get_info(entry: feedparser.util.FeedParserDict) -> str:
    detail = ""
    if hasattr(entry, "content"):
        detail = re.sub("<.*?>", "", entry.content[0].value)
        detail = re.sub("-{3,}", "", detail)
    elif hasattr(entry, "description"):
        detail = re.sub("<.*?>", "", entry.description)
        detail = re.sub("-{3,}", "", detail)

    return detail


def get_audiofile(
    entry: feedparser.util.FeedParserDict,
) -> tuple[str, str] | tuple[None, None]:
    # 音声ファイルへのリンクを取得
    for link in entry.links:
        if link.rel == "enclosure":
            return link.href, link.type
    return None, None


def get_thumbnail(entry: feedparser.util.FeedParserDict, default_image: str) -> str:
    if hasattr(entry, "image"):
        return entry.image["href"]
    elif hasattr(entry, "media_thumbnail"):
        return entry.media_thumbnail[0]["url"]

    return default_image


def output_column(
    title: str,
    entry: feedparser.util.FeedParserDict,
    default_image: str,
    detail: bool = False,
) -> None:
    col1, col2 = st.columns([2, 8])
    thumbnail = get_thumbnail(entry, default_image)
    col1.image(thumbnail)
    col2.markdown(f"##### {title}")
    link, type = get_audiofile(entry)
    if detail:
        print(get_info(entry))
        col2.write(get_info(entry), unsafe_allow_html=True)
        st.audio(link, format=type)  # type: ignore
    else:
        col2.audio(link, format=type)  # type: ignore
    st.divider()


def main() -> None:
    st.title("PodcastのRSSをごにょごにょ")

    podcast = st.selectbox("Podcastを選択", RSS_URL.keys())
    st.write(RSS_URL[podcast])

    process = st.radio("処理を選択", ["一覧", "キーワード検索"])

    d = feedparser.parse(RSS_URL[podcast])
    default_image = d.feed.image["href"]

    if process == "一覧":
        default_start_entry = get_date_from_entry(d.entries[9])
        default_end_entry = get_date_from_entry(d.entries[0])

        col1, col2 = st.columns([5, 5])
        from_date = col1.date_input(
            "この日から",
            value=default_start_entry,
        )
        to_date = col2.date_input("この日まで", value=default_end_entry)

        time_sum, time_sum_x13 = get_podcast_duration(d, from_date, to_date)  # type: ignore
        st.write(
            f'<div style="font-weight:bold;text-align:right;margin-bottom:1rem;">合計時間: {time_sum} (1.3倍速: {time_sum_x13})</div>',
            unsafe_allow_html=True,
        )

        latest_episode = len(d.entries)
        for idx, entry in enumerate(d.entries):
            entry_published = get_date_from_entry(entry)
            if from_date <= entry_published <= to_date:
                title = get_title(latest_episode - idx, entry)
                output_column(title, entry, default_image)

    else:
        keyword = st.text_input("キーワードをどうぞ")
        detail = st.toggle("詳細表示")

        idx = len(d.entries)
        for entry in d.entries:
            title = grep_and_get_title(idx, entry, keyword)
            idx -= 1
            if title:
                output_column(title, entry, default_image, detail=detail)


if __name__ == "__main__":
    main()
