import sqlite3
import os

dbname = "UserMgmt.db"

with open(F"{dbname[:-3]}.txt", "w", encoding='utf-8') as sy:sy.close()
os.rename(F"{dbname[:-3]}.txt", dbname)

connection = sqlite3.connect(dbname, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
cursor = connection.cursor()

# UserID,  UserHandle,  UserName,  PromoCode,  TimeStamp
createUserTable='''
CREATE TABLE IF NOT EXISTS
Users(UserID INTEGER PRIMARY KEY,
UserHandle TEXT,
UserName TEXT,
PromoCode TEXT,
TimeStamp TIMESTAMP)
'''
cursor.execute(createUserTable)

# UserID,  UserHandle,  UserName, PromoCode,  Plan, PromoPending, SSPending
createTempUserTable='''
CREATE TABLE IF NOT EXISTS
TempUsers(UserID INTEGER PRIMARY KEY,
UserHandle TEXT,
UserName TEXT,
PromoCode TEXT,
Plan TEXT,
PromoPending INTEGER DEFAULT 1,
SSPending INTEGER DEFAULT 1)
'''
cursor.execute(createTempUserTable)

# ProfileID,  SubID,   Plan,  Remaining,  PromoCode
createSubsTable='''
CREATE TABLE IF NOT EXISTS
Subs(ProfileID INTEGER PRIMARY KEY,
SubID INTEGER,
Plan TEXT,
Remaining INTEGER,
PromoCode TEXT)
'''
cursor.execute(createSubsTable)

# Users
# UserID,  UserHandle,  UserName,  PromoCode,  TimeStamp
# 127532   @Sys         SysWoW     HarryMack
# 675123   @Poezt       Poezee     SYGaming
# 385465   @Tanz        Tanzy      HarryMack

# TempUsers
# UserID,  UserHandle,  UserName, PromoCode,  Plan, PromoPending, SSPending
# 854389   @Newser      NewName   SYGamin     6m    1             1

# Subs
# ProfileID,  SubID,   Plan,  Remaining,  PromoCode
# 1           127532   1m     28          HarryMack
# 2           127532   6m     176         HarryMack
# 3           385465   1m     23          HarryMack
# 4           127532   12m    348         HarryMack
# 5           675123   6m     152         SYGaming
# 6           675123   12m    282         SYGaming

# Dir tree
# Subs/UserID/ProfileID.conf
# Subs/UserID/ProfileID.keys

createConfigTable='CREATE TABLE IF NOT EXISTS Config(UserID INTEGER PRIMARY KEY)'
cursor.execute(createConfigTable)
createConfigTable='CREATE TABLE IF NOT EXISTS approvalPending(UserID INTEGER PRIMARY KEY)'
cursor.execute(createConfigTable)