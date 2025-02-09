
#expected change in run expectency
import ast
from hit_dist_neural_net import load_model
import numpy as np
import os
from mock_model import mock_model
import pandas as pd
import progressbar
from pybaseball import playerid_lookup
from pybaseball import schedule_and_record
from pybaseball import statcast_pitcher
from pybaseball import statcast
import league_pitching_stats_with_ids as pitching_stats
import re
import sys
import time

i=0

def last_day(year, team='NYY'):
	"""returns the last day of the regular season"""
	last_day_str=list(schedule_and_record(year, team)['Date'])[-1]
	last_day = time.strptime(last_day_str+', '+str(year), '%A, %b %d, %Y')
	last_day_str = time.strftime('%Y-%m-%d', last_day)
	return last_day_str

def get_id_table(): #player_ids from http://crunchtimebaseball.com/baseball_map.html
	table = pd.read_csv('player_ids.csv', encoding='latin-1')
	return table

def get_pitcher_list(): #player_list from https://www.baseball-reference.com/leagues/MLB/2019-standard-pitching.shtml
	table = pd.read_csv('player_list.csv', encoding='latin-1')
	table['Name'] = table['Name'].apply(format_player_name)
	return table

def format_player_name(string):
	"""get baseball-reference id from their name in pitcher list"""
	bref = re.split(r'\*?\\', string)[-1] #split at * or *\, select last str
	return bref

def get_player_table():
	"""merge id_table and pitcher_list"""
	ids = get_id_table()
	pitcher_list = get_pitcher_list()
	player_table = pd.merge(pitcher_list, ids, how='inner', left_on=['Name', 'Tm'], right_on=['bref_id', 'mlb_team'])
	player_table = player_table.loc[player_table['Name'] != 'LgAvg per 180 IP'] #remove extraneous row
	return player_table[['mlb_name','mlb_id']]

def load_re_matrix():
	"""run expectation matrix"""
	return pd.read_csv('re_matrix.csv', delimiter='\t', index_col=0)

def get_re_from_mat(matrix, outs, runner1, runner2, runner3):
	"""gets run expectation for a situation"""
	runners = runner1 + 2*runner2 + 4*runner3
	keys = ['0 Outs', '1 Out', '2 Outs']
	return matrix[keys[int(outs)]][runners]

def runner_float2bool(runner):
	"""converts a runner value to a boolean (true if base is occupied)"""
	return not np.isnan(runner)

def get_velo_and_angle(pitch_data):
	try:
		velo = pitch_data['launch_speed']
		angle = pitch_data['launch_angle']
		return round(velo), round(angle)
	except:
		return None

def get_runners(pitch_data):
	runner1 = runner_float2bool(pitch_data['on_1b'])
	runner2 = runner_float2bool(pitch_data['on_2b'])
	runner3 = runner_float2bool(pitch_data['on_3b'])
	return (runner1, runner2, runner3)

def get_outs_and_runners(pitch_data):
	runner1, runner2, runner3 = get_runners(pitch_data)
	outs = pitch_data['outs_when_up']
	return (outs, runner1, runner2, runner3)

def get_start_re(pitch_data, re_matrix):
	"""calculates the run expectancy before the plate appearance"""
	outs, runner1, runner2, runner3 = get_outs_and_runners(pitch_data)
	return get_re_from_mat(re_matrix, outs, runner1, runner2, runner3)

def get_hp_data_from_nn(model, velo, angle):
	data = np.array([angle, velo]).reshape(1,-1)
	return model.predict(data)

def get_end_re(pitch_data, re_matrix, model):
	"""gets run expectancy after a batted ball"""
	outs, runner1, runner2, runner3 = get_outs_and_runners(pitch_data)
	o, r1, r2, r3, runs = single(outs, runner1, runner2, runner3)
	single_re = get_re_from_mat(re_matrix, o, r1, r2, r3) + runs #run expectancy of a single
	o, r1, r2, r3, runs = double(outs, runner1, runner2, runner3)
	double_re = get_re_from_mat(re_matrix, o, r1, r2, r3) + runs #run expectancy of a double
	o, r1, r2, r3, runs = triple(outs, runner1, runner2, runner3)
	triple_re = get_re_from_mat(re_matrix, o, r1, r2, r3) + runs #run expectancy of a triple
	o, r1, r2, r3, runs = homerun(outs, runner1, runner2, runner3)
	homerun_re = get_re_from_mat(re_matrix, o, r1, r2, r3) + runs #run expectancy of a homerun
	o, r1, r2, r3, runs = out(outs, runner1, runner2, runner3)
	if o == 3:
		#if 3rd out of inning, run expectancy for that inning is 0
		out_re = 0 
	else:
		#otherwise get run expectancy from matrix
		out_re = get_re_from_mat(re_matrix, o, r1, r2, r3) + runs
	velo, angle = get_velo_and_angle(pitch_data)
	hp_data = get_hp_data_from_nn(model, velo, angle)
	out_rate, single_rate, double_rate, triple_rate, homerun_rate = hp_data[0]
	#expected value: E(X) = ∑(X * P(X))
	exp_re = single_re*single_rate + double_re*double_rate + triple_re*triple_rate + homerun_re*homerun_rate + out_re*out_rate
	return exp_re

def change_in_re(pitch_data, re_matrix, model):
	"""calculcate change in run expectancy from the beginning to the end of a plate appearance"""
	start = get_start_re(pitch_data, re_matrix)
	end = get_end_re(pitch_data, re_matrix, model)
	delta = start - end #subtract this way so that higher number is better
	return delta

def single(outs, runner1, runner2, runner3):
	"""return the situation (outs & baserunners) that results from a single"""
	r1 = True
	r2 = runner1
	r3 = runner2
	runs = runner3
	return (outs, r1, r2, r3, runs)

def double(outs, runner1, runner2, runner3):
	"""return the situation (outs & baserunners) that results from a double"""
	r1 = False
	r2 = True
	r3 = runner1
	runs = (runner2+runner3)
	return (outs, r1, r2, r3, runs)

def triple(outs, runner1, runner2, runner3):
	"""return the situation (outs & baserunners) that results from a triple"""
	r1 = False
	r2 = False
	r3 = True
	runs = (runner1+runner2+runner3)
	return (outs, r1, r2, r3, runs)

def homerun(outs, runner1, runner2, runner3):
	"""return the situation (outs & baserunners) that results from a homerun"""
	r1 = False
	r2 = False
	r3 = False
	runs = (runner1+runner2+runner3+1)
	return (outs, r1, r2, r3, runs)

def out(outs, runner1, runner2, runner3):
	"""return the situation (outs & baserunners) that results from an out"""
	return (outs+1, runner1, runner2, runner3, 0)

def strikeout(re_matrix, pitch_data):
	"""returns the change in run expectancy follwing a strikeout"""
	outs, runner1, runner2, runner3 = get_outs_and_runners(pitch_data)
	if outs == 2:
		return get_re_from_mat(re_matrix, outs, runner1, runner2, runner3)
	else:
		return get_re_from_mat(re_matrix, outs, runner1, runner2, runner3)-get_re_from_mat(re_matrix, outs+1, runner1, runner2, runner3)

def walk(re_matrix, pitch_data):
	"""returns the change in run expectancy follwing a walk"""
	outs, runner1, runner2, runner3 = get_outs_and_runners(pitch_data)
	before = get_re_from_mat(re_matrix, outs, runner1, runner2, runner3)
	after = get_re_from_mat(re_matrix, outs, True, runner1, runner1 and runner2)+int(runner1 and runner2 and runner3)
	return before-after

def export_values(calc_table, filename='values.csv'):
	"""export all players stats to a csv file"""
	try:
		with open(filename, 'w', newline='') as file:
			file.write(calc_table.to_csv())
	#if file is open, this error occurs. Try exporting again	
	except (PermissionError, FileNotFoundError):
		x = input('Error exported values. Enter a filename to export to or hit Enter to try the same filename again.')
		if not x:
			x = filename
		export_values(calc_table, x)

def season_change_2(statcast_data, re_matrix, model):
	values = {}
	for index, row in statcast_data.iterrows():
		try:
			if row['type'] == 'X':
				if 'bunt' in row['des'].lower():
					continue
				val = change_in_re(row, re_matrix, model)
				add_to_dict(values, row['pitcher'], val)
			elif row['events'] in ['strikeout', 'strikeout_double_play']:
				val = strikeout(re_matrix, row)
				add_to_dict(values, row['pitcher'], val)
			#if bb or hbp, add walk change in run expectancy 
			elif row['events'] in ['walk', 'hit_by_pitch']:
				val = walk(re_matrix, row)
				add_to_dict(values, row['pitcher'], val)
		except:
			print('---here---')
	return pd.DataFrame([(key, values[key]) for key in values.keys()], columns=['id', 'Value'])

def add_to_dict(d, key, value):
	if key in d.keys():
		d[key] += value
	else:
		d[key] = value

def get_statcast_data():
	dfs = [pd.read_csv('data/statcast_data{}.csv'.format(i)) for i in range(3,10)]
	return pd.concat(dfs)

def calculate():
	statcast_data = get_statcast_data()
	re_matrix = load_re_matrix()
	model = load_model()
	values = season_change_2(statcast_data, re_matrix, model)
	ids = get_id_table()
	table = pd.merge(values, ids, how='inner', left_on=['id'], right_on=['mlb_id'])
	stats = pitching_stats.pitching_stats_bref(2019)
	table = pd.merge(table, stats, left_on=['id'], right_on=['mlb_ID'])
	table = table[['Name', 'Value', 'G', 'IP', "BF"]]
	val_g = table['Value']/table['G']
	#convert every 0.1 innings pitched to 1/3 inning pitched
	real_ips = [ip + (ip - int(ip)) * 10/3 for ip in table['IP']]
	val_ip = table['Value']/real_ips
	val_bf = table['Value']/table['BF']
	table['Value/G'] = val_g
	table['Value/IP'] = val_ip
	table['Value/BF'] = val_bf
	table = table[['Name', 'Value', 'G', 'Value/G', 'IP', 'Value/IP', "BF", 'Value/BF']]
	table.sort_values(by="Value", inplace=True, ascending=False)
	table.index = np.arange(1,len(table)+1)
	return table

start = time.time()
print("Calculating all pitchers' values. This should take several minutes")
calc_table = calculate()
export_values(calc_table)
print('\nDone in {} seconds'.format(int(np.ceil(time.time()-start))))