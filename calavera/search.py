from scrapy import Request, Spider
from RareCaratSpider.items import HotelItemLoader, ReviewItemLoader


class CalaveraSpider(Spider):
    """This class manages all the logic required for scraping the Rare Carat website.

    Attributes:
        name (str): The unique name of the spider.
        start_url (str): Root of the website and first URL to scrape.
        custom_settings (dict): Custom settings for the scraper
    """

    name = "calavera"

    start_url = "https://calaveranewyork.com/search?q=LG768694303&options%5Bprefix%5D=last"

    custom_settings = {
        "DEFAULT_REQUEST_HEADERS": {
            "Connection": "close",
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,
            'scrapers.middlewares.retry.RetryMiddleware': 550,
        },
    }

    def start_requests(self):
        """This method start 10 separate sessions on the homepage, one per page."""
        for page in range(1, 10):
            yield Request(
                url=self.start_url,
                callback=self.parse,
                errback=self.errback,
                dont_filter=True,
                meta=dict(
                    page=page,
                    cookiejar="jar%d" % page,
                ),
            )

    def parse(self, response):
        """After accessing the website's homepage, we retrieve the list of diamonds from page X."""
        yield Request(
            url=response.urljoin("diamonds?page=%d" % response.meta['page']),
            callback=self.parse_listing,
            errback=self.errback,
            meta=response.meta,
        )

    def parse_listing(self, response):
        """This method parses the list of diamonds from page X."""
        for el in response.css('.diamond-link'):
            yield response.follow(
                url=el,
                callback=self.parse_diamond,
                errback=self.errback,
                meta=response.meta,
            )

    def parse_diamond(self, response):
        """This method parses diamond details such as name, email, and reviews."""
        reviews = [self.get_review(review_el) for review_el in response.css('.diamond-review')]

        diamond = HotelItemLoader(response=response)
        diamond.add_css('name', '.diamond-name::text')
        diamond.add_css('email', '.diamond-email::text')
        diamond.add_value('reviews', reviews)
        return diamond.load_item()

    def get_review(self, review_el):
        """This method extracts rating from a review"""
        review = ReviewItemLoader(selector=review_el)
        review.add_css('rating', '.review-rating::text')
        return review.load_item()

    def errback(self, failure):
        """This method handles and logs errors and is invoked with each request."""
        print_failure(self.logger, failure)