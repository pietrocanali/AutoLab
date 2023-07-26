# -*- coding: utf-8 -*-
"""
Created on Fri Jul  7 15:29:32 2023

@author: py20pcClass to manage the Motor Monitoring Window.
"""

import tkinter as tk
from multiprocessing import Process, Queue, Pipe
import Instruments as Inst
import socket
import time
import re
import pyvisa


class Mon_Win(tk.Frame):
    """
    Class for the Monitoring window GUI
    """
    Motor_model = ['Mcallister']
    Mode_Select = ['Linear_Velocity', 'Costant_Velocity']
    Motion_Select = ['MoveBy', 'MoveTo']
    
    def __init__(self, master, parent, address):
        
        super().__init__(master)#adds all the TK objects in
        self.parent=parent
        
        addresses=self.parent.address_list
        
        self.Window=tk.Toplevel()
        self.Window.title("Motor Monitoring")
        self.Window.protocol("WM_DELETE_WINDOW",self.close_function)
        
        #Addresses not here since directly connected through ethernet?
        
        Control_Frame=tk.Frame(self.Window)#,height = 330,width = 480)
        Control_Frame.grid(column=0, row=1,sticky="E"+"W")
        
        self.Model=tk.StringVar(Control_Frame,"Mcallister")
        self.ModelEntry=tk.OptionMenu(Control_Frame, self.Model, *self.Motor_model)

        self.ModelEntry.grid(column=1, row=0)

        self.Com=tk.StringVar(Control_Frame,"GPIB Address")
        self.ComEntry=tk.OptionMenu(Control_Frame,self.Com,*addresses)
        self.ComEntry.grid(column=2,row=0)

        #this is to change mode for velocity - constant or linear
        self.Mode=tk.StringVar(Control_Frame,self.Mode_Select[0])
        self.Mode_Entry=tk.OptionMenu(Control_Frame,self.Mode,*self.Mode_Select)
        self.Mode_Entry.grid(column=1,row=1)
        self.Mode.trace_add("write", self.ChangeMode)
        #when a new mode is selected, automatically update the GUI and send
        #the correct mode to the Controller
        
        self.Motion=tk.StringVar(Control_Frame,self.Motion_Select[0])
        self.Motion_Entry=tk.OptionMenu(Control_Frame,self.Motion,*self.Motion_Select)
        self.Motion_Entry.grid(column=1,row=3)
        self.Motion.trace_add('write', self.ChangeMotion)
        
        #control widgets
        
        self.Initial_Velocity_entry=tk.Entry(Control_Frame)
        self.Initial_Velocity_entry.insert(tk.END,"Enter initial velocity")
        self.Maximum_Velocity_entry=tk.Entry(Control_Frame)
        self.Maximum_Velocity_entry.insert(tk.END,"Enter maximum velocity")
        self.Initial_Velocity_entry.grid(column=2, row=1)
        self.Maximum_Velocity_entry.grid(column=3, row=1)

        
        self.Accel_entry=tk.Entry(Control_Frame)
        self.Accel_entry.insert(tk.END,"Enter acceleration")
        self.Decel_entry=tk.Entry(Control_Frame)
        self.Decel_entry.insert(tk.END,'Enter deceleration')
        self.Accel_entry.grid(column=4, row=1)
        self.Decel_entry.grid(column=5, row=1)

        #Jog hidden by default
        self.Jog_entry=tk.Entry(Control_Frame)
        self.Jog_entry.insert(tk.END,'Enter speed')
        self.Jog_entry.grid(column=2, row=1)
        self.Jog_entry.grid_remove()
        
        self.MoveBy_entry=tk.Entry(Control_Frame)
        self.MoveBy_entry.insert(tk.END,'Enter distance')
        self.MoveBy_entry.grid(column=2, row=3)

        
        #MoveTo hidden by default
        self.MoveTo_entry=tk.Entry(Control_Frame)
        self.MoveTo_entry.insert(tk.END,'Enter position')
        self.MoveTo_entry.grid(column=2, row=3)
        self.MoveTo_entry.grid_remove()
        
        self.Position_Button = tk.Button(Control_Frame,
                                         text="Position?",
                                         command= self.GetPosition)
        
        self.Position_Button.grid(column=5, row=3)
        
        self.Stop_Button=tk.Button(Control_Frame,
                                         text = "Stop",
                                         command = self.Escape,
                                         bg = "red",
                                         width=15)
        
        self.Stop_Button.grid(column=3, row=3, sticky="s")
        
        self.Start_Button=tk.Button(Control_Frame,
                                         text = "Start",
                                         command = self.Start,
                                         bg = "green",
                                         width=15)
        
        self.Start_Button.grid(column=4,row=3)
        
        #now open the pipe
        
        self.Open_Pipes(address)

    def Open_Pipes(self, address):
        """
        Opens the MultiThreading and initialises. 
        """
        self.Motor_PipeRecv, self.Motor_PipeSend = Pipe(duplex=True)
        self.Control=Process(target=(Controller),args=(self.Motor_PipeSend, address))
        self.Control.start()

    def close_function(self):
        """
        Funciton to call when the monitoring window is exited.
        """
        print("This will exit the multithreading gracefully")
        self.Motor_PipeRecv.send("Close")
        self.Window.destroy()
        
    def Start(self, mode=Mode_Select[0], motion=Motion_Select[0]):
        '''Start function - updates mode and motion'''
        self.Motor_PipeRecv.send('{}'.format(mode))
        self.Motor_PipeRecv.send('{}'.format(motion))
        
    def Get_Pipe_Data(self):
        """   
        Check if the pipe has anything in it
        Loads data from the pipe and adds it to the datasets
        Stolen from Base Autolab
        """
        Start_T = time.time()
        
        while(True):
            # Timeout if it spends too long reading the que, likely because is very full
            if time.time()-Start_T>5:
                print("Timeout, Queue might be too large!")
                break
             
            #Check if there is something to recieve in the pipe
            if not self.Motor_PipeRecv.poll():
                break
             
            #get data from pipe
            Data = self.Motor_PipeRecv.recv()
             
            #If data isn't a string append to rawdata list
             
            if type(Data)!=str:
                self.current_Data=Data
             
            # TODO add more key work commands, NewFile, ClearGraph,
            elif Data=="Esc":
                #self.MeasureFinished()
                break
            elif Data=="ClearGraph":
                self.Temperature_Data = []
                continue
            else:
                None

    def GetPosition(self):
        '''
        Checks for position of motor.
        '''
        self.Motor_PipeRecv.send('Pos?')

    def set_Linear_Velocity(self):
        '''
        Sets initial velocity, maximum velocity, accel, decel for Linear Velocity mode.
        '''
        try:
            In_V= float(self.Initial_Velocity_entry.get())
            Max_V= float(self.Maximum_Velocity_entry.get())
            A= float(self.Accel_entry.get())
            D= float(self.Decel_entry.get())
            
            if 1<= In_V<= (Max_V-1) and (In_V+1)<= Max_V<= 5000000 and 91<= A<= 1525878997 and 91<= D<= 1525878997:
                self.Motor_PipeRecv.send("Lin; {0},{1},{2},{3}".format(In_V,Max_V,A,D))
            else:
                print("Invalid values for linear velocity! Velocity must be between 1 and 5000000 with Inital<Maximum and Accel,Decel between 91 and 1525878997")
                print("Recived values of InV:{0},MaxV:{1},Accel:{2},Decel:{3}".format(In_V,Max_V,A,D))
        except ValueError:
            print("velocities,accel,decel could not be cast as Float! values unchanged!")

    def set_Constant_Velocity(self):
        '''
        Sets speed, accel, decel for Constant Velocity mode.
        '''
        try:
            Speed= float(self.Jog_entry.get())
            A= float(self.Accel_entry.get())
            D= float(self.Decel_entry.get())
            
            if -5000000<= Speed<= 5000000 and 91<= A<= 1525878997 and 91<= D<= 1525878997:
                self.Motor_PipeRecv.send('Const; {0},{1},{2}'.format(Speed,A,D))
            else:
                print("Invalid values for constant velocity! Speed must be between -/+5000000 with Accel,Decel between 91 and 1525878997")
                print("Recived values of Speed:{0},,Accel:{1},Decel:{2}".format(Speed,A,D))
        except ValueError:
            print("speed, accel,decel could not be cast as Float! values unchanged!")

    def set_MoveBy(self):
        '''
        Sets MoveBy distance.
        
        At the moment can only do a max of 50000 steps at once.
        #TODO Check maximum distance possible
        '''
        try:
            dist= int(self.MoveBy_entry.get())
            
            if 1<= dist <=50000:
                self.Motor_PipeRecv.send('MoveBy; {0}'.format(dist))
            else:
                print('Invalid entry for distance to move by - max is 50000.')
                print('Received value of dist:{0}'.format(dist))
        except ValueError:
            print('distance could not be cast as Integer! value unchanged')

    def set_MoveTo(self):
        '''
        Sets MoveTo position.
        
        At the moment can only go to maximum step height of 1000000.
        Change to maximum distance from 0 lowest point.
        '''
        try:
            position= int(self.MoveTo_entry.get())
            
            if 0<= position <=1000000:
                self.Motor_PipeRecv.send('MoveTo; {0}'.format(position))
            else:
                print('Invalid entry for distance to move to - max is 1000000.')
                print('Received value of position:{0}'.format(position))
        except ValueError:
            print('position could not be cast as Integer! value unchanged')

    def Escape(self):
        """
        Stops the motor motion - decelrate to a stop. 
        Puts constant speed to 0 and decelration high.
        """
        self.Motor_PipeRecv.send("Esc")
        self.Motor_PipeRecv.send("Const; 0,100,10000000")

    def ChangeMode(self, var, index, mode):
        """
        Code to change the mode in  GUI elements and send commands to controller. 
        SHOULD only activate if the value changes, not if the menu was open so SHOULD be invuln to
        Monkey BS
        Paramters are TK Nonsense. Not used.
        
        """
        NewMode=self.Mode_Select.index(self.Mode.get())
        if NewMode==0: #Linear Velocity Mode
            self.Jog_entry.grid_remove()
            self.Accel_entry.grid_remove()
            self.Decel_entry.grid_remove() #Remove Unecessary GUI Elements
            self.Initial_Velocity_entry.grid()
            self.Maximum_Velocity_entry.grid()
            self.Accel_entry.grid()
            self.Decel_entry.grid() #re-show necessary GUI elements.
            #self.Start_Button.configure(mode='Linear_Velocity')#make sure correct values are being passed
        elif NewMode==1: #Constant Velocity
            self.Initial_Velocity_entry.grid_remove()
            self.Maximum_Velocity_entry.grid_remove()
            self.Accel_entry.grid_remove()
            self.Decel_entry.grid_remove()
            self.Jog_entry.grid()
            self.Accel_entry.grid()
            self.Decel_entry.grid()
           # self.Start_Button.configure(mode='Constant_Velocity')
        else:
            print('Check your Mode Selection')

    def ChangeMotion(self, var, index, mode):
        '''
        As for CahngeMode but changes motion in GUI elements and sends motion commands to controller.
        '''
        NewMotion=self.Motion_Select.index(self.Motion.get())
        if NewMotion==0: #MoveBy
            self.MoveTo_entry.grid_remove()
            self.MoveBy_entry.grid()
           # self.Start_Button.configure(motion='MoveBy')
        elif NewMotion==1: #MoveTo
            self.MoveBy_entry.grid_remove()
            self.MoveTo_entry.grid()
          #  self.Start_Button.configure(motion='MoveTo')
        else:
            print('Check your Motion Selection')

def Controller(Pipe, address):
    '''
    Multiprocessing Process for Motor Monitoring.
    
    Currently MS is 256, baud rate 96
    
    At startup inital velocity is 1000, maximum velocity is 768000,
    accel and decel are 1.0E6.
    
    Parameters
    ----------
    Pipe : Pipe
        PipeSend to pass things through
    '''
    Abort= False
    rm = pyvisa.ResourceManager()
    
    try:
        Motor= Inst.Mcallister(rm, address)
        print('Connected to Motor.')
    except Exception as e:
        print(e)
        print('Connection failed - Controller.')
        Pipe.close() #closing the Process since there is no connection
        #this will also close the window though?
        Abort=True
        
    while Abort== False:
        Current_Position= Motor.GetPosition(address)
        Pipe.send([time.time(), Current_Position])
        
        if Pipe.poll():
            Comm= Pipe.recv()
            
            if Comm== 'Close':
                Abort=True
                break
            
            elif Comm== 'Esc':
                try:
                    Motor.Escape(address)
                    print('Motor has stopped - Controller')
                except:
                    print('Motion could not be stopped - Controller. Stop it yourself!')
            
            elif Comm== 'Pos?':
                try:
                    Motor.GetPosition(address)
                except:
                    print('Something wrong with position')
            
            else:
                Param= re.split(';', str(Comm))
                
                if len(Param)== 2:
                    if Param[0]== 'Lin':
                        values= re.split(',', str(Param[1]))
                        
                        Motor.Initial_velocity(values[0], address)
                        Motor.Maximum_velocity(values[1], address)
                        Motor.Accel(values[2], address)
                        Motor.Decel(values[3], address)
                        
                    elif Param[0]== 'Const':
                        values= re.split(',', str(Param[1]))
                        
                        Motor.Jog(values[0], address)
                        Motor.Accel(values[1], address)
                        Motor.Decel(values[2], address)
                    
                    elif Param[0]== 'MoveBy':
                        Motor.MoveBy(Param[1], address)
                    
                    elif Param[0]== 'MoveTo':
                        Motor.MoveTo(Param[1], address)
                        
                    else:
                        print('Something wrong with command. - command not known')
                else:
                    print('Somehting wrong with command. - command not the right length')
    
#    try:
 #       Motor.Escape(address)
  #      print('Motor has stopped - Controller')
   # except:
    #    print('Motion could not be stopped - Controller. Stop it yourself!')
#
 #   try:
  #      Motor.Close(address)
   #     print('Connection closed. - Controller')
    #except:
     #   print('Connection could not be closed. - Controller')
      #  
#    try:
 #       Pipe.close()
  #      print('Pipe closed.')
   #     #not sure we want to close this? maybe first go through disconnect with Motor_Con
    #except:
     #   print('Pipe could not be closed.')
        
        