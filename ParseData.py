#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 13 19:08:07 2019
Tools for parsing the Protobuf Data Package
@author: yongyongwei
"""
import sys
sys.dont_write_bytecode = True
import os
import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import colors,cm
import Data_pb2
import MapUtils
import glob
import geojson
from geojson import FeatureCollection,Feature,Point


def location_interpolate(start, terminal, step_events, timestamp, steplen=None):
    """Interpolate the location during walking
    
    Args:
        start: The start location, type: Data_pb2.LatLon (GPS coordinate)
        terminal: The terminal location, type: Data_pb2.LatLon (GPS coordinate)
        step_events: Step event timestamps array, microsecond since boot
        timestamp: timestamp to query the location
        
    Returns:
        (latitude,longitude) <GPS coordinate>
    """
    start_latitude = start.latitude
    start_longitude = start.longitude
    terminal_latitude = terminal.latitude
    terminal_longitude = terminal.longitude
    pathlength = MapUtils.distance(start_latitude,start_longitude,
                                   terminal_latitude,terminal_longitude)
    #Get step length if not set from the paramater
    if (steplen == None):
        stepnum = len(step_events)
        steplen = pathlength*1.0/stepnum
    #Exceptinal case
    if timestamp < step_events[0]:
        #print("timestamp %ld less than start step event\n" % timestamp)
        return None
    if timestamp >= step_events[-1]:
        #print("timestamp %ld more than terminal step event\n" % timestamp)
        return None
    #Interpolate
    int_steps=0
    for steptime in step_events:
        if timestamp >= steptime:
            int_steps += 1
        else:
            break
    partial_steps = (timestamp - step_events[int_steps-1] )* 1.0  /  \
                    (step_events[int_steps] - step_events[int_steps-1])
    
    walklength = (int_steps + partial_steps) * steplen
    ratio = walklength/pathlength
    total_xoffset, total_yoffset = MapUtils.offset_coord(start_latitude,\
                        start_longitude,terminal_latitude,terminal_longitude)
    #Note the return of gps_fromxy is lon,lat
    reslon,reslat = MapUtils.gps_fromxy(start_latitude,start_longitude,\
                                   ratio * total_xoffset,ratio * total_yoffset)
    
    return (reslon,reslat)
    
def get_labeled_rss(datapack,bssid = None):
    """Get location (GPS) labled rss from datapack
    Args:
        datapack: Data package object
        bssid: Only extract the selected bssid
    Returns:
        List of labeled rss
    """
    ret = []
    for item in datapack.rssItems:
        if bssid != None and item.bssid != bssid:
            continue
        if datapack.collectMode != 2:
            label = location_interpolate(datapack.startLocation, \
                    datapack.terminalLocation, datapack.stepEvents, item.timestamp)    
        else:
            label = (datapack.startLocation.longitude,datapack.startLocation.latitude)
        #Note the label can be failed
        if label == None:
            continue
        ret.append([item.scanNum,item.timestamp,item.bssid,item.level, \
                    item.frequency,label[0],label[1]]) 
    #Endfor
    return ret
        
def get_labeled_mag(datapack,magnitude = False):
    """Get location (GPS)  labled magnetic field signal
    Args:
        - datapack: the data package object
        - magnitude: wheter only consider the magnitude
    Returns:
        List of GPS labeled mag
    """
    ret = []
    for item in datapack.magnetic:
        if datapack.collectMode != 2:
            label = location_interpolate(datapack.startLocation,\
                    datapack.terminalLocation, datapack.stepEvents,item.timestamp)
        else:
            label = (datapack.startLocation.longitude,datapack.startLocation.latitude)
        if label == None:
            continue
        if magnitude == False:
            ret.append([item.x,item.y,item.z,item.timestamp,label[0],label[1]])
        else:
            magmag = np.sqrt(item.x*item.x + item.y*item.y + item.z*item.z)
            ret.append([magmag,item.timestamp,label[0],label[1]])
    #Endfor
    return ret

def get_labeled_light(datapack):
    """Get location (GPS) labeled light sensor values"""
    ret = []
    for item in datapack.light:
        if datapack.collectMode != 2:
            label = location_interpolate(datapack.startLocation,\
                    datapack.terminalLocation, datapack.stepEvents,item.timestamp)
        else:
            label = (datapack.startLocation.longitude,datapack.startLocation.latitude)
        if label == None:
            continue
        ret.append([item.value,item.timestamp,label[0],label[1]])
    #Endfor
    return ret    
    
def get_statistics(datapack):
    """Retrieve  some statistic information for data package
    Args:
        - datapack: the datapackage object
    Returns:
        A dictionary
    """
    info={}
    info['collectMode'] = datapack.collectMode
    info['duration'] = (datapack.terminalTime - datapack.startTime)/1000.0
    info['numofscan'] = datapack.rssItems[-1].scanNum
    info['lightsize'] = len(datapack.light)
    info['magsize'] = len(datapack.magnetic)
    bssids = set()
    bssids2G = set()
    bssids5G = set()
    rss2GNum = 0
    rss5GNum = 0
    for item in datapack.rssItems:
        bssids.add(item.bssid)
        if item.frequency > 3000:
            bssids5G.add(item.bssid)
            rss5GNum += 1
        else:
            bssids2G.add(item.bssid)
            rss2GNum +=1
    info['numofbssid'] = len(bssids)
    info['bssids'] = bssids
    
    info['bssids2G'] = bssids2G
    info['bssids5G'] = bssids5G
    info['rss2GNum'] = rss2GNum
    info['rss5GNum'] = rss5GNum
    
    if datapack.collectMode !=2:
        info['numofstep'] = len(datapack.stepEvents)
        start_latitude = datapack.startLocation.latitude
        start_longitude = datapack.startLocation.longitude
        terminal_latitude = datapack.terminalLocation.latitude
        terminal_longitude = datapack.terminalLocation.longitude
        pathlength = MapUtils.distance(start_latitude,start_longitude,\
                                       terminal_latitude,terminal_longitude)
        info['pathlen'] = pathlength
        info['speed'] = pathlength/info['duration']
        
    #Endif
    return info

def merge_packages(datapacks,fptype):
    """Merge the data packages and extract the fingperints
    
    Args:
        datapacks - list of data package objects
        fptype - fingerprint type,i.e., "wifi","magnetic" or "light"
        
    Returns:
        For WiFi, return a dict of list organized by bssid; otherwise item list
    """
    #Building Check
    building_names = set()
    for pack in datapacks:
        if len(pack.buildingName)>0:
            building_names.add(pack.buildingName)
    assert len(building_names) == 1, "Packages must be from the same building"
    assert fptype in ["wifi","light","magnetic"], "fptype invalid"    
    data = []
    for datapack in datapacks:
        if fptype == "wifi":
            wifi = get_labeled_rss(datapack)
            data.extend(wifi)
        elif fptype == "light":
            light = get_labeled_light(datapack)
            data.extend(light)
        elif fptype == "magnetic":
            #Note the magnetic is magnitude, so it is a scalar
            magnetic = get_labeled_mag(datapack,magnitude=True)
            data.extend(magnetic)
    if fptype == "wifi":
        APs = set([item[2] for item in data])
        data_byAP={AP:[] for AP in APs}
        for entry in data:
            data_byAP[entry[2]].append([entry[5],entry[6],entry[3],entry[4]])
        return data_byAP
    else:
        #Note the format
        return [[entry[2],entry[3],entry[0]] for entry in data]
        

def rss_positions(datapacks,outfile=None):
    """Extract the all the gps positions from  the datapacks
    
    Args:
        datapacks - a list of datapack
        outfile - output file name
    Returns:
        if outfile == None, return the geojson string directly, otherwise write
    """       
    crs = geojson.crs.Named("urn:ogc:def:crs:OGC:1.3:CRS84")
    features = []
    for datapack in datapacks:
        weight = 1
        if datapack.collectMode == 2:
            weight = 5
        labeled_rss = get_labeled_rss(datapack)
        positions = set([(item[5],item[6]) for item in labeled_rss])
        for position in positions:
            features.append(Feature(geometry=Point(position),properties={"weight":weight}))
    #endfor
    collection = FeatureCollection(features,crs = crs)
    if outfile == None:
        return geojson.dumps(collection)
    else:
        with open(outfile,'w') as fout:
            geojson.dump(collection,fout)
    
def surveyed_positions(datapacks,outfile = None):
    """Extract the step positions from the datapacks
    
    Args:
        datapacks - the datapacks list
    Returns:
        if outfile == None, return the geojson string directly, otherwise write
    """
    crs = geojson.crs.Named("urn:ogc:def:crs:OGC:1.3:CRS84")
    features = []
    for datapack in datapacks:
        if datapack.collectMode == 2:
            weight = 5
            point_pos = (datapack.startLocation.longitude,datapack.startLocation.latitude)
            features.append(Feature(geometry=Point(point_pos),properties={"weight":weight}))
        else:
            weight = 1
            for steptime in datapack.stepEvents:
                step_pos = location_interpolate(datapack.startLocation, \
                    datapack.terminalLocation, datapack.stepEvents,steptime)
                if step_pos != None:
                    features.append(Feature(geometry=Point(step_pos),properties={"weight":weight}))
    #endfor
    collection = FeatureCollection(features,crs = crs)
    if outfile == None:
        return geojson.dumps(collection)
    else:
        with open(outfile,'w') as fout:
            geojson.dump(collection,fout)                    
                    
#=============Data Visualization Section======================================
def plot_data(datapacks, fptype='wifi',bssid= None,buildingprofile='building_dict.json'):
    """Visualize the fingerprint data
    
    Args:
        datapacks: path data packages (list)
        fptype: fingerprint to visualize, wifi, magnetic or light
        buidlingprofile: building information file
    """
    if fptype == "wifi":
        assert bssid != None, "please provide the bssid"
    #Get building name (all data packages are from the same building)
    building_name = datapacks[0].buildingName
    building_dict = None
    with open(buildingprofile) as fin:
        building_dict = json.load(fin)
    gpspo = building_dict[building_name]['gpspo']
    origin_lon,origin_lat = np.min(gpspo,axis=0).tolist()
    localpo = [MapUtils.offset_coord(origin_lat,origin_lon,lat,lon) for \
               lon,lat in gpspo]  
    fig, ax = plt.subplots(1, 1, figsize=(10,8)) 
    #Plot the building first
    ax.plot(*zip(*localpo))
    #Draw the paths
    for datapack in datapacks:
        if datapack.collectMode == 2:
            continue
        start_pos = MapUtils.offset_coord(origin_lat,origin_lon,\
            datapack.startLocation.latitude,datapack.startLocation.longitude)
        stop_pos = MapUtils.offset_coord(origin_lat,origin_lon,\
            datapack.terminalLocation.latitude,datapack.terminalLocation.longitude)
        ax.arrow(start_pos[0],start_pos[1],stop_pos[0] - start_pos[0], \
                  stop_pos[1]-start_pos[1],\
                  head_width=1, head_length=1,linestyle='--')
        """#Not nessesary to draw the steps (a step is too short)
        numofstep = len(datapack.stepEvents)
        for i in range(1,numofstep):
            ax.scatter(start_pos[0] + (stop_pos[0] - start_pos[0])*i/numofstep,\
                       start_pos[1] + (stop_pos[1] - start_pos[1])*i/numofstep,\
                       s=1)
        """
    #Endfor
    data = merge_packages(datapacks,fptype)
    #Format visualization data
    visdata = None
    if fptype == "wifi":
        #gpsrss = [[item[5],item[6],item[3]] for item in data if item[2] == bssid ]
        gpsrss = [[item[0],item[1],item[2]] for item in data[bssid]]
        localrss = []
        for rss in gpsrss:
            localpos = MapUtils.offset_coord(origin_lat,origin_lon,\
                                             rss[1],rss[0])
            localrss.append([localpos[0],localpos[1],rss[2]])
        visdata = np.array(localrss)
    #For light and magnetic the same format apply
    else:
        localdata = []
        for entry in data:
            localpos = MapUtils.offset_coord(origin_lat,origin_lon,\
                                             entry[1],entry[0])
            localdata.append([localpos[0],localpos[1],entry[2]])
        visdata = np.array(localdata)
    #Plot
    xs = np.array(visdata[:,0])
    ys = np.array(visdata[:,1])
    zs = np.array(visdata[:,2])
    
    jet = plt.get_cmap('jet') 
    cNorm  = colors.Normalize(vmin=np.nanmin(zs), vmax=np.nanmax(zs))
    scalarMap = cm.ScalarMappable(norm=cNorm, cmap=jet)
            
    ax.scatter(xs, ys, color=scalarMap.to_rgba(zs), marker='o')
    scalarMap.set_array(zs)
    fig.colorbar(scalarMap)

    ax.set_xlabel('X Label')
    ax.set_ylabel('Y Label')
    title = fptype+" distribution"
    if bssid != None:
        title = title + "("+bssid+","+str(len(zs))+")"
    plt.title(title)
    plt.show()    

def plot_wifi(datapacks,sigtype="bssids2G",buildingprofile='building_dict.json'):
    bssids2G=[]
    bssids5G=[]
    for datapack in datapacks:
        bssids2G.extend(get_statistics(datapack)['bssids2G'])
        bssids5G.extend(get_statistics(datapack)['bssids5G'])
    bssids2G=set(bssids2G)
    bssids5G=set(bssids5G)
    if sigtype == "bssids2G":
        for bssid in bssids2G:
            plt.close('all')
            plot_data(datapacks,bssid= bssid,buildingprofile='building_dict.json')
            plt.pause(0.5)
        plt.close('all')
            
    elif sigtype == "bssids5G":
        for bssid in bssids5G:
            plt.close('all')
            plot_data(datapacks,bssid= bssid,buildingprofile='building_dict.json')
            plt.pause(0.5)
        plt.close('all')
            
            
#==========Utils For Get The related data package files=======================
def get_file_list(folder, mode):
    """Get fingerprint file list inside a folder
    Args:
        folder - folder of fingerprint files
        mode - collect mode, 1: path based, 2: point-based
    Returns:
        List of filenames of the specified files inside the folder
    """
    all_files = glob.glob(folder+"/*.pbf")
    fp_files = []
    for fname in all_files:
        if "Calibration" in fname:
            continue
        parts = os.path.basename(fname).split('_')
        if len(parts) == 3 and int(parts[1]) == mode:
            fp_files.append(fname)
    #Replace with full paths
    return [os.path.realpath(f) for f in fp_files]

def get_floor_files(folder,floor,mode):
    """Get the files for specific floor
    
    Args:
        folder - the top folder (FpData)
        floor - the specific floor (string)
        mode - collect mode
    Returns:
        List of files in the floor with mode
    """
    buildings = [ name for name in os.listdir(folder) if os.path.isdir(os.path.join(folder, name))]
    files = []
    for building in buildings:
        subfolder = os.path.join(folder,building,floor)
        files.extend(get_file_list(subfolder, mode))
    return files
    
    
def load_data_packs(filelist):
    """Load the data packages from the file list
    Args:
        filelist - a list of file packs
    Returns:
        a list of data packages
    """
    datapacks = []
    for f in filelist:
        datapack = Data_pb2.DataPack()
        with open(f,'rb') as fin:
            datapack.ParseFromString(fin.read())
            datapacks.append(datapack)
    return datapacks
        
#=====================END======================================================
def location_interpolate_speed(start, terminal, speed, time):
    """Interpolate the location during walking with constant speed

    Args:
        start: The start location, type: Data_pb2.LatLon (GPS coordinate)
        terminal: The terminal location, type: Data_pb2.LatLon (GPS coordinate)
        start_time: The start time of walking
        terminal_time: The termial time of walking
        speed: the walk speed
        time: the walk time

    Returns:
        (latitude,longitude) <GPS coordinate>
    """
    start_latitude = start.latitude
    start_longitude = start.longitude
    terminal_latitude = terminal.latitude
    terminal_longitude = terminal.longitude
    pathlength = MapUtils.distance(start_latitude,start_longitude,
                                   terminal_latitude,terminal_longitude)
    #Interpolate
    walklength = speed * time
    ratio = walklength/pathlength
    total_xoffset, total_yoffset = MapUtils.offset_coord(start_latitude,\
                        start_longitude,terminal_latitude,terminal_longitude)
    #Note the return of gps_fromxy is lon,lat
    reslon,reslat = MapUtils.gps_fromxy(start_latitude,start_longitude,\
                                   ratio * total_xoffset,ratio * total_yoffset)

    return (reslon,reslat)

def parse_path_packages(path_packages,AP_bssids_index_dict,method=1):
    """Parse the WiFi signal values in packages
    Args:
        path_packages: a list of packages
        AP_bssids_index_dict: the dict of AP
        method: the way to interploate locations, default 1, constant speed
        0: step based
    Returns:
        (M,L), M is the data matrix(2D array), L is the loation labels
    """
    #Create the fingerprint and location label matrix.
    FPs = []
    labels = []
    #For the path data, to simplify, three assumptions are made
    #1. walk with the same speed. 2.path is straight line. 3. the scan time is the same for all bssids.
    for datapack in path_packages:
        walk_time = (datapack.terminalTime - datapack.startTime)/1000.0
        walk_distance = MapUtils.distance(datapack.startLocation.latitude,datapack.startLocation.longitude,\
                                 datapack.terminalLocation.latitude,datapack.terminalLocation.longitude)
        print('path length is %f meter' % walk_distance)
        if len(datapack.rssItems) == 0:
            print('This path has no scans!!!')
            #continue
        walk_speed = walk_distance/walk_time
        #estimate the locations for each scan
        scan_seq = 0
        #Init with None
        fp = None 
        #Init with empty
        bssid_timestamp = {}
        for e in datapack.rssItems:
            if e.scanNum == scan_seq:
                if e.bssid in AP_bssids_index_dict:
                    fp[AP_bssids_index_dict[e.bssid]] = e.level * 1.0
                    bssid_timestamp[e.bssid]=e.timestamp
                    #print(np.max(bssid_timestamp.values()) - np.min(bssid_timestamp.values()))
            else:
                #new scan encountered, save the previous scan and re-init
                if scan_seq!=0:
                    #Remove out liers from fp by using the bssid_timestamp
                    for k,v in bssid_timestamp.items():
                        if np.abs(v - np.median(list(bssid_timestamp.values())))>5000:
                            fp[AP_bssids_index_dict[k]]=np.nan
                            #print('outliers from AP',k)
                    if len(bssid_timestamp)==0:
                        print('This scan %d do not perceived valid APs!' % scan_seq)
                    else:
                        t = np.median(list(bssid_timestamp.values()))/1000.0 + datapack.deviceBootTime - datapack.startTime
                        walktime = t/1000.0
                        FPs.append(fp)
                        if method == 0:
                            loc = location_interpolate(datapack.startLocation, datapack.terminalLocation,datapack.stepEvents, t)
                        else:
                            loc = location_interpolate_speed(datapack.startLocation, datapack.terminalLocation, walk_speed, walktime)
                        labels.append(loc)
                    #print("Scan ID",scan_seq,",duration",scan_duration)
                #init and record the first of new scan
                scan_seq = e.scanNum
                fp = [np.nan] * len(AP_bssids_index_dict)
                bssid_timestamp = {}
                if e.bssid in AP_bssids_index_dict:
                    fp[AP_bssids_index_dict[e.bssid]] = e.level * 1.0
                    bssid_timestamp[e.bssid]=e.timestamp
        #Add the last scan
        for k,v in bssid_timestamp.items():
            if np.abs(v - np.median(list(bssid_timestamp.values())))>5000:
                fp[AP_bssids_index_dict[k]]=np.nan
                #print('outliers from AP',k)

        if len(bssid_timestamp)==0:
            print('The last scan do not have valid APs')
        else:
            
            FPs.append(fp)
            t = np.median(list(bssid_timestamp.values()))/1000.0 + datapack.deviceBootTime - datapack.startTime
            walktime = t/1000.0
            loc = location_interpolate_speed(datapack.startLocation, datapack.terminalLocation, walk_speed, walktime)
            labels.append(loc)
    #end for
    return (FPs,labels)

def parse_point_packages(point_packages,AP_bssids_index_dict,num_scan=-1):
    """Parse point packages
    num_scan: the number of scans to use, -1 means use all the scan and take the average
    """
    point_FPs = []
    point_labels = []
    #Load the point collected data
    for datapack in point_packages:
        loc = (datapack.startLocation.longitude,datapack.startLocation.latitude)
        scan_seq = 0
        fp_scans = []
        #Init with None
        fp = None 
        #Init with empty
        bssid_timestamp = {}
        for e in datapack.rssItems:
            if e.scanNum == scan_seq:
                if e.bssid in AP_bssids_index_dict:
                    fp[AP_bssids_index_dict[e.bssid]] = e.level * 1.0
                    bssid_timestamp[e.bssid]=e.timestamp
            else:
                #new scan encountered, save the previous scan and re-init
                if scan_seq!=0:
                    #Remove out liers from fp by using the bssid_timestamp
                    for k,v in bssid_timestamp.items():
                        if np.abs(v - np.median(list(bssid_timestamp.values())))>1000:
                            fp[AP_bssids_index_dict[k]]=np.nan
                            #print('outliers from AP',k)
                    if len(bssid_timestamp) == 0:
                        print("Scan %d do not have valid AP" % scan_seq)
                    else:
                        fp_scans.append(fp)
                    #print("Scan ID",scan_seq,",duration",scan_duration)

                #init and record the first of new scan
                scan_seq = e.scanNum
                fp = [np.nan] * len(AP_bssids_index_dict)
                bssid_timestamp = {}

                if e.bssid in AP_bssids_index_dict:
                    fp[AP_bssids_index_dict[e.bssid]] = e.level * 1.0
                    bssid_timestamp[e.bssid]=e.timestamp
        #Add the last scan
        for k,v in bssid_timestamp.items():
            if np.abs(v - np.median(list(bssid_timestamp.values())))>1000:
                fp[AP_bssids_index_dict[k]]=np.nan
                #print('outliers from AP',k)
                
        if len(bssid_timestamp) == 0 :
            print("Last scan %d do not have valid AP" % scan_seq)
        else:
            fp_scans.append(fp)
        
        if len(fp_scans)>0:    
            if num_scan == -1:
                res = np.nanmean(fp_scans,axis=0).tolist()
            else:
                res = np.nanmean(fp_scans[:num_scan],axis=0).tolist()
                    
            point_FPs.append(res)
            point_labels.append(loc)
        else:
            print('This whole package do not have any valid APs')
    #end for
    return (point_FPs,point_labels)

    
if __name__ == '__main__':
    
    #visualize path collected wifi data
    folder = 'FpData/ITB/2'
    datapacks = load_data_packs(get_file_list(folder,1))
    plot_wifi(datapacks)
    
    #Load a single data package
    datapackP = Data_pb2.DataPack()
    with open('FpData/ITB/2/weiy49_2_20181217124644.pbf','rb') as fin:
        datapackP.ParseFromString(fin.read())
