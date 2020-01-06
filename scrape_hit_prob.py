from bs4 import BeautifulSoup
import requests
import io
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
import time
import pandas as pd

binary = FirefoxBinary('C:\\Program Files\\Mozilla Firefox\\firefox.exe')
cap = DesiredCapabilities().FIREFOX
cap["marionette"] = True
driver = webdriver.Firefox(capabilities=cap, executable_path="C:\\Program Files\\GeckoDriver\\geckodriver.exe", firefox_binary=binary)
url = 'https://baseballsavant.mlb.com/statcast_hit_probability'
driver.get(url)
time.sleep(5)
elements = driver.find_elements_by_css_selector('.default-table-row')
for element in elements:	
	subel = element.find_element_by_tag_name('td')
	subel.click()
html = driver.page_source
soup = BeautifulSoup(html, 'html.parser')
mydivs = soup.find("div", {"class": "table-savant"})
mydivs = mydivs.find('table')
mydivs = mydivs.find('tbody')
mydivs = mydivs.findAll('tr')
d = {}
for div in mydivs:
	divid = div.get('id')
	if divid is None:
		pass
	elif 'data_' in divid and '-tr_' in divid:
		velo = divid.split('_')[1].split('-')[0]
		angle_data = div.findAll('td')
		angle = angle_data[0].find('span').string
		bbe = angle_data[2].find('span').string
		_1B = angle_data[5].find('span').string
		_2B = angle_data[6].find('span').string
		_3B = angle_data[7].find('span').string
		HR = angle_data[8].find('span').string
		if velo not in d.keys():
			d[velo] = {}
		d[velo][angle] = (bbe, _1B, _2B, _3B, HR)
df = pd.DataFrame(d)
df = df.sort_index()
with open('hit_prob_matrix.csv', 'w', newline='') as file:
	file.write(df.to_csv())
driver.quit()