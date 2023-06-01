from BotConfig import ServerPublicKey, ServerIPAddress, ListeningPort
import subprocess
import os


GenerateKeyFiles = "wg genkey | (umask 0077 && tee pv.key) | wg pubkey > pb.pub"
EnableClientTemplate = "wg set wg0 peer {ClientPublicKey} allowed-ips 10.0.0.{ProfileID}"
DisableClientTemplate = "wg set wg0 peer {ClientPublicKey} remove"
QrPNG = "qrencode -o {ImgOut} < {confFile}"
QRConsole =  "qrencode -t ansiutf8 < {confFile}"


def GenerateKeys():
  privkey = subprocess.check_output("wg genkey", shell=True).decode("utf-8").strip()
  pubkey = subprocess.check_output(f"echo '{privkey}' | wg pubkey", shell=True).decode("utf-8").strip()
  return (privkey, pubkey)

def EnableClient(pubkey, profileid):
  return os.system(EnableClientTemplate.format(ClientPublicKey=pubkey, ProfileID=profileid))

def DisableClient(pubkey):
  return os.system(DisableClientTemplate.format(ClientPublicKey=pubkey))


ClientConfFileTemplate = '''[Interface]
PrivateKey = {ClientPrivateKey}
Address = 10.0.0.{ProfileID}/24
DNS = 1.1.1.1, 8.8.8.8'''+F'''

[Peer]
PublicKey = {ServerPublicKey}
Endpoint = {ServerIPAddress}:{ListeningPort}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25'''


# Dir Struct: Subs/UserID/ProfileID/ProfileID.conf
def Setup_Profile(userPath, confPath, profileid):
  try:
    if not os.path.exists(userPath):
      os.makedirs(userPath)
    
    CliPrivKey, CliPubKey = GenerateKeys()
    
    with open(userPath+F"/Profile{profileid}.keys", "w", encoding='utf-8') as keys:
      keys.write(F"{CliPubKey}\n{CliPrivKey}")
      keys.close()
    
    with open(confPath, "w", encoding='utf-8') as sy:
      sy.write(ClientConfFileTemplate.format(ClientPrivateKey = CliPrivKey, ProfileID = profileid))
      sy.close()
    
    EnableClient(CliPubKey, profileid)
    
    return 1
  
  except:return 0