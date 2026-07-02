import selenium
from selenium.webdriver.common.by import By

driver = selenium.webdriver.Chrome()
driver.get("https://www.selenium.dev/selenium/web/web-form.html")

title = driver.title

driver.implicitly_wait(0.5)

text_box = driver.find_element(by=By.NAME, value="my-text")
submit_buton = driver.find_element(by=By.CLASS_NAME, value="button")

text_box.send_keys("Selenium")
submit_buton.click()

message = driver.find_element(by=By.CLASS_NAME, value="message")
text = message.text

driver.quit()