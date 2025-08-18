import scrapy
import os, shutil
import re
from scraper.items import MyScraperItem

class TestSpider(scrapy.Spider):
    # Name of the spider
    name = 'test_spider'

    # The URLs where the spider will start crawling
    # start_urls = ['http://www.gueury.com/']

    # The domains that this spider is allowed to crawl
    allowed_domains = [] # This is now determined dynamically.

    # The directory where the HTML files will be stored
    output_dir = '/tmp/scraper'

    def __init__(self, url=None, *args, **kwargs):
        """
        Initializes the spider with a URL from the command line.
        """
        super(TestSpider, self).__init__(*args, **kwargs)
        if url:
            # Set the start URL from the argument
            self.start_urls = [url]
            # Extract the domain from the URL to set allowed_domains
            domain = re.search(r'https?://([^/]+)', url).group(1)
            self.allowed_domains = [domain]
        else:
            raise ValueError("You must provide a URL using -a url=http://example.com")
        
        if os.path.isdir(self.output_dir):
            shutil.rmtree(self.output_dir)


    def parse(self, response):
        """
        Parses the current page response, saves the HTML, and follows links.
        """
        # Ensure the output directory exists
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        # Sanitize the URL to create a valid filename
        # This replaces characters that are not allowed in filenames
        # such as slashes, colons, and question marks.
        sanitized_url = re.sub(r'[^a-zA-Z0-9.\-]', '_', response.url)
        if not sanitized_url:
            sanitized_url = 'index'

        # Construct the full path for the HTML file
        filename = os.path.join(self.output_dir, f'{sanitized_url}.html')

        # Save the HTML content of the page to a file
        self.log(f'Saving HTML page: {filename}')
        try:
            with open(filename, 'wb') as f:
                f.write(response.body)
        except Exception as e:
            self.log(f'Error saving file {filename}: {e}', level=scrapy.log.ERROR)

        # Create a new item to hold the data and yield it
        item = MyScraperItem()
        item['url'] = response.url
        item['filename'] = filename
        yield item

        # Follow all links found on the page
        # This creates a new request for each link discovered on the page.
        # It's a simple way to crawl an entire site.
        for href in response.css('a::attr(href), area::attr(href), iframe::attr(src)'):
            yield response.follow(href, self.parse)
