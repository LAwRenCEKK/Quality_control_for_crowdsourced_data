import sys
sys.dont_write_bytecode = True
import  Data_pb2
import os,glob
import pandas as pd
import numpy as np
import argparse
import math

def get_AP_name(file_path):
	fin = open(file_path,'rb')
	frame = pd.DataFrame(columns=['scanNum','Wifi Name','AP Name','Level'])
	datapack = Data_pb2.DataPack()
	datapack.ParseFromString(fin.read())
	fin.close()
	rss = datapack.rssItems

	for i in rss:
		frame = frame.append({'scanNum':i.scanNum,'Wifi Name':i.ssid,'AP Name':i.bssid,\
		 'Level': i.level}, ignore_index=True)

	macsecure = []
	for k in ['Mac-WiFi','MacSecure','eduroam']:
		for i in range(len(frame['Wifi Name'])):
			if frame['Wifi Name'][i] == k:
				macsecure.append(frame['AP Name'][i])

	return set(macsecure)

def get_AP_name2(file_path,scanNum):
	fin = open(file_path,'rb')
	frame = pd.DataFrame(columns=['scanNum','Wifi Name','AP Name','Level'])
	datapack = Data_pb2.DataPack()
	datapack.ParseFromString(fin.read())
	fin.close()
	rss = datapack.rssItems
	for i in rss:
		frame = frame.append({'scanNum':i.scanNum,'Wifi Name':i.ssid,'AP Name':i.bssid,\
		 'Level': i.level}, ignore_index=True)
	macsecure = []
	for k in ['Mac-WiFi','MacSecure','eduroam']:
		for i in range(len(frame['Wifi Name'])):
			if frame['scanNum'][i] == int(scanNum):
				if frame['Wifi Name'][i] == k:
					macsecure.append(frame['AP Name'][i])
	return set(macsecure)

def cosine_sim(file_name1,file_name2, same_ap, scan_num):
	# open the regarding A,B files 
	base_dir = "/Users/lawrence/Desktop/Temp/"
	fin1 = open(base_dir+"cali_data/"+file_name1, 'rb')
	fin2 = open(base_dir+"data_path/"+file_name2, 'rb')

	datapack1 = Data_pb2.DataPack()
	datapack1.ParseFromString(fin1.read())
	fin1.close()

	datapack2 = Data_pb2.DataPack()
	datapack2.ParseFromString(fin2.read())
	fin2.close()

	rss1 = datapack1.rssItems
	rss2 = datapack2.rssItems
	# preprocessing the repeated level 
	level1 = {}
	level2 = {}
	for i in same_ap:
		level1.update({i:[]})
		level2.update({i:[]})

	for i in rss1:
		for j in same_ap:
			if i.bssid == j:
				level1.get(j).append(i.level)
	
	for i in rss2:	
		for j in same_ap:
			if i.scanNum == int(scan_num) and i.bssid == j:
				level2.get(j).append(i.level)

	for i in level1.keys():
		# average
		a = sum(level1.get(i))/len(level1.get(i))
		b = sum(level2.get(i))/len(level2.get(i))
		level1.update({i:a})
		level2.update({i:b})

	result = 0
	for i in same_ap:
		result = result + math.pow(level1.get(i)-level2.get(i),2)
	try:
		result = math.sqrt(result)/len(same_ap)
	except:
		result = 0

	print(result)
	return result

def get_level(file_path, wifi_name):
	fin = open(file_path,'rb')
	frame = pd.DataFrame(columns=['scanNum','Wifi Name','AP Name','Level'])
	datapack = Data_pb2.DataPack()
	datapack.ParseFromString(fin.read())
	fin.close()
	rss = datapack.rssItems

	for i in rss:
		frame = frame.append({'scanNum':i.scanNum,'Wifi Name':i.ssid,'AP Name':i.bssid,\
		 'Level': i.level}, ignore_index=True)

	level = []
	for i in range(len(frame['Wifi Name'])):
		if frame['Wifi Name'][i] == wifi_name:
			level.append(frame['Level'][i])

	return level


def ap_similarity(fileA,fileB):
	same_ap = []
	for i in fileA:
		for j in fileB:
			if i==j:
				same_ap.append(i)

	return same_ap


def main():
	base_dir = "/Users/lawrence/Desktop/Temp/"
	guide = []
	unguide = []
	pair = open("./path_temp.csv",'r')
	lines = pair.readlines()
	for i in lines:
		mode = i.split(',')[4]
		fileA = i.split(',')[0]
		fileB_n = i.split(',')[1]
		fileB_sn = i.split(',')[2]
		dis = float(i.split(',')[3])
		if int(mode) == 1:
			if dis < (10**-4):
				print(str(i).strip())
				a = get_AP_name(base_dir+"cali_data/"+fileA.strip())
				b = get_AP_name2(base_dir+"data_path/"+fileB_n.strip(),fileB_sn)
				same_ap = ap_similarity(a,b)
				result = cosine_sim(fileA.strip(),fileB_n.strip(),same_ap,fileB_sn)
				guide.append(result)
		else:
			if dis < (10**-4):
				print(str(i).strip())
				a = get_AP_name(base_dir+"cali_data/"+fileA.strip())
				b = get_AP_name2(base_dir+"data_path/"+fileB_n.strip(),fileB_sn)
				same_ap = ap_similarity(a,b)
				result = cosine_sim(fileA.strip(),fileB_n.strip(),same_ap,fileB_sn)
				guide.append(result)
				unguide.append(result)

	print(sum(guide)/len(guide))
	print(sum(unguide)/len(unguide))

			# print("Similarity: " + str(sim))
			# aa = get_level(fileA,args.wifi)
			# print("Average Level: " + str(sum(aa)/len(aa)))
			# bb = get_level(fileB,args.wifi)
			# print("Average Level: " + str(sum(bb)/len(bb)))

if __name__ == "__main__":
	main()





