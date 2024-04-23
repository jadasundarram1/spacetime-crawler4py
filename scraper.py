import re
from urllib.parse import urlparse
from urllib import robotparser
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def scraper(url, resp):
    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]

def extract_next_links(url, resp):
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    if resp.status != 200:
        return []
    # TODO: resp.error: when status is not 200, you can check the error here, if needed.

    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    soup = BeautifulSoup(resp.raw_response.content, 'lxml')
    # Find all hyperlinks
    links = soup.findAll('a')
    # Get href only. This will contain relative URLs (e.g. ../images/picture.gif)
    hrefs = [link.get('href') for link in links]
    # Convert to absolute (e.g. http://www.yourdomain.org/images/picture.gif)
    absolute_links = [urljoin(url, href) for href in hrefs if href]

    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    return absolute_links

robot_instances = {}

def allowed_by_robots(parsed_url, raw_url):
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


def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)
        if parsed.path not in set([".ics.uci.edu/", ".cs.uci.edu/", ".informatics.uci.edu/", ".stat.uci.edu/"]):
            return False
        if parsed.scheme not in set(["http", "https"]):
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
