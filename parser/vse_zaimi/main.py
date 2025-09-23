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

    def expand_all_reviews(self):
        """Кликает по кнопке 'Показать полностью' во всех отзывах"""
        try:
            buttons = self.driver.find_elements(By.CLASS_NAME, "responses-item__more")
            for btn in buttons:
                try:
                    self.driver.execute_script("arguments[0].click();", btn)
                    time.sleep(0.3)
                except Exception:
                    pass
        except Exception as e:
            logging.warning(f"Ошибка при попытке раскрытия отзывов: {e}")

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
            logging.exception("Не удалось расарсить дату")
            logging.exception(e)
            return date_text
    
    def extract_review_data(self, review_element):
        """Извлечение данных из отзыва (обновлённая версия под новую верстку)"""
        try:
            html = review_element.get_attribute('outerHTML')
            soup = BeautifulSoup(html, 'lxml')


            title_tag = soup.select_one('div[class*="StyledTitleItem"] a')
            title = title_tag.text.strip() if title_tag else 'Без заголовка'


            text_tag = soup.select_one('div[class*="StyledItemText"] a')
            text = text_tag.text.strip() if text_tag else ''
            text = self.clean_text(text)


            rating_tag = soup.select_one('div.Grade__sc-m0t12o-0')
            rating = int(rating_tag.text.strip()) if rating_tag else 0


            date_tag = soup.select_one('span[class*="StyledItemSmallText"]')
            date_text = date_tag.text.strip() if date_tag else ''
            try:
                date = datetime.strptime(date_text, '%d.%m.%Y %H:%M').strftime('%Y-%m-%d %H:%M')
            except Exception as e:
                logging.exception(e)
                date = date_text

            has_bank_reply = bool(soup.select_one('[data-test="responses__response-tag-answered"]'))
            has_docs = bool(soup.select_one('[data-test="responses__response-tag-documents"]'))

            return {
                'title': title,
                'text': text,
                'rating': rating,
                'date': date,
                'has_bank_reply': has_bank_reply,
                'has_docs': has_docs,
                'source': 'banki.ru'
            }

        except Exception as e:
            logging.warning(f"Ошибка извлечения данных: {e}")
            return None
        except Exception as e:
            logging.info(f"Ошибка извлечения данных: {e}")
            return None
    
    def scrape_gazprombank_reviews(self, max_clicks=10):
        """Скрейпит отзывы с подгрузкой по кнопке 'Показать ещё'"""
        url = "https://vsezaimyonline.ru/banks/gazprombank/reviews"
        all_reviews = set()
        seen_elements = set()

        try:
            logging.info("Запускаем скрейпинг Газпромбанка...")
            logging.info(f"Запланировано итераций: {max_clicks}")
            self.driver.get(url)
            time.sleep(5)

            """
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CLASS_NAME, "cookie-warning__button"))
                ).click()
                logging.info("Cookies приняты")
            except Exception:
                logging.info("Cookie-баннер не найден или уже принят")
            """

            for click_num in range(max_clicks):
                logging.info(f"🔁 Подгрузка блока {click_num + 1} из {max_clicks}...")

                self.scroll_page()
                time.sleep(1)

                review_elements = self.driver.find_elements(By.CSS_SELECTOR, '[data-test="responses__response"]')
                logging.info(f"📦 Найдено {len(review_elements)} отзывов на текущем этапе")

                for el in review_elements:
                    el_id = el.get_attribute("outerHTML")
                    if el_id in seen_elements:
                        continue
                    seen_elements.add(el_id)

                    review_data = self.extract_review_data(el)
                    if review_data:
                        all_reviews.add(json.dumps(review_data, ensure_ascii=False))  # В set только хэши или строки

                try:
                    show_more = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Показать еще')]"))
                    )
                    self.driver.execute_script("arguments[0].click();", show_more)
                    time.sleep(2)
                except Exception:
                    logging.info("🔚 Кнопка 'Показать ещё' не найдена — конец отзывов.")
                    break

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
    try:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[logging.StreamHandler()]
        )
        logging.info("🚀 Запуск скрейпера Газпромбанка...")

        scraper = GazprombankScraper(headless=False)
        

        reviews = scraper.scrape_gazprombank_reviews(max_clicks=420)

        if reviews:
            df = scraper.save_results(reviews)
            logging.info(f"\n✅ Успешно собрано отзывов: {len(reviews)}")
        else:
            logging.info("❌ Не удалось собрать отзывы")
    except Exception as e:
        logging.error(e)