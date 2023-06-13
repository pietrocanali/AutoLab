# -*- coding: utf-8 -*-
"""
Created on Thu Jun  1 17:35:23 2023

@author: eencsk
Class to manage the Temperature Monitoring Window. 
Developed for the green cryostat but should be adaptable
TODO:(In order of Importance) Write log files
Make Reconnecting to the Controllers POssible if Incorrect adresses supplied
Stability Criteria for Measurements as a Fn of Temperature
Unshow certain elements in the Monitor window (I.e Stage 1 Temperature)
Methods to Read Controller and Populate GUI with current values of, say, Setpoint
Support for Non-Lakeshore 350 Temperature Controllers

"""
import tkinter as tk
from multiprocessing import Process, Queue, Pipe
import Instruments as Inst
from Utility import GraphUtil
from tkinter import ttk
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)
# Implement the default Matplotlib key bindings.
from matplotlib.backend_bases import key_press_handler
from matplotlib.figure import Figure
from matplotlib import ticker
import pyvisa
import time

class Mon_Win:
    """
    Class for the Monitoring window GUI
    """
    Mode_Select=[ "Zone","Open Loop", "Manual PID"]
    SensorInput=["A","B","C","D"]
    TC_Model=["Lakeshore 350"]#Temperature controller Models
    TM_Model=["Lakeshore 218", "Lakeshore 350"]#temperature Monitor models
    Heater_Range=["Off","5/2.5 mW","50/25 mW","500/250 mW","5/2.5 W","50/25 W"]#Delete as appropraite when you know the power
    Temperature_Data=[]#empty list to append data to
    
    def __init__(self, master,parent,default_addresses):
        #assume that the last element of the Default addresses is the temperature monitor
        self.parent=parent
        addresses=self.parent.address_list
        """Set up Temperature Monitoring GUI"""
        self.Window=tk.Toplevel()
        self.Window.title("Temperature Monitoring")
        self.Window.protocol("WM_DELETE_WINDOW",self.close_function)
        
        Control_Frame=tk.Frame(self.Window)#,height = 330,width = 480)
        Control_Frame.grid(column=0, row=1,sticky="E"+"W")
        if len(addresses)==0:
            rm=pyvisa.ResourceManager()
            addresses=rm.list_resources()
            rm.close()
        #if addresses are supplied through the script which calls this util, we dont need to poll all instruments
        #speeds up loading the util
        self.Model=tk.StringVar(Control_Frame,"Lakeshore 350")
        self.ModelEntry=tk.OptionMenu(Control_Frame, self.Model, *self.TC_Model)
        #future-proofing if we want to apply this to, say, HgITCs
        #For now, rely on having the temperature polling being written with the same syntax
        self.ModelEntry.grid(row=0,column=0)
        self.Com=tk.StringVar(Control_Frame,"GPIB Address")
        self.ComEntry=tk.OptionMenu(Control_Frame,self.Com,*addresses)
        self.ComEntry.grid(column=1,row=0)
        
        self.Mode=tk.StringVar(Control_Frame,self.Mode_Select[0])
        self.Mode_Entry=tk.OptionMenu(Control_Frame,self.Mode,*self.Mode_Select)
        self.Mode_Entry.grid(column=3,row=0)
        self.Mode.trace_add("write", self.ChangeMode)
        #when a new mode is selected, automatically update the GUI and send
        #the correct mode to the Controller
        
        self.Range_var=tk.StringVar(Control_Frame,"Heater Range")
        self.range_Entry=tk.OptionMenu(Control_Frame,self.Range_var,*self.Heater_Range)
        self.range_Entry.grid(column=2,row=0)
# =============================================================================
#         HEATER CONTROL WIGETS
# =============================================================================
        self.setpoint_entry=tk.Entry(Control_Frame)
        self.setpoint_entry.insert(tk.END,"Enter Setpoint")
        self.setpoint_entry.grid(column = 0, row =1)
        self.ramp_enable=tk.BooleanVar(Control_Frame)
        self.ramp_button=tk.Checkbutton(Control_Frame,text="Ramp Setpoint?", variable=self.ramp_enable, onvalue=True, offvalue=False)
        self.ramp_button.grid(column=1,row=1)
        self.ramp_entry=tk.Entry(Control_Frame)
        self.ramp_entry.insert(tk.END,"Enter Ramp Rate")
        self.ramp_entry.grid(column=2,row=1)
        
        #Setup Manual Heater Output, Hidden by default
        self.power_Label=tk.Label(Control_Frame,text="Heater Power")
        self.power_Label.grid(column=0,row=1)
        self.power_Label.grid_remove()
        self.power_Entry=tk.Scale(Control_Frame, from_=0, to=100, length=300, orient="horizontal",tickinterval=10)
        self.power_Entry.grid(column=1,row=1,columnspan=3)
        self.power_Entry.grid_remove()

        
        #setup PID entry for Manual PID Hidden by Default
        self.P_entry=tk.Entry(Control_Frame)
        self.P_entry.insert(tk.END,"Enter P")
        self.I_entry=tk.Entry(Control_Frame)
        self.I_entry.insert(tk.END,"Enter I")
        self.D_entry=tk.Entry(Control_Frame)
        self.D_entry.insert(tk.END,"Enter D")
        self.P_entry.grid(column=1, row=1)
        self.I_entry.grid(column=2, row=1)
        self.D_entry.grid(column=3, row=1)
        self.P_entry.grid_remove()
        self.I_entry.grid_remove()
        self.D_entry.grid_remove()       
        
        
        self.setpoint_Button = tk.Button(Control_Frame,
                                         text="Activate",
                                         command= self.set_Setpoint_Zone
                                         )
        self.setpoint_Button.grid(column = 5, row =1)
        #Default is Zone, but the function to switch modes should have a 
        #Method to change the command to the Appropriate mode
        
        self.Off_Button=tk.Button(Control_Frame,
                                         text = "All Off",
                                         command = self.Alloff,
                                         bg = "red",
                                         width=55
                                         )
        self.Off_Button.grid(column = 0, row = 6, columnspan=4,sticky="s")
        
        

        #frame weighting, from https://stackoverflow.com/questions/31844173/tkinter-sticky-not-working-for-some-frames
        # Control_Frame.grid_rowconfigure(0, weight=1)
        # Control_Frame.grid_columnconfigure(0, weight=1)
# =============================================================================
#         MONITORING GRAPH GUI, Stolen from Base Autolab
# =============================================================================
        self.GraphFrame = tk.Frame(self.Window)
        self.GraphFrame.grid(column=0, row=0)#, columnspan=3, rowspan=3)
        self.GraphFrame['borderwidth'] = 10
        self.GraphFrame['relief'] = 'sunken'
        self.GraphFrame['padx'] = 5
        self.GraphFrame['pady'] = 5
        
        self.fig = Figure(figsize=(6,4.62), dpi=100)
        self.fig.set_facecolor("white")
        self.ax = self.fig.add_subplot(111)

        self.Plot1, = self.ax.plot([], [],"#000000",antialiased=False,linewidth=0.5)
       
        
        self.ax.set_facecolor("black")
        self.ax.grid(color="grey")
        self.ax.tick_params(axis='y', colors='#000000')
        #self.ax.yaxis.set_major_formatter(FormatStrFormatter('%.2e'))
        #self.axtwin.yaxis.set_major_formatter(FormatStrFormatter('%.2e'))
        
        formatter = ticker.ScalarFormatter(useMathText=True)
        #formatter.set_powerlimits((-2,2))
        
        self.ax.yaxis.set_major_formatter(formatter)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.GraphFrame)  # A tk.DrawingArea.
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        
        toolbar = NavigationToolbar2Tk(self.canvas, self.GraphFrame)
        toolbar.update()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        
        self.Open_Pipes(default_addresses[0],TMon_Address=(default_addresses[1]))
        
# =============================================================================
#  OPEN/CLOSE FUNCTIONS   
# =============================================================================
    def Open_Pipes(self,TCon_Address,TMon_Address=None):
        """
        Opens the MultiThreading and initialises. 
     
        """
        self.Temp_PipeRecv, self.Temp_PipeSend = Pipe(duplex=True)
        self.Control=Process(target=(Controller),args=(self.Temp_PipeSend,TCon_Address,TMon_Address))
        self.Control.start()
        self.Temp_PipeRecv.send("T; S; 0")#set setpoint to 0 so nothing stupid happens
        self.Temp_PipeRecv.send("HMD; S; Z")#initialise Heater control in Zone mode, to match W. gui.
        #Set Setpoint to 0 has to be there to prevent unintentional application of MAX POWER from Base
        #If the Setpoint was, say, 290K but actual T was 1.5 K.
        self.UpdateWindow()
    
    def close_function(self):
        """
        Funciton to call when the monitoring window is exited.

        """
        print("This will exit the multithreading gracefully")
        self.Temp_PipeRecv.send("STOP")
        self.Window.destroy()
# =============================================================================
# UPDATE WINDOW FUNCTIONS
# =============================================================================
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
            if not self.PipeRecv.poll():
                break
            
            #get data from pipe
            Data = self.PipeRecv.recv()
            
            #If data isn't a string append to rawdata list
            if type(Data)!=str:
                if len(self.Data) <= 10000:#will attempt to gather points every 0.1 s
                    self.Data.append(Data)
                else:
                    del self.Data[0]#remove first point
                    self.Data.append(Data)
            
            # TODO add more key work commands, NewFile, ClearGraph,
            elif Data=="Esc":
                self.MeasureFinished()
                break
            elif Data=="ClearGraph":
                self.Data = []
                continue
    
    
    def UpdateWindow(self):
        """
        This is the general window that updates anything that needs updating.
        Avoid running long process here, must be quick as possible Again, Base Autolab Stuff
        """
        # Get data from the worker by reading the que
        self.Get_Pipe_Data()
        self.UpdateGraph()        
        self.after(250,self.UpdateWindow)
        
    def UpdateGraph(self):
        """
        Take the data from the pipe and plot. Iterate over the list and plot a line for each 
        Dataset available

        """
        try:
            for Dataset in self.Data[-1][1:-2]:#1st Data POint will be the current time, so dont need. Last 2 Elements will be Bools so also dont need
                self.Plot1.plot(self.Data[0],Dataset)
        except Exception as e:
            print(e)
# =============================================================================
# ACT ON CONTROLLER FUNCTIONS        
# =============================================================================
    def set_Setpoint_Zone(self):
        """
        Set the setpoint in Zone Mode and sanitises setpoint and Ramping inputs. Assume that the controller is in Zone
        If ramping is set to true, also activate the Ramping mode.
        """
        
        try:
            ramp_rate=float(self.ramp_entry.get())
            if self.ramp_enable.get()==True and 0.001<=ramp_rate<=100:
                self.Temp_PipeRecv.send("RAMP; S; {}".format(ramp_rate))
            elif self.ramp_enable.get()==True:
                print("Invalid Ramp Rate! Ramp rate not applied!")
                self.Temp_PipeRecv.send("NORAMP")
            else:
                self.Temp_PipeRecv.send("NORAMP")
        except ValueError:
            if self.ramp_enable.get()==True:
                print("Invalid Ramp rate Entered! Ramp Not enabled!")
                self.Temp_PipeRecv.send("NORAMP")
            else:
                self.Temp_PipeRecv.send("NORAMP")#If you've entered the Bee movie script into the Ramp_enable but havent ticked it, I dont care.
        try:
            setpoint=float(self.setpoint_entry.get())
            if setpoint < 300 and setpoint >= 0:
                #make sure temperature is in Kelvin and that temperature is OK for a cryostat
                self.Temp_PipeRecv.send("T; S; {}".format(setpoint))
            else:
                print("Invalid Setpoint given. Has to be in Kelvin and Less than 300 K")
                
        except ValueError:
            print("Invalid Temperature Setpoint given! Has to be able to be cast as a float!")
            
    def set_Setpoint_PID(self):
        """
        Set the Setpoint in Manual PID mode and Stanises inputs for PID.
        Assume that the controller is in Manual Mode
        """
        try:
            P=float(self.P_entry.get())
            I=float(self.I_entry.get())
            D=float(self.D_entry.get())
            if 0.1 <= P <= 1000 and 0.1<= I <= 1000 and 0<= D<= 200:
                self.Temp_PipeRecv.send("PID; S; {0},{1},{2}".format(P,I,D))
            else:
                print("Invalid PID values! P and I have to be less than 1000, and D under 200")
                print("Recived PID of {0},{1},{2}".format(P,I,D))
        except ValueError:
            print("PIDs could not be cast as Float! PIDS unchanged!")
            
        try:
            Range_to_send=self.Heater_Range.index(self.Range_var.get())
            self.Temp_PipeRecv.send("RNG; S; {}".format(Range_to_send))
        except ValueError:
            print("No Range Entered, Range Not changed!")
            
        try:
            setpoint=float(self.setpoint_entry.get())
            if setpoint < 300 and setpoint >= 0:
                #make sure temperature is in Kelvin and that temperature is OK for a cryostat
                self.Temp_PipeRecv.send("T; S; {}".format(setpoint))
            else:
                print("Invalid Setpoint given. Has to be in Kelvin and Less than 300 K")
                
        except ValueError:
            print("Invalid Temperature Setpoint given! Has to be able to be cast as a float!")
            
    def set_Manual_Power(self):
        try:
            Range_to_send=self.Heater_Range.index(self.Range_var.get())
            self.Temp_PipeRecv.send("RNG; S; {}".format(Range_to_send))
        except ValueError:
            print("No Range Entered, Range Not changed!")
        
        try:
            power_to_send=float(self.power_Entry.get())
            self.Temp_PipeRecv.send("PO; S; {}".format(power_to_send))
        except Exception as e:
            print(e)#not quite sure how you fuck this up but just in case
            
    def Alloff(self):
        """
        Turns all the heaters off and sets Setpoint and Manual Output Power to 0. 
        ULTIMATE PANIC BUTTON. MASH FOR SAFE SYSTEM* 
        
        *Doesnt control anyfuckups you've done with the gas flow

        """
        self.Temp_PipeRecv.send("ALLOFF")
        self.Temp_PipeRecv.send("PO; S; 0")
        self.Temp_PipeRecv.send("T; S; 0")
        
    def ChangeMode(self,var,index,mode):
        """
        Code to change the mode in both GUI elements and Applied mode in the Heater controller. 
        SHOULD only activate if the value changes, not if the menu was open so SHOULD be invuln to
        Monkey BS
        Paramters are TK Nonsense. Not used.
        
        """
        NewMode=self.Mode_Select.index(self.Mode.get())
        if NewMode==0:#Zone Mode
            self.P_entry.grid_remove()
            self.I_entry.grid_remove()
            self.D_entry.grid_remove()
            self.power_Entry.grid_remove()
            self.power_Label.grid_remove()#Remove Unecessary GUI Elements
            self.setpoint_entry.grid()
            self.ramp_button.grid()
            self.ramp_entry.grid()#re-show necessary GUI elements.
            self.Temp_PipeRecv.send("HMD; S; Z")
            self.setpoint_Button.configure(command=self.set_Setpoint_Zone)#make sure correct values are being passed
        elif NewMode==1 :#Open Loop Control
            self.P_entry.grid_remove()
            self.I_entry.grid_remove()
            self.D_entry.grid_remove()
            self.ramp_button.grid_remove()
            self.ramp_entry.grid_remove()
            self.setpoint_entry.grid_remove()
            self.power_Entry.grid()
            self.power_Label.grid()
            self.Temp_PipeRecv.send("HMD; S; MO")
            self.setpoint_Button.configure(command=self.set_Manual_Power)
        elif NewMode==2:#Manual PID mode
            self.power_Entry.grid_remove()
            self.power_Label.grid_remove()
            self.ramp_button.grid_remove()
            self.ramp_entry.grid_remove()
            self.setpoint_entry.grid()
            self.P_entry.grid()
            self.I_entry.grid()
            self.D_entry.grid()
            self.Temp_PipeRecv.send("HMD; S; MP")
            self.setpoint_Button.configure(command=self.set_Setpoint_PID)
            
            
        

def Controller(Pipe,TCon_add,Backup_TConAdd, TMon_add=None):
    """
    Multiprocessing Process for Temperature Monitoring
    Last 2 elements in the pipe must always be the IsRamping and IsStable Bools. Make sure to Slice before plotting!
    Currently Assumes that you're doing Loop 1 connected to sensor A
        
    Special Commands that can be sent through the pipe to the Controller:
        ALLOFF=Turns the Heaters on the Controller OFF
        NORAMP, Turns Ramping Off.
        
    Standard Commands have the Syntax;
        Parameter; X; Y
        X is either S(set) or G(get). Y is the Parameter to Be entered. Assumed Sanitary at this pt.
        
    Parameters are
    HMD; Heater Mode, can be be Z (Zone), MP (Manual PID) or MO (Manual Output).
    T; Setpoint in K
    PO; Manual Power output in %
    PID: PID paramters. In this case, the Parameter is a list of len 3 containing P I and D
    RNG: Heater Range
    RAMP: Ramp rate in K/min
        
      

    Parameters
    ----------
    Pipe : Pipe
        PipeSend to pass things through
    TCon_add : VISA address for the temperature Controller
    Backup_TConAdd: The contents of the GPIB entry from the gUI to allow Reconnecting if incorrect 
    Addresses entered.
    WARNING: AT CURRENT MOMENT, NO WAY TO RECONNECT TO TEMPERATURE MONITOR. HAVE TO CLOSE+REOPENT WINDOW
    
    TMon_add : VISA address for a Temperature Monitor.

    """
    rm = pyvisa.ResourceManager()
    
    Abort = False
    IsRamping=False#Bool to tag if temperature is ramping
    IsStable=False#Placeholder for Stability criteria.
    try:
        T_Con = Inst.lakeshore350(rm,TCon_add)
        if TMon_add != None:
            T_Mon=Inst.lakeshore218(rm,TMon_add)
        else:
            T_Mon=None
    except Exception as e:
        print(e)
        isConnected=False
        iterator=0
        while isConnected==False:
            try:
                T_Con = Inst.lakeshore350(rm,Backup_TConAdd)
                isConnected=True
            except Exception:
                iterator+=1
                time.sleep(0.1)
                if iterator == 10000:
                    print("TIMEOUT ON RECONNECT")        
                    Pipe.send("Esc")
            #TODO: Test this
                    return
    
    while Abort == False:
        Comm = Pipe.recv()
        if Comm=="STOP":
            Abort=True
        Current_TCon=T_Con.getTAll()
        if T_Mon != None:
            Current_TMon=T_Mon.getTAll()
        else:
            Current_TMon=[]
        Pipe.send([time.time(),*Current_TCon,*Current_TMon,IsRamping,IsStable])#sends the current reading of the pipes to be read
        time.sleep(0.1)
# =============================================================================
#         PIPE NOW CHECKS FOR INPUT
# =============================================================================
        if Comm =="ALLOFF":
            T_Con.allOff()
        elif Comm == "NORAMP":
            T_Con.setRampRate(1,0,0)
# =============================================================================
#        PIPE NOW CHECKS FOR GET COMMANDS
# =============================================================================
        else:
            Param=str(Comm).split(";")#TODO: Check that this works when no comms
            if len(Param) ==2:#I'M VIOLATING MY OWN GUIDELINES AND YOU CANT STOP ME!!!
            #In Essence, as the "Read" Command wont send a setpoint, we can take Param of Len 2 to always be a "Get" command
            #Yes this does allow you to Send "T; Red Dragon Archfiend" as a valid get command but SHHH. 
                if Param[0]=="HMD":
                    mode=T_Con.getOutputMode(1)[0]
                    if mode==3:
                        mode="M0"
                    elif mode==2:
                        mode="Z"
                    elif mode==1:
                        mode="MP"
                    Pipe.send(mode)
                elif Param[0]=="T":
                    Pipe.send(T_Con.getTempSetpointN(1))
                elif Param[0]=="PO":
                    Pipe.send(T_Con.readMout(1))
                elif Param[0]=="PID":
                    Pipe.send([T_Con.getPID(1)])
                elif Param[0]=="RNG":
                    Pipe.send(T_Con.getRange(1))
                elif Param[0]=="RAMP":
                    Pipe.send(T_Con.getRampRate(1))
                else:
                    print("Invalid Get Command")
# =============================================================================
#             PIPE NOW CHECKS FOR SET COMMANDS
# =============================================================================
            elif len(Param)==3:
                #again, assuming a command with 3 things would be a Set command
                if Param[0]=="HMD":
                    if Param[2]=="M0":
                        T_Con.setOutputMode(1,3)
                    elif Param[2]=="Z":
                        T_Con.setOutputMode(1,2)
                    elif Param[2]=="MP":
                        T_Con.setOutputMode(1,1)
                    
                elif Param[0]=="T":
                    T_Con.setTempSetpointN(1,float(Param[2]))
                elif Param[0]=="PO":
                    T_Con.ManOut(1,float(Param[2]))
                    Pipe.send(T_Con.readMout(1))
                elif Param[0]=="PID":
                    list_PID=Param[2].split(",")
                    #break up PID into a Len3 list. This is why you split by semicolon in the first case
                    T_Con.setPID(1,float(list_PID[0]),float(list_PID[1]),float(list_PID[2]))
                elif Param[0]=="RNG":
                    T_Con.setRange(1,int(Param[2]))
                elif Param[0]=="RAMP":
                    T_Con.setRampRate(1,1,float(Param[2]))
                else:
                    print("Invalid Set Command")
# =============================================================================
#             ERROR/DO NOTHING CASE
# =============================================================================
            else:
                pass#should handle the Len1 case of nothing
                print(len(Param))#debugging code fragment to delete
            