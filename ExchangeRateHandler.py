from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium import webdriver

from constants import UNIFIED_CURRENCY

import time


SupportedCurrency = ['HKD', 'CNY', "GBP"]


LINK = "https://www.oanda.com/currency-converter/en/?from=CNY&to=USD&amount=12"

# baseCur_ctry_path = "/html/body/div[1]/main/div[1]/div/div/div[3]/div/div[1]/div[1]/div/div[2]/div[1]/div[1]/div/div[2]/div/div/div[1]/div"
baseCur_ctry_edit_path = "/html/body/div[1]/main/div[1]/div/div/div[3]/div/div[1]/div[1]/div/div[2]/div[1]/div[1]/div/div[2]/div/div/input"
baseCur_amt_path = "/html/body/div[1]/main/div[1]/div/div/div[3]/div/div[1]/div[1]/div/div[2]/div[1]/div[2]/div[1]/div/input"

# targetCur_ctry_path = "/html/body/div[1]/main/div[1]/div/div/div[3]/div/div[1]/div[1]/div/div[2]/div[3]/div[1]/div/div[2]/div/div/div[1]/div"
targetCur_ctry_edit_path = "/html/body/div[1]/main/div[1]/div/div/div[3]/div/div[1]/div[1]/div/div[2]/div[3]/div[1]/div/div[2]/div/div/input"
targetCur_amt_path = "/html/body/div[1]/main/div[1]/div/div/div[3]/div/div[1]/div[1]/div/div[2]/div[3]/div[2]/div[1]/div/input"


class ExchangeRateHandler:
    currency = 0
    driver = None

    def change_currency(self, cur: str, path) -> None:
        text_box = self.driver.find_element('xpath', path)
        text_box.click()
        text_box.send_keys(cur)
        text_box.send_keys(Keys.DOWN)
        text_box.send_keys(Keys.ENTER)

    def enter_amount(self, amount: str, path) -> None:
        text_box = self.driver.find_element('xpath', path)
        text_box.send_keys(Keys.CONTROL + "a")
        text_box.send_keys("\b" + amount)

    def get_amount(self, path) -> str:
        text_box = self.driver.find_element('xpath', path)
        return text_box.get_attribute('value')

    def quit(self):
        self.driver.quit()

    def __call__(self, base: str, amount: str, target=UNIFIED_CURRENCY) -> str:
        if not is_supported_currency(base):
            raise ValueError("Unsupported currency")
        elif base == target:
            return amount

        self.driver = webdriver.Edge()
        self.driver.get(LINK)

        present = EC.presence_of_element_located(('xpath', baseCur_ctry_edit_path))  # check if button clickable
        WebDriverWait(self.driver, 180).until(present)

        self.change_currency(base, baseCur_ctry_edit_path)
        self.change_currency(target, targetCur_ctry_edit_path)
        self.enter_amount(amount, baseCur_amt_path)
        time.sleep(0.3)
        return self.get_amount(targetCur_amt_path)


def is_supported_currency(currency: str) -> bool:
    return currency in SupportedCurrency


def switch_currency(currency: str) -> str:
    currency = SupportedCurrency.index(currency)
    currency = (currency + 1) % len(SupportedCurrency)
    return SupportedCurrency[currency]


if __name__ == '__main__':
    a = ExchangeRateHandler()
    print(a('CNY', '10'))
    input()
