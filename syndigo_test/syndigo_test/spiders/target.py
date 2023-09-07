import scrapy
from loguru import logger
import re
from datetime import datetime
from syndigo_test.items import SyndigoTestItem
from scrapy.loader import ItemLoader  # Import ItemLoader

class TargetSpider(scrapy.Spider):
    name = "target"
    allowed_domains = ["www.target.com", "redsky.target.com", "r2d2.target.com"]
    ROBOTSTXT_OBEY = False

    def __init__(self, start_url=None):
        self.start_urls = [start_url] if start_url else ['https://www.target.com/p/-/A-79344798']
        self.data = dict()
        self.qa = []
        self.map_currency = {
            '$': 'USD',
            '€': 'EURO',
            '£': 'POUND',
            '¥': 'YEN',
            '₹': 'RUPEES'
        }
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
        }
        self.product_data = SyndigoTestItem()

    def start_requests(self):
        logger.info(f'Processing for {self.start_urls[0]}')
        yield scrapy.Request(self.start_urls[0], self.parse)

    def parse(self, response):
        script_data = response.xpath('//script[contains(text(),"propNames")]/text()').get()
        if script_data:
            discription = response.xpath('//meta[@name="description"]/@content').get()
            script_data = script_data.replace('\\', '')
            logger.info('script data is present')
            is_api = re.findall(r'apiKey":"(\d.+)","wh', script_data)
            is_store_id = re.findall(r'store_id":"(\d+)', script_data)
            if is_api and is_store_id:
                api_key = is_api[0]
                tcin = response.url.split('-')[-1]
                data_url = f"https://redsky.target.com/redsky_aggregations/v1/web/pdp_client_v1?key={api_key}&tcin={tcin}&store_id={is_store_id[0]}&pricing_store_id={is_store_id[0]}"
                yield scrapy.Request(data_url, self.parse_data, headers=self.headers, meta={"api_key": api_key, "tcin": tcin, 'discription': discription})
            else:
                logger.error('issue in getting api_key and store_id, please check regex')
        else:
            logger.info('script data not present, Please check')

    def parse_data(self, response):
        loader = ItemLoader(item=SyndigoTestItem(), response=response)
        logger.info(f'fetching data from api - {response.url}')
        meta_data = response.meta
        json_response = response.json()
        try:
            currency = self.map_currency.get(json_response.get('data', {}).get('product', {}).get('price', {}).get('formatted_current_price')[0])
        except Exception as e:
            currency = ''
            logger.error(f'Error while fetching currency:: {e}')
        try:
            ingredients = json_response.get('data', {}).get('product', {}).get('item', {}).get('enrichment', {}).get('nutrition_facts', {}).get('ingredients', '').replace('ingredients:', '').split(',')
            ingredients = [ingredient.strip() for ingredient in ingredients]
        except:
            ingredients = []
            logger.info('issue while fetching ingredients')

        loader.add_value('url', json_response.get('data', {}).get('product', {}).get('item', {}).get('enrichment', {}).get('buy_url', ''))
        loader.add_value('tcin', meta_data.get('tcin', ''))
        loader.add_value('upc', json_response.get('data', {}).get('product', {}).get('item', {}).get('primary_barcode', ''))
        loader.add_value('price_amount', json_response.get('data', {}).get('product', {}).get('price', {}).get('current_retail', '') or json_response.get('data', {}).get('product', {}).get('price', {}).get('current_retail_min', '')) 
        loader.add_value('currency', currency)
        loader.add_value('description', meta_data.get('discription'))
        loader.add_value('features', [feature.replace('<B>', '').replace('</B>', '') for feature in json_response.get('data', {}).get('product', {}).get('item', {}).get('product_description', {}).get('bullet_descriptions')])
        loader.add_value('bullets', json_response.get('data', {}).get('product', {}).get('item', {}).get('product_description', {}).get('soft_bullets', {}).get('bullets'))
        loader.add_value('ingredients', ingredients)
        qa_url = f"https://r2d2.target.com/ggc/Q&A/v1/question-answer?key={meta_data.get('api_key', '')}&page=0&questionedId={meta_data.get('tcin', '')}&type=product&size=10"
        # in above qa_url, size params value we can change to 100 (so less number of request in case of more questions)
        yield scrapy.Request(qa_url, self.parse_qa, headers=self.headers, meta={"loader": loader, "api_key": meta_data.get('api_key', ''), "tcin": meta_data.get('tcin', ''), "current_page": 1})


    ### custome method get date as per requirement
    def get_date(self, _date):
        timestamp = datetime.strptime(_date, '%Y-%m-%dT%H:%M:%SZ')
        return timestamp.strftime('%Y-%m-%d')

    def parse_qa(self, response):
        logger.info(f'fetching quations and answers from api - {response.url}')
        meta_data = response.meta
        loader = meta_data["loader"]
        json_response = response.json()
        total_pages = json_response.get('total_pages', 0)
        for result in json_response.get('results'):
            answer_data = []
            answers = result.get('answers')
            for answer in answers:
                temp = {
                    'answer_id': answer.get('id'),
                    'answer_summary': answer.get('text'),
                    'submission_date': self.get_date(answer.get('submitted_at')),
                    'user_nickname': answer.get('author', {}).get('nickname', '')
                }
                answer_data.append(temp)
            qustion = {
                'question_id': result.get('id', ''),
                'submission_date': self.get_date(result.get('submitted_at')),
                'question_summary': result.get('text'),
                'user_nickname': result.get('author', {}).get('nickname', ''),
                'answers': answer_data
            }
            self.qa.append(qustion)
        if total_pages > meta_data.get('current_page'):
            qa_url = f"https://r2d2.target.com/ggc/Q&A/v1/question-answer?key={meta_data.get('api_key', '')}&page={meta_data.get('current_page')}&questionedId={meta_data.get('tcin', '')}&type=product&size=10"
            yield scrapy.Request(qa_url, self.parse_qa, headers=self.headers, meta={"loader": loader, "api_key": meta_data.get('api_key', ''), "tcin": meta_data.get('tcin', ''), "current_page": meta_data.get('current_page')+1})
        else:
            loader.add_value('questions', self.qa)
            logger.info('Done scraping....!!!')
            yield loader.load_item()

