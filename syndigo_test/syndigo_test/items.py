# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy
from scrapy.loader.processors import TakeFirst


class SyndigoTestItem(scrapy.Item):
    # define the fields for your item here like:
    url = scrapy.Field(output_processor=scrapy.loader.processors.TakeFirst())
    tcin = scrapy.Field(output_processor=scrapy.loader.processors.TakeFirst())
    upc = scrapy.Field(output_processor=scrapy.loader.processors.TakeFirst())
    price_amount = scrapy.Field(output_processor=scrapy.loader.processors.TakeFirst())
    currency = scrapy.Field(output_processor=scrapy.loader.processors.TakeFirst())
    description = scrapy.Field(output_processor=scrapy.loader.processors.TakeFirst())
    features = scrapy.Field()
    bullets = scrapy.Field()
    ingredients = scrapy.Field()
    specs = scrapy.Field(output_processor=scrapy.loader.processors.TakeFirst())
    questions = scrapy.Field()
