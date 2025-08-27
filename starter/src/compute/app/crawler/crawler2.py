import scrapy
from scrapy.crawler import CrawlerProcess
from urllib.parse import urlparse


class SmartSpider(scrapy.Spider):
    name = "smart_spider"

    def __init__(self, start_url=None, *args, **kwargs):
        super(SmartSpider, self).__init__(*args, **kwargs)
        self.start_url = start_url
        self.allowed_domain = urlparse(start_url).netloc if start_url else None

    def start_requests(self):
        if not self.start_url:
            self.logger.error("You must provide start_url (root page or sitemap)")
            return
        yield scrapy.Request(self.start_url, callback=self.parse)

    def parse(self, response):
        content_type = response.headers.get("Content-Type", b"").decode("utf-8")

        # Case 1: XML Sitemap (sitemap index or urlset)
        if "xml" in content_type or response.text.strip().startswith("<?xml"):
            # Detect sitemap index
            sitemap_locs = response.xpath("//sitemap/loc/text()").getall()
            if sitemap_locs:
                for loc in sitemap_locs:
                    yield scrapy.Request(url=loc, callback=self.parse)
                return

            # Detect urlset (normal sitemap)
            url_locs = response.xpath("//url/loc/text()").getall()
            for loc in url_locs:
                if self.allowed_domain in urlparse(loc).netloc:
                    yield scrapy.Request(url=loc, callback=self.parse)
            return

        # Case 2: HTML page
        if "html" in content_type or "<html" in response.text.lower():
            yield {
                "url": response.url,
                "title": response.xpath("//title/text()").get(),
            }

            for href in response.css("a::attr(href)").getall():
                absolute_url = response.urljoin(href)
                if self.allowed_domain in urlparse(absolute_url).netloc:
                    yield response.follow(absolute_url, callback=self.parse)


if __name__ == "__main__":
    process = CrawlerProcess(settings={
        "FEEDS": {"output.json": {"format": "json"}},  # save results to file
        "LOG_LEVEL": "INFO",
        "ROBOTSTXT_OBEY": True,  # ✅ respect robots.txt
    })

    # Example usage:
    # process.crawl(SmartSpider, start_url="https://example.com")
    # process.crawl(SmartSpider, start_url="https://example.com/sitemap.xml")
    process.crawl(SmartSpider, start_url="http://www.gueury.com/sitemap.xml")

    process.start()