from threading import Thread

from inspect import getsource
from utils.download import download
from utils import get_logger
import scraper
import time
from urllib.parse import urldefrag, urlparse

def get_subdomain(url):
    parsed_url = urlparse(url)
    domain_parts = parsed_url.netloc.split('.')
    if len(domain_parts) > 2:
        return ','.join(domain_parts[:-2])
    return ''

def print_subdomain_counts(subdomain_counts):
    sorted_subdomains = sorted(subdomain_counts.keys())
    for subdomain in sorted_subdomains:
        print(f"{subdomain}.ics.uci.edu, {len(subdomain_counts[subdomain])}")

class Worker(Thread):
    def __init__(self, worker_id, config, frontier):
        super().__init__(daemon=True)
        self.logger = get_logger(f"Worker-{worker_id}", "Worker")
        self.config = config
        self.frontier = frontier
        self.subdomain_counts = {}
        # basic check for requests in scraper
        assert {getsource(scraper).find(req) for req in {"from requests import", "import requests"}} == {-1}, "Do not use requests in scraper.py"
        assert {getsource(scraper).find(req) for req in {"from urllib.request import", "import urllib.request"}} == {-1}, "Do not use urllib.request in scraper.py"


    def run(self):
        unique_urls = set()
        while True:
            tbd_url = self.frontier.get_tbd_url()
            
            if not tbd_url:
                self.logger.info("Frontier is empty. Stopping Crawler.")
                break
                
            if (urldefrag(tbd_url)[0]) in unique_urls:
                self.logger.info(f"URL {tbd_url} has already been visited.")
                self.frontier.mark_url_complete(tbd_url)
                continue
                
            resp = download(tbd_url, self.config, self.logger)
            self.logger.info(
                f"Downloaded {tbd_url}, status <{resp.status}>, "
                f"using cache {self.config.cache_server}.")
            scraped_urls = scraper.scraper(tbd_url, resp)
            for scraped_url in scraped_urls:
                self.frontier.add_url(scraped_url)
            self.frontier.mark_url_complete(tbd_url)
            unique_urls.add(urldefrag(tbd_url)[0])

            # Grab subdomains
            subdomain = get_subdomain(tbd_url)
            if subdomain not in self.subdomain_counts:
                self.subdomain_counts[subdomain] = set()
            self.subdomain_counts[subdomain].add(urldefrag(tbd_url)[0])

            time.sleep(self.config.time_delay)
        print(f"Number of unique pages found: {len(unique_urls)}")
        print (f"Longest page found was {scraper.get_max_length_url()[1]} with {scraper.get_max_length_url()[0]} words.")
        print_subdomain_counts(self.subdomain_counts)