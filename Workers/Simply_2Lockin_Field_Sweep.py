# -*- coding: utf-8 -*-
"""
Created on Fri May  6 14:59:33 2022

@author: eenmv

Basic Keithley IV curve setup

"""

import tkinter as tk
import time
import numpy as np

import sys
sys.path.append("..")

from multiprocessing import Process, Queue

import pyvisa

import Instruments as Inst

class Handler(tk.Frame):
    """
    Measurement worker of the main AutoLab window
    """
    def __init__(self, master):
        """
        Initial setup of GUI widgets and the general window position
        """
        super().__init__(master)
        
        StartEntryLabel = tk.Label(master,text="Start (T)")
        StartEntryLabel.pack()
        self.StartEntry = tk.Entry(master,width = 10)
        self.StartEntry.insert(tk.END,"0")
        self.StartEntry.pack()
        
        StopEntryLabel = tk.Label(master,text="Stop (T)")
        StopEntryLabel.pack()
        self.StopEntry = tk.Entry(master,width = 10)
        self.StopEntry.insert(tk.END,"0.5")
        self.StopEntry.pack()
        
        RateEntryLabel = tk.Label(master,text="Sweep Rate (T/min)")
        RateEntryLabel.pack()
        self.RateEntry = tk.Entry(master,width = 10)
        self.RateEntry.insert(tk.END,"0.1")
        self.RateEntry.pack()
        
        DwellEntryLabel = tk.Label(master,text="Dwell (s)")
        DwellEntryLabel.pack()
        self.DwellEntry = tk.Entry(master,width = 10)
        self.DwellEntry.insert(tk.END,"0.5")
        self.DwellEntry.pack()

        
    def Start(self,Pipe):
        """
        Start the worker doing the measurement
        """
        
        # get values from entry windows
        Str  = float(self.StartEntry.get())
        Stp  = float(self.StopEntry.get() )
        Rate = float(self.RateEntry.get())
        Dwl  = float(self.DwellEntry.get())
        
        #Test parameters
        if (Rate>0.1):
            print("Ramp rate too high. Limit is 0.1T/min")
            return False
        elif (abs(Str)>8):
            print("Parameters out of bounds")
            return False
        elif (abs(Stp)>8):
            print("Parameters out of bounds")
            return False
        
        try:
            
            self.Worker = Process(target=Worker, args=(Pipe,Str,Stp,Rate,Dwl))
            self.Worker.start()
            
        except Exception as e:
            print(e)
            print("failed to start multiprocessing of expirement worker")
            return False
        
        return True
    
    def Stop(self):
        """
        Abort the current measurement as gracefully as possible
        """
        try:
            self.Measure.terminate()
        except:
            print("Failed to stop process")
            return False
       
        return True

        
def Worker(Pipe,Str,Stp,Rate,Dwl):
    
    rm = pyvisa.ResourceManager()
    
    Abort = False
    
    try:
        Lockin1 = Inst.DSP_7265(rm,14)
        Lockin2 = Inst.DSP_7280(rm,12)
        Mag = Inst.IPS120(rm,25)
    except:
        Pipe.send("Esc")
        return
    
    #column headers
    Pipe.send("B    Rxx_X    Rxy_X    Rxx_Y    Rxy_Y")
    
    #Test if Magnet switch heater is on
    Mag.ExamineStatus()
    
    if Mag.is_SwitchHeaterOn:
        pass
    else:
        Mag.SwitchHeaterOn()
        time.sleep(60)
    
    
    #Go to start position
    Mag.set_SetPoint(Str)
    Mag.set_RampRate(Rate)
    Mag.sweep_SetPoint()
    
    Mag.ExamineStatus()
    #Wait until reached start position
    while(Mag.Ramping):
        time.sleep(1)
        Mag.ExamineStatus()
    
    
    #Ramp to stop field
    Mag.set_SetPoint(Stp)
    Mag.sweep_SetPoint()
    
    while(Mag.Ramping):
        
        #Check for commands from controller
        if Pipe.poll():
            Comm = Pipe.recv()
            if Comm=="STOP":
                Abort = True
        if Abort == True:
            break
        
        B = Mag.get_B()
        
        Rxx_X,Rxx_Y = Lockin1.XY
        Rxy_X,Rxy_Y = Lockin2.XY
        
        Pipe.send([B,Rxx_X,Rxy_X,Rxx_Y,Rxy_Y])
        
        time.sleep(Dwl)
        Mag.ExamineStatus()
    
    #Ramp to start field
    Mag.set_SetPoint(Str)
    Mag.sweep_SetPoint()
    
    while(Mag.Ramping):
        
        if Pipe.poll():
            Comm = Pipe.recv()
            if Comm=="STOP":
                Abort = True
        if Abort == True:
            break
        
        B = Mag.get_B()
        
        Rxx_X,Rxx_Y = Lockin1.XY
        Rxy_X,Rxy_Y = Lockin2.XY
        
        Pipe.send([B,Rxx_X,Rxy_X,Rxx_Y,Rxy_Y])
        
        time.sleep(Dwl)
        Mag.ExamineStatus()
    
    Pipe.send("Esc")



if __name__=="__main__":
    root = tk.Tk()
    Expirment = Handler(root)
    Expirment.mainloop()
    