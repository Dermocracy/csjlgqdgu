from pyrogram import Client
import BotConfig
#----------------------------
bottoken = BotConfig.bottoken
apiid = 6
apihash = "eb06d4abfb49dc3eeb1aeb98ae0f581e"
plugins = dict(root="addons")
app = Client("UserMgmtBot", bot_token = bottoken, api_id = apiid, api_hash = apihash, plugins = plugins)
#----------------------------
import os
os.chdir(os.path.dirname(os.path.realpath(__file__)))



#---------Daily Job---------
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import sqlite3
from shutil import rmtree
import requests
import BotConfig
from multiprocessing import Pool
from functools import partial
from FileOps import *
import TerminalStuff
import os

def fwrite(text, file):
  with open(file, "a", encoding='utf-8') as outfile:
    outfile.write(f"{text}\n")
    outfile.close()
def validity_warn(res, text): # res = (UserID, Plan, ProfileID, Remaining)
  try:
    requests.get(F"https://api.telegram.org/bot{BotConfig.bottoken}/sendMessage", params={"chat_id": res[0], "text": text.format(res[1].strip('m'), res[2], res[3])})
    fwrite(F"Warned: {str(res)[1:-1]}", "WGWarns.log")
  except:
    fwrite(F"Warn Failed: {str(res)[1:-1]}", "WGWarns.log")

def daily_job():
  # print("!!")
  connection = sqlite3.connect("UserMgmt.db", detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
  cursor = connection.cursor()
  def Exec(query: str):
    cursor.execute(query)
    return cursor.fetchall()
  def ExecS(query: str):
    cursor.execute(query)
    connection.commit()
  def deleteProfiles(res): # res = (SubID, ProfileID)
    fwrite(F"Deletion Tried: {str(res)[1:-1]}", "WGDel.log")
    userid = res[0]
    profileid = res[1]
    if Exec(F"Select ProfileID from Subs where ProfileID={profileid}"):
      UserPath = F"Subs/{userid}"
      file = open(F"{UserPath}/Profile{profileid}.keys")
      pubkey = file.readline().strip()
      file.close()
      if not TerminalStuff.DisableClient(pubkey): # Profile Disabled
        if Exec(F"Select count(ProfileID) from Subs where SubID = {userid}")[0][0]==1:
        # Delete User + All Profiles
          ExecS(F"delete from Users where UserID={userid}")
          ExecS(F"delete from Subs where SubID={userid}")
          rmtree(UserPath)
          fwrite(F"Deleted User: {str(res)[1:-1]}", "WGDel.log")
        else:
        # Delete Profile
          DelFileNames(UserPath, F"Profile{profileid}")
          ExecS(F"delete from Subs where ProfileID = {profileid}")
          fwrite(F"Deleted Profile: {str(res)[1:-1]}", "WGDel.log")
  
  os.system("echo $(date) >> WGWarns.log")
  os.system("echo $(date) >> WGDel.log")
  
  # Validity Warning
  pool = Pool()
  ExpiryText = "Напоминание: Ваш тариф {} месяцев (Profile {}) закончится через {} дней."
  oneMonthLeftUserList = Exec("Select SubID, Plan, ProfileID, Remaining from Subs where Plan!='1m' and Remaining = 30")
  oneWeekLeftUserList = Exec("Select SubID, Plan, ProfileID, Remaining from Subs where Remaining = 7")
  threeDaysLeftUserList = Exec("Select SubID, Plan, ProfileID, Remaining from Subs where Remaining = 3")
  oneDayLeftUserList = Exec("Select SubID, Plan, ProfileID, Remaining from Subs where Remaining = 1")
  pool.map(partial(validity_warn, text=ExpiryText), oneMonthLeftUserList)
  pool.map(partial(validity_warn, text=ExpiryText), oneWeekLeftUserList)
  pool.map(partial(validity_warn, text=ExpiryText), threeDaysLeftUserList)
  pool.map(partial(validity_warn, text=ExpiryText), oneDayLeftUserList)

  # Delete expired profiles
  if Exec("Select count(*) from Subs where Remaining=0")[0][0]:
    expiredUsers = Exec("Select SubID, ProfileID from Subs where Remaining = 0")
    for user in expiredUsers:deleteProfiles(user)

  # Decrement remaining validity by 1 day
  ExecS("update Subs set remaining=remaining-1 where remaining>0")
#=========x=x=x=x=x=x=x=x=x=x=x=========



scheduler = AsyncIOScheduler()
scheduler.add_job(daily_job, "interval", days=1)
scheduler.start()

app.run()
