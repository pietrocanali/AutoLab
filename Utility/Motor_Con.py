# -*- coding: utf-8 -*-
"""
Created on Tue Jul 11 13:51:34 2023

@author: py20pc
"""

# from Grren CryoTem_Con
import tkinter as tk
import time
import pyvisa
import Instruments as Inst
from time import sleep
from Utility import MotorMon_Window


class Util(tk.Frame):
    """Controller widget for Motor control
    This uses rm to find the gpib address to send to the MotorMon_Window.
    """
    
    #Name of utility so it can be refer to later as part of a dictionary
    name = "Motor_Con"
    statusTemplate = """Position (steps) :{}\nInitial Velocity (steps/s):{}\nMaximum Velocity (steps/s):{} \nAccel (steps/s**2):{}\nDecel (steps/s**2):{}
        """
    
    statParam = ["NAN","NAN","NAN","NAN"]
    
    def __init__(self, master, parent):
        """
        Initial Setup of the Util Frame
        """
        self.parent=parent
        super().__init__(master)
        Utilframe = tk.Frame(master)
        master.add(Utilframe,text="Pos Reading Mcallister")
        self.Is_connected=False
        #latch to see if something is connected. If not connected, asking to update
        #Status or Turn off Heaters will connect first, Setting a setpoint will yell at foolhardy user
        self.Is_monitoring=False
        
        gbipLabel_Motor = tk.Label(Utilframe,text="Motor COM")
        gbipLabel_Motor.grid(column=0, row=0, pady=5)
        self.gpibMotorEntry = tk.Entry(Utilframe,width = 5)
        self.gpibMotorEntry.insert(tk.END,"4")
        self.gpibMotorEntry.grid(column=1, row=0, pady=5)
        
        #gbipLabel_218 = tk.Label(Utilframe,text="218 GPIB")
        #gbipLabel_218.grid(column=0, row=1)
        #self.gpib218Entry = tk.Entry(Utilframe,width = 5)
        #self.gpib218Entry.insert(tk.END,"6")
        #self.gpib218Entry.grid(column=1, row=1)
        
        self.ConnectButton = tk.Button(Utilframe,
                                         text = "Connect",
                                         command = self.Connect,
                                         bg="light gray"
                                         )
        self.ConnectButton.grid(column = 2, row = 0)
        #This button Toggles between Connect and Disconnect depending on the last function used.
        
        
        self.Stop_Button=tk.Button(Utilframe,
                                         text = "Stop",
                                         command = self.Escape,
                                         bg = "red",
                                         width=55)
        
        self.Stop_Button.grid(column=0, row=2, columnspan=4)
        
        self.Position_Button = tk.Button(Utilframe,
                                        text="Position?",
                                        command= self.GetPosition)
       
        self.Position_Button.grid(column=2, row=1)
        
        """
        Status Widget
        """
        self.statParam = ["NAN","NAN","NAN","NAN","NAN"]
        
        self.StatusLabel = tk.Label(Utilframe,text=self.statusTemplate.format(*self.statParam),
                                    relief=tk.RIDGE,
                                    justify=tk.LEFT)
        self.StatusLabel.grid(column=5, row=0, rowspan=3)
        
        self.Toggle_Monitor = tk.Button(Utilframe,
                                         text="Open\nMotorCon",
                                         command= self.Start_monitoring,
                                         height=5
                                         )
        self.Toggle_Monitor.grid(column = 6, row =0, rowspan=3)
        
    def Connect(self):
        """
        Attempt to connect to the two temperature controllers
        """
        self.rm=pyvisa.ResourceManager()
        LMotoradd=self.gpibMotorEntry.get()
        #L218add=int(self.gpib218Entry.get())#lakeshore addresses
        try:
            self.Motorcon=Inst.Mcallister(self.rm,int(LMotoradd))
            #self.Tmon=Inst.lakeshore218(self.rm,L218add)
            self.ConnectButton.configure(bg="green",text="Disconnect",command=self.Disconnect)
            self.Is_connected=True
        except Exception as e:
            print("Error Found In Connection")
            self.ConnectButton.configure(bg="red")
            print(e)
        
    def Disconnect(self):
        """
        Attempt to Disconnect from the instruments and close the resource manager

        """
        try:
            self.Motorcon.close()
            #self.Tmon.close()
            self.ConnectButton.configure(bg="light gray",text="Connect",command=self.Connect)
            self.Is_connected=False
            self.rm.close()
        except Exception as e:
            self.ConnectButton.configure(bg="red")
            print(e)
        
    def update_status(self,Position,Initial_Velocity,Maximum_Velocity,Accel,Decel):
        """ 
        Quick Method to update the StatParam Box
        """
        self.statParam=[Position,Initial_Velocity,Maximum_Velocity,Accel,Decel]
        self.StatusLabel["text"] = self.statusTemplate.format(*self.statParam)
        
    def Escape(self):
        if self.Isconnected == False:
            rm=pyvisa.ResourceManager()
            LMotoradd=self.gpibMotorEntry.get()
            Motorcon=Inst.Mcallister(self.rm,int(LMotoradd))
            Motorcon.allOff()
            Motorcon.close()
            rm.close()
        else:            
            self.Motorcon.allOff()
            
    def GetPosition(self):
        '''Ask for current position of motor.'''
        if self.Is_connected==True:
            rm=pyvisa.ResourceManager()
            LMotoradd=self.gpibMotorEntry.get()
            Motorcon=Inst.Mcallister(self.rm,int(LMotoradd))
            Motorcon.GetPosition(LMotoradd)
        
    
    def Start_monitoring(self):
        """
        Starts a new thread to read and control the temperature controllers. 
        NOTE: While monitoring, all commands have to be sent via the pipe.

        Returns
        -------
        None.

        """
        # Mon_Window=tk.Toplevel(self.master)
        # Mon_Window.title("Temp_Mon")
        address=[int(self.gpibMotorEntry.get())]
        #print(address)
        self.parent.Motor_Monitor=MotorMon_Window.Mon_Win(self,self.parent,address)
        #Passes the Temperature Monitor to the Main Autolab script, where Workers can inherit it
        #Note; I think the Base thing will be inheriting a bit much from this! 
        #It only NEEDS the output of the Pipe and a way to send commands to the Controller. 
        #TODO: Think.
        

        
        
