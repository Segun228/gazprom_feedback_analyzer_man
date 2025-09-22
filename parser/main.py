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

class GazprombankScraper:
    def __init__(self, headless=True):
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
    
    def parse_date(self, date_text):
        """Парсинг даты из текста"""
        try:
            months = {
                'января': '01', 'февраля': '02', 'марта': '03',
                'апреля': '04', 'мая': '05', 'июня': '06',
                'июля': '07', 'августа': '08', 'сентября': '09',
                'октября': '10', 'ноября': '11', 'декабря': '12'
            }
            
            for ru_month, num_month in months.items():
                if ru_month in date_text:
                    date_text = date_text.replace(ru_month, num_month)
                    break
            
            date_obj = datetime.strptime(date_text, '%d %m %Y')
            return date_obj.strftime('%Y-%m-%d')
            
        except Exception as e:
            logging.exception(e)
            return date_text  # Возвращаем как есть если не удалось распарсить
    
    def extract_review_data(self, review_element):
        """Извлечение данных из отзыва"""
        try:
            # Используем BeautifulSoup для парсинга HTML
            html = review_element.get_attribute('outerHTML')
            soup = BeautifulSoup(html, 'lxml')
            
            # Извлекаем основные данные
            author = soup.find('div', class_='response-page__header__author')
            author = author.text.strip() if author else 'Аноним'
            
            date = soup.find('div', class_='response-page__header__date')
            date = date.text.strip() if date else 'Не указана'
            date = self.parse_date(date)
            
            # Текст отзыва
            text_div = soup.find('div', class_='response-page__text')
            text = text_div.text.strip() if text_div else ''
            text = self.clean_text(text)
            
            # Рейтинг (если есть)
            rating = 0
            rating_div = soup.find('div', class_='response-page__header__rating')
            if rating_div:
                stars = rating_div.find_all('svg', class_='icon-star')
                rating = len([star for star in stars if 'icon-star_active' in str(star)])
            
            # Продукт (если указан)
            product = soup.find('a', class_='response-page__header__product')
            product = product.text.strip() if product else 'Не указан'
            
            return {
                'author': author,
                'date': date,
                'rating': rating,
                'product': product,
                'text': text,
                'source': 'banki.ru'
            }
            
        except Exception as e:
            logging.info(f"Ошибка извлечения данных: {e}")
            return None
    
    def scrape_gazprombank_reviews(self, max_pages=10):
        """Основная функция скрейпинга"""
        url = "https://www.banki.ru/services/responses/bank/gazprombank/"
        all_reviews = []
        
        try:
            logging.info("Запускаем скрейпинг Газпромбанка...")
            self.driver.get(url)
            
            try:
                cookie_btn = self.wait.until(
                    EC.element_to_be_clickable((By.CLASS_NAME, "cookie-warning__button"))
                )
                cookie_btn.click()
                logging.info("Cookies приняты")
                time.sleep(1)
            except Exception as e:
                logging.exception(e)
                pass
            
            current_page = 1
            
            while current_page <= max_pages:
                logging.info(f"Обрабатываем страницу {current_page}...")
                
                self.wait.until(
                    EC.presence_of_element_located((By.CLASS_NAME, "response-page"))
                )
                
                self.scroll_page()
                time.sleep(2)
                
                review_elements = self.driver.find_elements(By.CLASS_NAME, "response-page")
                logging.info(f"Найдено отзывов на странице: {len(review_elements)}")
                
                for element in review_elements:
                    review_data = self.extract_review_data(element)
                    if review_data:
                        all_reviews.append(review_data)
                
                if not self.go_to_next_page() or current_page >= max_pages:
                    break
                
                current_page += 1
                time.sleep(3)
            
        except Exception as e:
            logging.error(f"Ошибка при скрейпинге: {e}")

        finally:
            self.driver.quit()
        
        return all_reviews
    
    def scroll_page(self):
        """Прокрутка страницы"""
        try:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
        except Exception as e:
            logging.exception(e)
            pass
    
    def go_to_next_page(self):
        """Переход на следующую страницу"""
        try:
            next_buttons = self.driver.find_elements(By.CSS_SELECTOR, ".paginator__item-next:not(.paginator__item-disabled)")
            
            if next_buttons:
                next_buttons[0].click()
                time.sleep(2)
                return True
            return False
            
        except Exception as e:
            logging.error(f"Ошибка при скрейпинге: {e}")
    
    def save_results(self, reviews, filename_prefix="gazprombank_reviews"):
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
    logging.info("🚀 Запуск скрейпера Газпромбанка...")

    scraper = GazprombankScraper(headless=False)
    

    reviews = scraper.scrape_gazprombank_reviews(max_pages=10)
    

    if reviews:
        df = scraper.save_results(reviews)
        logging.info(f"\n✅ Успешно собрано отзывов: {len(reviews)}")
        logging.info("\n📊 Пример данных:")
        logging.info(df[['date', 'rating', 'product', 'text']].head(3).to_string())
    else:
        logging.info("❌ Не удалось собрать отзывы")