# -*- coding: utf-8 -*-
"""
Created on Wed Jul  5 10:34:49 2023

@author: py20pc
"""

import socket
import time
from pyvisa.constants import StopBits, Parity

class Mcallister(object):
    '''Stolen from LexiumMDrive.py GitHub: PythonForLexium nickarmenta.
    Class for sending and receiving commands to motor in Python.'''
    
    def __init__(self, parent, add):
        '''Initialize commands: microstep resolution and baud rate (48, 96, 19, 38, 11 bps).
        Goes to startup if connected.'''
        resolution= '256'
        baud_rate= '96'
        
        #parent argumnet not used
        
        super(Mcallister, self).__init__()
        
        try:
            #print(parent)
            self.inst = parent.open_resource('COM'+str(add), baud_rate=9600,
                                      data_bits=8,
                                      parity=None,
                                      stop_bits=StopBits.one)
            print('rm done')
        except Exception as e:
            print('Could not connect - motor with pyvisa')
            print('Error from motor: '+str(e))
        
        try:
            #print(add)
            #print(socket.gethostbyname(socket.gethostname()))
            self.host_name= socket.gethostname()
            self.host_ip= socket.gethostbyname(self.host_name)
            self.Connect('192.168.33.1', 503)
        except:
            print('Connection with motor failed.')
        
        self.Write('MS'+str(resolution), add)
        self.Write('BD'+str(baud_rate), add)
        
        self.Startup(add)
        self.Read('AL', add) #retrieve all parameters

    def Connect(self, ip, add):
        '''Connect to motor at specified IP address and port.'''
        
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # create proper socket instance
        #print(self.s)
     #   try:
      #      self.s.bind(add) # attempt connection
       #     print('connection bind sent')
        #except:
         #   print('could not attempt socket connection')
     #   self.s.listen(1)
      #  connection, address = self.s.accept()
        self.s.connect(ip, add)
        print('connection passed')
        #print('Connected by', connection)
        self.Write('EM 0', add) # motor MUST be in echo mode 0 to run this Class
        print('Motor is ready for startup')
        
        #in echo mode no messages sent from motor
        #while True:
        #    try:
        #        data = connection.recv(503).decode()
        #        print(data)
        #        if not data: break
        #    except socket.error:
        #        print('Error occurred in socket.')
        #        break
    
    def Startup(self, add):
        '''Reset variables and position motor at bottom limit switch = position is zero.'''
        
        self.Initial_velocity(self, '1000', add)
        self.Maximum_velocity(self, '768000', add)
        self.Accel(self, '1000000', add)
        self.Decel(self, '1000000', add)
        
        self.Write('LM 0', add) #when hits a limit switch it decelerates to zero
        
        move = '-100'
        speed = self.Jog('100000', add)
        
        while self.Read('MV', add) == '1':
            self.MoveBy(move, add)
            if self.Read('V', add) == speed:
                move += '-100'
            else:
                print('Bottom limit switch reached.')
                self.Write('P 0', add) #sets zero position
                #self.Write('LD 0') #sets lead limit at position
                break
      
    # converts val to scaled output
    #def _Translate(self, val):
    #    return str(int(val*self.scale))
        
    def Initial_velocity(self, vel, add):
        '''Initial velocity in distance units per second per second.'''
        
        self.Write('VI '+self.vel, add)
        return self.Read('VI', add)
    
    def Maximum_velocity(self, vel, add):
        '''Maximum velocity in distance units per second per second.'''
        
        self.Write('VM '+self.vel, add)
        return self.Read('VM', add)

    def Accel(self, acc, add):
        '''Acceleration in distance units per second per second.'''
        self.Write('A '+self.acc, add)  
        return self.Read('A', add)

    def Decel(self, dec, add):
        '''Deceleration in distance units per second per second.'''
        
        self.Write('D '+self.dec, add)
        return self.Read('D', add)

    def MoveBy(self, dist, add):
        '''Move by a specific amount in one direction.'''
        
        self.Write('MR '+self.dist, add)

    def MoveTo(self, dist, add):
        '''Move to a specific point.'''
        
        self.Write('MA '+self.dist, add)

    def Jog(self, speed, add):
        '''Set moving at constant speed.'''
        
        self.Write('SL '+self.speed, add)

    #def WaitForStop(self):
    #    while(motor.Read('MV')!=0): continue
    #    return

    def GetPosition(self, add):
        return self.Read('P', add)

    #def ReadInput(self, di):
    #    return self.Read('I'+str(di)) # motor MUST be in echo mode 0 to run this Class
    
    def Moving(self, add):
        'if returns 0 then it is not moving, if it returns 1 it is moving'
        return self.Read('MV', add)

    def Write(self, cmd, add):
        '''Write MCode command to motor.'''
        
        # Create send string while checking for formatting
        try:
            msg = cmd+'\r'
        except (TypeError):
            raise AssertionError('Commands must be strings')

        self.s.sendall(msg.encode()) # send message as bytes
        if '?' in str(self.s.recv('COM'+str(add)).decode()): print("Error", self.Read('ER')) # print error code if received

    def Read(self, param, add):
        '''Read MCode parameter from motor.'''
        
        # Create send string while checking for formatting
        try:
            msg = 'PR '+param+'\r'
        except (TypeError):
            raise AssertionError('Parameters must be strings')
        
        self.s.sendall(msg.encode()) # send message as bytes
        read_msg = None
        while read_msg is None:
            read_msg = self.s.recv('COM'+str(add)).decode()

        #param_value = [int(i) for i in read_msg.split() if i.isdigit()] # extract numbers in reply
        ## Make sure there are parameter values before sending
        #if len(param_value) > 0:
        #    return param_value[0]
        #else:
        #    return None
        
        return read_msg
        
    def Escape(self, add):
        self.Write('ES', add) #stops motion
        
        if str(self.Moving)== '1':
            self.Escape(add)
            print('Wait 2 seconds...')
            #check if it is moving
            start_time = time.time()
            motion=True
            count=0
            
            while motion==True:
                if (time.time()-start_time)>2:
                    if str(self.Moving(add))== '0':
                        motion==False
                        print('Motion stopped.')
                        break
                    
                    elif str(self.Moving(add))== '1':
                        print('Wait 2 more seconds...')
                        start_time=0
                        count +=1
                        if count== 5:
                            print('10 seconds elapsed. Motor decelerating too slow or not stopping! Better if you flick a switch')
                            #TODO: no solution given yet!
                    
                    else:
                        print('Check your Motor.Moving output. Better if you flick a switch')
                        break
                else:
                    continue
        
        elif str(self.Moving(add))== '0':
            pass
        else:
            print('Check your Motor.Moving output. Better if you flick a switch')
        
    def Close(self):
        try:
            self.connection.close()
        except:
            print('Connection failed to close')
