import sys
sys.dont_write_bytecode = True
import  Data_pb2
import os,glob
import pandas as pd
import numpy as np
import argparse


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
	A = set(fileA)
	for i in fileB:
		A.add(i)
	result = (len(fileA) + len(fileB) - len(A))/float(len(A))
	return result


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
				sim = ap_similarity(a,b)
				print ("S:"+str(sim))
				guide.append(sim)
		else:
			if dis < (10**-4):
				print(str(i).strip())
				a = get_AP_name(base_dir+"cali_data/"+fileA.strip())
				b = get_AP_name2(base_dir+"data_path/"+fileB_n.strip(),fileB_sn)
				sim = ap_similarity(a,b)
				print ("S:"+str(sim))
				unguide.append(sim)

	print(sum(guide)/len(guide))
	print(sum(unguide)/len(unguide))

			# print("Similarity: " + str(sim))
			# aa = get_level(fileA,args.wifi)
			# print("Average Level: " + str(sum(aa)/len(aa)))
			# bb = get_level(fileB,args.wifi)
			# print("Average Level: " + str(sum(bb)/len(bb)))

if __name__ == "__main__":
	main()





