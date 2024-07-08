import asyncio
import aiohttp
from aiohttp import ClientSession
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import os
import re
import importlib.util
import fitz
from typing import Tuple, List, Dict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DOMAINS = ['coopercity.gov', 'coopercityfl.org']

total_pdfs = []

non_searchable_extensions = (
    'mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a', 'wma',
    'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'tif', 'svg', 'webp', 'ico',
    'mp4', 'mkv', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mpeg', 'mpg',
    'doc', 'docx', 'pdf', 'xls', 'xlsx', 'ppt', 'pptx', 'odt', 'ods', 'odp', 'rtf',
    'zip', 'rar', '7z', 'tar', 'gz', 'bz2',
    'exe', 'bat', 'sh', 'bin', 'dll', 'msi', 'deb', 'rpm',
    'py', 'java', 'c', 'cpp', 'h', 'cs', 'js', 'ts',
    'iso', 'dmg', 'epub', 'mobi', 'apk'
)

results_dict = dict()

target_dict = dict()

old_structure = {'Broward': {'COOPER CITY': {}}}
new_structure = {'Broward': {'COOPER CITY': {}}}


async def fetch(url: str, session: ClientSession) -> str:
    """
    Fetch a URL and return the response content.

    Parameters
    ----------
    url : str
        The url that is being fetched.
    session : ClientSession
        The session from aiohttp.ClientSession().

    Returns
    -------
    str
        The text (html) from the searched link.
    """

    try:
        async with session.get(url) as response:
            return await response.text()

    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        return ""


def extract_links(html: str, base_url: str) -> set:
    """
    Extracts links from a webpage html.

    Parameters
    ----------
    html : str
        The fetched html.
    base_url : str
        The html's original url.

    Returns
    -------
    set
        A set of all links found on the page.
    """

    soup = BeautifulSoup(html, 'html.parser')
    links = set()

    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href'].strip()
        full_url = urljoin(base_url, href)
        if any(domain in full_url for domain in DOMAINS):
            links.add(full_url)

    return links


def filter_pdf_links(links: set) -> set:
    """
    Filters the links to be only pdf links.

    Paramters
    ---------
    links : set
        The links we received.

    Returns
    -------
    set
        The pdfs within the links we received.
    """

    # pdf_links = {link for link in links if link.lower().endswith('.pdf')}

    pdf_links = set()
    for link in links:
        if link.lower().endswith('.pdf'):
            pdf_links.add(link)
            results_dict

    return pdf_links


async def download_pdf(url, session) -> bytes:
    """
    Executes the download_pdf and extract_text_from_pdf functions asyncronously and formats the text results.

    Parameters
    ----------
    url : str
        The pdf link about to be searched.

    Returns
    -------
    Tuple[str, str]
        A tuple of a link and its respective pdf content.
    """

    async with session.get(url) as response:

        if response.status == 200:
            return await response.read()
        else:
            raise Exception(f"Failed to download PDF from {url}")


def extract_text_from_pdf(pdf_content: bytes) -> str:
    """
    Opens the inputted pdf and reads its bytes into text.

    Parameters
    ----------
    pdf_content : bytes
        The pdf link about to be searched.

    Returns
    -------
    str
        A string of the read pdf content.
    """

    doc = fitz.open(stream=pdf_content, filetype="pdf")
    text = ""

    for page in doc:
        text += page.get_text()

    return text


async def process_pdf(url: str, session: ClientSession) -> Tuple[str, str]:
    """
    Executes the download_pdf and extract_text_from_pdf functions asyncronously and formats the text results.

    Parameters
    ----------
    url : str
        The pdf link about to be searched.

    Returns
    -------
    Tuple[str, str]
        A tuple of a link and its respective pdf content.
    """

    try:
        pdf_content = await download_pdf(url, session)
        text = extract_text_from_pdf(pdf_content)
        return url, text

    except Exception as e:
        print(f"Error processing {url}: {e}")
        return None, None


async def download_and_process_pdfs(pdf_links: List[str]) -> List[Tuple[str, str]]:
    """
    Executes the process_pdf function asyncronously and formats the results.

    Parameters
    ----------
    pdf_links : List[str]
        The pdf links about to be searched.

    Returns
    -------
    List[Tuple[str, str]]
        A list of the tuples of links and their respective pdfs.
    """

    async with aiohttp.ClientSession() as session:
        tasks = [process_pdf(link, session) for link in pdf_links]
        pdfs = await asyncio.gather(*tasks)
        return [pdf for pdf in pdfs if pdf[0] is not None]


def custom_preprocessor(text: str) -> str:
    """
    Remove punctuation and special characters.

    Parameters
    ----------
    text : str
        The text about to be filtered.

    Returns
    -------
    str
        The filtered text.
    """

    text = re.sub(r'[^\w\s]', '', text)

    return text


def calculate_cosine_similarity(text1: str, text2: str) -> float:
    """
    Calculates cosine similarity scores between two strings.

    Parameters
    ----------
    text1 : str
        The first piece of text.
    text2 : str
        The second piece of text.

    Returns
    -------
    float
        A score from 0.0 to 1.0 of how closely matched the text is (0.0 being none, and 1.0 being an exact match).
    """

    vectorizer = TfidfVectorizer(preprocessor=custom_preprocessor)
    vectors = vectorizer.fit_transform([text1, text2]).toarray()

    return cosine_similarity(vectors)[0, 1]


async def crawl(url: str, session: ClientSession, depth: int) -> set:
    """
    Function to crawl a given depth.

    Parameters
    ----------
    url : str
        The link we want to crawl.
    session : ClientSession
        The client session from aiohttp.ClientSession().
    depth : int
        Depth of search - hyperparameter.

    Returns
    -------
    set
        All unique pdfs from all links searched so far.
    """

    visited = set()
    to_visit = {url}
    all_pdfs = set()

    for current_depth in range(depth):
        tasks = []  # possibly expand to be faster later - instead of 1 wave of tasks waiting upon completion and running concurrently for each depth, we could run all n-depths concurrently. However, this may interfere with the whole idea of depth.
        new_links = set()
        print(f"Current depth: {current_depth}, now searching {len(to_visit)} links")
        for link in to_visit:
            if link not in visited:
                if (not link.lower().endswith(non_searchable_extensions)) and ("mailto" not in link.lower()):
                    tasks.append(fetch(link, session))
                    visited.add(link)
        to_visit.clear()
        if tasks:
            responses = await asyncio.gather(*tasks)
            for html, link in zip(responses, visited):
                links = extract_links(html, link)
                pdf_links = filter_pdf_links(links)
                all_pdfs.update(pdf_links)
                new_links.update(links)
        to_visit = new_links
        total_pdfs.extend(all_pdfs)

    return all_pdfs


def build_old_structure(pdf_data: List[Tuple[str, str]], county: str, city: str) -> None:
    """
    Updates the old_structure dictionary globally with pdf data for the given county and city.

    Parameters
    ----------
    pdf_data : List[Tuple[str, str]]
        List of (url, text) tuples representing the pdf data.
    county : str
        The county name.
    city : str
        The city name.

    Returns
    -------
    None
    """

    # Ensure the county entry exists
    if county not in old_structure:
        old_structure[county] = {}

    # Ensure the city entry exists within the county
    if city not in old_structure[county]:
        old_structure[county][city] = {}

    for url, text in pdf_data:
        old_structure[county][city][url] = text

    return None


def build_new_structure(pdf_data: List[Tuple[str, str]], county: str, city: str) -> None:
    """
    Updates the new_structure dictionary globally with pdf data for the given county and city.

    Parameters
    ----------
    pdf_data : List[Tuple[str, str]]
        List of (url, text) tuples representing the pdf data.
    county : str
        The county name.
    city : str
        The city name.

    Returns
    -------
    None
    """

    # Ensure the county entry exists
    if county not in new_structure:
        new_structure[county] = {}

    # Ensure the city entry exists within the county
    if city not in new_structure[county]:
        new_structure[county][city] = {}

    for url, text in pdf_data:
        new_structure[county][city][url] = text

    return None


def compare_structures(old_structure: Dict[str, Dict[str, Dict[str, str]]],
                       new_structure: Dict[str, Dict[str, Dict[str, str]]], threshold=0.95, county=None,
                       city=None) -> list:
    """
    Updates the new_structure dictionary globally with pdf data for the given county and city.

    Parameters
    ----------
    old_structure : Dict[str,Dict[str,Dict[str,str]]]
        The dictionary for target pdfs.
    new_structure : Dict[str,Dict[str,Dict[str,str]]]
        The dictionary for result pdfs.
    threshold : int
        The threshold of similarity tolerance.
    county : str
        This iteration's county.
    city : str
        This iteration's city.

    Returns
    -------
    list
        The number of pdf content matches.
    """

    differences = []

    old_texts = [text for text in old_structure[county][city].values()]
    new_texts = [text for text in new_structure[county][city].values()]

    for new_text in new_texts:
        for old_text in old_texts:
            similarity = calculate_cosine_similarity(old_text, new_text)
            if similarity > threshold:
                differences.append(1)

    return differences


# def create_dicts() -> None:

#     # get relative path to the Florida folder
#     base_path = "/storage/Florida/children/"
#     links = {}

#     # Check if the base path exists
#     for county in os.listdir(os.getcwd() + base_path):
#         if os.path.isdir(os.getcwd() + base_path + county) and county != "__pycache__":
#             for municipality in os.listdir(os.getcwd() + base_path + county + "/children/"):
#                 if os.path.isdir(os.getcwd() + base_path + county + "/children/" + municipality) and municipality != "__pycache__":
#                     module = importlib.import_module(f"storage.Florida.children.{county}.children.{municipality}")
#                     my_class = getattr(module, re.sub(r'\W+','', municipality))
#                     results = my_class.getMunicipalityInfo() #dict

#                     # if county not in links:
#                     #     links[county] = {}
#                     #     links[county][municipality] = results

#                     # print(municipality, 2)
#                     # print(links['MiamiDade'])
#                     if county not in results_dict:
#                         results_dict[county] = {}

#                     try:
#                         results_dict[county][municipality] = results['website'][0]['url']
#                     except:
#                         pass

#                     ## Creating the target_dict


#                     if county not in target_dict:
#                         target_dict[county] = {}

#                     try:
#                         target_dict[county][municipality] = None
#                     except:
#                         pass

#     # print(results_dict['Broward']['COOPER CITY'])

#     # Broward_links = list(results_dict['Broward'].values())
#     # MiamiDade_links = list(results_dict['MiamiDade'].values())
#     # # print(MiamiDade_links)
#     # all_links = MiamiDade_links + Broward_links

#     print(results_dict)

#     # print(target_dict)

#     return None


async def main(url: str, old_pdf_links: list, county: str, city: str, depth: int) -> None:
    """
    Main function.

    Parameters
    ----------
    url : str
        Starting url.
    olf_pdf_links : list
        Target pdfs.
    county : str
        County for this iteration (i.e. 'Broward').
    city : str
        City for this iteration (i.e. 'COOPER CITY').
    depth : int
        Search depth.

    Returns
    -------
    None
        This function does not return anything.
    """

    async with aiohttp.ClientSession() as session:
        new_pdf_links = await crawl(url, session, depth)
        # tasks = [process_pdf(link, session) for link in pdf_links]
        # pdf_json_strings = await asyncio.gather(*tasks)
        # pdf_json_strings = [pdf_json for pdf_json in pdf_json_strings if pdf_json is not None]
        # print(pdf_json_strings[0][0:10])
        # for pdf_json in pdf_json_strings:
        #     print(pdf_json)
    print(new_pdf_links)
    print(len(new_pdf_links))

    old_pdfs = await download_and_process_pdfs(old_pdf_links)
    new_pdfs = await download_and_process_pdfs(new_pdf_links)

    print(len(new_pdfs))

    build_old_structure(old_pdfs, county, city)
    build_new_structure(new_pdfs, county, city)

    differences = compare_structures(old_structure, new_structure, threshold=0.95, county=county, city=city)

    # for diff in differences:
    #     print(f"PDF has changed with cosine similarity: {diff[2]}")
    #     # Optionally, you can print or handle the differences here

    # print(type(new_structure.values))
    # print(new_structure['Broward']['COOPER CITY'].keys())
    # print(new_structure.keys())
    # print(old_structure['Broward']['COOPER CITY'].keys())

    print(differences)
    # create_dicts()


if __name__ == '__main__':
    url = 'https://coopercity.gov/'
    old_pdf_links = [
        'https://coopercity.gov/vertical/sites/%7B6B555694-E6ED-4811-95F9-68AA3BD0A2FF%7D/uploads/2022_STORM_SHUTTER_AFFIDAVIT_FILLABLE(1).pdf',
        'https://coopercity.gov/vertical/sites/%7B6B555694-E6ED-4811-95F9-68AA3BD0A2FF%7D/uploads/Affidavit_-_Hurricane_Mitigation_2023.pdf']
    county = 'Broward'
    city = 'COOPER CITY'
    depth = 2
    asyncio.run(main(url=url, old_pdf_links=old_pdf_links, county=county, city=city, depth=depth))
    # list_no_repeats = list(set(total_pdfs))
    # print(list_no_repeats)
    # print(len(list_no_repeats))

