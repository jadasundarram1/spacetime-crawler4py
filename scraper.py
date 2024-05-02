import re, crawler.frontier, httpx
from urllib.parse import urlparse, urljoin, parse_qs
from urllib import robotparser
from bs4 import BeautifulSoup
from urllib.parse import urldefrag
from detector import URLDuplicateDetector
from simhash import Simhash


def scraper(url, resp):
    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]

#dict of each url's robot parser instance
robot_instances = {}

#dict of each url's length
url_content_length = {}

def fetch(url):
    try:
        # getting response from the url
        response = httpx.get(url)
        # Return the response object
        return response
    except httpx.HTTPError as error:
        # Handle HTTP errors
        print(f"Error fetching {url}: {error}")
        return None
    except Exception as error:
        # Handle other exceptions
        print(f"Error fetching {url}: {error}")
        return None

def get_max_length_url():
    a = max(url_content_length)
    return [a, url_content_length[a]]

def allowed_by_robots(raw_url):
    parsed_url = urlparse(raw_url)
    try:
        #get domain of website
        web_domain = parsed_url.scheme + "://" + parsed_url.netloc

        #check if robots.txt has already been parsed for this url
        if web_domain in robot_instances:
            robot = robot_instances[web_domain]

        #if not create a new instance of robotparser to check if allowed to crawl
        else:
            robot = robotparser.RobotFileParser()
            robot.set_url(web_domain + "/robots.txt")
            robot.read()
            robot_instances[web_domain] = robot
        
        #if every useragent is allowed to parse this url, return true, else return false
        return robot.can_fetch("*", raw_url)
    
    except Exception as e:
        print("There was an error: ", e)
        return True

url_duplicate_detector = URLDuplicateDetector()

def extract_next_links(url, resp, max_redirects = 10):
    hyperlinks = []
    # Implementation required
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.

    original_url = url
    while 300 <= resp.status < 400 and max_redirects > 0:
        # Handle redirection
        redirected_url = resp.headers.get('Location')
        if redirected_url:
            print(f"Redirected from {url} to {redirected_url}")
            hyperlinks.append(redirected_url)
            #Reduce max_directs by 1
            max_redirects -= 1
            #perform the next request to next redirection
            resp = fetch(redirected_url)
            #update the current URL to the redirected URL
            url = redirected_url
        else:
            break
    #After redirections, check if final URL is diffrent from original URL
    if url != original_url:
        #update frontier with final URL after all redirects
        crawler.Frontier.add_url(url)
    if resp.status != 200:
        return []  # Other status codes indicate an error or other issues

    # Continue processing for 200 OK responses, if robots.txt does not, allow crawling return an empty list
    if not allowed_by_robots(url):
        return []

    #decode url content to find simhash index
    url_content = resp.raw_response.content.decode('utf-8')
    
    #get the simhash index of page
    simhash = Simhash(url_content)
    
    # TODO: resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    
    if not url_duplicate_detector.is_duplicate(simhash):
        soup = BeautifulSoup(resp.raw_response.content, 'html.parser')
        
        #get length of url content to add to dict
        len_content = len(soup.get_text().split())
        url_content_length[len_content] = url

        current_word_count = 0
        max_word_link = ("", 0)
        common_words = defaultdict(int)
        stopwords = {'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', "you're", "you've", "you'll", "you'd", 'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', "she's", 'her', 'hers', 'herself', 'it', "it's", 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves', 'what', 'which', 'who', 'whom', 'this', 'that', "that'll", 'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', "don't", 'should', "should've", 'now', 'd', 'll', 'm', 'o', 're', 've', 'y', 'ain', 'aren', "aren't", 'couldn', "couldn't", 'didn', "didn't", 'doesn', "doesn't", 'hadn', "hadn't", 'hasn', "hasn't", 'haven', "haven't", 'isn', "isn't", 'ma', 'mightn', "mightn't", 'mustn', "mustn't", 'needn', "needn't", 'shan', "shan't", 'shouldn', "shouldn't", 'wasn', "wasn't", 'weren', "weren't", 'won', "won't", 'wouldn', "wouldn't"}
        for line in soup.stripped_strings: #stripped_strings is an iterator that gets all the lines in the document (better than get_text which loads all the data in one variable at once)
            lowerLine = line.lower()
            for word in re.findall(r'[a-zA-Z0-9]+', lowerLine): #alphanumeric words
                if word not in stopwords and ((word.isdigit() and len(word) >= 3) or (not word.isdigit() and len(word) > 1)): #filtering stopwords and small numbers/words
                    common_words[word] += 1
                    current_word_count += 1

            if currrent_word_count > maxWordLink[1]: #keeping track of url with most words
                max_word_link = (url, current_word_count) #storing in a tuple with the url associated with most words
            else:
                isSitemap = True
                soup = BeautifulSoup(resp.raw_response.content, 'lxml-xml') #have to change the soup object to parse XML sites for sitemaps
        
        # Find all hyperlinks
        links = soup.findAll('a')
        # Get href and defragment url, use 0 index to get first element 
        for link in links:
            href = link.get('href')
            if href:
                absolute_url = urljoin(resp.url, href)
                absolute_url_defragmented = urldefrag(absolute_url)[0]
                hyperlinks.append(absolute_url_defragmented)
                #Add link and its simhash fingerprint to index
                url_duplicate_detector.add_to_sh_index(absolute_url_defragmented, simhash)
    return hyperlinks

def is_calendar_url(url):
    """
    Checks if the normalized url is a calendar or not. If it is it returns
    False
    """
    # URL Pattern Matching
    date_pattern = re.compile(r"\d{4}-\d{2}-\d{2}")  # Matches YYYY-MM-DD in URL
    calendar_keywords = re.compile(r"\b(calendar|event|schedule)\b", re.IGNORECASE)

    # Query Parameter Analysis
    query_params = parse_qs(urlparse(url).query)
    date_related_keys = {'date', 'month', 'year'}

    # Check for date patterns or calendar-related keywords in the URL path
    if date_pattern.search(url) or calendar_keywords.search(url):
        return True

    # Check for date-related query parameters
    if any(key in date_related_keys for key in query_params):
        return True

    return False
def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)
        if (".ics.uci.edu" not in parsed.netloc) and (".cs.uci.edu" not in parsed.netloc) and (".informatics.uci.edu" not in parsed.netloc) and (".stat.uci.edu" not in parsed.netloc):
            return False
        
        if parsed.scheme not in set(["http", "https"]):
            return False
        
        if parsed.path.endswith(('.pdf', '.jpg', '.jpeg', '.png', '.ppt', '.pptx', '.doc', '.docx')):
            return False

        if is_calendar_url(parsed):
            return False

        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

    except TypeError:
        print ("TypeError for ", parsed)
        raise

