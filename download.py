import os
import requests
import xml.etree.ElementTree as ET
import re
import time
import zipfile
import json

# human readable at https://www.opensubtitles.org/en/ssearch/sublanguageid-all/idmovie-185080
# allEpisodesIndex = 'https://www.opensubtitles.org/en/ssearch/sublanguageid-all/idmovie-185080/xml'
allEpisodesIndex = 'https://www.opensubtitles.org/en/ssearch/sublanguageid-en/idmovie-185080/xml'

# not too related: https://blog.parse.ly/post/2380/measuring-the-impact-of-the-john-oliver-effect/

def get_file_path(filename):
    script_folder = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(script_folder, 'data', filename)

def download_file(url, filename):
    path = get_file_path(filename)
    if os.path.isfile(path):
        print(f'already downloaded "{url}" to "{filename}". delete to download again.')
        return path, False

    # to get the session id - clear all cookies under opensubtitles.org in your browser,
    # try to download a subtitle file and solve the captch. then copy the new session id here.
    cookies = {
        "searchform":"formname%3Dsearchform%7C%7C%7C%7C%7C%7C%7C%7C%7C%7C%7C%7C%7C%7C1%7C%7C%7C1%7C%7C%7C%7C%7C%7C%7C%7C%7C%7C%7C%7C%7C%7C%7C%7C%7C",
        "PHPSESSID":"XXXXXXXXXXXXXXXXXXXXXXXX",
    }

    # after a few hundred files:
    #   Sorry, maximum download count for IP: {ip} exceeded. If you will continue trying to download, 
    #   your IP will be blocked by our firewall. For more information read our FAQ or contact us, if you think
    #   you should not see this error. This deny will be removed after around 24 hours, so be patient.

    response = requests.get(url, cookies=cookies)
    print('\t\tContent-Type=' +  response.headers.get("Content-Type"))
    if response.headers.get("Content-Type") != 'application/zip':
        raise('Please solve a captcha and update cookies: ' + url)
    open(path, 'wb').write(response.content)
    return path, True

def get_xml_data(path):
    tree = ET.parse(path)
    root = tree.getroot()
    return root

# all languages index
# <subtitle>
#     <MovieName><![CDATA["Last Week Tonight with John Oliver" Civil Forfeiture]]></MovieName>
#     <EpisodeName Link='/en/search/sublanguageid-all/imdbid-4072006' ImdbLink='http://www.imdb.com/title/tt4072006/'><![CDATA[Civil Forfeiture]]></EpisodeName>
#     <MovieImdbRating>8.5</MovieImdbRating>
#     <SeriesSeason>1</SeriesSeason>
#     <SeriesEpisode>20</SeriesEpisode>
#     <SeriesSubtitles>5</SeriesSubtitles>
#     <SeriesDownloadsCnt LinkDownload='/download/sad/sublanguageid-all/imdbid-4072006'>7258</SeriesDownloadsCnt>
#     <Newest time='19:31:05' rfc822='Tue, 18 Feb 2020 19:31:05 CET' rfc3339='2020-02-18T19:31:05+0100' time_locale='19:31:05' date_locale='18/02/2020' ISO8601='2020-02-18T19:31:05+01:00'>2020-02-18</Newest>
# </subtitle>

# english only index has fewer fields
# <subtitle>
#     <MovieName><![CDATA[Lead]]></MovieName>
#     <EpisodeName Link='/en/upload/idmovieimdb-5605696' ImdbLink='http://www.imdb.com/title/tt5605696/'><![CDATA[Lead]]></EpisodeName>
#     <SeriesSeason>3</SeriesSeason>
#     <SeriesEpisode>9</SeriesEpisode>
#     <MovieImdbRating>0.0</MovieImdbRating>
# </subtitle>

# one episode
# xml https://www.opensubtitles.org/en/search/sublanguageid-all/imdbid-3711092/xml
# subtitle url english https://www.opensubtitles.org/en/subtitles/8100367/last-week-tonight-with-john-oliver-climate-change-denial-en

def get_index_data(path):
    # example: https://docs.python.org/3/library/xml.etree.elementtree.html
    index_data = get_xml_data(path)
    for episode in index_data.findall('./search/results/subtitle'):
        yield {
            'season': int(episode.findtext('SeriesSeason')),
            'episode': int(episode.findtext('SeriesEpisode')),
            'episode_name': episode.findtext('MovieName'),
            'link': episode.find('EpisodeName').get('Link'),
        }

def download_episode(episode):
    safe_episode_name = re.sub('\\W+', '', episode["episode_name"])
    id = episode["link"].split('-')[1]
    base_file_name = f'lwtwjo_s{episode["season"]:02d}e{episode["episode"]:02d}_{id}_{safe_episode_name}'
    # xml_path = get_file_path(base_file_name + '.xml')
    xml_url = f'https://www.opensubtitles.org/en/search/sublanguageid-all/imdbid-{id}/xml'
    xml_path, downloaded_xml = download_file(xml_url, base_file_name + '.xml')
    
    # skip zip files for now.
    # return downloaded_xml

    print('\t' + base_file_name)
    data = get_xml_data(xml_path)
    download_links_element = data.find(f'./search/results/subtitle[LanguageName=\'English\'][SubFormat=\'srt\']/IDSubtitle')
    if download_links_element == None:
        print("\t!! Can't find XML element with English subtitles")
        return False
    download_link = download_links_element.get('LinkDownload')
    print('\tdownloading ' + download_link)
    zip_path, downloaded_zip = download_file(download_link, base_file_name + '.zip')
    srt_path = get_file_path(base_file_name + '.srt')
    episode['id'] = id
    episode['zip_path'] = zip_path
    episode['srt_path'] = srt_path
    episode['json_path'] =  get_file_path(base_file_name + '.json')
    return downloaded_xml or downloaded_zip

def download_all(episodes):
    for episode in episodes:
        downloaded = download_episode(episode)
        # don't be hasty.
        if downloaded:
            time.sleep(100)
        unzip_srt(episode['zip_path'], episode['srt_path'])
        save_json(episode, episode['json_path'])
    
def unzip_srt(zip_path, target_srt_path):
    if os.path.isfile(target_srt_path):
        return
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        srt_file_info = next(f for f in zip_ref.filelist if f.filename.endswith('.srt'))
        #for f in zip_ref.filelist:
        #    print(f)
        folder = os.path.dirname(target_srt_path)
        temp_srt_path = zip_ref.extract(srt_file_info, path=folder)
        os.rename(temp_srt_path, target_srt_path)
        #zip_ref.extractall(directory_to_extract_to)

def save_json(dict, json_path):
    if os.path.isfile(json_path):
        return
    with open(json_path, 'w') as outfile: 
        json.dump(dict, outfile, indent=4)

index_file_path, _ = download_file(allEpisodesIndex, 'last_week_tonight_index_en.xml')
index_data = list(get_index_data(index_file_path))
print(len(index_data))

download_all(index_data)
