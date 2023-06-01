from importlib import reload
import re
from pyrogram import Client, filters
from multiprocessing import Pool
from functools import partial
import requests
from Sqlite import Exec, ExecS
from tabulate import tabulate
from datetime import datetime
import BotConfig
import sqlite3
import TerminalStuff
from FileOps import *
from shutil import rmtree
from subprocess import getoutput
import PromoDB
import os
#*---------------------------------------------------------------------


'''
Contstants | Variables | Global Functions
'''
preFix = "/"
custom_filter = lambda cmd: filters.command(cmd, prefixes = preFix)

admins = BotConfig.admins
my_admin_filters = filters.user(admins)

allowedChats = BotConfig.allowedChats
my_chat_filters = filters.chat(allowedChats)

bottoken = BotConfig.bottoken

# command line
def cmdLine(cmd: str, logFile):
  out = getoutput(cmd)
  if 0<len(out)<=4096: # telegram message limit <= 4096 characters
    return out
  elif len(out)>4096:
    with open(logFile, "w", encoding='utf-8') as outfile:
      outfile.write(f"{out}")
      outfile.close()
    return F'`Output > 4096\nLogged to {logFile}`'
  else:
    return "Returned None"


def promoRegex(text):
  if len(text)==7:
   if(re.match("^[a-zA-Z0-9]*$", text) != None):
     return True
  return False
#*---------------------------------------------------------------------


'''
/cmd terminal_command
'''
@Client.on_message((my_admin_filters | my_chat_filters) & custom_filter(["cmd"]))
def cmd(_, message):
  url = message.text.partition(message.text.split()[0])[-1].strip()
  rep = message.reply("Executing...")
  logFileName = F"CommandLine{message.id}.log"
  rep.edit(f"`{cmdLine(url, logFileName)}`")
#*---------------------------------------------------------------------


'''
/save [filename]
'''
@Client.on_message((my_admin_filters | my_chat_filters) & custom_filter(["save"]))
def save(_, message):
  if message.reply_to_message:
    fname = 0
    if len(message.text.split())>1:
      fname = message.text.partition(message.text.split()[0])[-1].strip()
    omsg = message.reply_to_message
    rep = message.reply('Uploading...')
    if fname:
      dl = omsg.download(os.getcwd()+'/'+fname)
    else:
      dl = omsg.download(os.getcwd()+'/')
    if dl:
      rep.edit(f'Uploaded: `{dl}`')
    else:
      rep.edit("Failed to upload.")
  else:
    message.reply_text(F'Reply to a message containing file.\n`{preFix}save [filename]`')
#*---------------------------------------------------------------------


'''
/get filetype | filename
'''
@Client.on_message((my_admin_filters | my_chat_filters) & custom_filter(["get"]))
def get(_, message):
  if len(message.text.split())>1:
    typeName = [x.strip() for x in message.text.partition(message.text.split()[0])[-1].strip().split('|')]
    ftype = typeName[0].lower()
    if ftype in ['animation','audio','document','photo','sticker','video']:
      fname = typeName[1]
      rep = message.reply('Fetching...')
      testString = f'message.reply_{ftype}({ftype} = "{fname}")'
      if ftype == "document":
        testString = f'message.reply_{ftype}({ftype} = "{fname}", force_document = 1)'
      try:
        eval(testString)
        rep.delete()
      except:
        rep.edit("Exception Occurred!")
    else:
      message.reply("Wrong filetype :/\nAllowed: [animation/audio/document/photo/sticker/video]")
  else:
    message.reply(F'Provide the filename!\n`{preFix}get filetype[animation/audio/document/photo/sticker/video]|filename`')
#*---------------------------------------------------------------------


'''
/total | Returns the total number of subscribers
'''
@Client.on_message((my_admin_filters | my_chat_filters) & custom_filter(["total"]))
async def Total(_, msg):
  totalUsers = Exec("select count(*) from users")[0][0]
  await msg.reply(F"Total Users: {totalUsers}", quote=1)
#*---------------------------------------------------------------------


'''
/user | Returns help info
/user 1234567890
/user @username
'''
@Client.on_message((my_admin_filters | my_chat_filters) & custom_filter(["user"]))
async def User(_, msg):
  # Arguments Provided
  if len(msg.text.split())>1:
    targetUser = msg.text.partition(msg.text.split()[0])[-1].strip()
    UserInfo = "ID: {}\nHandle: {}\nPromo Code: {}\nProfiles Owned: {}\n\n"
    UserInfoHTM = "ID: {}<br>\nHandle: {}<br>\nPromo Code: {}<br>\nProfiles Owned: {}<br>\n"
    handle, promocode = 'None', 'None'
    try:
      data = [('Profile', 'Plan', 'Remaining (days)')]
      if targetUser.isdigit():
        exists = Exec(F"Select UserID from Users where UserID = {targetUser}")
        if exists: # User Exists
          row = Exec(F"Select UserID, UserHandle, Users.PromoCode, count(ProfileID) from Users, Subs where UserID={targetUser} and SubID = {targetUser}")
          if row[0][1]:handle=row[0][1]
          if row[0][2]:promocode=row[0][2]
          UserInfo = UserInfo.format(row[0][0], handle, promocode, row[0][3])
          UserInfoHTM = UserInfoHTM.format(row[0][0], handle, promocode, row[0][3])
          data += Exec(F"select ProfileID, Plan, Remaining from Subs where SubID = '{targetUser}'")
        else:raise Exception (F"User with User ID: {targetUser} doesn't exist!")

      else:
        exists = Exec(F"Select UserID from Users where lower(UserHandle) = lower('{targetUser}')")
        if exists: # User Exists
          row = Exec(F"Select UserID, UserHandle, Users.PromoCode, count(ProfileID) from Users, Subs where lower(UserHandle) = lower('{targetUser}') and SubID = (select UserID from Users where lower(UserHandle) = lower('{targetUser}'))")
          if row[0][1]:handle=row[0][1]
          if row[0][2]:promocode=row[0][2]
          UserInfo = UserInfo.format(row[0][0], handle, promocode, row[0][3])
          UserInfoHTM = UserInfoHTM.format(row[0][0], handle, promocode, row[0][3])
          data += Exec(F"select ProfileID, Plan, Remaining from Subs where SubID = '{row[0][0]}'")
        else:raise Exception (F"User with Handle: {targetUser} doesn't exist!")

      tabulatedData = UserInfo + tabulate(data, headers='firstrow')
      
      if len(tabulatedData)<=4094:
        return await msg.reply(F"`{tabulatedData}`", quote=1)

      with open("User.html","w", encoding='utf-8') as sy:
        sy.write("""<head><style>table, th, td{font-size: 20px; border: solid white 1px; border-collapse:collapse; background: #111920; padding: 2px;}body {font-family: 'Consolas'; background:#0B1016; color:white}</style></head><center>\n"""+F"{UserInfoHTM}\n{tabulate(data, headers='firstrow', tablefmt='html')}\n</center>")
        sy.close()
      await msg.reply_document(document = "User.html", quote=1)
      DelFiles(["User.html"])
      return
    except Exception as e:return await msg.reply(e, quote=1)

  # No Arguments | Returns help
  await msg.reply(F"--**Usage**--\n`{preFix}user 1234567890`\n`{preFix}user @username`", quote=1)
#*---------------------------------------------------------------------


'''
/promo | Returns help info
/promo PROMO_CODE
'''
@Client.on_message((my_admin_filters | my_chat_filters) & custom_filter(["promo"]))
async def Promo(_, msg):
  # Arguments Provided
  if len(msg.text.split())>1:
    promocode = msg.text.partition(msg.text.split()[0])[-1].strip()
    PlanInfo = "Plan Type\n1m  = {}\n6m  = {}\n12m = {}\nTotal Subs: {}\n\n"
    PlanInfoHTM = "Plan Type<br>\n1m  = {}<br>\n6m  = {}<br>\n12m = {}<br>\nTotal Subs: {}<br><br>\n\n"
    try:
      count1m = Exec(F"select count(*) from Subs where Plan = '1m' and lower(PromoCode) = lower('{promocode}')")[0][0]
      count6m = Exec(F"select count(*) from Subs where Plan = '6m' and lower(PromoCode) = lower('{promocode}')")[0][0]
      count12m = Exec(F"select count(*) from Subs where Plan = '12m' and lower(PromoCode) = lower('{promocode}')")[0][0]
      total = count1m + count6m + count12m
      if total:
        data = [('ID', 'Handle')]
        PlanInfo = PlanInfo.format(count1m, count6m, count12m, total)
        PlanInfoHTM = PlanInfoHTM.format(count1m, count6m, count12m, total)
        data += Exec(F"select UserID, UserHandle from Users where lower(PromoCode) = lower('{promocode}')")

        tabulatedData = PlanInfo + tabulate(data, headers='firstrow')
        if len(tabulatedData)<=4094:
          return await msg.reply(F"`{tabulatedData}`", quote=1)

        with open("Promo.html","w", encoding='utf-8') as sy:
          sy.write("""<head><style>table, th, td{font-size: 20px; border: solid white 1px; border-collapse:collapse; background: #111920; padding: 2px;}body {font-family: 'Consolas'; background:#0B1016; color:white}</style></head><center>\n"""+F"{PlanInfoHTM}\n{tabulate(data, headers='firstrow', tablefmt='html')}\n</center>")
          sy.close()
        await msg.reply_document(document = "Promo.html", quote=1)
        DelFiles(["Promo.html"])
        return
      else:raise Exception ("No records found regarding this promo code!")

    except Exception as e:return await msg.reply(e, quote=1)

  # No Arguments | Returns help
  await msg.reply(F"--**Usage**--\n`{preFix}promo PROMO_CODE`", quote=1)
#*---------------------------------------------------------------------


'''
/users | Returns all users details
'''
@Client.on_message((my_admin_filters | my_chat_filters) & custom_filter(["users"]))
async def Users(_, msg):
  data = [('ID', 'Handle', 'Promo', 'Profiles')]
  data += Exec("Select * from (Select UserID, UserHandle, Users.PromoCode, count(ProfileID) from Users inner join Subs ON SubID = UserID group by UserID)")
  tabulatedData = tabulate(data, headers='firstrow')
  if len(tabulatedData)<=4094:
    await msg.reply(F"`{tabulatedData}`", quote=1)
  else:
    with open("Users.html","w", encoding='utf-8') as sy:
      sy.write("""<head><style>table, th, td{font-size: 20px; border: solid white 1px; border-collapse:collapse; background: #111920; padding: 2px;}body {font-family: 'Consolas'; background:#0B1016; color:white}</style></head><center>\n"""+F"{tabulate(data, headers='firstrow', tablefmt='html')}\n</center>")
      sy.close()
    await msg.reply_document(document = "Users.html", quote=1)
    DelFiles(["Users.html"])
#*---------------------------------------------------------------------


'''
/html | Returns the users table as html file
'''
@Client.on_message((my_admin_filters | my_chat_filters) & custom_filter(["html"]))
async def HTML(_, msg):
  # ID, Handle, Name, Promo, Profiles Owned, TimeStamp
  data = [('ID', 'Handle', 'Name', 'Promo Code', 'Profiles Owned','TimeStamp (YYYY-MM-DD 24Hrs)')]
  data += Exec("Select * from (Select UserID, UserHandle, UserName, Users.PromoCode, count(ProfileID), TimeStamp from Users inner join Subs ON SubID = UserID group by UserID)")

  with open("UsersTable.html","w", encoding='utf-8') as sy:
    sy.write("""<head><style>table, th, td{font-size: 20px; border: solid white 1px; border-collapse:collapse; background: #111920; padding: 2px;}body {font-family: 'Consolas'; background:#0B1016; color:white}</style></head><center>\n"""+F"{tabulate(data, headers='firstrow', tablefmt='html')}\n</center>")
    sy.close()
  await msg.reply_document(document = "UsersTable.html", quote=1)
  DelFiles(["UsersTable.html"])
#*---------------------------------------------------------------------


'''
/addu | Returns help info
/addu *UserID, *Name, *Subscription [6m] (in months), Handle, PromoCode (7 Characters)
'''
@Client.on_message((my_admin_filters | my_chat_filters) & custom_filter(["addu"]))
async def AddU(_, msg):
  try:
    # Arguments Provided
    if len(msg.text.split())>1:
      args = msg.text.partition(msg.text.split()[0])[-1].strip()
      args = [x.strip() for x in args.split(",")]
      if len(args)>=3:
        userid = int(args[0])
        username = args[1]
        userhandle = ''
        promocode = ''
        plan = args[2].lower()
        try:
          remaining = int(args[2][:-1]) * 30
          if not plan.endswith("m"):raise
        except:return await msg.reply("There's something wrong with the provided **subscription**, please try again with valid subscription plan.", quote=1)
        if len(args)>3:
          if len(args[3])==0:pass
          elif args[3].startswith("@") and len(args[3])>=6:userhandle = args[3]
          else: raise Exception ("There's something wrong with the provided **user handle**, please try again with a valid user handle or leave it blank.")
          if len(args)>4:
            if len(args[4])==0:pass
            elif len(args[4])==7:promocode = args[4]
            else: raise Exception ("There's something wrong with the provided **promo code**, please try again with a valid promo code (7 Characters) or leave it blank.")
        try:
          if Exec(F"Select count(ProfileID) from Subs")[0][0]:
            existingIDs = {x[0] for  x in Exec("select ProfileID from Subs")}
            idealIDs = {x for x in range(2, Exec("select max(ProfileID) from Subs")[0][0]+1)}
            freeIDs = idealIDs.difference(existingIDs)
            if freeIDs:profileid = freeIDs.pop()
            else:profileid = Exec("select max(ProfileID) from Subs")[0][0]+1
          else:profileid = 2
          
          UserPath = F"Subs/{userid}"
          ConfPath = F"{UserPath}/Profile{profileid}.conf"
          if TerminalStuff.Setup_Profile(UserPath, ConfPath, profileid):
            ExecS(F"insert into Users values('{userid}', '{userhandle}', '{username}', '{promocode}', '{datetime.now()}')")
            ExecS(F"insert into Subs values('{profileid}', '{userid}', '{plan}', '{remaining}', '{promocode}')")
            await msg.reply_document(document=ConfPath, quote=1)
            return await msg.reply(F"[User](tg://user?id={userid})"+ (F" ({userhandle})" if userhandle else "") +F" added!\nProfile ID: {profileid}", quote=1)
          return await msg.reply("Failed to set up new user profile :/", quote=1)
          
        except sqlite3.IntegrityError: return await msg.reply(F"User already exist in the database.\nUse {preFix}addp command to add a new profile.", quote=1)
        except Exception as e: return await msg.reply(F"Error while inserting values:\n{e}", quote=1)
      else: raise Exception (F"Wrong number of arguments.\nMinimum 3, maximum 5 expected, {len(args)} received.")
    else: raise Exception # No Arguments | Returns help
  except Exception as e: return await msg.reply((F"--**Error:**--\n{e}\n\n" if len(str(e)) else "") + F"--**Usage**--\n`{preFix}addu *UserID, *Name, *Subscription [6m] (in months), Handle, PromoCode (7 Characters)`", quote=1)
#*---------------------------------------------------------------------


'''
/addp | Returns help info
/addp *UserID, *Subscription [6m] (in months)
'''
@Client.on_message((my_admin_filters | my_chat_filters) & custom_filter(["addp"]))
async def AddP(_, msg):
  try:
    # Arguments Provided
    if len(msg.text.split())>1:
      args = msg.text.partition(msg.text.split()[0])[-1].strip()
      args = [x.strip() for x in args.split(",")]
      if len(args)==2:
        userid = int(args[0])
        if not Exec(f"Select UserID from Users where UserID={userid}"):return await msg.reply(F"User with user id: {userid} doesn't exist in the database. Make sure to add the user first.", quote=1)

        plan = args[1].lower()
        try:
          remaining = int(args[1][:-1]) * 30
          if not plan.endswith("m"):raise
        except:return await msg.reply("There's something wrong with the provided **subscription**, please try again with valid subscription plan.", quote=1)

        try:
          existingIDs = {x[0] for  x in Exec("select ProfileID from Subs")}
          idealIDs = {x for x in range(2, Exec("select max(ProfileID) from Subs")[0][0]+1)}
          freeIDs = idealIDs.difference(existingIDs)
          if freeIDs:profileid = freeIDs.pop()
          elif Exec("select count(ProfileID) from Subs")[0][0]:
            profileid = Exec("select max(ProfileID) from Subs")[0][0]+1
          else:profileid = 2

          userhandle = Exec(F"Select UserHandle from Users where UserID = {userid}")[0][0]

          UserPath = F"Subs/{userid}"
          ConfPath = F"{UserPath}/Profile{profileid}.conf"
          if TerminalStuff.Setup_Profile(UserPath, ConfPath, profileid):
            ExecS(F"insert into Subs values('{profileid}', '{userid}', '{plan}', '{remaining}', (Select PromoCode from Users where UserID = {userid}))")
            await msg.reply_document(document=ConfPath, quote=1)
            return await msg.reply(F"New profile for [User](tg://user?id={userid})"+ (F" ({userhandle})" if userhandle else "") +F" added!\nProfile ID: {profileid}", quote=1)
          return await msg.reply("Failed to set up new user profile :/", quote=1)

        except Exception as e: return await msg.reply(F"Error:\n{e}", quote=1)
      else: raise Exception (F"Wrong number of arguments.\n2 expected, {len(args)} received.")
    else: raise Exception # No Arguments | Returns help
  except Exception as e: return await msg.reply((F"--**Error:**--\n{e}\n\n" if len(str(e)) else "") + F"--**Usage**--\n`{preFix}addp *UserID, *Subscription [6m] (in months)`", quote=1)
#*---------------------------------------------------------------------


'''
/delu | Returns help info
/delu UserID [1234567890]
'''
@Client.on_message((my_admin_filters | my_chat_filters) & custom_filter(["delu"]))
async def DeleteUser(_, msg):
  try:
    # Arguments Provided
    if len(msg.text.split())>1:
      userid = msg.text.partition(msg.text.split()[0])[-1].strip()
      try:
        userid = int(userid)
        if Exec(F"Select * from Users where UserID={userid}"):
          
          rep = await msg.reply(F"Deleting data for user id: {userid}", quote=1)
          profileids = [x[0] for x in Exec(F"Select ProfileID from Subs where SubID = {userid}")]
          UserPath = F"Subs/{userid}"
          for profileid in profileids:
            file = open(F"{UserPath}/Profile{profileid}.keys")
            pubkey = file.readline().strip()
            file.close()
            if not TerminalStuff.DisableClient(pubkey):
              await rep.edit(F"{rep.text}\n• Profile {profileid} deleted.")
              DelFileNames(UserPath, F"Profile{profileid}")
            else:await rep.edit(F"{rep.text}\n• Profile {profileid} not deleted.")
          ExecS(F"delete from Users where UserID={userid}")
          ExecS(F"delete from Subs where SubID = {userid}")
          rmtree(UserPath)

          return await rep.edit(F"{rep.text}\nAll the data for user id: {userid} has been deleted!")
        else: return await msg.reply(F"User with User ID: {userid} doesn't exist!\nNo data was deleted.", quote=1)
      except:raise Exception ("Incorrect argument provided :/")
    else:raise Exception # No Arguments | Returns help
  except Exception as e: return await msg.reply((F"--**Error:**--\n{e}\n\n" if len(str(e)) else "") + F"--**Usage**--\n`{preFix}del UserID [1234567890]`", quote=1)
#*---------------------------------------------------------------------


'''
/delp | Returns help info
/delp ProfileID
'''
@Client.on_message((my_admin_filters | my_chat_filters) & custom_filter(["delp"]))
async def DeleteProfile(_, msg):
  try:
    # Arguments Provided
    if len(msg.text.split())>1:
      profileid = msg.text.partition(msg.text.split()[0])[-1].strip()
      try:
        profileid = int(profileid)
        if Exec(F"Select ProfileID from Subs where ProfileID={profileid}"):
          if Exec(F"Select count(ProfileID) from Subs where SubID = (Select SubID from Subs where ProfileID={profileid})")[0][0]==1:return await msg.reply(F"You can't delete the only profile associated with a user.\nUse {preFix}delu command to delete the whole user data including the profile info.", quote=1)

          rep = await msg.reply(F"Deleting data for Profile {profileid}", quote=1)
          userid = Exec(F"Select SubID from Subs where ProfileID = {profileid}")[0][0]
          UserPath = F"Subs/{userid}"
          file = open(F"{UserPath}/Profile{profileid}.keys")
          pubkey = file.readline().strip()
          file.close()
          if not TerminalStuff.DisableClient(pubkey):
            await rep.edit(F"{rep.text}\n• Profile {profileid} disabled.")
            DelFileNames(UserPath, F"Profile{profileid}")
          else:return await rep.edit(F"{rep.text}\n• Failed to disable Profile {profileid}.\nNo data was deleted.")
          ExecS(F"delete from Subs where ProfileID = {profileid}")

          return await rep.edit(F"{rep.text}\nAll data for Profile {profileid} has been deleted!")
        else: return await msg.reply(F"Profile {profileid} not found!\nNo data was deleted.", quote=1)
      except:raise Exception ("Incorrect argument provided :/")
    else:raise Exception # No Arguments | Returns help
  except Exception as e: return await msg.reply((F"--**Error:**--\n{e}\n\n" if len(str(e)) else "") + F"--**Usage**--\n`{preFix}delp Profile ID`", quote=1)
#*---------------------------------------------------------------------


'''
/sup | Returns help info
/sup ProfileID, New remaining time [30d/6m] (in days/months)
'''
@Client.on_message((my_admin_filters | my_chat_filters) & custom_filter(["sup"]))
async def SubsciptionUpdate(_, msg):
  try:
    # Arguments Provided
    if len(msg.text.split())>1:
      args = msg.text.partition(msg.text.split()[0])[-1].strip().lower()
      args = [x.strip() for x in args.split(",")]

      profileid = args[0]
      try:profileid = int(profileid)
      except:return await msg.reply("Invalid profile id provided.", quote=1)

      if len(args)!=2:raise Exception (F"Wrong number of arguments.\n2 expected, {len(args)} received.")
      if args[1].endswith("m"):remaining = int(args[1][:-1]) * 30
      elif args[1].endswith("d"):remaining = int(args[1][:-1])
      else: raise Exception ("There's something wrong with the provided argument(s) (**new remaining time**), please try again with correct information.")

      plan = Exec(F"select Plan from Subs where ProfileID={profileid}")
      if plan:
        plan = int(plan[0][0].removesuffix('m')) * 30
        if 0<= remaining <= plan:
          ExecS(F"update Subs set Remaining = {remaining} where ProfileID = {profileid}")
          return await msg.reply(F"Profile {profileid} updated!", quote=1)
        else:raise Exception (F"The provided new remaining time: {remaining}d exceeds the plan duration: {plan}d! Provide a valid (0d ≤ new remaining time ≤ {plan}d).")
      else: return await msg.reply(F"Profile {profileid} doesn't exist!\nNo profiles were updated.", quote=1)
    else:raise Exception # No Arguments | Returns help
  except Exception as e: return await msg.reply((F"--**Error:**--\n{e}\n\n" if len(str(e)) else "") + F"--**Usage**--\n`{preFix}sup ProfileID, New remaining time [30d/6m] (in days/months)`", quote=1)
#*---------------------------------------------------------------------


'''
/addtime | Returns help info
/addtime ProfileID, Additional time [1m] (in months)
'''
@Client.on_message((my_admin_filters | my_chat_filters) & custom_filter(["addtime"]))
async def PlanUpdate(_, msg):
  try:
    # Arguments Provided
    if len(msg.text.split())>1:
      args = msg.text.partition(msg.text.split()[0])[-1].strip().lower()
      args = [x.strip() for x in args.split(",")]

      profileid = args[0]
      try:profileid = int(profileid)
      except:return await msg.reply("Invalid profile id provided.", quote=1)

      if len(args)!=2:raise Exception (F"Wrong number of arguments.\n2 expected, {len(args)} received.")
      if args[1].endswith("m"):additional = int(args[1][:-1])
      else: raise Exception ("There's something wrong with the provided argument(s) (**additional time**), please try again with correct information.")

      plan = Exec(F"select Plan from Subs where ProfileID={profileid}")
      if plan:
        plan = int(plan[0][0].removesuffix('m'))
        plan+=additional
        rem = int(Exec(F"select Remaining from Subs where ProfileID={profileid}")[0][0])
        rem+=(additional*30)
        ExecS(F"update Subs set Plan = '{plan}m', Remaining='{rem}' where ProfileID = {profileid}")
        return await msg.reply(F"Profile {profileid} updated!", quote=1)
      else: return await msg.reply(F"Profile {profileid} doesn't exist!\nNo profiles were updated.", quote=1)
    else:raise Exception # No Arguments | Returns help
  except Exception as e: return await msg.reply((F"--**Error:**--\n{e}\n\n" if len(str(e)) else "") + F"--**Usage**--\n`{preFix}addtime ProfileID, Additional time [1m] (in months)`", quote=1)
#*---------------------------------------------------------------------


'''
/broadcast -> message
'''
def BroadcastMsg(userid, msgobj):
  # r=
  requests.get(F"https://api.telegram.org/bot{bottoken}/copyMessage?chat_id={userid}&from_chat_id={msgobj.chat.id}&message_id={msgobj.id}")
  # res = json.loads(r.content)

@Client.on_message((my_admin_filters | my_chat_filters) & custom_filter(["broadcast"]) & filters.reply)
async def Broadcast(_, msg):
  allUsers = [x[0] for x in Exec("Select userid from users")]
  pool = Pool()
  msgObj = msg.reply_to_message
  await msg.reply("Broadcasting...", quote=1)
  pool.map_async(partial(BroadcastMsg, msgobj=msgObj), [user for user in allUsers])
#*---------------------------------------------------------------------


'''
/forward -> message
'''
def ForwardMsg(userid, msgobj):
  requests.get(F"https://api.telegram.org/bot{bottoken}/forwardMessage?chat_id={userid}&from_chat_id={msgobj.chat.id}&message_id={msgobj.id}")

@Client.on_message((my_admin_filters | my_chat_filters) & custom_filter(["forward"]) & filters.reply)
async def Forward(_, msg):
  allUsers = [x[0] for x in Exec("Select userid from users")]
  pool = Pool()
  msgObj = msg.reply_to_message
  await msg.reply("Forwarding...", quote=1)
  pool.map_async(partial(ForwardMsg, msgobj=msgObj), [user for user in allUsers])
#*---------------------------------------------------------------------


'''
/addpromo 7 Digit Promo Code
'''
@Client.on_message((my_admin_filters | my_chat_filters) & custom_filter(["addpromo"]))
async def AddPromo(_, msg):
  if len(msg.text.split())==2:
    promocode = msg.text.partition(msg.text.split()[0])[-1].strip().lower()
    if promoRegex(promocode):
      global PromoDB
      PromoDB=reload(PromoDB)      
      if not {promocode}.intersection(PromoDB.promoSet):
        #Add to db if not in db
        PromoDB.promoSet.add(promocode)
        with open("PromoDB.py","w+") as sy:
          sy.write("promoSet="+str(PromoDB.promoSet))
          sy.close()
        return await msg.reply(F"Promo code: {promocode} **added** to the database!", quote=1)
      return await msg.reply(F"Promo code: {promocode} **already exist** in the database!", quote=1)
    return await msg.reply("Invalid code. Make sure to provide a 7 digit alphanumeric promo code.", quote=1)
  return await msg.reply(F"--**Usage**--\n`{preFix}addpromo 7 Digit Promo Code`", quote=1)
#*---------------------------------------------------------------------


'''
/delpromo 7 Digit Promo Code
'''
@Client.on_message((my_admin_filters | my_chat_filters) & custom_filter(["delpromo"]))
async def DelPromo(_, msg):
  if len(msg.text.split())==2:
    promocode = msg.text.partition(msg.text.split()[0])[-1].strip().lower()
    if promoRegex(promocode):
      global PromoDB
      PromoDB=reload(PromoDB)      
      if {promocode}.intersection(PromoDB.promoSet):
        #Remove from db if in db
        PromoDB.promoSet.remove(promocode)
        with open("PromoDB.py","w+") as sy:
          sy.write("promoSet="+str(PromoDB.promoSet))
          sy.close()
        return await msg.reply(F"Promo code: {promocode} **removed** from the database!", quote=1)
      return await msg.reply(F"Promo code: {promocode} **doesn't exist** in the database! What should I remove?!", quote=1)
    return await msg.reply("Invalid code. Make sure to provide a 7 digit alphanumeric promo code which exists in the database.", quote=1)
  return await msg.reply(F"--**Usage**--\n`{preFix}delpromo 7 Digit Promo Code`", quote=1)
#*---------------------------------------------------------------------


'''
/promos | Returns list of existing promo codes
'''
@Client.on_message((my_admin_filters | my_chat_filters) & custom_filter(["promos"]))
async def Promos(_, msg):
  global PromoDB
  PromoDB=reload(PromoDB)
  csvPromos = ", ".join(str(e) for e in PromoDB.promoSet)
  if len(csvPromos)<=4094:
    return await msg.reply(csvPromos, quote=1)
  with open("csvPromos.txt","w+") as sy:
    sy.write(csvPromos)
    sy.close()
  await msg.reply_document(document = "csvPromos.txt", quote=1)
  DelFiles(["csvPromos.txt"])