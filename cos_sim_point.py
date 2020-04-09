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


def cosine_sim(file_name1,file_name2, same_ap):
	# open the regarding A,B files 
	base_dir = "/Users/lawrence/Desktop/Temp/"
	fin1 = open(base_dir+"cali_data/"+file_name1, 'rb')
	fin2 = open(base_dir+"data_point/"+file_name2, 'rb')

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
			if i.bssid == j:
				level2.get(j).append(i.level)

	for i in level1.keys():
		# average
		a = sum(level1.get(i))/len(level1.get(i))
		b = sum(level2.get(i))/len(level2.get(i))
		level1.update({i:a})
		level2.update({i:b})

	numerator = 0
	A_sqaure = 0
	B_sqaure = 0

	for i in same_ap:
		numerator = numerator + level1.get(i) * level2.get(i)
		A_sqaure = A_sqaure + (level1.get(i)*level1.get(i)) 
		B_sqaure = B_sqaure + (level2.get(i)*level2.get(i)) 
	
	denominator = math.sqrt(A_sqaure) * math.sqrt(B_sqaure)

	try:
		result = numerator/denominator
	except:
		result =0
	
	return result


def ap_similarity(fileA,fileB):
	same_ap = []
	for i in fileA:
		for j in fileB:
			if i==j:
				same_ap.append(i)

	return same_ap


def main():
	base_dir = "/Users/lawrence/Desktop/Temp/"
	guided = []
	unguided = []
	pair = open("./pair.csv",'r')
	lines = pair.readlines()
	for i in lines:
		fileA = i.split(',')[0]
		fileB = i.split(',')[1]
		mode = int(i.split(',')[2])
		if mode == 1:
			a = get_AP_name(base_dir+"cali_data/"+fileA.strip())
			b = get_AP_name(base_dir+"data_point/"+fileB.strip())
			same_ap = ap_similarity(a,b)
			result = cosine_sim(fileA.strip(),fileB.strip(),same_ap)
			guided.append(result)
		else:
			a = get_AP_name(base_dir+"cali_data/"+fileA.strip())
			b = get_AP_name(base_dir+"data_point/"+fileB.strip())
			same_ap = ap_similarity(a,b)
			result = cosine_sim(fileA.strip(),fileB.strip(),same_ap)
			unguided.append(result)
	#Results
	print("guided_point full: "+ str(sum(guided)/len(guided)))
	print("guided_point full: "+ str(sum(unguided)/len(unguided)))


	guided = []
	unguided = []
	pair = open("./pair_same_size.csv",'r')	
	lines = pair.readlines()
	for i in lines:
		fileA = i.split(',')[0]
		fileB = i.split(',')[1]
		mode = int(i.split(',')[2])
		if mode == 1:
			a = get_AP_name(base_dir+"cali_data/"+fileA.strip())
			b = get_AP_name(base_dir+"data_point/"+fileB.strip())
			same_ap = ap_similarity(a,b)
			result = cosine_sim(fileA.strip(),fileB.strip(),same_ap)
			guided.append(result)
		else:
			a = get_AP_name(base_dir+"cali_data/"+fileA.strip())
			b = get_AP_name(base_dir+"data_point/"+fileB.strip())
			same_ap = ap_similarity(a,b)
			result = cosine_sim(fileA.strip(),fileB.strip(),same_ap)
			unguided.append(result)

	#Results
	print("guided_point same: "+ str(sum(guided)/len(guided)))
	print("guided_point same: "+ str(sum(unguided)/len(unguided)))




if __name__ == "__main__":
	main()





