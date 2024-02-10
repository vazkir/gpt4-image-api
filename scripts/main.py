import os
import requests
import time
import json
import ast, textwrap

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc


load_dotenv()


options = uc.ChromeOptions()
options.headless = False
driver = uc.Chrome(options=options)
app = FastAPI()


class Payload(BaseModel):
    image_url: str
    prompt: str


ANSWER_FORMAT = "Answer ONLY by JSON following this format: " '{"answer": your answer}'


@app.get("/start")
async def start_session():
    driver.get("https://chat.openai.com/")
    time.sleep(3)
    login_button = driver.find_element(By.XPATH, '//div[text()="Log in"]')
    login_button.click()
    time.sleep(3)
    google = driver.find_element(By.XPATH, '//button[@data-provider="google"]')
    google.click()
    # find email field
    time.sleep(3)
    email = driver.find_element(By.XPATH, '//input[@type="email"]')
    email.send_keys(os.getenv("GOOGLE_EMAIL"))
    # Find next button
    next_button = driver.find_element(By.XPATH, '//span[text()="Next"]')
    next_button.click()
    time.sleep(3)
    # Find password field
    password = driver.find_element(By.XPATH, '//input[@type="password"]')
    password.send_keys(os.getenv("GOOGLE_PASSWORD"))
    # Find next button
    next_button = driver.find_element(By.XPATH, '//span[text()="Next"]')
    next_button.click()
    time.sleep(3)
    # # Wait for user to validate login
    # input("Press Enter to continue...")
    # # Find the Okay, let’s go button
    # okay_button = driver.find_element(By.XPATH, '//div[text()="Okay, let’s go"]')
    # okay_button.click()
    # Setup OK
    return {"status": "Selenium session started!"}


@app.post("/action/")
async def perform_action(payload: Payload):
    try:
        print(payload)
        # Download the image from the provided URL
        response = requests.get(payload.image_url, stream=True)
        response.raise_for_status()

        # Extract image filename and save inside 'images' folder
        image_filename = os.path.join("images", os.path.basename(payload.image_url))
        with open(image_filename, "wb") as image_file:
            for chunk in response.iter_content(chunk_size=8192):
                image_file.write(chunk)

        # open new chat
        driver.get("https://chat.openai.com/?model=gpt-4")
        time.sleep(5)

        # Make the input file element visible
        driver.execute_script(
            'document.querySelector(\'input[type="file"]\').style.display = "block";'
        )

        # Send the local path of the downloaded image to the file input element
        upload = driver.find_element(By.CSS_SELECTOR, 'input[type="file"]')
        upload.send_keys(os.path.abspath(image_filename))

        # Find prompt text area
        prompt = driver.find_element(By.XPATH, '//textarea[@id="prompt-textarea"]')
        prompt.send_keys(payload.prompt)

        # Find the submit button data-testid="send-button
        submit_button = driver.find_element(
            By.XPATH, '//button[@data-testid="send-button"]'
        )
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable(submit_button))
        prompt.send_keys(Keys.ENTER)

        # Wait the result
        time.sleep(5)
        regen_btn = (By.XPATH, "//button[@aria-label='Stop generating']")
        WebDriverWait(driver, 120).until(EC.invisibility_of_element_located(regen_btn))


        # Finds the div containing the html generated output
        output_element = driver.find_element(
                    By.XPATH, "//div[starts-with(@class, 'markdown prose w-full')]"
                )

        if output_element:
            # Removes all the extra in between spaces while keeping the newlines /n
            gen_content = repr(textwrap.dedent(output_element.text))

            # Set to json as response
            final_resp["result"] = json.loads(gen_content)

        else:
            final_resp = {"status": "Success", "result": {}}


        # Cleanup
        os.remove(os.path.abspath(image_filename))

        return final_resp

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/stop")
async def stop_session():
    driver.quit()
    return {"status": "Selenium session closed!"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
