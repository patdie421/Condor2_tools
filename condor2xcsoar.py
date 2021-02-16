import sys
import os
import time
import subprocess
import hashlib
import serial
import socket
import signal
import shutil

import configparser

from watchdog.observers import Observer
from watchdog.events    import FileSystemEventHandler


iniFileName="condor2xcsoar.ini"
config = configparser.ConfigParser()
config["sync"]={"tool":"None", "datapath":"/mnt/sdcard/XCSoarData"} 
config["cotaco"]={"cotaco":"cotaco.exe"}  
config["condor"]={"flppath":"C:\\condor2\\FlightPlans"}
config["xcsoar"]={"tskpath":"C:\\XCSoarData"}
files={}


def signal_handler(sig, frame):
   sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)


def err(msg):
   sys.stderr.write("ERROR: "+str(msg)+'\n')


def errExit(msg,code=1):
   sys.stderr.write("ERROR: "+str(msg)+'\n')
   sys.exit(code)


def info(msg):
   sys.stderr.write("INFO: "+str(msg)+'\n')


def warning(msg):
   sys.stderr.write("WARNING: "+str(msg)+'\n')


def doComToUdp(comPort, destHosts):
   nb=0
   while True:
      if nb==0:
         info("starting ...")
         info("CTRL-C to quit")
      else:
         info("restarting ("+str(nb)+") ...")
      nb=nb+1

      try:
         ser = serial.Serial(
            port=comPort,\
            baudrate=57600,\
            parity=serial.PARITY_NONE,\
            stopbits=serial.STOPBITS_ONE,\
            bytesize=serial.EIGHTBITS,\
            timeout=1)
         sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
         info("init done")
      except Exception as _err:
         info("Can't initialize communications")
         info(str(_err))
         sys.exit(1)

      try:
         while True:
            data=ser.read_until(size=256)
            if len(data) > 0:
               for i in destHosts:
                  sock.sendto(data, i)
               sys.stderr.write(data.decode())
      except Exception as _err:
         err("communication error. Reset communications ...")
         err(str(_err))

      sock.close()
      ser.close()


def android_adb_push(filename):
   if "sync" in config and "tool" in config["sync"] and config["sync"]["tool"].lower()=="adb":
      adb=config["sync"]["adb"]
      adbp = subprocess.Popen([adb, "push", filename, config["sync"]["datapath"]])
      stdout, stderr = adbp.communicate()


def android_adb_rm(filename):
   if "sync" in config and "tool" in config["sync"] and config["sync"]["tool"].lower()=="adb":
      adb=config["sync"]["adb"]
      print(repr(config["sync"]["datapath"]+"/"+os.path.basename(filename)))
      adbp = subprocess.Popen([adb, "shell", "rm", repr(config["sync"]["datapath"]+"/"+os.path.basename(filename))])
      stdout, stderr = adbp.communicate()


def flp2tsk(source, destination):
#   os.system(config["cotaco"]["cotaco"] + ' -line "' + source + '" "' + destination + '"')
   process = subprocess.Popen([config["cotaco"]["cotaco"], "-line", source, destination])
   try:
      outs, errs = process.communicate(timeout=15)
   except TimeoutExpired:
      process.kill()
      outs, errs = process.communicate()


def getDigest(filename):
   h = hashlib.sha256()
   with open(filename, 'rb') as file:
      while True:
         # Reading is buffered, so we can read smaller chunks.
         chunk = file.read(h.block_size)
         if not chunk:
            break
         h.update(chunk)
   return h.hexdigest()


def isFlightPlan(filename):
   if not os.path.isfile(filename):
      return False
   ext=filename.split(".")[-1].upper()
   if ext!="FPL":
      return False
   return True


def initFilesList(filespath):
   _files={}
   onlyfiles = [ os.path.join(filespath, f) for f in os.listdir(filespath) if isFlightPlan(os.path.join(filespath, f))]
   for i in onlyfiles:
     _files[i]={}
     _files[i]["digest"]=getDigest(i)
   return _files


class _FileSystemEventHandler_xcsoar(FileSystemEventHandler):
   def on_any_event(self, event):
      print("XCSOAR:", event.event_type, event.src_path)
      pass


class _FileSystemEventHandler_flp(FileSystemEventHandler):
   def on_any_event(self, event):
      print("FLP:", event.event_type, event.src_path)
      pass

   def on_created(self, event):
      if isFlightPlan(event.src_path):
         files[event.src_path]={}
         files[event.src_path]["digest"]=getDigest(event.src_path)
         _f=config["xcsoar"]["tskpath"] + os.path.sep + os.path.splitext(os.path.basename(event.src_path))[0] + ".tsk"
         flp2tsk(event.src_path, _f)
         android_adb_push(_f)

   def on_deleted(self, event):
      if event.src_path in files:
         del files[event.src_path]
         _f=os.path.splitext(os.path.basename(event.src_path))[0] + ".tsk"
         android_adb_rm(_f)

   def on_modified(self, event):
      if isFlightPlan(event.src_path):
         _digest=getDigest(event.src_path)
         if _digest != files[event.src_path]["digest"]:
            files[event.src_path]["digest"]=_digest
            _f=config["xcsoar"]["tskpath"] + os.path.sep + os.path.splitext(os.path.basename(event.src_path))[0] + ".tsk"
            flp2tsk(event.src_path,_f)
            android_adb_push(_f)

   def on_moved(self, event):
      if event.src_path in files:
         del files[event.src_path]
         _f=os.path.splitext(os.path.basename(event.src_path))[0] + ".tsk"
         android_adb_rm(_f)
      if isFlightPlan(event.dest_path):
         files[event.dest_path]={}
         files[event.dest_path]["digest"]=getDigest(event.dest_path)
         _f=config["xcsoar"]["tskpath"] + os.path.sep + os.path.splitext(os.path.basename(event.src_path))[0] + ".tsk"
         flp2tsk(event.src_path, _f)
         android_adb_push(_f)


if __name__ == "__main__":
   r=config.read(iniFileName)
   if not iniFileName in r:
      info("create "+iniFileName)
      with open(iniFileName, 'w') as configfile:
         config.write(configfile)

   if shutil.which(config["cotaco"]["cotaco"]) == None:
      errExit("can't find cotaco.exe",1)

   if os.path.isdir(config["condor"]["flppath"]):
      files=initFilesList(config["condor"]["flppath"])
   else:
      errExit(config["condor"]["flppath"]+"is not an reachable directory",1)

   if not os.path.isdir(config["xcsoar"]["tskpath"]):
      errExit(config["condor"]["flppath"]+"is not an reachable directory",1)

   event_handler_flp = _FileSystemEventHandler_flp()
   observer_flp = Observer()
   observer_flp.schedule(event_handler_flp, path=config["condor"]["flppath"]+os.path.sep, recursive=False)
   observer_flp.start()

   if "pltpath" in config["condor"]:
      defflp=config["condor"]["pltpath"]+os.path.sep+"Flightplan.fpl"
      if os.path.isfile(defflp):
         files[defflp]={}
         files[defflp]["digest"]=getDigest(defflp)   
         _f=config["xcsoar"]["tskpath"] + os.path.sep + os.path.splitext(os.path.basename(defflp))[0] + ".tsk"
         flp2tsk(defflp,_f)
         android_adb_push(_f)
      observer_flp_default = Observer()
      observer_flp_default.schedule(event_handler_flp, path=config["condor"]["pltpath"] + os.path.sep, recursive=False)
      observer_flp_default.start()

   event_handler_xcsoar = _FileSystemEventHandler_xcsoar()
   observer_xcsoar = Observer()
   observer_xcsoar.schedule(event_handler_xcsoar, path=config["xcsoar"]["tskpath"]+os.path.sep, recursive=True)
   observer_xcsoar.start()

   addrs=[]
   if "clients" in config["condor"]:
      _addrs=config["condor"]["clients"].split(",")
      for i in _addrs:
         addr,port=i.split(":")
         _port=None
         try:
	         _port=socket.getservbyname(port.strip(),"udp")
         except:
            try:
               _port=int(port.strip())
            except:
               _port=port.strip()
         addrs.append((addr.strip(),_port))
      if len(addrs)>0 and "serialport" in config["condor"]:
         doComToUdp(config["condor"]["serialport"],addrs)
      else:
         while True:
           time.sleep(5)
   observer.stop()
