import sys
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import argparse
import signal

import pygame as pg
import keyboard

cli_description='''
Brake for Condor2 with rubber or throttle
'''

def signal_handler(sig, frame):
    info('The end')
    pg.quit()
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)
    
def errExit(msg,code=1):
   sys.stderr.write("ERROR: "+str(msg)+'\n')
   pg.quit()
   sys.exit(code)

def info(msg):
   sys.stderr.write("INFO: "+str(msg)+'\n')
   
def warning(msg):
   sys.stderr.write("WARNING: "+str(msg)+'\n')
   
def getArgs():
   args_common = argparse.ArgumentParser()
   args_common.add_argument("-l", "--list", action="store_true", dest="list", help="list available joysticks", default=False)
   args_common.add_argument("-r", "--reverse", action="store_true", dest="reverse", help="reverse use", default=False)
   args_common.add_argument("-i", "--instance_id", dest="instance_id", help="select joystick by instance_id", default=None)
   args_common.add_argument("-n", "--name", dest="name", help="select joystick by name", default=None)
   args_common.add_argument("-g", "--guid", dest="guid", help="select joystick by guid", default=None)
   args_common.add_argument("-1", "--axis_1", dest="a1", help="first axis to use", default=0)
   args_common.add_argument("-2", "--axis_2", dest="a2", help="second axis to use", default=None)
   args_common.add_argument("-k", "--key", dest="key", help="key to send", default='B')
   
   
   args_parser = argparse.ArgumentParser(description=cli_description, formatter_class=argparse.RawDescriptionHelpFormatter, parents=[args_common], add_help=False)

   args, _args = args_parser.parse_known_args()
   
   return args_parser, args, _args


def listJoysticks(joysticks):
   for joystick in joysticks:
      print(joystick.get_instance_id(),"-","name:",joystick.get_name())
      print("- instance_id:",joystick.get_instance_id())
      print("- guid:",joystick.get_guid())
      print("- nb axes:",joystick.get_numaxes())
      print("- nb buttons:",joystick.get_numbuttons())
      print("- nb hats:",joystick.get_numhats())
      print("- nb balls:",joystick.get_numballs())
      print("- power lvl:",joystick.get_power_level())


def doBrakes4Condor(joysticks, instance_id=0, a1=0, a2=1, key=';', reverse=1):
   _joystickByInstanceId=[None]*len(joysticks)
   for joystick in joysticks:
      _joystickByInstanceId[joystick.get_instance_id()]=joystick
      joystick.init()
   pressed = 0
   running = True
   while running:
      for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False
            if event.type in [pg.JOYBUTTONDOWN,pg.JOYBUTTONUP,pg.JOYAXISMOTION,pg.JOYHATMOTION,pg.JOYBALLMOTION]:
                _j = event.instance_id
                if event.type == pg.JOYBALLMOTION:
#                    print("BALL:",_j)
                    pass
                if event.type == pg.JOYBUTTONDOWN:
#                    print("BUTTON DOWN: ", _j, event.button)
                    pass
                elif event.type == pg.JOYBUTTONUP:
#                    print("BUTTON UP: ", _j, event.button)
                    pass
                elif event.type == pg.JOYHATMOTION:
                    h = event.hat
                    hat = _joystickByInstanceId[_j].get_hat(h)
#                    print("HAT:", _j,hat)
                elif event.type == pg.JOYAXISMOTION:
                    a = event.axis
#                    axis = _joystickByInstanceId[_j].get_axis(a)
#                    print("AXIS:",j,a,axis)
                    if _j==instance_id and (a==a1 or a==a2):
                       axis1 = _joystickByInstanceId[instance_id].get_axis(a1)*reverse
                       if a2 != None:
                          axis2 = _joystickByInstanceId[instance_id].get_axis(a2)*reverse
                       else:
                          axis2 = 1.0
                       if axis1 > 0.75 and axis2 > 0.75:
                          if pressed==0:
                             keyboard.press(key)
                             info("BRAKES ON")
                             pressed=1
                       elif axis1 < 0.70 or axis2 < 0.70:
                          if pressed==1:
                             keyboard.release(key)
                             info("BRAKES OFF")
                             pressed=0
      pg.time.wait(25)


def getInstanceIdByName(joysticks, name):
   for j in joysticks:
      if j.get_name().lower() == name.lower():
         return j.get_instance_id()
   return None

def getInstanceIdByGuid(joysticks, guid):
   for j in joysticks:
      if j.get_guid().lower() == guid.lower():
         return j.get_instance_id()
   return None

def getJoystickByInstanceId(joysticks, instance_id):
   for j in joysticks:
      if j.get_instance_id() == instance_id:
         return j
   return None

if __name__ == "__main__":
   args_parser, args, _args = getArgs()
      
   count=0
   for param in [ args.name, args.instance_id, args.guid ]:
      if param != None:
         count=count+1
   if count > 1:
      errExit("instance_id, name, guid are exclusivs. Use only one to select joystick")
   
   pg.init()
   # Create a list of available joysticks and initialize them.
   joysticks = [pg.joystick.Joystick(x) for x in range(pg.joystick.get_count())]

   if len(joysticks) < 1:
      errExit("no joystick available")
   joysticks.sort(key=lambda x: x.get_instance_id(), reverse=False)

   if args.list==True:
      listJoysticks(joysticks)
      pg.quit()
      sys.exit(0)

   if args.reverse==True:
      reverse=-1
   else:
      reverse=1
   print(reverse)
   instance_id=joysticks[0].get_instance_id()
   a1=0
   a2=0
   a1=int(args.a1)
   if args.a2==None:
      a2=None
   else:
      a2=int(args.a2)

   if args.name!=None:
      instance_id = getInstanceIdByName(joysticks,str(args.name))
   elif args.instance_id!=None:
      instance_id=int(args.instance_id)
   elif args.guid!=None:
      instance_id = getInstanceIdByGuid(joysticks,str(args.guid))
   else:
      warning("no selection, we will trying with first joystick found")

   if instance_id == None:
      errExit("Can't select joystick with your parameters")

   j=getJoystickByInstanceId(joysticks, instance_id)

   nb_axes = j.get_numaxes()
   if(nb_axes == 0):
      errExit("no axes available on selected joystick")

   if not (a1 < nb_axes) or a1 < 0:
      errExit("axes selection error - axe a1 out of range [0,"+str(nb_axes-1)+"]")
   if a2 and (not (a2 < nb_axes) or a2 < 0):
      errExit("axes selection error - axe a2 out of range [0,"+str(nb_axes-1)+"]")

   info("using: "+j.get_name()+" (instance_id:"+str(instance_id)+" guid:"+str(j.get_guid())+")")
   if a2==None:
      info("one axe used: "+str(a1))
   else:
      info("two axe used: "+str(a1)+" and "+str(a2))
   info("CTRL-C to quit")
   doBrakes4Condor(joysticks, instance_id=instance_id, a1=a1, a2=a2, key=args.key[0].lower(), reverse=reverse)

   pg.quit()