# -*- coding: utf-8 -*-
"""
Created on Sat Jan 25 14:03:48 2020

@author: omedeiro

Functions created for the design of SNSPD 

import qnngds.omedeiro as om 

"""
from __future__ import division, print_function, absolute_import
import numpy as np
from phidl import Device
import phidl.geometry as pg
import phidl.routing as pr
from phidl import quickplot as qp
# import colang as mc
import string
from datetime import datetime
import os
import sys
from time import sleep
from phidl.device_layout import _parse_layer, DeviceReference

from argparse import Namespace    



sys.path.append(r'Q:\qnnpy')
import qnnpy.functions.functions as qf
import qnngds.utilities as qu
import qnngds.geometry as qg


    
def outline_invert(device, polygon=None):
    """
    This function takes a outlined device (for positive tone resist and etch
    process) and inverts the device. 
    
    Works with mc.meander

    Parameters
    ----------
    device : DEVICE
        PHIDL device object.
    polygon : INT, optional
        After the boolean operation there are typically three polygons the 
        snspd and two trimmed pieces. Somtimes there is a problem with 
        returning the correct one. 
        This parameter can be used to change the selection. The default is None.

    Returns
    -------
    I : DEVICE
        PHIDL device object.

    """
    device.move(origin=device.bbox[0],destination=(0,0))
    sw = device.bbox[0]
    ne = device.bbox[1]
    
    box = pg.rectangle(size=(ne[0]-sw[0],ne[1]-sw[1]))
    box.move(origin=box.bbox[0], destination=sw)
    
    inverse = pg.boolean(device,box,'B-A', layer=1, precision=1e-7)
    I = Device('inversepoly')
    if polygon:
        for poly in polygon:
            I.add_polygon(inverse.polygons[poly])
    else:
        I.add_polygon(inverse.polygons[1])

    I.move(origin = I.bbox[0], destination=(0,0))

    return I


def create_device_doc(D_pack_list):
    """
    Creates text file containing the parameters related to the device IDs.
    Automatically saved in the corrspoinding sample folder. 
    
    Only parameters that TYPE: np.array are shown in the table. 
    The entire parameter dictionary is saved with the save_gds
    
    Sample name is entered as an imput. This ensures that the file is saved 
    in the correct location.
    
    Parameters
    ----------
    D_pack : LIST 
        list of lists containing phidl device objects with parameters and names attached. 
        


    Returns
    -------
    None.

    """
    
    sample = input('enter a sample name: ')
    
    if sample=='':
        print('Device document not created')
        return
    
    path = os.path.join('S:\SC\Measurements',sample)
    os.makedirs(path, exist_ok=True)
    
    path = os.path.join('S:\SC\Measurements',sample, sample+'_device_doc.txt')
    
    file = open(path, "w")


    tab = '\t'    
    txt_spacing = 20 #there is probably a better method 
    """ Loop through list of sublists """
    for i in range(len(D_pack_list)):
        headers = []   #new headers because each sublist could be a different device. 
        string_list=[]
        
        headers.append('ID'+' '*(txt_spacing-2))
        headers.append('TYPE'+' '*(txt_spacing-4))
        
        """ Loop through references in sublist"""
        for j in range(len(D_pack_list[i].references)):
            line=[]
            name = D_pack_list[i].references[j].parent.name
            line.append(name+ (txt_spacing-len(name))*' ') #append device name
            typE = D_pack_list[i].references[j].parent.type
            line.append(typE+ (txt_spacing-len(typE))*' ') #append device type

            #All references in in D_pack_list will have identical parameters. Hence references[0]
            for key in D_pack_list[i].references[0].parent.parameters: 
                
                # Only save parameters in DOC that are changing. 
                # If the parameter is an array then the array will be the length of the array will be the same as the references length.
                if type(D_pack_list[i].references[0].parent.parameters[key]) == np.ndarray:
                    if j == 0: #If it is the first of the loop append name of columns
                        headers.append(key+(txt_spacing-len(key))*' ')
                    text = str(D_pack_list[i].references[0].parent.parameters[key][j].round(4))
                    line.append(text + (txt_spacing-len(text))*' ')

            line.append('\n')
            string_list.append('.'*len(tab.join(line))+' \n')
            string_list.append(tab.join(line))
            # string_list.append('.'*len(tab.join(line))+' \n')
        string_list.append('\\'+'-'*(len(tab.join(line)))+'\\ \n')
    
        headers.append('\n')
        file.write('\\'+'-'*(len(tab.join(line)))+'\\ \n')
        file.write(tab.join(headers))
        file.writelines(string_list)
    file.close()
    
 
    
def squares_meander_calc(width, area, pitch):
    """
    CALCULATE THE NUMBER OF SQUARES OF A SQUARE SNSPD MEANDER.
    
    Parameters
    ----------
    width : FLOAT
        SNSPD WIDTH.
    area : FLOAT
        SNSPD AREA. ASSUMING A SQUARE DETECTOR
    pitch : FLOAT
        SNSPD PITCH.
        

    Returns
    -------
    squares : FLOAT
        ROUGH CALCULATION OF THE NUMBER OF SQUARES OF A SQUARE SNSPD MEANDER.

    """
    
    number_of_lines = area / (width + pitch)
    squares_per_line = area/width
    
    squares = squares_per_line*number_of_lines
    return round(squares)


def reset_time_calc(width=1, area=10, pitch=2, Ls=80, RL = 50, squares = None):
    """
    CALCULATE SNSPD RESET TIME BASED ON GEOMETRY AND INDUCTANCE. 
    
    Parameters
    ----------
    width : FLOAT
        SNSPD WIDTH.
    area : FLOAT
        SNSPD AREA.
    pitch : FLOAT
        SNSPD PITCH.
    Ls : FLOAT
        SHEET INDUCTANCE.
    RL : FLOAT, optional
        LOAD RESISTANCE. The default is 50.
    squares : FLOAT, optional
        Predetermined number of squares. Input instead of geometry. 

    Returns
    -------
    reset_time : FLOAT
        SNSPD RESET TIME IN (ns).

    """
    if squares != None:
        sq = squares
    else:
        sq = squares_meander_calc(width, area, pitch)
    
    Lk = Ls*sq*1e-3 #Kinetic inductance in nH
    
    reset_time = 3*(Lk/RL)
    print('Squares %0.f, Reset time(ns) %0.f' %(sq,reset_time))
    return reset_time

    
 

def meander(width=0.1, pitch=0.250, area=8, length=None, number_of_paths=1, layer=1, terminals_same_side=False):
    """
    

    Parameters
    ----------
    width : FLOAT, optional
        SNSPD wire width. The default is 0.1.
    pitch : FLOAT, optional
        SNSPD wire pitch. The default is 0.250.
    area : FLOAT, optional
        SNSPD overall Y dimension, and or snspd area if Length is not specified. The default is 8.
    length : FLOAT, optional
        SNSPD overall X dimension. The default is None.
    number_of_paths : INT, optional
        Number of times the SNSPD traverses over the Y dimension. This value is limited by the length of the SNSPD The default is 1.

    Returns
    -------
    X : Device
        PHIDL device object is returned.

    """
    D=Device('x')
    X=Device('big')
    
    n=number_of_paths
    if length==None:
        length = area/number_of_paths
    else:
        length = (length-0.5*(number_of_paths-1))/number_of_paths
        
        
    S=pg.snspd(wire_width = width, wire_pitch = pitch+width, size = (length,area), terminals_same_side = terminals_same_side)
    
    if n==1:
        S=pg.snspd(wire_width = width, wire_pitch = pitch+width, size = (length,area), terminals_same_side = terminals_same_side)
        s=D.add_ref(S)
    
    i=0    
    while i < n:
        s=D.add_ref(S)
        if i==0:
            start=s.ports[1].midpoint
        if np.mod(i,2)!=0:
            s.mirror((0,1),(1,1))
        if i>0:
            s.move(origin=s.ports[1], destination=straight.ports[2])
        if i != n-1:
            straight=D.add_ref(pg.straight(size=(width,0.5),  layer = 0))
            straight.rotate(90)
            straight.move(straight.ports[1], s.ports[2])
        if i == n-1:
            end=s.ports[2].midpoint
        i=i+1
    D.flatten(single_layer=layer)    
    X=pg.deepcopy(D)
    X.add_port(name=1, midpoint = start, width=width, orientation=180)
    X.add_port(name=2, midpoint = end, width=width, orientation=0)
    X.move(origin=X.ports[1], destination=(0,0))
    return X



def snspd_pad_bilayer(parameters=None, sheet_inductance = 300):
    """

    """
    ''' Default parameters for example testing '''
    if parameters == None: 
        parameters = {
                'pad_outline': 7,
                'pad_taper_length': 40,
                'snspd_outline': .2,
                'snspd_width': np.array([1]),
                'snspd_fill': 0.50,
                'snspd_area': np.array([30]),
                'ground_taper_length': 10,
                'pad_width': 200,
                'ground_taper_width': 50,
                'snspd_layer': 1,
                'pad_layer': 2
                }
    
    """ Get length of parameters """ 
    for key in parameters:
            if type(parameters[key]) == np.ndarray:
                parameter_length = len(parameters[key])
                break
            else:
                parameter_length = 0
    
    # """ Convert dictionary keys to local variables """
    # globals().update(parameters) #I love this, but, every variable appears to be undefined. 
    
    """ Convert dictionary keys to namespace """
    n = Namespace(**parameters) #This method of converting dictionary removes "Undefined name" warning
    
    
    """ Generate list of devices from parameters 
        Additionally, this loop will calculate the number of squares of each device. 
    """
    device_list = []
    device_squares_list = []
    for i in range(parameter_length):
        D = Device('snspd')    
        detector = meander(width = n.snspd_width[i],
                              pitch = n.snspd_width[i]/n.snspd_fill-n.snspd_width[i],
                              area = n.snspd_area[i],
                              layer = n.snspd_layer,
                              )
        detector = qg.outline(detector,distance=n.snspd_outline,open_ports=2)
        pad = qg.pad_U(pad_width= n.pad_width, layer=n.pad_layer)
        pad.rotate(180)
        
        inductor_squares = squares_meander_calc(n.snspd_width[i], n.snspd_area[i], n.snspd_width[i]/n.snspd_fill-n.snspd_width[i])
        device_squares = inductor_squares
        reset_time = reset_time_calc(squares = device_squares, Ls=sheet_inductance)

        device_squares_list.append(device_squares)
        
        pad_taper = qg.outline(qg.hyper_taper(40, n.pad_width+n.pad_outline,n.snspd_width[i],n.snspd_layer), distance=n.snspd_outline,open_ports=2)
        pad_taper.move(pad_taper.ports['wide'], pad.ports[1]).movex(10)
        detector.move(origin=detector.ports[2],destination=pad_taper.ports['narrow'])

        
        ground_taper = qg.outline(qg.hyper_taper(n.ground_taper_length,n.ground_taper_width, n.snspd_width[i],n.snspd_layer),distance=n.snspd_outline, open_ports=2)
        ground_taper.rotate(180)
        ground_taper.move(origin=ground_taper.ports['narrow'],destination=detector.ports[1])
                


        D.add_ref([pad_taper,detector, ground_taper])
        D.flatten(single_layer=n.snspd_layer)
        D.add_ref(pad)
        D.rotate(-90)
        D.move(D.bbox[0],destination=(0,0))

        qp(D)
        # """ Attach dynamical parameters to device object. """
        D.width = n.snspd_width[i]
        D.area = n.snspd_area[i]
        D.squares = device_squares
        D.parameters = parameters
        D.type = 'meander_snspd'
        device_list.append(D)
        
    # """ Attach squares calculation to parameters """
    parameters['snspd_squares']=np.array(device_squares_list)
    return device_list

snspd_pad_bilayer()

def snspd_2pad_bilayer(parameters=None, sheet_inductance = 80):
    """

    """
    ''' Default parameters for example testing '''
    if parameters == None: 
        parameters = {
                'pad_outline': 7,
                'pad_taper_length': 60,
                'snspd_outline': .2,
                'snspd_width': np.array([1]),
                'snspd_fill': 0.50,
                'snspd_area': np.array([30]),
                'pad_width': 200,
                'snspd_layer': 1,
                'pad_layer': 2
                }
    
    """ Get length of parameters """ 
    for key in parameters:
            if type(parameters[key]) == np.ndarray:
                parameter_length = len(parameters[key])
                break
            else:
                parameter_length = 0
    
    # """ Convert dictionary keys to local variables """
    # globals().update(parameters) #I love this, but, every variable appears to be undefined. 
    
    """ Convert dictionary keys to namespace """
    n = Namespace(**parameters) #This method of converting dictionary removes "Undefined name" warning
    
    
    """ Generate list of devices from parameters 
        Additionally, this loop will calculate the number of squares of each device. 
    """
    device_list = []
    device_squares_list = []
    for i in range(parameter_length):
        D = Device('snspd')    
        detector = meander(width = n.snspd_width[i],
                              pitch = n.snspd_width[i]/n.snspd_fill-n.snspd_width[i],
                              area = n.snspd_area[i],
                              layer = n.snspd_layer,
                              )
        detector = qg.outline(detector,distance=n.snspd_outline,open_ports=2)
        pad = qg.pad_U(pad_width= n.pad_width, layer=n.pad_layer)
        pad.rotate(180)
        
        inductor_squares = squares_meander_calc(n.snspd_width[i], n.snspd_area[i], n.snspd_width[i]/n.snspd_fill-n.snspd_width[i])
        device_squares = inductor_squares
        reset_time = reset_time_calc(squares = device_squares, Ls=sheet_inductance)

        device_squares_list.append(device_squares)
        
        pad_taper = qg.outline(qg.hyper_taper(n.pad_taper_length, n.pad_width+n.pad_outline,n.snspd_width[i],n.snspd_layer), distance=n.snspd_outline,open_ports=2)
        pad_taper.move(pad_taper.ports['wide'], pad.ports[1]).movex(10)
        detector.move(origin=detector.ports[2],destination=pad_taper.ports['narrow'])

        
        pad_taper2 = qg.outline(qg.hyper_taper(n.pad_taper_length, n.pad_width+n.pad_outline,n.snspd_width[i],n.snspd_layer), distance=n.snspd_outline,open_ports=2)
        pad_taper2.rotate(180)
        pad_taper2.move(origin=pad_taper2.ports['narrow'],destination=detector.ports[1])
                
        pad2 = qg.pad_U(pad_width= n.pad_width, layer=n.pad_layer)
        pad2.move(pad2.ports[1],pad_taper2.ports['wide']).movex(10)
    
        D.add_ref([pad_taper,detector, pad_taper2])
        D.flatten(single_layer=n.snspd_layer)
        D.add_ref([pad, pad2])
        D.rotate(-90)
        D.move(D.bbox[0],destination=(0,0))

        # """ Attach dynamical parameters to device object. """
        D.width = n.snspd_width[i]
        D.area = n.snspd_area[i]
        D.squares = device_squares
        D.parameters = parameters
        D.type = 'meander_snspd_diff'
        device_list.append(D)
        
    # """ Attach squares calculation to parameters """
    parameters['snspd_squares']=np.array(device_squares_list)
    return device_list



def straight_snspd_pad_bilayer(parameters=None, sheet_inductance = 300):
    """

    """
    ''' Default parameters for example testing '''
    if parameters == None: 
        parameters = {
                'pad_outline': 7,
                'pad_taper_length': 40,
                'snspd_outline': .2,
                'snspd_width': np.array([1]),
                'snspd_fill': 0.50,
                'snspd_area': np.array([30]),
                'ground_taper_length': 40,
                'pad_width': 200,
                'ground_taper_width': 150,
                'snspd_layer': 1,
                'pad_layer': 2,
                'straight_width':np.array([.1]),
                'straight_length':np.array([50])
                }
    
    """ Get length of parameters """ 
    for key in parameters:
            if type(parameters[key]) == np.ndarray:
                parameter_length = len(parameters[key])
                break
            else:
                parameter_length = 0
    
    # """ Convert dictionary keys to local variables """
    # globals().update(parameters) #I love this, but, every variable appears to be undefined. 
    
    """ Convert dictionary keys to namespace """
    n = Namespace(**parameters) #This method of converting dictionary removes "Undefined name" warning
    
    
    """ Generate list of devices from parameters 
        Additionally, this loop will calculate the number of squares of each device. 
    """
    device_list = []
    device_squares_list = []
    for i in range(parameter_length):
        D = Device('snspd')    
        detector = meander(width = n.snspd_width[i],
                              pitch = n.snspd_width[i]/n.snspd_fill-n.snspd_width[i],
                              area = n.snspd_area[i],
                              layer = n.snspd_layer,
                              )
        detector = qg.outline(detector,distance=n.snspd_outline,open_ports=2)
        pad = qg.pad_U(pad_width= n.pad_width, layer=n.pad_layer)
        pad.rotate(180)
        inductor_squares = squares_meander_calc(n.snspd_width[i], n.snspd_area[i], n.snspd_width[i]/n.snspd_fill-n.snspd_width[i])
        straight_squares = n.straight_length[i]/n.straight_width[i]
        device_squares = inductor_squares + straight_squares
        reset_time = reset_time_calc(squares = device_squares, Ls=sheet_inductance)
        print('- straight squares:%0.f - inductor_squares:%0.f' %(straight_squares, inductor_squares))
        device_squares_list.append(device_squares)
        
        pad_taper = qg.outline(qg.hyper_taper(40, n.pad_width+n.pad_outline,n.snspd_width[i],n.snspd_layer), distance=n.snspd_outline,open_ports=2)
        pad_taper.move(pad_taper.ports['wide'], pad.ports[1]).movex(10)
        detector.move(origin=detector.ports[2],destination=pad_taper.ports['narrow'])
        
        bend1 = qg.outline(pg.optimal_90deg(n.snspd_width[i]), distance=n.snspd_outline, open_ports=2)
        bend1.rotate(-90)
        bend1.move(bend1.ports[1],detector.ports[1])
        
        step1 = qg.outline(pg.optimal_step(n.straight_width[i],n.snspd_width[i], num_pts=100),distance=n.snspd_outline, open_ports=3)
        step1.rotate(90)
        step1.move(step1.ports[2],bend1.ports[2])
        
        STRAIGHT = qg.outline(pg.straight((n.straight_width[i],n.straight_length[i])),distance=n.snspd_outline, open_ports=2)
        STRAIGHT.move(STRAIGHT.ports[1], step1.ports[1])
                
        step2 = qg.outline(pg.optimal_step(n.snspd_width[i],n.straight_width[i], num_pts=100),distance=n.snspd_outline, open_ports=3)
        step2.rotate(90)
        step2.move(step2.ports[2],STRAIGHT.ports[2])
        
        bend2 = qg.outline(pg.optimal_90deg(n.snspd_width[i]), distance=n.snspd_outline, open_ports=3)
        bend2.rotate(90)
        bend2.move(bend2.ports[2],step2.ports[1])

        
        ground_taper = qg.outline(qg.hyper_taper(n.ground_taper_length,n.ground_taper_width, n.snspd_width[i],n.snspd_layer),distance=n.snspd_outline, open_ports=2)
        ground_taper.rotate(180)
        ground_taper.move(origin=ground_taper.ports['narrow'],destination=bend2.ports[1])
        

        D.add_ref([pad_taper,detector,bend1, step1, STRAIGHT, step2, bend2, ground_taper])#,bend1,STRAIGHT, bend2, ground_taper])
        D.flatten(single_layer=n.snspd_layer)
        D.add_ref(pad)
        D.rotate(-90)
        D.move(D.bbox[0],destination=(0,0))

        # """ Attach dynamical parameters to device object. """
        D.width = n.snspd_width[i]
        D.area = n.snspd_area[i]
        D.squares = device_squares
        D.parameters = parameters
        D.type = 'straight_snspd'

        device_list.append(D)
        
    # """ Attach squares calculation to parameters """
    # parameters['snspd_squares']=np.array(device_squares_list)
    return device_list

def straight_snspd_2pad_bilayer(parameters=None, sheet_inductance = 300):
    """

    """
    ''' Default parameters for example testing '''
    if parameters == None: 
        parameters = {
                'pad_outline': 7,
                'pad_taper_length': 40,
                'snspd_outline': .2,
                'snspd_width': np.array([1]),
                'snspd_fill': 0.50,
                'snspd_area': np.array([30]),
                'pad_width': 200,
                'snspd_layer': 1,
                'pad_layer': 2,
                'straight_width':np.array([.1]),
                'straight_length':np.array([50])
                }
    
    """ Get length of parameters """ 
    for key in parameters:
            if type(parameters[key]) == np.ndarray:
                parameter_length = len(parameters[key])
                break
            else:
                parameter_length = 0
    
    # """ Convert dictionary keys to local variables """
    # globals().update(parameters) #I love this, but, every variable appears to be undefined. 
    
    """ Convert dictionary keys to namespace """
    n = Namespace(**parameters) #This method of converting dictionary removes "Undefined name" warning
    
    
    """ Generate list of devices from parameters 
        Additionally, this loop will calculate the number of squares of each device. 
    """
    device_list = []
    device_squares_list = []
    for i in range(parameter_length):
        D = Device('snspd')    
        detector = meander(width = n.snspd_width[i],
                              pitch = n.snspd_width[i]/n.snspd_fill-n.snspd_width[i],
                              area = n.snspd_area[i],
                              layer = n.snspd_layer,
                              )
        detector = qg.outline(detector,distance=n.snspd_outline,open_ports=2)
        pad = qg.pad_U(pad_width= n.pad_width, layer=n.pad_layer)
        pad.rotate(180)
        inductor_squares = squares_meander_calc(n.snspd_width[i], n.snspd_area[i], n.snspd_width[i]/n.snspd_fill-n.snspd_width[i])
        straight_squares = n.straight_length[i]/n.straight_width[i]
        device_squares = inductor_squares + straight_squares
        reset_time = reset_time_calc(squares = device_squares, Ls=sheet_inductance)
        print('- straight squares:%0.f - inductor_squares:%0.f' %(straight_squares, inductor_squares))
        device_squares_list.append(device_squares)
        
        pad_taper = qg.outline(qg.hyper_taper(40, n.pad_width+n.pad_outline,n.snspd_width[i],n.snspd_layer), distance=n.snspd_outline,open_ports=2)
        pad_taper.move(pad_taper.ports['wide'], pad.ports[1]).movex(10)
        detector.move(origin=detector.ports[2],destination=pad_taper.ports['narrow'])
        
        bend1 = qg.outline(pg.optimal_90deg(n.snspd_width[i]), distance=n.snspd_outline, open_ports=2)
        bend1.rotate(-90)
        bend1.move(bend1.ports[1],detector.ports[1])
        
        step1 = qg.outline(pg.optimal_step(n.straight_width[i],n.snspd_width[i], num_pts=100),distance=n.snspd_outline, open_ports=3)
        step1.rotate(90)
        step1.move(step1.ports[2],bend1.ports[2])
        
        STRAIGHT = qg.outline(pg.straight((n.straight_width[i],n.straight_length[i])),distance=n.snspd_outline, open_ports=2)
        STRAIGHT.move(STRAIGHT.ports[1], step1.ports[1])
                
        step2 = qg.outline(pg.optimal_step(n.snspd_width[i],n.straight_width[i], num_pts=100),distance=n.snspd_outline, open_ports=3)
        step2.rotate(90)
        step2.move(step2.ports[2],STRAIGHT.ports[2])
        
        bend2 = qg.outline(pg.optimal_90deg(n.snspd_width[i]), distance=n.snspd_outline, open_ports=3)
        bend2.rotate(90)
        bend2.move(bend2.ports[2],step2.ports[1])

        
        pad_taper2 = qg.outline(qg.hyper_taper(40, n.pad_width+n.pad_outline,n.snspd_width[i],n.snspd_layer), distance=n.snspd_outline,open_ports=2)
        pad_taper2.rotate(180)
        pad_taper2.move(origin=pad_taper2.ports['narrow'],destination=bend2.ports[1])
        
        pad2 = qg.pad_U(pad_width= n.pad_width, layer=n.pad_layer)
        pad2.move(origin=pad2.ports[1],destination=pad_taper2.ports['wide']).movex(10)
        
        D.add_ref([pad_taper,detector,bend1, step1, STRAIGHT, step2, bend2, pad_taper2])#,bend1,STRAIGHT, bend2, ground_taper])
        D.flatten(single_layer=n.snspd_layer)
        D.add_ref([pad,pad2])
        D.rotate(-90)
        D.move(D.bbox[0],destination=(0,0))

        qp(D)
        # """ Attach dynamical parameters to device object. """
        D.width = n.snspd_width[i]
        D.area = n.snspd_area[i]
        D.squares = device_squares
        D.parameters = parameters
        D.type = 'straight_snspd_diff'

        device_list.append(D)
        
    # """ Attach squares calculation to parameters """
    parameters['snspd_squares']=np.array(device_squares_list)
    return device_list


def straight_wire_pad_bilayer(parameters=None, sheet_inductance = 300):
    """

    """
    ''' Default parameters for example testing '''
    if parameters == None: 
        parameters = {
                'pad_width': 200,
                'pad_outline': 7,
                'pad_taper_length': 40,
                'ground_taper_length': 10,
                'ground_taper_width': 20,
                'straight_outline': 0.2,
                'straight_width':np.array([.1]),
                'straight_length':np.array([40]),
                'straight_layer': 1,
                'pad_layer': 2
                }
    
    """ Get length of parameters """ 
    for key in parameters:
            if type(parameters[key]) == np.ndarray:
                parameter_length = len(parameters[key])
                break
            else:
                parameter_length = 0
    
    # """ Convert dictionary keys to local variables """
    # globals().update(parameters) #I love this, but, every variable appears to be undefined. 
    
    """ Convert dictionary keys to namespace """
    n = Namespace(**parameters) #This method of converting dictionary removes "Undefined name" warning
    
    
    """ Generate list of devices from parameters 
        Additionally, this loop will calculate the number of squares of each device. 
    """
    device_list = []
    device_squares_list = []
    step_scale = 4
    for i in range(parameter_length):
        D = Device('wire')    

        straight_squares = n.straight_length[i]/n.straight_width[i]
        reset_time = reset_time_calc(squares = straight_squares, Ls=sheet_inductance)
        device_squares_list.append(straight_squares)
        
        
        
        ######################################################################

        detector = qg.outline(pg.straight((n.straight_width[i],n.straight_length[i])),distance=n.straight_outline, open_ports=2)
        
        pad = qg.pad_U(pad_width= n.pad_width, layer=n.pad_layer)
        pad.rotate(180)

        pad_taper = qg.outline(qg.hyper_taper(40, n.pad_width+n.pad_outline,n.straight_width[i]*step_scale),distance=n.straight_outline, open_ports=2)
        pad_taper.move(pad_taper.ports['wide'], pad.ports[1]).movex(10)
        
        step1 = qg.outline(pg.optimal_step(n.straight_width[i]*step_scale,n.straight_width[i]),distance=n.straight_outline, open_ports=3)
        step1.rotate(180)
        step1.move(step1.ports[1],pad_taper.ports['narrow'])
        
        detector.rotate(90)
        detector.move(origin=detector.ports[2],destination=step1.ports[2])
        
        step2 = qg.outline(pg.optimal_step(n.straight_width[i]*step_scale,n.straight_width[i]),distance=n.straight_outline, open_ports=3)
        step2.move(step2.ports[2],detector.ports[1])
             
        ground_taper = qg.outline(qg.hyper_taper(n.ground_taper_length, n.ground_taper_width, n.straight_width[i]*step_scale), distance= n.straight_outline, open_ports=2)
        ground_taper.rotate(180)
        ground_taper.move(ground_taper.ports['narrow'],step2.ports[1])

        D.add_ref([pad_taper,detector, step1, step2, ground_taper])
        D.flatten(single_layer=n.straight_layer)
        D.add_ref(pad)
        D.rotate(-90)
        D.move(D.bbox[0],destination=(0,0))
        
        
        # """ Attach dynamical parameters to device object. """
        D.width = n.straight_width[i]
        D.squares = straight_squares
        D.parameters = parameters
        D.type = 'straight_wire'

        device_list.append(D)
        
    # """ Attach squares calculation to parameters """
    parameters['snspd_squares']=np.array(device_squares_list)
    return device_list

def resistor_pad_bilayer(parameters=None, sheet_resistance=1):
    """

    """
    ''' Default parameters for example testing '''
    if parameters == None: 
        parameters = {
                'pad_width': 200,
                'pad_outline': 7,
                'pad_taper_length': 40,
                'ground_taper_length': 20,
                'ground_taper_width': 100,
                'straight_width':3,
                'straight_outline': 0.2,
                'r_width':np.array([1]),
                'r_length':np.array([6]),
                'r_over': 2,
                'straight_layer': 1,
                'pad_layer': 2,
                'r_layer':3
                }
    
    """ Get length of parameters """ 
    for key in parameters:
            if type(parameters[key]) == np.ndarray:
                parameter_length = len(parameters[key])
                break
            else:
                parameter_length = 0

    """ Convert dictionary keys to namespace """
    n = Namespace(**parameters) #This method of converting dictionary removes "Undefined name" warning
    
    
    """ Generate list of devices from parameters 
        Additionally, this loop will calculate the number of squares of each device. 
    """
    device_list = []
    device_squares_list = []
    step_scale = 4
    for i in range(parameter_length):
        D = Device('wire')    

        straight_squares = n.r_length[i]/n.r_width[i]
        # reset_time = reset_time_calc(squares = straight_squares, Ls=sheet_inductance)
        device_squares_list.append(straight_squares)
        
        
        
        ######################################################################

        r = qg.resistor_pos(size=(n.r_width[i],n.r_length[i]), 
                         width=n.straight_width, 
                         length=n.r_length[i], 
                         overhang=n.r_over, 
                         pos_outline=n.straight_outline, layer=n.straight_layer, rlayer=n.r_layer)
        
        step1 = qg.outline(pg.optimal_step(n.straight_width*step_scale,n.straight_width, symmetric=True),distance=n.straight_outline,layer=n.straight_layer, open_ports=n.straight_outline)
        step1.rotate(-90)
        step1.move(step1.ports[2],r.ports[1])
        
        step2 = qg.outline(pg.optimal_step(n.straight_width*step_scale,n.straight_width, symmetric=True),distance=n.straight_outline,layer=n.straight_layer, open_ports=n.straight_outline)
        step2.rotate(90)
        step2.move(step2.ports[2],r.ports[2])
        
        pad_taper = qg.outline(qg.hyper_taper(40, n.pad_width+n.pad_outline,n.straight_width*step_scale),distance=n.straight_outline,layer=n.straight_layer, open_ports=n.straight_outline)
        pad_taper.rotate(-90)
        pad_taper.move(pad_taper.ports['narrow'], step2.ports[1])
        
        pad = qg.pad_U(pad_width= n.pad_width, layer=n.pad_layer)
        pad.rotate(90)
        pad.move(pad.ports[1], pad_taper.ports['wide']).movey(10)
        
        ground_taper = qg.outline(qg.hyper_taper(n.ground_taper_length, n.ground_taper_width, n.straight_width*step_scale), distance= n.straight_outline, open_ports=2)
        ground_taper.rotate(90)
        ground_taper.move(ground_taper.ports['narrow'],step1.ports[1])



        D.add_ref([r, step1, step2, pad_taper, pad, ground_taper])
        D.flatten()
        D.move(D.bbox[0],destination=(0,0))
        
        
        # # """ Attach dynamical parameters to device object. """
        D.squares = (n.r_length[i]-n.r_over)/n.r_width[i]
        print("Squares="+str(D.squares)+" Resistance="+str(D.squares*sheet_resistance))
        D.parameters = parameters
        D.type = 'resistor'

        device_list.append(D)
    # """ Attach squares calculation to parameters """
    parameters['snspd_squares']=np.array(device_squares_list)
    return device_list




def four_point_wire(parameters=None):
    
    ''' Default parameters for example testing '''
    if parameters == None: 
        parameters = {
                'pad_width': 200,   
                'pad_outline': 10,
                'pad_taper_length': 40,
                'ground_taper_length': 10,
                'ground_taper_width': 20,
                'straight_outline': 0.2,
                'straight_width':np.array([.2]),
                'straight_length':np.array([40]),
                'straight_layer': 1,
                'pad_layer': 2
                }
    
    """ Get length of parameters """ 
    for key in parameters:
            if type(parameters[key]) == np.ndarray:
                parameter_length = len(parameters[key])
                break
            else:
                parameter_length = 0
    
    """ Convert dictionary keys to namespace """
    n = Namespace(**parameters) #This method of converting dictionary removes "Undefined name" warning
    
    
    """ Generate list of devices from parameters 
        Additionally, this loop will calculate the number of squares of each device. 
    """
    device_list = []
    device_squares_list = []
    step_scale = 10
    for i in range(parameter_length):
        D = Device('four_point')    
        E = Device('wire')

        straight_squares = n.straight_length[i]/n.straight_width[i]
        # reset_time = reset_time_calc(squares = straight_squares, Ls=sheet_inductance)
        device_squares_list.append(straight_squares)
        
        
        
        ######################################################################
        step_scale=10
        
        for z in range(4): 
            pad = qg.pad_U(pad_width= n.pad_width, width=n.pad_outline, layer=n.pad_layer, port_yshift=-10, port_width_add=n.pad_outline/2)
            pad.rotate(90)
            pad.move(pad.bbox[0], (n.pad_width*z*1.2,0))
            pad_taper = qg.outline(qg.hyper_taper(40, n.pad_width+n.pad_outline,n.straight_width[i]*step_scale, layer=n.straight_layer),distance=n.straight_outline, open_ports=2)
            # pad_taper = outline(hyper_taper(40, n.pad_width+n.pad_outline,step_scale),distance=n.straight_outline, open_ports=2)
            pad_taper.rotate(-90)
            pad_taper.move(pad_taper.ports['wide'], pad.ports[1])
            E.add_ref(pad_taper)
            D.add_ref(pad)
            
        
        straight = qg.outline(pg.straight(size=(n.straight_width[i],n.straight_length[i])),distance=n.straight_outline,open_ports=2)
        straight.rotate(90)
        straight.move(straight.center,D.center)
        straight.movey(n.pad_width*1.25)
        

        pad_taper = qg.outline(qg.hyper_taper(40, n.pad_width+n.pad_outline,n.straight_width[i]*step_scale),distance=n.straight_outline, open_ports=2)
        
        t1 = qg.outline(pg.tee(size=(n.straight_width[i]*4,n.straight_width[i]),stub_size=(n.straight_width[i]*2,n.straight_width[i]*2),taper_type='fillet', layer=n.straight_layer),distance=n.straight_outline, open_ports=2)
        t1.move(t1.ports[1],straight.ports[1])
        
        t2 = qg.outline(pg.tee(size=(n.straight_width[i]*4,n.straight_width[i]),stub_size=(n.straight_width[i]*2,n.straight_width[i]*2),taper_type='fillet', layer=n.straight_layer),distance=n.straight_outline, open_ports=2)
        t2.move(t2.ports[2],straight.ports[2])
        
        s1 = qg.outline(pg.optimal_step(n.straight_width[i]*step_scale,n.straight_width[i]*2),distance=n.straight_outline, open_ports=3)
        s1.rotate(90)
        s1.move(s1.ports[2], t1.ports[3])
        
        s2 = qg.outline(pg.optimal_step(n.straight_width[i]*step_scale,n.straight_width[i]),distance=n.straight_outline, open_ports=3)
        s2.move(s2.ports[2], t1.ports[2])
        
        s3 = qg.outline(pg.optimal_step(n.straight_width[i]*step_scale,n.straight_width[i]*2),distance=n.straight_outline, open_ports=3)
        s3.rotate(90)
        s3.move(s3.ports[2], t2.ports[3])
        
        s4 = qg.outline(pg.optimal_step(n.straight_width[i]*step_scale,n.straight_width[i]),distance=n.straight_outline, open_ports=3)
        s4.rotate(180)
        s4.move(s4.ports[2], t2.ports[1])


        r1 = qg.outline(pr.route_manhattan(port1=E.references[0].ports['narrow'], port2=s2.ports[1]), distance=n.straight_outline,open_ports=3, rotate_ports=True)
        r2 = qg.outline(pr.route_manhattan(port1=E.references[1].ports['narrow'], port2=s1.ports[1]), distance=n.straight_outline,open_ports=3, rotate_ports=True)
        r3 = qg.outline(pr.route_manhattan(port1=E.references[2].ports['narrow'], port2=s3.ports[1]), distance=n.straight_outline,open_ports=3, rotate_ports=True)
        r4 = qg.outline(pr.route_manhattan(port1=E.references[3].ports['narrow'], port2=s4.ports[1]), distance=n.straight_outline,open_ports=3, rotate_ports=True)

        
        E.add_ref([straight, t1, t2, s1, s2, s3, s4, r1, r2, r3, r4])
        E.flatten(single_layer=n.straight_layer)

        D.flatten()
        D.add_ref(E)
        
        """ Attach dynamical parameters to device object. """
        D.width = n.straight_width[i]
        D.squares = straight_squares
        D.parameters = parameters
        D.type='four_point'
        device_list.append(D)
        
    # """ Attach squares calculation to parameters """
    parameters['snspd_squares']=np.array(device_squares_list)
    return device_list









    
    
    
    
    


def meander_outline(width=0.1, pitch=0.250, area=8, length=None, number_of_paths=1, outline=0.25, layer=1, terminals_same_side=False):
    """
                    width=0.1, pitch=0.250, area=8, length=None, number_of_paths=1, layer=1, terminals_same_side=False):

    Parameters
    ----------
    width : FLOAT, optional
        SNSPD wire width. The default is 0.1.
    pitch : FLOAT, optional
        SNSPD wire pitch. The default is 0.250.
    area : FLOAT, optional
        SNSPD overall Y dimension, and or snspd area if Length is not specified. The default is 8.
    length : FLOAT, optional
        SNSPD overall X dimension. The default is None.
    number_of_paths : INT, optional
        Number of times the SNSPD traverses over the Y dimension. This value is limited by the length of the SNSPD The default is 1.

    Returns
    -------
    X : Device
        PHIDL device object is returned.

    """
    D=Device('x')
    X=Device('big')
    
    n=number_of_paths
    if length==None:
        length = area/number_of_paths
    else:
        length = (length-0.5*(number_of_paths-1))/number_of_paths
        
        
    S=pg.snspd(wire_width = width, wire_pitch = pitch+width, size = (length,area), terminals_same_side = terminals_same_side)
    
    if n==1:
        S=pg.snspd(wire_width = width, wire_pitch = pitch+width, size = (length,area), terminals_same_side = terminals_same_side)
        s=D.add_ref(S)
    
    i=0    
    while i < n:
        s=D.add_ref(S)
        if i==0:
            start=s.ports[1].midpoint
        if np.mod(i,2)!=0:
            s.mirror((0,1),(1,1))
        if i>0:
            s.move(origin=s.ports[1], destination=straight.ports[2])
        if i != n-1:
            straight=D.add_ref(pg.straight(size=(width,0.5),  layer = 0))
            straight.rotate(90)
            straight.move(straight.ports[1], s.ports[2])
        if i == n-1:
            end=s.ports[2].midpoint
        i=i+1
    D.flatten(single_layer=layer)    
    t1 = pg.straight(size=(width,outline))
    t1.rotate(90)
    t1.move(origin=t1.ports[1], destination=end)
    
    t2 = pg.straight(size=(width,outline))
    t2.rotate(90)
    t2.move(origin=t2.ports[2], destination=start)
    
    
    X=pg.deepcopy(D)
    X = qg.outline(X,distance=outline,precision=1e-6,layer=layer)
    X = pg.boolean(X,t1,'A-B',1e-6,layer=layer)
    X = pg.boolean(X,t2,'A-B',1e-6,layer=layer)
    X.add_port(port=t1.ports[2], name=2)
    X.add_port(port=t2.ports[1], name=1)
    X.move(origin=X.ports[1], destination=(0,0))
    
    return X

    
    
def meander_taper(width=0.1, pitch=0.250, area=8, length=None, number_of_paths=1, taper_length=50, taper_narrow=.1, taper_wide=200, layer=1):
    
    X=Device('x')
    m=meander(width=width, pitch=pitch, area=area, length=length, number_of_paths=number_of_paths, layer=layer)
    X.add_ref(m)
    ht = qg.hyper_taper(taper_length, taper_wide, taper_narrow, layer=layer)
    HT1 = X.add_ref(ht)
    HT1.rotate(180)
    HT1.move(origin=HT1.ports['narrow'],destination=X.references[0].ports[1])
    HT2 = X.add_ref(ht)
    HT2.move(origin=HT2.ports['narrow'],destination=X.references[0].ports[2])

    X.add_port(name=1, midpoint = HT1.ports['wide'].midpoint, width=taper_wide, orientation=180)
    X.add_port(name=2, midpoint = HT2.ports['wide'].midpoint, width=taper_wide, orientation=0)
    
    X.move(origin=X.ports[1],destination=(0,0))
    return X

def meander_taper_outline(width=0.1, pitch=0.250, area=8, length=None, number_of_paths=1, taper_length=10, taper_narrow=.1, taper_wide=100, outline=0.5, layer=1):
    
    X=Device('x')
    T=Device('t')
    m=meander_taper(width=width, pitch=pitch, area=area, length=length, 
                    number_of_paths=number_of_paths, taper_length=taper_length, 
                    taper_narrow=taper_narrow, taper_wide=taper_wide, layer=layer)
    X.add_ref(qg.outline(m,distance=outline, precision=1e-4))
    
    SW = (X.bbox[0,0],-X.bbox[1,1])
    SE = (X.bbox[1,0]-outline,X.bbox[0,1])
    ''' Trim edge of outline '''
    t = pg.rectangle(size=(outline, X.bbox[1,1]*2))
    t.move(destination=SE)
    T.add_ref(t)
    t = pg.rectangle(size=(outline, X.bbox[1,1]*2))
    t.move(destination=SW)
    T.add_ref(t)
    X=pg.boolean(X,T,'A-B',precision=1e-6,layer=layer )
    X.add_port(name=1,midpoint=m.ports[1].midpoint,width=taper_wide,orientation=180)
    X.add_port(name=2,midpoint=m.ports[2].midpoint,width=taper_wide,orientation=0)
    return X
