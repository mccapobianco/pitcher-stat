#expected change in run expectency
from pybaseball import playerid_lookup
from pybaseball import statcast_pitcher
import pandas as pd
import ast
import numpy as np
import re
import time
import sys
import os
import progressbar

# def get_pitcher_stats(last_name, first_name, year):
# 	player_info = get_player_info(last_name, first_name)
# 	player_id = int(player_info['key_mlbam'])
# 	stats = statcast_pitcher(str(year)+'-01-01', str(year)+'-12-31', player_id)
# 	return stats

def get_pitcher_stats(player_id, year):
	sys.stdout = open(os.devnull, "w")
	stats = statcast_pitcher(str(year)+'-01-01', str(year)+'-12-31', player_id)
	sys.stdout = sys.__stdout__
	return stats

def get_id_table(): #player_ids from http://crunchtimebaseball.com/baseball_map.html
	table = pd.read_csv('player_ids.csv', encoding='latin-1')
	return table

def get_pitcher_list(): #player_list from https://www.baseball-reference.com/leagues/MLB/2019-standard-pitching.shtml
	table = pd.read_csv('player_list.csv', encoding='latin-1')
	table['Name'] = table['Name'].apply(format_player_name)
	return table

def format_player_name(name):
	new_name = re.split(r'\*?\\', name)[-1]
	return new_name

def get_player_table():
	ids = get_id_table()
	pitcher_list = get_pitcher_list()
	player_table = pd.merge(pitcher_list, ids, how='inner', left_on=['Name', 'Tm'], right_on=['bref_id', 'mlb_team'])
	player_table = player_table.loc[player_table['Name'] != 'LgAvg per 180 IP']
	return player_table[['mlb_name','mlb_id']]

def get_player_info(last_name, first_name):
	player_info = playerid_lookup(last_name, first_name)
	if len(player_info) > 1:
		s = 'Multiple Results Found. Please choose one:\n'
		i=0
		for index, player in player_info.iterrows():
			start = player['mlb_played_first']
			try:
				start = int(start)
			except:
				pass
			end = player['mlb_played_last']
			try:
				end = int(end)
			except:
				pass
			s += ('({}) '.format(i) + '{} {} played from {} to {}'.format(player['name_first'], player['name_last'], start, end))
			s += '\n'
			i+=1
		selection = input(s+'Choose (enter a number between 0 and {}): '.format(len(player_info)-1))
		return player_info.loc[int(selection)]
	else:
		print('Found player.')
		return player_info



def load_re_matrix():
	return pd.read_csv('re_matrix.csv', delimiter='\t', index_col=0)

def load_hp_matrix():
	df = pd.read_csv('hit_prob_matrix.csv', delimiter=',', index_col=0)
	df.columns = df.columns.astype(int)
	return df

def get_re_from_mat(matrix, outs, runner1, runner2, runner3):
	runners = runner1 + 2*runner2 + 4*runner3
	keys = ['0 Outs', '1 Out', '2 Outs']
	return matrix[keys[outs]][runners]

def runner_float2bool(runner):
	return not np.isnan(runner)

def get_velo_and_angle(pitch_data):
	velo = pitch_data['launch_speed']
	angle = pitch_data['launch_angle']
	return round(velo), round(angle)

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
	outs, runner1, runner2, runner3 = get_outs_and_runners(pitch_data)
	return get_re_from_mat(re_matrix, outs, runner1, runner2, runner3)

def get_hp_data(hp_matrix, velo, angle):
	val = hp_matrix[velo][angle]
	tup = ast.literal_eval(val)
	return tuple(int(x) for x in tup)


def get_end_re(pitch_data, re_matrix, hp_matrix):
	outs, runner1, runner2, runner3 = get_outs_and_runners(pitch_data)
	o, r1, r2, r3, runs = single(outs, runner1, runner2, runner3)
	single_re = get_re_from_mat(re_matrix, o, r1, r2, r3) + runs
	o, r1, r2, r3, runs = double(outs, runner1, runner2, runner3)
	double_re = get_re_from_mat(re_matrix, o, r1, r2, r3) + runs
	o, r1, r2, r3, runs = triple(outs, runner1, runner2, runner3)
	triple_re = get_re_from_mat(re_matrix, o, r1, r2, r3) + runs
	o, r1, r2, r3, runs = homerun(outs, runner1, runner2, runner3)
	homerun_re = get_re_from_mat(re_matrix, o, r1, r2, r3) + runs
	o, r1, r2, r3, runs = out(outs, runner1, runner2, runner3)
	if o == 3:
		out_re = 0
	else:
		out_re = get_re_from_mat(re_matrix, o, r1, r2, r3) + runs
	velo, angle = get_velo_and_angle(pitch_data)
	hp_data = get_hp_data(hp_matrix, velo, angle)
	single_rate = hp_data[1] / hp_data[0]
	double_rate = hp_data[2] / hp_data[0]
	triple_rate = hp_data[3] / hp_data[0]
	homerun_rate = hp_data[4] / hp_data[0]
	out_rate = 1 - sum((single_rate, double_rate, triple_rate, homerun_rate))
	re = single_re*single_rate + double_re*double_rate + triple_re*triple_rate + homerun_re*homerun_rate + out_re*out_rate
	return re

def change_in_re(pitch_data, re_matrix, hp_matrix):
	start = get_start_re(pitch_data, re_matrix)
	end = get_end_re(pitch_data, re_matrix, hp_matrix)
	delta = start - end
	return delta

def single(outs, runner1, runner2, runner3):
	r1 = True
	r2 = runner1
	r3 = runner2
	runs = runner3
	return (outs, r1, r2, r3, runs)

def double(outs, runner1, runner2, runner3):
	r1 = False
	r2 = True
	r3 = runner1
	runs = (runner2+runner3)
	return (outs, r1, r2, r3, runs)

def triple(outs, runner1, runner2, runner3):
	r1 = False
	r2 = False
	r3 = True
	runs = (runner1+runner2+runner3)
	return (outs, r1, r2, r3, runs)

def homerun(outs, runner1, runner2, runner3):
	r1 = False
	r2 = False
	r3 = False
	runs = (runner1+runner2+runner3+1)
	return (outs, r1, r2, r3, runs)

def out(outs, runner1, runner2, runner3):
	return (outs+1, runner1, runner2, runner3, 0)

def strikeout(re_matrix, pitch_data):
	outs, runner1, runner2, runner3 = get_outs_and_runners(pitch_data)
	if outs == 2:
		return get_re_from_mat(re_matrix, outs, runner1, runner2, runner3)
	else:
		return get_re_from_mat(re_matrix, outs, runner1, runner2, runner3)-get_re_from_mat(re_matrix, outs+1, runner1, runner2, runner3)

def walk(re_matrix, pitch_data):
	outs, runner1, runner2, runner3 = get_outs_and_runners(pitch_data)
	return get_re_from_mat(re_matrix, outs, runner1, runner2, runner3)-get_re_from_mat(re_matrix, outs, True, runner1, runner2)+runner3

def season_change_in_re(player_id, year, re_matrix, hp_matrix):
	df = get_pitcher_stats(player_id, year)
	re = 0
	error = 0
	for index, row in df.iterrows():
		try:
			if type(row['events']) is float and np.isnan(row['events']):
				continue
			elif row['events'] in ['caught_stealing_2b', 'caught_stealing_3b']:
				continue
			elif row['events'] in ['strikeout', 'strikeout_double_play']:
				re += strikeout(re_matrix, row)
			elif row['events'] in ['walk', 'hit_by_pitch']:
				re += walk(re_matrix, row)
			else: 
				re += change_in_re(row, re_matrix, hp_matrix)
		except (ValueError, KeyError):
			error += 1
	return re, error

def calculate(player_id, year):
	re_matrix = load_re_matrix()
	hp_matrix = load_hp_matrix()
	return season_change_in_re(player_id, year, re_matrix, hp_matrix)

def calculate_all(year, player_table, progress=0):
	table = player_table.copy()
	row_count = table.shape[0]
	bar = progressbar.ProgressBar(maxval=row_count, \
		widgets=[progressbar.Bar('=', '[', ']'), ' ', progressbar.Percentage()])
	bar.start()
	stats = []
	error = []
	for index, row in list(table.iterrows()):
		bar.update(index)
		stats.append(calculate(row['mlb_id'], year)[0])
		error.append(calculate(row['mlb_id'], year)[1])
	table['values'] = stats
	table['error'] = error
	return table

def export_values(calc_table, filename='values.csv'):
	with open(filename, 'w', newline='') as file:
		file.write(calc_table[['mlb_name', 'values']].to_csv())
# name = input('Enter pitcher name: ')
# year = input('Enter year: ')
# names = name.split(' ', 1) if ' ' in name else name
# re, error = calculate(names[1], names[0],year) if ' ' in name else calculate(names, None, year)
# print(name+"'s", str(year), "value is {:0.4f} (".format(re)+str(error), 'data points excluded)')
start = time.time()
calc_table = calculate_all(2019, get_player_table())
export_values(calc_table)
print('Done in {} seconds'.format(time.time()-start))
