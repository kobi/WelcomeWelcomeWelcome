import json
import os
import glob
# from os.path import join, split
import re
from datetime import timedelta

query_welcome_welcome_welcome = [
    {'title': 'Welcome Welcome Welcome', 'pattern':['welcome', 'welcome', 'welcome']},
    {'title': 'Our main story', 'pattern':['our', 'main', 'story']},
    {'title': 'Void', 'pattern':['void']},
    {'title': 'And now... this', 'pattern':['and', 'now', 'this']},
    {'title': 'it\'s true!', 'pattern':['it.?s', 'true']},
    {'title': 'That\'s our show', 'pattern':['that.?s', 'our', 'show']}
]

query_test = [
    {'title':'lines', 'pattern': ['on','site', 'as', 'this', 'old']},
    {'title':'on site', 'pattern': ['on','site', 'as']}
]

# presidents?
# dems/reps?
# virus?
# yaerly? peeps?

# hashtags: either "hashtag" or "#www" in subtitles

def get_all_episodes():
    script_folder = os.path.dirname(os.path.realpath(__file__))
    data_folder = os.path.join(script_folder, 'data')
    json_files = glob.glob(data_folder + '/*.json')
    for json_file in json_files:
        with open(json_file) as f:
            data = json.load(f)
            yield data


# preview:
#   7
#   00:00:40,440 --> 00:00:44,600
#   I'm not talking about the fact that
#   Nicolas Cage will be starring in "Pig",
#
# the pattern:
# * captures the timestamp
# * allows skipping non-empty lines (so still on same entry)
# * matches each word in the pattern
#   * allows only non-words between these words. this may cross over to the next timestamp entry.
def pattern_to_regex(pattern):
    return re.compile(r'^\d+$\r?\n(^\d\d:\d\d:\d\d,\d{3})\s*-->.*\r?\n(?:.+\r?\n)*.*' + '[^a-z]+'.join(pattern), re.IGNORECASE | re.MULTILINE)

def srt_timestamp_to_seconds(srt_timestamp):
    times = re.split(r'[:,]', srt_timestamp)
    ts = timedelta(hours=int(times[0]), minutes=int(times[1]),seconds=int(times[2]))
    return int(ts.total_seconds())

def get_episode_length_seconds(full_srt_string):
    last_timestamp = re.findall(r'\d\d:\d\d:\d\d,\d{3}', full_srt_string)[-1]
    return srt_timestamp_to_seconds(last_timestamp)

def query_episode(episode, query):
    print(episode['srt_path'])
    with open(episode['srt_path'], 'r') as file:
        full_srt_string = file.read()
    episode['episode_length'] = get_episode_length_seconds(full_srt_string)
    for quote_index, quote in enumerate(query):
        str_regex = pattern_to_regex(quote['pattern'])
        matches = list(str_regex.finditer(full_srt_string))
        if matches:
            yield {
                'quote_title': quote['title'],
                'quote_index': quote_index,
                'times': [srt_timestamp_to_seconds(m.group(1)) for m in matches]
            }

def query_all_episodes(episodes, query):
    for episode in episodes:
        yield {
            'season': episode['season'],
            'episode': episode['episode'],
            'episode_name': episode['episode_name'],
            # 'episode_length': episode['episode_length'], # not there - it's in each quote beacuse we only open the file there
            'quotes': list(query_episode(episode, query))
        }

episodes = list(get_all_episodes())
print(len(episodes))

# ep = list(query_episode(episodes[100], query_welcome_welcome_welcome))
# print(ep)

report = list(query_all_episodes(episodes, query_welcome_welcome_welcome))
print(report)

