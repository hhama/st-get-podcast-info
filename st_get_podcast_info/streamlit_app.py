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

    all_secondsx1_25 = int(all_seconds * 4 / 5)
    hour2, mod_sec2 = divmod(all_secondsx1_25, 3600)
    min2, sec2 = divmod(mod_sec2, 60)

    return (
        f"{hour:02d}:{min:02d}:{sec:02d} (全{topic_num}話)",
        f"{hour2:02d}:{min2:02d}:{sec2:02d}",
    )


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


def get_title(idx, entry):
    the_date = parse(entry.published).strftime("%Y-%m-%d")
    return f"{idx}: {the_date} {entry.title}"


def get_info(entry):
    detail = ""
    if hasattr(entry, "content"):
        detail = re.sub("<.*?>", "", entry.content[0].value)
        detail = re.sub("-{4,}", "", detail)
    elif hasattr(entry, "description"):
        detail = re.sub("<.*?>", "", entry.description)
        detail = re.sub("-{4,}", "", detail)

    return detail


def get_audiofile(entry):
    # 音声ファイルへのリンクを取得
    for link in entry.links:
        if link.rel == "enclosure":
            return link.href, link.type


def file_output(text):
    with open("./temp.txt", "wt") as fout:
        fout.write(text)


RSS_URL = {
    "ゆとりっ娘たちのたわごと": "https://anchor.fm/s/6e491dbc/podcast/rss",
    "ドングリFM": "https://anchor.fm/s/76a89c80/podcast/rss",
    "上京ボーイズ": "https://anchor.fm/s/11f7ff38/podcast/rss",
    "忘れてみたい夜だから": "https://radiotalk.jp/rss/3710302b24c7e88c",
    "まめまめキャスト": "https://anchor.fm/s/8bec512c/podcast/rss",
    "Rebuild": "https://feeds.rebuild.fm/rebuildfm",
    "でこぽんFM": "https://anchor.fm/s/8f913194/podcast/rss",
    "Ossan.fm": "https://ossan.fm/feed.xml",
    "いなみまも": "https://anchor.fm/s/3af273dc/podcast/rss",
    "Sounds by monolith": "https://anchor.fm/s/1b32dd5c/podcast/rss",
}

st.title("PodcastのRSSをごにょごにょ")  # ② タイトル表示

podcast = st.selectbox("Podcastを選択", RSS_URL.keys())
st.write(RSS_URL[podcast])

process = st.radio("処理を選択", ["一覧", "キーワード検索", "日付を指定して時間計算"])

d = feedparser.parse(RSS_URL[podcast])
if process == "日付を指定して時間計算":
    from_date = st.date_input("この日から")
    to_date = st.date_input("この日まで")
    duration, durationx1_25 = get_podcast_duration(d, from_date, to_date)
    st.header(duration)
    st.write(f"(x1.25: {durationx1_25})")
elif process == "一覧":
    latest_episode = len(d.entries)
    start_episode_number = st.number_input(
        "このエピソードから",
        value=latest_episode,
        max_value=latest_episode,
        min_value=1,
    )
    end_episode_number = st.number_input(
        "このエピソードまで",
        value=latest_episode - 9,
        max_value=start_episode_number,
        min_value=1,
    )

    output_range = list(
        range(
            latest_episode - start_episode_number,
            latest_episode - end_episode_number + 1,
        )
    )

    for idx, entry in enumerate(d.entries):
        if idx in output_range:
            title = get_title(latest_episode - idx, entry)
            st.markdown(f"##### {title}")
            link, type = get_audiofile(entry)
            st.audio(link, format=type)
            st.divider()


else:
    keyword = st.text_input("キーワードをどうぞ")
    detail = st.toggle("詳細表示")

    idx = len(d.entries)
    for entry in d.entries:
        title = grep_and_get_title(idx, entry, keyword)
        idx -= 1
        if title:
            if detail:
                st.markdown(f"##### {title}")
                st.write(get_info(entry), unsafe_allow_html=True)
                link, type = get_audiofile(entry)
                st.audio(link, format=type)
                st.divider()
            else:
                st.markdown(f"##### {title}")
                link, type = get_audiofile(entry)
                st.audio(link, format=type)
                st.divider()
