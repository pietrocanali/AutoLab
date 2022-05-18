# -*- coding: utf-8 -*-
"""
Created on Fri May 13 10:54:26 2022

@author: eenmv
"""

class IPS120(object):
    
    def __init__(self, rm, channel):
        
        self.inst = rm.open_resource('GPIB0::'+str(channel)+'::INSTR')
        #Setup termination characters
        self.inst.write_termination = "\r"
        self.inst.read_termination = "\r"
        
        try:
            #Set to remote and unlocked
            self.inst.write("C3")
            #Set to extend high precesion return values
            self.inst.write("Q4")
        except:
            pass
        
        self.inst.clear()
        
    
    def __del__(self):
        self.inst.close()
    
    def ExamineStatus(self):
        #Get Statues of machine
        self.inst.clear()
        
        statusMessage = self.inst.query("X")
        #returns:
        #   XnmAnCnHnMmnPmn
        self.SystemStatus = int(statusMessage[1:3])
        
        self.ActivityStatus = int(statusMessage[4])
        
        if self.ActivityStatus==0:
            self.Activity = "Hold"
            self.Ramping = False
            
        elif self.ActivityStatus==1:
            self.Activity = "Ramping to Zero"
            self.Ramping = True
            
        elif self.ActivityStatus==2:
            self.Activity = "Ramping to Zero"
            self.Ramping = True
            
        elif self.ActivityStatus==3:
            self.Activity = "Clamped"
            self.Ramping = False
        
        self.SwitchHeaterStatus = int(statusMessage[8])
        
        if self.SwitchHeaterStatus==1:
            self.is_SwitchHeaterOn = True
        else:
            self.is_SwitchHeaterON = False
            
        self.RemoteStatus = int(statusMessage[6])
        
        self.PolarityStatus = int(statusMessage[13:])
    
    
    def SwitchHeaterOff(self):
        self.inst.write("H0")
    
    def SwitchHeaterOn(self):
        self.inst.write("H2")
    
    
    def get_SweepRate(self):
        return self.inst.query("R 9")
    
    def get_SetPoint(self):
        return self.inst.query("R 8")
    
    def get_B(self):
        return self.inst.query("R 7")
    
    
    def set_SetPoint(self,B):
        self.inst.write("J{:.5f}".format(B))
        
    def set_FieldRate(self,Rate):
        self.inst.write("J{:.5f}".format(Rate))
    
    
    #set the activity of the IPS
    def sweep_Hold(self):
        self.inst.write("A0")
        
    def sweep_SetPoint(self):
        self.inst.write("A1")
        
    def sweep_ToZero(self):
        self.inst.write("A2")
    
    def sweep_Clamp(self):
        self.inst.write("A4")