from typing import List
from download import get_file_path
import json
import os
import glob
import re
from datetime import timedelta
from itertools import groupby, chain
from sre_constants import CH_UNICODE
import html

query_welcome_welcome_welcome = [
    {'title': 'Welcome Welcome Welcome', 'pattern':['welcome', 'welcome', 'welcome']},
    # {'title': 'I\'m John Oliver', 'pattern':['i.?m', 'john', 'oliver']},
    {'title': 'Thank you for joining us', 'pattern':['Thank', r'you(?: so much)?', 'for', r'joining|being\W+with', 'us']},
    {'title': 'And now... this', 'pattern':['and', 'now', 'this']},
    {'title': 'Our main story', 'pattern':['our', 'main', 'story']},
    {'title': 'it\'s true!', 'pattern':[r'\bit.?s', 'true']},
    {'title': 'That\'s our show', 'pattern':['that.?s', 'our', 'show']},
    {'title': 'Blank Void', 'pattern':[r'(?:blank|empty|white|this|the)' ,r'\bvoid\b']},
]

query_presidents = [
    # {'title':'Bush', 'pattern': [r'\bbush']}, # alsmost no mentiones of Bush
    {'title':'Obama', 'pattern': [r'\bobama']},
    {'title':'Clinton', 'pattern': [r'\bclinton']},
    {'title':'Trump', 'pattern': [r'\btrump']},
    {'title':'Biden', 'pattern': [r'\bbiden']},
]

query_parties = [
    {'title':'Democrats', 'pattern': [r'\bdemocrat']},
    {'title':'Republicans', 'pattern': [r'\brepublican|\bg\.?o\.p\b']},
]

query_seasonal = [
    {'title':'Peeps', 'pattern': [r'\bpeeps']},
    {'title':'Pumpkin Spice', 'pattern': ['pumpkin', 'spice']},
    {'title':'Adam Driver', 'pattern': ['adam', 'driver']},
]

query_test = [
    {'title':'lines', 'pattern': ['on','site', 'as', 'this', 'old']},
    {'title':'on site', 'pattern': ['on','site', 'as']},
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
# NOT USING IT.
# this is a single pattern, but we can't find multiple matches on the same block beacuse the timespan is consumed.
# instead we're using pattern_to_regex_words_only and get_timespan_of_position
def pattern_to_regex(pattern):
    return re.compile(r'^\d+$\r?\n(^\d\d:\d\d:\d\d,\d{3})\s*-->.*\r?\n(?:.+\r?\n)*.*' + '[^a-z]+'.join(pattern), re.IGNORECASE | re.MULTILINE)

def pattern_to_regex_words_only(pattern):
    return re.compile(r'[^a-z]+'.join(pattern), re.IGNORECASE | re.MULTILINE)

# find the first timespamp before the osition of the match.
def get_timespan_of_position(srt_string: str, position: int) -> int:
    srt_string = srt_string[:position]
    last_timestamp = re.findall(r'^\d\d:\d\d:\d\d,\d{3}(?=\s*-->)', srt_string, re.MULTILINE)[-1]
    return srt_timestamp_to_seconds(last_timestamp)

def srt_timestamp_to_seconds(srt_timestamp: str) -> int:
    times = re.split(r'[:,]', srt_timestamp)
    ts = timedelta(hours=int(times[0]), minutes=int(times[1]),seconds=int(times[2]))
    return int(ts.total_seconds())

def get_episode_length_seconds(full_srt_string):
    last_timestamp = re.findall(r'\d\d:\d\d:\d\d,\d{3}', full_srt_string)[-1]
    return srt_timestamp_to_seconds(last_timestamp)

def remove_duplicated_lines(full_srt_string):
    # remove repeated sentences from subtitles. can't tell if really said twice or just written twice. :(
    # example: s05e18
    # 192
    # 00:05:29,697 --> 00:05:31,963
    # LOOK, $120 BILLION IS A LOT OF
    # MONEY.

    # 193
    # 00:05:31,965 --> 00:05:32,698
    # MONEY.
    # FOR CONTEXT, IT IS MORE THAN THE

    # 194
    # 00:05:32,700 --> 00:05:33,932
    # FOR CONTEXT, IT IS MORE THAN THE
    # SIZE OF THE ENTIRE GLOBAL CHEESE
    return re.sub(r'(^\S.+\n)(?=\n\d+\n.*-->.*\n\1)', '[xxxxxxxxxxxxxxxxxxxxxxxxx]', full_srt_string, flags= re.MULTILINE)

def query_episode(episode, query):
    print(episode['srt_path'])
    if 'full_str_string' not in episode:
        with open(episode['srt_path'], 'r') as file:
            full_srt_string = file.read()
        full_srt_string = remove_duplicated_lines(full_srt_string)
        episode['full_str_string'] = full_srt_string
        episode['episode_length'] = get_episode_length_seconds(full_srt_string)
    else:
        full_srt_string = episode['full_str_string']
    for quote_index, quote in enumerate(query):
        str_regex = pattern_to_regex_words_only(quote['pattern'])
        matches = list(str_regex.finditer(full_srt_string))
        if matches:
            yield {
                'quote_title': quote['title'],
                'quote_index': quote_index,
                'times': list([get_timespan_of_position(full_srt_string, m.start()) for m in matches])
            }

def query_all_episodes(episodes, query):
    for episode in episodes:
        quotes = list(query_episode(episode, query))
        yield {
            'quotes': quotes,
            'season': episode['season'],
            'episode': episode['episode'],
            'episode_name': episode['episode_name'],
            'episode_length': episode['episode_length']
        }

# remove episodes, rerun groups by quotes
def combine_quotes(episodes):
    f = list(chain(*[ep['quotes'] for ep in episodes]))
    s = sorted(f, key=lambda q: q['quote_title'])
    for key, quotes_in_group in groupby(s, lambda q: q['quote_title']):
        quotes = list(quotes_in_group)
        first = quotes[0]
        all_times = list(chain(*[q['times'] for q in quotes]))
        yield {
            'quote_title': key,
            'quote_index': first['quote_index'],
            'times': sorted(all_times),
            'total_count': len(all_times)
        }

def get_statistics_by_group(full_report, key_func):
    s = list(sorted(full_report, key=key_func))
    for key, episodes in groupby(s, key_func):
        combined = list(combine_quotes(list(episodes)))
        yield (key, combined)

def full_report_to_html(report, report_title: str, query, css_classes: List[str], season_headers: List[str]):
    by_season = groupby(report, lambda episode: episode['season'])
    html_chunks = []
    # let's write html like it's 1999.
    html_chunks.append(f'<h1>{report_title}</h1>')
    html_chunks.append(f'<div class="chart {" ".join(css_classes)}">')
    for season, episodes in by_season:
        html_chunks.append(f'<div class="season season{season:02d}" data-season="{season:02d}">')
        html_chunks.append(f'<h2>{season_headers[season-1]}</h2>')
        for episode in episodes:
            episode_length = episode['episode_length']
            html_chunks.append(f'  <div class="episode episode{episode["episode"]:02d}" data-episode-length="{episode_length}">')
            quote_time_pairs = [(quote, timestamp_seconds) for quote in episode['quotes'] for timestamp_seconds in quote['times']]
            for quote, timestamp_seconds in sorted(quote_time_pairs, key=lambda x: x[1]):
                quote_index = quote['quote_index']
                relative_position = 100*timestamp_seconds / episode_length
                relative_position_round = round(relative_position, 2)
                title = html.escape(quote["quote_title"])
                html_chunks.append(f'    <div class="marker marker{quote_index}" data-timestamp="{timestamp_seconds}" title="{title}" data-relative-position="{relative_position_round}" style="left: {relative_position_round}%;">')
                html_chunks.append('    </div>')
            html_chunks.append('  </div>')
        html_chunks.append('</div>')
    html_chunks.append('  <div class="ledend">')
    for i, q in enumerate(query):
        title = html.escape(q["title"])
        html_chunks.append(f'   <div class="group group{i}"><div class="marker marker{i}"></div>{title}</div>')
    html_chunks.append('  </div>')

    html_chunks.append('</div>')    
    return "\n".join(html_chunks)


def build_html_report(report_name: str, title: str, query, css_classes: List[str], season_headers: List[str]):
    report = list(query_all_episodes(episodes, query))
    full_report_html = full_report_to_html(report, title, query, [report_name] + css_classes, season_headers)

    print('groups:')
    report_per_season = list(get_statistics_by_group(report, lambda episode: episode['season']))
    print('report_per_season = ', report_per_season)

    report_total = list(get_statistics_by_group(report, lambda _: 'Total'))
    print('report_total = ', report_total)

    return '\n\n'.join([full_report_html])

def build_html_file(html_snippets: List[str]):
    with open('template.html', 'r') as file:
        html_template = file.read()
    final_html = html_template.replace('{chart}', '\n\n'.join(html_snippets))
    with open(get_file_path(f'report.html', 'reports'), 'w') as report_file: 
        report_file.write(final_html)

episodes = list(get_all_episodes())
print(len(episodes))

# report = list(query_all_episodes(episodes, query_presidents))
# # print('report:')
# print(report)

# print('groups:')
# report_per_season = list(get_statistics_by_group(report, lambda episode: episode['season']))
# print('report_per_season = ', report_per_season)

# report_total = list(get_statistics_by_group(report, lambda _: 'Total'))
# print('report_total = ', report_total)

# # print(full_report_to_html(report, query_welcome_welcome_welcome))

years = range(2014, 2022)

build_html_file([
    build_html_report('welcome', 'Things John Oliver Says', query_welcome_welcome_welcome, ['abacus', 'XXfullwidth'], years),
    build_html_report('presidents', 'Presidents', query_presidents, ['demrep'], years),
    build_html_report('parties', 'Democrat/Republican', query_parties, ['demrep'], years),
    build_html_report('seasonal', 'Seasonal', query_seasonal, [], years),
])