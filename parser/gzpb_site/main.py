from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import logging
import pandas as pd
import time
import re
from datetime import datetime
import json
import dateparser


class GazprombankScraperVBT:
    def __init__(self, headless=False):
        self.driver = None
        self.setup_driver(headless)
        
    def setup_driver(self, headless):
        """Настройка браузера"""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 20)

    def clean_text(self, text):
        """Очистка текста от лишних символов"""
        if not text:
            return ""
        
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        text = re.sub(r'©.*?$', '', text)
        text = re.sub(r'Ответ банка.*', '', text)
        text = re.sub(r'Показать полностью', '', text)
        
        return text

    def parse_date(self, date_text: str) -> str:
        """Парсинг даты из текста, поддерживает dd.mm.yyyy и русские даты с месяцами и временем"""
        if not date_text or not date_text.strip():
            return ""

        try:
            try:
                date_obj = datetime.strptime(date_text, '%d.%m.%Y')
                return date_obj.strftime('%Y-%m-%d')
            except ValueError:
                pass


            date_obj = dateparser.parse(date_text, languages=['ru'])
            if date_obj:
                return date_obj.strftime('%Y-%m-%d %H:%M')
            else:
                logging.warning(f"Не удалось распарсить дату через dateparser: {date_text}")
                return date_text

        except Exception as e:
            logging.exception(f"Ошибка при разборе даты: {date_text}")
            return date_text
    
    def extract_review_data(self, review_element):
        """Извлечение данных из отзыва (обновлённая версия под новую верстку)"""
        try:
            html = review_element.get_attribute('outerHTML')
            soup = BeautifulSoup(html, 'lxml')



            title_tag = soup.select_one('.avatar-title-text')
            text_tag = soup.select_one('div.reviews-text > p.teaser')

            text = text_tag.text.strip() if text_tag else ''
            title = title_tag.text.strip() if title_tag else ''

            title = self.clean_text(title)
            text = self.clean_text(text)


            rating_tag = soup.select_one('.rating-star-simple')
            rating = int(rating_tag.text.strip()) if rating_tag else 0 # TODO


            date_tag = soup.select_one('.created')
            date_text = date_tag.text.strip() if date_tag else ''

            try:
                date = datetime.strptime(date_text, '%d.%m.%Y').strftime('%Y-%m-%d %H:%M')
            except Exception as e:
                logging.exception(e)
                date = date_text


            return {
                'title': title,
                'text': text,
                'rating': rating,
                'date': date,
                'has_bank_reply': "",
                'has_docs': "",
                'source': 'vbr.ru'
            }

        except Exception as e:
            logging.warning(f"Ошибка извлечения данных: {e}")
            return None
        except Exception as e:
            logging.info(f"Ошибка извлечения данных: {e}")
            return None
    
    def scrape_gazprombank_reviews(self, max_pages=10):
        """Скрейпит отзывы, переходя по страницам с параметром ?page=N"""
        base_url = "https://www.vbr.ru/banki/gazprombank/otzivy/"
        all_reviews = set()
        seen_elements = set()

        try:
            logging.info("🔍 Начинаем скрейпинг по страницам...")
            
            for page_num in range(1, max_pages + 1):
                page_url = f"{base_url}?page={page_num}" if page_num > 1 else base_url
                logging.info(f"📄 Переход на страницу {page_num}: {page_url}")
                
                self.driver.get(page_url)
                time.sleep(2)
                self.scroll_page()
                time.sleep(2)

                review_elements = self.driver.find_elements(By.CSS_SELECTOR, 'div.reviews-list-item')
                logging.info(f"📦 Найдено {len(review_elements)} отзывов на странице")

                for el in review_elements:
                    el_id = el.get_attribute("outerHTML")
                    if el_id in seen_elements:
                        continue
                    seen_elements.add(el_id)

                    review_data = self.extract_review_data(el)
                    if review_data:
                        all_reviews.add(json.dumps(review_data, ensure_ascii=False))

        except Exception as e:
            logging.error(f"Ошибка при скрейпинге: {e}")
        finally:
            self.driver.quit()

        parsed_reviews = [json.loads(r) for r in all_reviews]
        return parsed_reviews

    def scroll_page(self):
        """Прокрутка страницы"""
        try:
            for i in range(3):
                self.driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight*{(i+1)/3});")
                time.sleep(1.5)
        except Exception as e:
            logging.exception(e)
            pass


    def go_to_next_page(self):
        """Переход на следующую страницу пагинации (новая верстка)"""
        try:
            next_buttons = self.driver.find_elements(By.CSS_SELECTOR, "li.pager-item-next > button.btn")
            if not next_buttons:
                logging.info("Кнопка 'Вперед' не найдена — конец пагинации.")
                return False

            next_btn = next_buttons[0]

            self.driver.execute_script("arguments[0].click();", next_btn)
            time.sleep(2)
            return True

        except Exception as e:
            logging.error(f"Ошибка при переходе на следующую страницу: {e}")
            return False

    def save_results(self, reviews, filename_prefix="gazprombank_reviews_irecommend"):
        """Сохранение результатов"""
        df = pd.DataFrame(reviews)
        

        csv_file = f"{filename_prefix}.csv"
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        

        json_file = f"{filename_prefix}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(reviews, f, ensure_ascii=False, indent=2)
        

        excel_file = f"{filename_prefix}.xlsx"
        df.to_excel(excel_file, index=False)
        
        logging.info("\nРезультаты сохранены:")
        logging.info(f"CSV: {csv_file}")
        logging.info(f"JSON: {json_file}")
        logging.info(f"Excel: {excel_file}")
        
        return df


if __name__ == "__main__":
    try:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[logging.StreamHandler()]
        )
        logging.info("🚀 Запуск скрейпера Газпромбанка...")

        scraper = GazprombankScraperVBT(headless=False)
        

        reviews = scraper.scrape_gazprombank_reviews(max_pages=8)

        if reviews:
            df = scraper.save_results(reviews)
            logging.info(f"\n✅ Успешно собрано отзывов: {len(reviews)}")
        else:
            logging.info("❌ Не удалось собрать отзывы")
    except Exception as e:
        logging.error(e)