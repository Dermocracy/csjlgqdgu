import sqlite3

dbname = "UserMgmt.db"
connection = sqlite3.connect(dbname, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
cursor = connection.cursor()

def Exec(query: str):
  cursor.execute(query)
  return cursor.fetchall()

def SaveDB():
  connection.commit()

def ExecS(query: str):
  cursor.execute(query)
  SaveDB()