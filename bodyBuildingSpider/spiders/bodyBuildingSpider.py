import scrapy
from pandas import DataFrame
import re
import urllib
import os

class BodyBuildingSpider(scrapy.Spider):
    main_urls = [{'link':'https://www.bodybuilding.com/fun/healthy-breakfast-recipes.html',
                  'label':'Breakfast',
                  'DataFrame':DataFrame(dtype = str)},
                 {'link': 'https://www.bodybuilding.com/fun/healthy-lunch-recipes.html',
                  'label': 'Lunch',
                  'DataFrame': DataFrame( dtype=str)},
                 {'link': 'https://www.bodybuilding.com/fun/healthy-dinner-recipes.html',
                  'label': 'Dinner',
                  'DataFrame': DataFrame(dtype=str)}]
    name='bodyBuilding'
    def start_requests(self):
        for idx in range(len(self.main_urls)):
            mainURLLabel = self.main_urls[idx]['label']
            self.logger.info('start_requests: Parsing {} Pages'.format(mainURLLabel))
            #check if directory with label name exists or not if not exists create it
            #if not(os.path.exists(mainURLLabel) and os.path.isdir(mainURLLabel)):
            os.makedirs(mainURLLabel, exist_ok=True)
            request = scrapy.Request(url=self.main_urls[idx]['link'], callback=self.parseMainURL)
            request.meta['mainURLIdx'] = idx
            yield request

    def parseMainURL(self, response):
        mainURLIdx = response.meta['mainURLIdx']
        for article_link in response.css('div.small-article-graphic a'):
            self.logger.info('parseMainURL: Parsing {} link: {}'.format(self.main_urls[mainURLIdx]['label'], article_link.css('::attr(href)').extract_first()))
            request = response.follow(article_link, callback=self.parseSecondaryURL)
            request.meta['mainURLIdx'] = mainURLIdx
            yield request

    def parseSecondaryURL(self, response):
        mainURLIdx = response.meta['mainURLIdx']
        for link in response.css('a'):
            if link.css('::text').extract_first() == 'View Recipe Here':
                self.logger.info('parseSecondaryURL: Parsing {} link: {}'.format(self.main_urls[mainURLIdx]['label'], link.css('::attr(href)').extract_first()))
                request = response.follow(link, callback=self.parseRecipe)
                request.meta['mainURLIdx'] = mainURLIdx
                request.meta['link'] = link.css('::attr(href)').extract_first()
                yield request

    def parseRecipe(self, response):
        self.logger.info('parseRecipe Started')
        mainURLIdx = response.meta['mainURLIdx']
        RecipeContent = {}
        RecipeContent['link'] = response.meta['link']
        self.logger.info('Parsing Recipe at: {}'.format(RecipeContent['link']))
        RecipeContent['Title'] = response.css('h1.bb-recipe-headline-title::text').extract_first()
        image_link = response.css('div.bb-recipe-header-image img::attr(src)').extract_first()
        RecipeContent['Image'] = self.extractImageNameFromLink(image_link)
        for nutrition_object in response.css('div.bb-recipe__meta-nutrient'):
            value = nutrition_object.css('span.bb-recipe__meta-nutrient-value::text').extract_first()
            label = nutrition_object.css('span.bb-recipe__meta-nutrient-label::text').extract_first()
            RecipeContent[label] = value
        RecipeContent['Description'] = response.css('p.BBCMS__content--article-description strong::text').extract_first()
        ingredients_text = ''
        for ingredient in response.css('li.bb-recipe__ingredient-list-item'):
            ingredient_text = ingredient.css('::text').extract_first()
            ingredient_text = self.removeExtraSpacesAndQuotes(ingredient_text)
            ingredients_text += ingredient_text + ';';
        ingredients_text = ingredients_text.strip(';')#removing extra semi-colon
        RecipeContent['Ingredients'] = ingredients_text
        RecipeContent['Prep'] = response.css('div.bb-recipe__directions-timing--prep time::text').extract_first()
        RecipeContent['Cook'] = response.css('div.bb-recipe__directions-timing--cook time::text').extract_first()
        directions_text = ''
        for direction_text in response.css('li.bb-recipe__directions-list-item::text'):
            directions_text += direction_text.extract() + ';'
        directions_text = directions_text.strip(';')
        RecipeContent['Directions'] = directions_text
        tags_text = ''
        for tag_text in response.css('div.bb-recipe__desktop-tags div.bb-recipe__topic a::text'):
            tags_text += tag_text.extract() + ';'
        tags_text = tags_text.strip(';')
        RecipeContent['Recipe Tags'] = tags_text
        self.logger.info('Found Recipe Informations: {}'.format(RecipeContent))
        self.main_urls[mainURLIdx]['DataFrame'] = self.main_urls[mainURLIdx]['DataFrame'].append(RecipeContent, ignore_index=True)
        #request = response.follow(image_link, callback=self.saveImage)
        #request.meta['fileName'] = RecipeContent['Image']
        #yield request#SaveImage with a request at the end of this request
        #image_data = request.urlopen(image_link)
        #with open(self.main_urls[mainURLIdx]['label'] + '/' + RecipeContent['Image'], 'wb') as f:
            #f.write(image_data)
        label = self.main_urls[mainURLIdx]['label']
        self.main_urls[mainURLIdx]['DataFrame'].to_excel(label + '/' + label + '.xlsx')
        urllib.request.urlretrieve(image_link, self.main_urls[mainURLIdx]['label'] + '/' + RecipeContent['Image'])


    def saveImage(self, response):
        fileName = response.meta['fileName']
        with open(fileName, mode='wb') as f:
            #f.
            pass

    def removeExtraSpacesAndQuotes(self, text):
        new_text = re.sub('\s+|"', ' ', text).strip()
        return new_text

    def extractImageNameFromLink(self, imageLink):
        tokens = imageLink.split('/')
        imageName = tokens[-1]
        return imageName

    def closed(self, reason):
        self.logger.info('Spider will be closed because: {}'.format(reason))
        for main_url in self.main_urls:
            label = main_url['label']
            main_url['DataFrame'].to_excel(label + '/' + label + '.xlsx')