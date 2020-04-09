# This script generate a csv file containing the information
# regarding the matching results 
# (One crowdsourced data instance matches to on test data instance)
# The output csv file will be used as the input by similarity algorithms later

import sys
sys.dont_write_bytecode = True
import Data_pb2
import os,glob
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import pandas as pd
import pickle


# calibration data 
scan_df1 = pd.read_csv('./cali.csv')
# real data
scan_df2 = pd.read_csv('./data_point_info.csv')

fn = scan_df1['filename']
lo = scan_df1['longitude']
la = scan_df1['latitude']
fl = scan_df1['floor']
cali = []
for i in range(len(fn)):
	cali.append({fn[i]:[lo[i],la[i],fl[i]]})

fn1 = scan_df2['filename']
lo1 = scan_df2['longitude']
la1 = scan_df2['latitude']
fl1 = scan_df2['floor']
real = []
for i in range(len(fn1)):
	real.append({fn1[i]:[lo1[i],la1[i],fl1[i]]})

result = []
dis = []
name = []
pair = []
for i in cali:
	min_dis = 3 
	min_name = "Wrong!"
	fn1 = list(i.keys())[0]
	log1 = list(i.values())[0][0]
	lat1 = list(i.values())[0][1]
	fl1 = list(i.values())[0][2]
	for j in real:
		# get i's log1,lat1 
		# get j's log2,lat2
		# dis = sqrt(abs(log1-log2)^2 + abs(lat1-lat2)^2)
		fn2 = list(j.keys())[0]
		log2 = list(j.values())[0][0]
		lat2 = list(j.values())[0][1]
		fl2 = list(i.values())[0][2]
		if fl1 == fl2: # only compare the distance if a at same floor 
			di = np.sqrt(np.power((log1-log2),2) + np.power((lat1-lat2),2))
			if min_dis > di:
				min_dis = di
				min_name = fn2
	pair.append([fn1,min_name])
	dis.append(min_dis)
	name.append(min_name)

final = []
j= 0
for i in cali:
 	final.append([list(i.keys())[0], name[j], dis[j]])
 	j = j+ 1
final_2 = final
for i in range(len(final)):
	re = final[i][1]
	try:
		re_n = final[i+1][1]
	except:
		break
	if re == re_n:
		if final[i][2] < final[i+1][2]:
			final_2.remove(final[i+1])

pa = pd.DataFrame(columns=['cali','real'])
for i in final_2:
	pa = pa.append({'cali':i[0], 'real':i[1]},ignore_index=True)

# Output
pa.to_csv("matching_result_point.csv",index = None, header=True)









