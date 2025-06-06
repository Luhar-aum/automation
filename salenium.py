# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.common.keys import Keys
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# import time

# EMAIL = ""
# PASSWORD = ""

# driver = webdriver.Chrome()

# try:
#     # Open the login page
#     driver.get("https://app.joinhomebase.com/accounts/sign-in")

#     WebDriverWait(driver, 20).until(
#         EC.visibility_of_element_located((By.NAME, "email"))
#     )

 
#     email_input = driver.find_element(By.NAME, "email")
#     email_input.send_keys(EMAIL)

#     password_input = driver.find_element(By.NAME, "password")
#     password_input.send_keys(PASSWORD)

#     sign_in_button = WebDriverWait(driver, 20).until(
#         EC.element_to_be_clickable((By.XPATH, "//button[.//span[text()='Sign in']]"))
#     )
#     sign_in_button.click()

#     print("✅ Logged in successfully. Waiting for your next instruction...")

#     timesheet_link = WebDriverWait(driver, 20).until(
#     EC.visibility_of_element_located((By.LINK_TEXT, "Timesheets"))
#     )
#     timesheet_link.click()


#     pay_period_button = WebDriverWait(driver, 20).until(
#     EC.element_to_be_clickable((By.XPATH, "//button[@data-testid='timesheets-tab-nav-pay_period_review']"))
#     )
#     pay_period_button.click()


#     date_input = WebDriverWait(driver, 20).until(
#     EC.element_to_be_clickable((By.NAME, "DateRangeInput"))
#     )
#     date_input.click()


#     yesterday_button = WebDriverWait(driver, 20).until(
#     EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'Preset') and text()='Yesterday']"))
#     )
#     yesterday_button.click()

#     apply_button = WebDriverWait(driver, 20).until(
#     EC.element_to_be_clickable((By.XPATH, "//button[.//span[text()='Apply']]"))
#     )
#     apply_button.click()

#     #span[contains(text)
#     download_button = WebDriverWait(driver, 20).until(
#     EC.element_to_be_clickable((By.XPATH, "//button[.//span[contains(text(), 'Download')]]"))
#     )
#     download_button.click()


#     wait = WebDriverWait(driver, 20)  #wait untiul it is clickable
#     customize_button = wait.until(EC.element_to_be_clickable((By.XPATH,"//button[.//span[contains(text(), 'Customize')]]"))
#     )
#     customize_button.click()

#     time.sleep(5)  # Optional delay


#     download_button = driver.find_element(By.CSS_SELECTOR, "a[href*='/timesheets/download.csv']")
#     download_button.click()


# WebDriverWait(driver, 20).until(
    # EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="ModalCloseIcon"]'))
# ).click()
# 


#     while True:
#         time.sleep(10)

# except Exception as e:
#     print("❌ An error occurred:", e)
#     driver.quit()




from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

EMAIL = ""
PASSWORD = ""
URL = "https://app.joinhomebase.com/accounts/sign-in"


def login(driver, wait):
    driver.get(URL)
    wait.until(EC.visibility_of_element_located((By.NAME, "email"))).send_keys(EMAIL)
    driver.find_element(By.NAME, "password").send_keys(PASSWORD)

    sign_in = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[.//span[text()='Sign in']]")))
    sign_in.click()
    print("✅ Logged in successfully.")

def open_timesheets(driver, wait):
    wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Timesheets"))).click()
    wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@data-testid='timesheets-tab-nav-pay_period_review']"))).click()
    print(" Opened Timesheets > Pay Period Review tab.")

def select_yesterday_date_range(wait):
    wait.until(EC.element_to_be_clickable((By.NAME, "DateRangeInput"))).click()
    wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'Preset') and text()='Yesterday']"))).click()
    wait.until(EC.element_to_be_clickable((By.XPATH, "//button[.//span[text()='Apply']]"))).click()
    print("📅 'Yesterday' date range selected and applied.")

def download_csv(driver, wait):
    wait.until(EC.element_to_be_clickable((By.XPATH, "//button[.//span[contains(text(), 'Download')]]"))).click()
    wait.until(EC.element_to_be_clickable((By.XPATH, "//button[.//span[contains(text(), 'Customize')]]"))).click()
    
    time.sleep(3)  # Optional: Replace with wait if dynamic content loading

    csv_link = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href*='/timesheets/download.csv']")))
    csv_link.click()
    print(" CSV file download initiated.")
    
    close_icon = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, '[data-testid="ModalCloseIcon"]'))
        )
    close_icon.click()
    print("✅ Modal closed.")


def main():
    driver = webdriver.Chrome()
    wait = WebDriverWait(driver, 20)

    try:
        login(driver, wait)
        # open_timesheets(driver, wait)
        # select_yesterday_date_range(wait)
        # download_csv(driver, wait)

        print("✅ All steps completed. Script is now idle.")
        while True:
            time.sleep(10)

    except Exception as e:
        print("❌ An error occurred:", e)

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
