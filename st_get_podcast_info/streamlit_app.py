import datetime
import re

from dateutil.parser import parse
import feedparser
import streamlit as st


def duration_to_seconds(duration):
    time_data = [int(x) for x in duration.split(":")]
    if len(time_data) == 3:
        return time_data[2] + time_data[1] * 60 + time_data[0] * 3600
    elif len(time_data) == 2:
        return time_data[1] + time_data[0] * 60
    else:
        raise ValueError("durationのフォーマットが不正です")


def get_podcast_duration(d, from_date, to_date):
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

    return f"{hour:02d}:{min:02d}:{sec:02d} (全{topic_num}話)"


def grep_and_get_title(idx, entry, keyword):
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


def grep_and_get_info(idx, entry, keyword):
    if not keyword:
        return ""

    the_date = parse(entry.published).strftime("%Y-%m-%d")
    podcast_info = f"{idx}: {the_date} {entry.title}"

    detail = ""
    if keyword in podcast_info or (
        hasattr(entry, "content") and keyword in entry.content[0].value
    ):
        detail = re.sub("<.*?>", "", entry.content[0].value)
    elif keyword in podcast_info or (
        hasattr(entry, "description") and keyword in entry.description
    ):
        detail = re.sub("<.*?>", "", entry.description)

    return detail


def get_audiofile(entry):
    # 音声ファイルへのリンクを取得
    for link in entry.links:
        if link.rel == "enclosure":
            return link.href, link.type


RSS_URL = {
    "ゆとりっ娘たちのたわごと": "https://anchor.fm/s/6e491dbc/podcast/rss",
    "ドングリFM": "https://anchor.fm/s/76a89c80/podcast/rss",
    "上京ボーイズ": "https://anchor.fm/s/11f7ff38/podcast/rss",
    "忘れてみたい夜だから": "https://radiotalk.jp/rss/3710302b24c7e88c",
    "まめまめキャスト": "https://anchor.fm/s/8bec512c/podcast/rss",
    "rebuild.fm": "https://feeds.rebuild.fm/rebuildfm",
}

st.title("PodcastのRSSをごにょごにょ")  # ② タイトル表示

podcast = st.selectbox("Podcastを選択", RSS_URL.keys())
st.write(RSS_URL[podcast])

process = st.radio("処理を選択", ["キーワード検索", "日付を指定して時間計算"])

d = feedparser.parse(RSS_URL[podcast])
if process == "日付を指定して時間計算":
    from_date = st.date_input("この日から")
    to_date = st.date_input("この日まで")
    st.header(get_podcast_duration(d, from_date, to_date))
else:
    keyword = st.text_input("キーワードをどうぞ")
    detail = st.toggle("詳細表示")

    for idx, entry in enumerate(reversed(d.entries), 1):
        title = grep_and_get_title(idx, entry, keyword)
        if title:
            if detail:
                st.markdown(f"##### {title}")
                st.write(
                    grep_and_get_info(idx, entry, keyword),
                    unsafe_allow_html=True,
                )
                link, type = get_audiofile(entry)
                st.audio(link, format=type)
                st.divider()
            else:
                st.markdown(f"##### {title}")
                link, type = get_audiofile(entry)
                st.audio(link, format=type)
                st.divider()
