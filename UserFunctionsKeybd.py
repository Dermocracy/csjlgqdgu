from pyrogram import Client, filters, enums
from pyrogram.types import CallbackQuery, Message, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
import BotConfig
from Sqlite import Exec, ExecS
from datetime import datetime
from tabulate import tabulate
from FileOps import *
import TerminalStuff
from importlib import reload
import PromoDB

import re
import os
import sqlite3
from multiprocessing import Pool
from functools import partial
import requests, json
#*---------------------------------------------------------------------


'''
Contstants | Filters | Global Functions
'''
preFix = "\u2063"
custom_filter = lambda cmd: filters.command(cmd, prefixes = preFix)

async def cb_private_filter(_, __, cb: CallbackQuery):
  return bool(cb.message.chat and cb.message.chat.type in {enums.ChatType.PRIVATE, enums.ChatType.BOT})
cb_private = filters.create(cb_private_filter)


def promoValid(promocode):
  global PromoDB
  PromoDB=reload(PromoDB)
  return {promocode.lower()}.intersection(PromoDB.promoSet)

def generateProfilesKeybd(profiles: list, maxbtns = 3):
  keybdBtnList = "["
  for x in range(1, len(profiles)+1):
    keybdBtnList += "KeyboardButton('\u2063\u2063{}'), ".format(profiles[x-1][0])
    if not x%maxbtns:
      keybdBtnList+=F'], ['
  keybdBtnList+=']'
  if not len(profiles)%maxbtns:keybdBtnList=keybdBtnList[:-4]
  keybdBtnList+=F", [KeyboardButton('\u2063{mainMenuText}'), ]"
  return eval("ReplyKeyboardMarkup([{}], resize_keyboard = 1, one_time_keyboard = 1, selective = 1)".format(keybdBtnList))

def cleanUp(userid):
  ExecS(F"delete from Config where UserID={userid}")
  approvalPending = Exec(F"Select count(*) from approvalPending where UserID={userid}")[0][0]
  if not approvalPending:
    ExecS(F"delete from TempUsers where UserID={userid}")



baseChat = BotConfig.allowedChats[0]

admins = BotConfig.admins
my_admin_filters = filters.user(admins)

allowedChats = BotConfig.allowedChats
my_chat_filters = filters.chat(allowedChats)
#*---------------------------------------------------------------------


'''
Buttons | Keyboards | Variables
'''
yesNoBtns = [[InlineKeyboardButton('Да', callback_data='yes'), InlineKeyboardButton('Нет', callback_data='no'),],]
prompt = InlineKeyboardMarkup(yesNoBtns)



cancelText = "Отменить Оплату"
plansBtns = [[KeyboardButton('\u20631 Месяц = 500₽'), KeyboardButton('\u20636 Месяцев = 1500₽'), KeyboardButton('\u206312 Месяцев = 2000₽')],
                                  [KeyboardButton(F'\u2063{cancelText}')]]
plansKeybd = ReplyKeyboardMarkup(plansBtns, resize_keyboard = 1, one_time_keyboard = 1, selective = 1)

yesNoPromoBtns = [[KeyboardButton('\u2063Да'), KeyboardButton('\u2063Нет')], [KeyboardButton(F'\u2063{cancelText}')]]
promoPromptKeybd = ReplyKeyboardMarkup(yesNoPromoBtns, resize_keyboard = 1, one_time_keyboard = 1, selective = 1)

NoPromoBtns = [[KeyboardButton('\u2063Продолжить без промокода'),], [KeyboardButton(F'\u2063{cancelText}'),],]
noPromoPromptKeybd = ReplyKeyboardMarkup(NoPromoBtns, resize_keyboard = 1, one_time_keyboard = 1, selective = 1)


mainBtns = [[KeyboardButton("\u2063Информация"), KeyboardButton("\u2063Оплата")],
            [KeyboardButton("\u2063Получить VPN"), KeyboardButton("\u2063Поддержка")]]
mainKeybd = ReplyKeyboardMarkup(mainBtns, resize_keyboard = 1, one_time_keyboard = 1, selective = 1)

changePlanBtns = [[KeyboardButton("\u2063Сменить Тариф")], [KeyboardButton(F"\u2063{cancelText}")]]
changePlanKeybd = ReplyKeyboardMarkup(changePlanBtns, resize_keyboard = 1, one_time_keyboard = 1, selective = 1)

cancelRegBtns = [[KeyboardButton(F"\u2063{cancelText}")]]
cancelRegKeybd = ReplyKeyboardMarkup(cancelRegBtns, resize_keyboard = 1, one_time_keyboard = 1, selective = 1)


mainMenuText = "Главное Меню"
getVPNBtns = [[KeyboardButton('\u2063Установить Wireguard'), KeyboardButton('\u2063Получить Профиль')],
                                  [KeyboardButton(F'\u2063{mainMenuText}')]]
getVPNKeybd = ReplyKeyboardMarkup(getVPNBtns, resize_keyboard = 1, one_time_keyboard = 1, selective = 1)

installWGBtns = [[KeyboardButton("\u2063iOS App Store"), KeyboardButton("\u2063Google Play")],
            [KeyboardButton("\u2063Официальный сайт"), KeyboardButton(F"\u2063{mainMenuText}")]]
installWGKeybd = ReplyKeyboardMarkup(installWGBtns, resize_keyboard = 1, one_time_keyboard = 1, selective = 1)




ssprompt = "Вы выбрали тариф: {} месяц(ев)\n(Используйте кнопку Сменить Тариф, если желаете изменить свой выбор.\n\n**Отправьте скриншот платежа из онлайн банка для завершения оплаты \n**Средства XXX платежу!**"

planSet = "update TempUsers set Plan = '{}' where UserID = {}"
#*---------------------------------------------------------------------


'''
/start | Displays Custom Start Text and main menu
'''
@Client.on_message(filters.command(["start"], prefixes=["/"]))
async def Start(_, msg):
  userid = msg.from_user.id
  cleanUp(userid)
  await msg.reply(BotConfig.startMessage, reply_markup = mainKeybd, quote=1)
#*---------------------------------------------------------------------


'''
Main Menu | Displays the main menu
'''
@Client.on_message(filters.private & custom_filter([mainMenuText]))
async def MainMenu(_, msg):
  userid = msg.from_user.id
  cleanUp(userid)
  await msg.reply("Выберите интересующее Вас меню", reply_markup = mainKeybd, quote=1)
#*---------------------------------------------------------------------


'''
Info | Displays user info
'''
@Client.on_message(filters.private & custom_filter(["Информация"]))
async def Info(_, msg):
  targetUser = msg.from_user.id
  UserInfo = "ID: {}\nЛогин: {}\nPromo Code: {}\nКоличество профилей: {}\n\n"
  UserInfoHTM = "ID: {}<br>\nЛогин: {}<br>\nПромокод: {}<br>\nКоличество профилей: {}<br>\n"
  handle, promocode = 'None', 'None'
  try:
    data = [('ПрофильID', 'Тариф', 'Осталось дней')]
    exists = Exec(F"Select UserID from Users where UserID = {targetUser}")
    if exists:
      row = Exec(F"Select UserID, UserHandle, Users.PromoCode, count(ProfileID) from Users, Subs where UserID={targetUser} and SubID = {targetUser}")
      if row[0][1]:handle=row[0][1]
      if row[0][2]:promocode=row[0][2]
      UserInfo = UserInfo.format(row[0][0], handle, promocode, row[0][3])
      UserInfoHTM = UserInfoHTM.format(row[0][0], handle, promocode, row[0][3])
      data += Exec(F"select ProfileID, Plan, Remaining from Subs where SubID = '{targetUser}'")
    else:raise Exception (F"Наш VPN сервис поможет зашифровать и пропустить Ваш трафик через иностранный сервер, что позволяет получать доступ к сервисам и сайтам, заблокированным на территории РФ. Крупные VPN сервисы имеют гораздо большую вероятность блокировок, а в случае блокировки - максимально оперативно обновим способы соединения, для того, чтобы Вы оставались довольны и продолжали пользоваться интернетом! \nДля подключения, перейдите в меню ОПЛАТА, выберите тариф и совершите платеж. После - установите приложение и добавьте в него файл конфигурации, полученный после оплаты и активируйте его.")

    tabulatedData = UserInfo + tabulate(data, headers='firstrow')
    
    if len(tabulatedData)<=4094:
      cleanUp(targetUser)
      return await msg.reply(F"`{tabulatedData}`", reply_markup = mainKeybd, quote=1)

    with open("User.html","w", encoding='utf-8') as sy:
      sy.write("""<head><style>table, th, td{font-size: 20px; border: solid white 1px; border-collapse:collapse; background: #111920; padding: 2px;}body {font-family: 'Consolas'; background:#0B1016; color:white}</style></head><center>\n"""+F"{UserInfoHTM}\n{tabulate(data, headers='firstrow', tablefmt='html')}\n</center>")
      sy.close()
    cleanUp(targetUser)
    await msg.reply_document(document = "User.html", reply_markup = mainKeybd, quote=1)
    DelFiles(["User.html"])
    return
  except Exception as e:
    cleanUp(targetUser)
    return await msg.reply(e, reply_markup = mainKeybd, quote=1)
#*---------------------------------------------------------------------


'''
Payment | Register new users or Add new profile if existing user
'''
@Client.on_message(filters.private & custom_filter(["Оплата"]))
async def Register(_, msg):
  userid = msg.from_user.id
  cleanUp(userid)
  approvalPending = Exec(F"Select count(*) from approvalPending where UserID={userid}")[0][0]
  if approvalPending:
    plan = Exec(F"Select Plan from TempUsers where UserID={userid}")[0][0]
    return await msg.reply(F"Ваша оплата тарифа {plan.strip('m')} месяц(ев) в обработке, пожалуйста, ожидайте подтверждения.", quote=1)

  rows = Exec(F"Select count(UserID), UserHandle, UserName, PromoCode from Users where UserID={userid}")[0]
  if rows[0]: # Existing User
    userhandle = rows[1]
    username = rows[2]
    promocode = rows[3] if rows[3] else 'None'
    #                                      UserID,  UserHandle,  UserName, PromoCode,  Plan, PromoPending, SSPending
    ExecS(F"insert into TempUsers values('{userid}', '{userhandle}', '{username}', '{promocode}Xisting', 'DummyPlan', 0, 0)")
    return await msg.reply(F"Вы выбрали меню оплаты.\nВаш промокод: {promocode}\n\nВыберите тариф", reply_markup=plansKeybd, quote=1)

  # New User
  username = msg.from_user.first_name + (F" {msg.from_user.last_name}" if msg.from_user.last_name else "")
  userhandle = ('@'+msg.from_user.username.lower()) if msg.from_user.username else ""
  #                                      UserID,  UserHandle,  UserName, PromoCode,  Plan, PromoPending, SSPending
  ExecS(F"insert into TempUsers values('{userid}', '{userhandle}', '{username}', 'DummyPromo', 'DummyPlan', 0, 0)")
  await msg.reply(F"У Вас есть промокод?", reply_markup=promoPromptKeybd, quote=1)
#*---------------------------------------------------------------------


'''
Change Plan | Changes the current plan selection
'''
@Client.on_message(filters.private & custom_filter(["Сменить Тариф"]))
async def ChangePlan(_, msg):
  userid = msg.from_user.id
  rowsTemp = Exec(F"Select SSPending from TempUsers where UserID={userid}")
  if rowsTemp:
    sspending = rowsTemp[0][0]
    if sspending:return await msg.reply(F"Выберите из предложенных тарифов", reply_markup=plansKeybd, quote=1)
#*---------------------------------------------------------------------


"""
Yes | User have a promo code
"""
@Client.on_message(filters.private & custom_filter(["Да"]))
async def YesPromo(_, msg):
  userid = msg.from_user.id
  ExecS(F"update TempUsers set PromoPending=1 where UserID = {userid}")
  await msg.reply("Введите **7 значный промокод**", reply_markup = noPromoPromptKeybd, quote=1)
#*---------------------------------------------------------------------


"""
No | User doesn't have a promo code
"""
@Client.on_message(filters.private & custom_filter(["Нет", "Продолжить без промокода"]))
async def NoPromo(_, msg):
  userid = msg.from_user.id
  ExecS(F"update TempUsers set PromoCode = '' where UserID = {userid}")
  await msg.reply(F"ОК!\nТеперь выберите тариф", reply_markup = plansKeybd, quote=1)
#*---------------------------------------------------------------------


"""
1 Month Plan
"""
@Client.on_message(filters.private & custom_filter(["1 Месяц = 500₽"]))
async def OneMonth(_, msg):
  userid = msg.from_user.id
  ExecS(planSet.format("1m", userid))
  ExecS(F"update TempUsers set SSPending=1 where UserID = {userid}")
  await msg.reply(ssprompt.format(1), reply_markup = changePlanKeybd, quote=1)
#*---------------------------------------------------------------------


"""
6 Months Plan
"""
@Client.on_message(filters.private & custom_filter(["6 Месяцев = 1500₽"]))
async def SixMonths(_, msg):
  userid = msg.from_user.id
  ExecS(planSet.format("6m", userid))
  ExecS(F"update TempUsers set SSPending=1 where UserID = {userid}")
  await msg.reply(ssprompt.format(6), reply_markup = changePlanKeybd, quote=1)
#*---------------------------------------------------------------------


"""
12 Months Plan
"""
@Client.on_message(filters.private & custom_filter(["12 Месяцев = 2000₽"]))
async def TwelveMonths(_, msg):
  userid = msg.from_user.id
  ExecS(planSet.format("12m", userid))
  ExecS(F"update TempUsers set SSPending=1 where UserID = {userid}")
  await msg.reply(ssprompt.format(12), reply_markup = changePlanKeybd, quote=1)
#*---------------------------------------------------------------------


'''
Cancel Registration
'''
@Client.on_message(filters.private & custom_filter([cancelText]))
async def CancelRegistration(_, msg):
  userid = msg.from_user.id
  ExecS(F"delete from TempUsers where UserID = {userid}")
  ExecS(F"delete from Config where UserID={userid}")
  await msg.reply("Процесс оплаты отменён!", reply_markup = mainKeybd, quote = 1)
#*---------------------------------------------------------------------


'''
Get VPN -> Install WG || Get Config
'''
@Client.on_message(filters.private & custom_filter(["Получить VPN"]))
async def GetVPN(_, msg):
  cleanUp(msg.from_user.id)
  return await msg.reply(F"Для подключения к VPN, необходимо установить Wireguard на Ваше устройство, добавить в него файл профиля и активировать его", reply_markup = getVPNKeybd, quote=1)
#*---------------------------------------------------------------------


'''
Get Config | Provide conf files
'''
@Client.on_message(filters.private & custom_filter(["Получить Профиль"]))
async def GetConfig(_, msg):
  userid = msg.from_user.id
  exists = Exec(F"Select count(ProfileID) from Subs where SubID={userid}")[0][0]
  if exists:
    ExecS(F"Insert or Replace into Config values({userid})")
    profiles = Exec(F"Select ProfileID from Subs where SubID={userid}")
    return await msg.reply(F"Выберите **номер профиля**", reply_markup = generateProfilesKeybd(profiles), quote=1)
  cleanUp(userid)
  return await msg.reply(F"У вас нет оплаченных профилей, пожалуйста совершите оплату, чтобы получить профиль.", reply_markup = mainKeybd, quote=1)
#*---------------------------------------------------------------------


'''
Install Wireguard -> iOS App Store || Google Play || Official Site
'''
@Client.on_message(filters.private & custom_filter(["Установить Wireguard"]))
async def InstallWG(_, msg):
  cleanUp(msg.from_user.id)
  return await msg.reply(F"Выберите подходящий вариант", reply_markup = installWGKeybd, quote=1)
#*---------------------------------------------------------------------


'''
iOS App Store
'''
@Client.on_message(filters.private & custom_filter(["iOS App Store"]))
async def iOS(_, msg):
  cleanUp(msg.from_user.id)
  return await msg.reply(F"Ссылка для скачивания: https://apps.apple.com/ru/app/wireguard/id1441195209 После скачивания - добавить в приложение файл профиля", reply_markup = mainKeybd, quote=1)
#*---------------------------------------------------------------------


'''
Google Play
'''
@Client.on_message(filters.private & custom_filter(["Google Play"]))
async def GooglePlay(_, msg):
  cleanUp(msg.from_user.id)
  return await msg.reply(F"Ссылка для скачивания: https://play.google.com/store/apps/details?id=com.wireguard.android После скачивания - добавить в приложение файл профиля.", reply_markup = mainKeybd, quote=1)
#*---------------------------------------------------------------------


'''
Official Site
'''
@Client.on_message(filters.private & custom_filter(["Официальный сайт"]))
async def OfficialSite(_, msg):
  cleanUp(msg.from_user.id)
  return await msg.reply(F"Ссылки для скачивания на любые устройства: https://www.wireguard.com/install/", reply_markup = mainKeybd, quote=1)
#*---------------------------------------------------------------------


'''
Support | Displays support info
'''
@Client.on_message(filters.private & custom_filter(["Поддержка"]))
async def Support(_, msg):
  cleanUp(msg.from_user.id)
  await msg.reply(BotConfig.supportMessage, reply_markup = mainKeybd, quote=1)
#*---------------------------------------------------------------------


'''
Text Listeners
'''
@Client.on_message(filters.private & filters.text)
async def TextListeners(app, msg):
  userid = msg.from_user.id
  msgtext = msg.text

  '''
  Listen for Profile IDs | Required for Get Config button
  '''
  if msgtext.startswith("\u2063\u2063"):
    profileid = int(msgtext.strip("\u2063"))
    try:
      if Exec(F"Select count(*) from Config where UserID = {userid}")[0][0]:
        if Exec(F"Select count(ProfileID) from Subs where ProfileID = {profileid}")[0][0]:
          if Exec(F"Select SubID from Subs where ProfileID = {profileid}")[0][0] == userid:
            UserPath = F"Subs/{userid}"
            ConfPath = F"{UserPath}/Profile{profileid}.conf"
            cleanUp(userid)
            return await msg.reply_document(document=ConfPath, caption=F"Файл конфигурации для профиля {profileid}, добавьте его в wireguard и активируйте подключение ", reply_markup = mainKeybd, quote=1)
          raise
        raise
    except:
      cleanUp(userid)
      return await msg.reply(F"Profile {profileid} doesn't exist. Make sure to send the correct ProfileID.", reply_markup = mainKeybd, quote=1)
#*---------------------------------------------------------------------
  
  
  '''
  Listen for Promo Code
  '''
  rowsTemp = Exec(F"Select count(UserID), PromoPending from TempUsers where UserID={userid}")[0]
  if rowsTemp[0]:
    promopending = rowsTemp[1]
    if promopending:
      promocode = msgtext
      if promoValid(promocode):
        ExecS(F"update TempUsers set PromoCode = '{promocode}', PromoPending=0 where UserID = {userid}")
        return await msg.reply(F"Ваш промокод: {promocode}\n\nВыберите подходящий тариф", reply_markup=plansKeybd, quote=1)
      await msg.reply("Неправильный промокод!\nПожалуйста, отправьте действительный **7 значный промокод ** или нажмите на кнопку ниже, чтобы продолжить без промокода.", reply_markup = noPromoPromptKeybd, quote=1)
#*---------------------------------------------------------------------


'''
Listen for Screenshot
'''
@Client.on_message(filters.private & filters.photo)
async def SSGrab(_, msg):
  userid = msg.from_user.id
  rowsTemp = Exec(F"Select count(UserID), SSPending, Plan, UserName, UserHandle, PromoCode from TempUsers where UserID={userid}")[0]
  if rowsTemp[0]:
    sspending = rowsTemp[1]
    if sspending:
      plan = rowsTemp[2].strip("m")
      username = rowsTemp[3]
      userhandle = rowsTemp[4]
      promocode = rowsTemp[5]

      await msg.copy(baseChat, caption = F"ID: {userid}\nName: [{username}](tg://user?id={userid})\nHandle: {userhandle if userhandle else 'None'}\nSubscription Plan: {plan} Month(s)\nPromo Code: {promocode.removesuffix('Xisting') if promocode.removesuffix('Xisting') else 'None'}"+("\n**Existing user!**" if promocode.endswith('Xisting') else '')+"\n\n**Do you approve the above subscription?**", reply_markup = prompt)
      
      ExecS(F"update TempUsers set SSPending = 0 where userid = {userid}")
      ExecS(F"insert into approvalPending values({userid})")
      cleanUp(userid)
      
      return await msg.reply(F"Мы получили Ваш скриншот, пожалуйста ожидайте подтверждения.\n\nВыбранный тариф: {plan} месяц(ев) \n\nЭтот процесс может занять некоторое время.\nПожалуйста, ожидайте. Пока мы проверяем оплату, вы можете скачать приложение нажав кнопку **ПОЛУЧИТЬ VPN**", reply_markup = mainKeybd, quote=1)
#*---------------------------------------------------------------------


'''
Handle Callback Queries
'''
@Client.on_callback_query(my_admin_filters | my_chat_filters)
async def botCallbacksGroup(app, query):
  if query.data=="yes":
    userid = int(query.message.caption.split("\n")[0][4:])
    
    # UserID,  UserHandle,  UserName, PromoCode,  Plan, PromoPending, SSPending
    rows = Exec(F"select * from TempUsers where userid = {userid}")[0]
    # print(F"{rows=}")
    userhandle = rows[1]
    username = rows[2]
    promocode = rows[3].removesuffix('Xisting')
    plan = rows[4]
    remaining = int(plan.strip("m"))*30

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
      if not rows[3].endswith('Xisting'):
        #                                  UserID,     UserHandle,     UserName,     PromoCode,     TimeStamp
        ExecS(F"insert into users values('{userid}', '{userhandle}', '{username}', '{promocode}', '{datetime.now()}')")
      #                                 ProfileID,     SubID,      Plan,     Remaining,     PromoCode
      ExecS(F"insert into Subs values('{profileid}', '{userid}', '{plan}', '{remaining}', '{promocode}')")
      ExecS(F"delete from TempUsers where userid = {userid}")
      ExecS(F"delete from approvalPending where userid = {userid}")
      
      await app.send_document(userid, document=ConfPath, caption = F"Ваш платеж подтврежден!\nНовый ПрофильID: {profileid}\n\nТариф {plan.strip('m')} месяц(ев) активирован! ✅ Добавьте этот файл в WireGuard и активируйте его для подключения.", reply_markup=mainKeybd)

      newCaption = "\n".join(query.message.caption.split("\n")[:-2])
      
      await query.edit_message_text(F"{newCaption}\nNew Profile ID: {profileid}\n\n**Subscription Approved! ✅**\n[Admin](tg://user?id={userid}) ID: {userid}")
      return await app.send_document(baseChat, document=ConfPath, caption = F"This config file has been sent to the [User](tg://user?id={userid})"+ (F" ({userhandle})" if userhandle else ""), reply_to_message_id = query.message.id)
    
    
    await app.send_message(baseChat, "Failed to set up new user profile :/", reply_to_message_id = query.message.id)

  if query.data=="no":
    userid = int(query.message.caption.split("\n")[0][4:])

    plan = Exec(F"Select Plan from TempUsers where UserID = {userid}")[0][0]
    await app.send_message(userid, F"Ваш платеж отклонён!\n\nТариф {plan.strip('m')} месяц(ев) не активирован! ❌", reply_markup=mainKeybd)
    ExecS(F"delete from TempUsers where userid = {userid}")
    ExecS(F"delete from approvalPending where userid = {userid}")
    newCaption = "\n".join(query.message.caption.split("\n")[:-1])
    
    await query.edit_message_text(F"{newCaption}\n**Subscription Disapproved! ❌**\n[Admin](tg://user?id={userid}) ID: {userid}")
#*---------------------------------------------------------------------
