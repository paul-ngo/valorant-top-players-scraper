import numpy as np
import pandas as pd
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import time
import datetime
import concurrent.futures
import threading
from statsmodels.stats.weightstats import ztest as ztest
import math
import requests

class Timer(object):
    def __init__(self, name=None):
        self.name = name

    def __enter__(self):
        self.tstart = time.time()

    def __exit__(self, type, value, traceback):
        if self.name:
            print('[%s]' % self.name,)
        print('Elapsed: %s' % (time.time() - self.tstart))
        
class Driver():
    def __init__(self, headless):
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        prefs = {"profile.managed_default_content_settings.images": 2}
        options.add_experimental_option("prefs", prefs)
        self.driver = webdriver.Chrome(options=options)

    def __del__(self):
        self.driver.quit()
            
def get_driver(threadLocal, headless=True):
    the_driver = getattr(threadLocal, 'the_driver', None)
    if the_driver is None:
        the_driver = Driver(headless)
        setattr(threadLocal, 'the_driver', the_driver)
    return the_driver.driver

timeout = 3

def getTopPlayers(args):
    actId = args[0]
    pages = args[1]
    n = args[2]
    threadLocal = args[3]
    headless = args[4]
    driver = get_driver(threadLocal, headless)
    arrPlayers = []
    arrRanks = []
    for page in range(pages-n, pages):
        url = "https://playvalorant.com/en-us/leaderboards/?page=" + str(page+1) + "&act=" + actId
        driver.get(url)

        playerTileAttr = "LeaderboardsItem-module--playerName--2BYaw"
        playerRankAttr = "LeaderboardsItem-module--leaderboardRank--3DHty"
        
        try:
            WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.CLASS_NAME, playerTileAttr)))
        except: 
            try:
                print('Error encountered...trying again')
                driver.refresh()        
                WebDriverWait(driver, timeout*2).until(EC.presence_of_element_located((By.CLASS_NAME, playerTileAttr)))
            except:
                print('Error encountered on page ' + str(page))
                continue

        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')   

        lsPlayers = []
        lsPlayers = soup.find_all("h2", {"class": playerTileAttr})
        lsRanks = soup.find_all("h3", {"class": playerRankAttr})
        
        for rank, player in zip(lsRanks, lsPlayers):
            arrRanks = np.append(arrRanks, rank.text.replace("#", "-"))
            arrPlayers = np.append(arrPlayers, player.text.replace("#", "-"))

    arrPlayerNames = []
    arrPlayerRanks = []
    arrPlayerIds = []
       
    for playerName, playerRank in zip(arrPlayers, arrRanks):
        url = 'https://valorant.iesdev.com/player/' + playerName.lower()
        r = requests.get(url)
        
        if r.status_code == 404:
            continue
        
        playerData = r.json()
        playerId = playerData['id'] or playerData['puuid']
        arrPlayerNames = np.append(arrPlayerNames, playerName)
        arrPlayerRanks = np.append(arrPlayerRanks, playerRank)
        arrPlayerIds = np.append(arrPlayerIds, playerId)
    
    
    del threadLocal
    return arrPlayerNames, arrPlayerRanks, arrPlayerIds

def scrapePlayers(actId, playerCount, maxThreads, headless):
    pageCount = math.ceil(playerCount/10)
    n = math.ceil(pageCount/maxThreads)

    arrPlayerNames = []
    arrPlayerRanks = []
    arrPlayerIds = []
    
    with Timer('Leaderboard Scrape:'):

        args = [(actId, n*i, n, threading.local(), headless) for i in range(1, maxThreads+1)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=maxThreads) as executor:
            results = executor.map(getTopPlayers, args)

            for result in results:
                arrPlayerNames = np.append(arrPlayerNames, result[0])
                arrPlayerRanks = np.append(arrPlayerRanks, result[1])    
                arrPlayerIds = np.append(arrPlayerIds, result[2]) 
                
            dfPlayerList = pd.DataFrame(data=[arrPlayerIds, arrPlayerRanks, arrPlayerNames]).T
            dfPlayerList.columns = ['player_id', 'player_rank', 'player_name']
            dfPlayerList['date_added'] = datetime.datetime.now()#.strftime("%Y-%m-%d %H:%M:%S")
            dfPlayerList['latest_data'] = True
            
    return dfPlayerList
  