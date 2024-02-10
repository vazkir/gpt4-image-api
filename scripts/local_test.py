from bs4 import BeautifulSoup


def check_page():
    
    soup = BeautifulSoup(open('../page_html/example_generate.html'), "lxml")
    print(soup)



if __name__ == "__main__":
    check_page()