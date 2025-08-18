import scrapy
import os
import re

class TestSpider(scrapy.Spider):
    # Name of the spider
    name = 'test_spider'

    # The domains that this spider is allowed to crawl
    allowed_domains = ['gueury.com']

    # The URLs where the spider will start crawling
    start_urls = ['http://www.gueury.com/']

    # The directory where the HTML files will be stored
    output_dir = 'test'

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

        # Follow all links found on the page
        # This creates a new request for each link discovered on the page.
        # It's a simple way to crawl an entire site.
        for href in response.css('a::attr(href)'):
            yield response.follow(href, self.parse)