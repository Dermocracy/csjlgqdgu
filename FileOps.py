import os, glob

def GetFilesAll(path):
  filelist = list()
  for root, _, files in os.walk(path):
    for file in files:
      filelist.append(os.path.join(root,file))
  return filelist

def GetFileNames(path, name):
  filelist = list()
  for root, _, files in os.walk(path):
    for file in files:
      if(file.startswith(name)):
        filelist.append(os.path.join(root,file))
  return filelist

def GetFileExtensions(path, extension):
  filelist = list()
  for root, _, files in os.walk(path):
    for file in files:
      if(file.endswith(extension)):
        filelist.append(os.path.join(root,file))
  return filelist

def DelFiles(files_to_del: list):
  for x in files_to_del:
    if os.path.exists(x):
      os.remove(x)

def DelFileNames(path, name):
  for filename in glob.glob(F"{path}/{name}*"):
    os.remove(filename)