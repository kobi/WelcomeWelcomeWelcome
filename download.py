import os
import requests
import xml.etree.ElementTree as ET

base_url = 'https://www.opensubtitles.org/'
# human readable at https://www.opensubtitles.org/en/ssearch/sublanguageid-all/idmovie-185080
# allEpisodesIndex = 'https://www.opensubtitles.org/en/ssearch/sublanguageid-all/idmovie-185080/xml'
allEpisodesIndex = 'https://www.opensubtitles.org/en/ssearch/sublanguageid-en/idmovie-185080/xml'

def get_file_path(filename):
    script_folder = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(script_folder, 'data', filename)

def download_file(url, filename):
    path = get_file_path(filename)
    if os.path.isfile(path):
        print(f'already downloaded "{url}" to "{filename}". delete to download again.')
        return path
    myfile = requests.get(url)
    open(path, 'wb').write(myfile.content)
    return path

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

# english only index
# <subtitle>
#     <MovieName><![CDATA[Lead]]></MovieName>
#     <EpisodeName Link='/en/upload/idmovieimdb-5605696' ImdbLink='http://www.imdb.com/title/tt5605696/'><![CDATA[Lead]]></EpisodeName>
#     <SeriesSeason>3</SeriesSeason>
#     <SeriesEpisode>9</SeriesEpisode>
#     <MovieImdbRating>0.0</MovieImdbRating>
# </subtitle>

def get_index_data(path):
    # example: https://docs.python.org/3/library/xml.etree.elementtree.html
    index_data = get_xml_data(path)
    for episode in index_data.findall('./search/results/subtitle'):
        yield {
            'season': int(episode.findtext('SeriesSeason')),
            'episode': int(episode.findtext('SeriesEpisode')),
            'episode_name': episode.findtext('MovieName'),
            'link': episode.find('EpisodeName').get('Link')
        }
    

index_file_path = download_file(allEpisodesIndex, 'last_week_tonight_index_en.xml')
index_data = get_index_data(index_file_path)
print(list(index_data))