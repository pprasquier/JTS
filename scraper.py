import logging
import requests
import csv


from bs4 import BeautifulSoup
from prefy import PreferencesWrapper

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s -  %(filename)s - %(lineno)d - %(message)s')

class WebParser():
    def __init__(self,provider,url,content_div_name=None,content_div_class=None):
        self.provider=provider
        self.url=url
        self.content_div_name=content_div_name
        self.content_div_class=content_div_class

class ParserDefinitions():
    def __init__(self,file_path):
        self.file_path=file_path
        self.parsers=[]
        self.refresh_parsers()

    def refresh_parsers(self):
        with open(self.file_path, newline='') as csvfile:
            csv_reader = csv.DictReader(csvfile)
            for row in csv_reader:
                self.parsers.append(WebParser(provider=row['Provider'],url=row['URL'],content_div_name=row['Content_DIV'],content_div_class=row['Content_CLASS']))

class Page(PreferencesWrapper):
    def __init__(self,url,provider=None) -> None:
        try:
            super().__init__()
            self.parser_list=ParserDefinitions(file_path=self.settings.parser_definition_file_path)
            self.url=url
            self.response=requests.get(url)
            self.html=self.response.content
            self.soup=BeautifulSoup(self.html,'html.parser') 
            self.provider=provider
            self.parser=None
            self.derive_provider_and_parser()
                  
        except (requests.exceptions.InvalidURL,requests.exceptions.HTTPError,requests.exceptions.URLRequired,requests.exceptions.MissingSchema) as e:
            logging.warning('Invalid URL: {}'.format(e))
            raise
            
        except Exception as e:
           logging.error('Error {} .'.format(e))
           raise Exception
    
    def derive_provider_and_parser(self):
        # Try to derive the provider from the URL
        if self.provider is None:
            for parser in self.parser_list.parsers:
                if parser.url in self.url:
                    self.provider=parser.provider
                    self.parser=parser
                    break
        else:
            for parser in self.parser_list.parsers:
                if parser.provider==self.provider:
                    self.parser=parser
                    break          
    
    def get_content(self):
        try:
            if self.parser is None:
                logging.warning("Parser not found or page not accessible without login. Consider creating a text file with the content of the job post and import it.")
                return None
            if self.parser.content_div_name is not None and self.parser.content_div_name !='':
                self.raw_content=self.soup.find(id=self.parser.content_div_name)
                self.content=self.raw_content.get_text()       
                        
            return self.content
                    
        except Exception as e:
           logging.error('Error {} .'.format(e))
           raise Exception

def test():
    testPage=Page("https://remotive.com/remote-jobs/product/staff-product-manager-1907158")
#    testPage=Page("https://jobs.careers.microsoft.com/global/en/job/1679717/Principal-Product-Manager")
    print(testPage.get_content())
    
if __name__ == "__main__":
    test()