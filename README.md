# Running the Code
This code was run using [Python 3.6.2](https://www.python.org/downloads/release/python-362/). To generate a value for all MLB pitchers in 2019, use calculate_stat.py (i.e. run `python calculate_stat.py`). This will output the values to values.csv. To generate a matrix of hit probabilities based on launch angle and exit velocity, use scrape_hit_prob.py (i.e. run `python scrape_hit_prob.py`). This will output the values to hit_prob_matrix.csv. To train a neural network that predicts hit probabilities, use hit_dist_neural_net.py (i.e. run `python scrape_iht_prob.py`). This will output the weights of the network to model.h5.
___
# Explanation of Statistic
## Overview
The statistic is the expected change in run expectancy. I use the [pybaseball](https://github.com/jldbc/pybaseball/tree/master/pybaseball) package to get statcast data for each pitch a pitcher threw in a season. The [*Run Expectation*](https://github.com/mccapobianco/pitcher-stat/blob/master/README.md#run-expectation) is calculated before a plate appearance based on the situation (baserunners and outs). Then, the [*Hit Distribution*](https://github.com/mccapobianco/pitcher-stat/blob/master/README.md#hit-distribution) is calculated based on the batted ball (launch angle and exit veolcity). Then, the Run Expectation of each outcome is calculated. This value is multiplied by Outcome Distribution to determine the run expectation after the batted ball. The change is calculated by subtracting the after from the before (delta = before - after; higher values are better because pitchers are trying to minimize runs). The value outputted by this code is the season total of all batters faced for each pitcher.
## Statcast Data
Using pybaseball's pitcher [statcast_pitcher](https://github.com/jldbc/pybaseball/blob/master/pybaseball/statcast_pitcher.py) function, we can get all the statcast data for each pitch that a pitcher threw between two dates. Use year/01/01 and year/12/31/ to get the stats for an entire season (incl. postseason). The statcast_pitcher function takes in a player's MLBAM ID. To get the MLBAM ID for every player who threw a pitch in 2019, join [player_ids.csv](https://github.com/jldbc/pybaseball/blob/master/pybaseball/player_ids.csv) from [CrunchTimeBaseball](http://crunchtimebaseball.com/baseball_map.html) with [player_list.csv](https://github.com/jldbc/pybaseball/blob/master/pybaseball/player_list.csv) from [Baseball Reference](https://www.baseball-reference.com/leagues/MLB/2019-standard-pitching.shtml). Each pitch has 89 values attached to it. The important values for this project are `on_1b`, `on_2b`, `on_3b`, `outs_when_up`, `launch speed`, `launch angle`, and `events`. The `events` field is used to filter out all pitches that did not end a plate appearance. The `on_1b`, `on_2b`, `on_3b`, and `outs_when_up` fields are used for Run Expectation. The `launch_speed` and `launch_angle` are used for Hit Distribution.
## Run Expectation
Run Expectation is calculated using the following run expectation matrix from [Fangraphs](https://library.fangraphs.com/misc/re24/):

| Runners | 0 Outs | 1 Out | 2 Outs |
|---------|--------|-------|--------|
|  Empty  |  0.461 | 0.243 | 0.095  |
|  1 _ _  |  0.831 | 0.489 | 0.214  |
|  _ 2 _  |  1.068 | 0.644 | 0.305  |
|  1 2 _  |  1.373 | 0.908 | 0.343  |
|  _ _ 3  |  1.426 | 0.865 | 0.413  |
|  1 _ 3  |  1.798 | 1.140 | 0.471  |
|  _ 2 3  |  1.920 | 1.352 | 0.570  |
|  1 2 3  |  2.282 | 1.520 | 0.736  |

## Hit Distribution
The Hit Distribution consists of the probabilities of an out, single, double, triple, and home run of a batted ball given the launch angle and exit velocity. First, data is scraped from [Baseball Savant](https://baseballsavant.mlb.com/statcast_hit_probability) using [scrape_hit_prob.py](https://github.com/mccapobianco/pitcher-stat/blob/master/scrape_hit_prob.py) and stored in [hit_prob_matrix.csv](https://github.com/mccapobianco/pitcher-stat/blob/master/hit_prob_matrix.csv). In order to scrape this data from Baseball Savant, each row in the table needs to be clicked in order to expand the table. The script uses Selenium to do this automatically before scraping the webpage. To accommodate for missing data and uncommon events, a neural network is used to predict the probabilities. The neural network is trained by running [hit_dist_neural_net.py](https://github.com/mccapobianco/pitcher-stat/blob/master/hit_dist_neural_net.py). Its weights are then loaded from [model.h5](https://github.com/mccapobianco/pitcher-stat/blob/master/model.h5).
## Future
* Run expectation based on opponent: Currently, the run expectation is based on league averages. However, these values can change based on the upcoming batters and the runners on base. For example, having a more skilled batter in the box or best baserunners on base increases the run expectation. 
* More advanced hit outcomes: Currently, the expected outcome of a hit is that all runners advance the same number of bases as the batter. However, this is often not the case. I would like to be able to predict where the runners would end up. One issue with this is that is depends heavily on the speed and aggressiveness of the baserunners. The intention of this statistic is to evaluate how the pitcher does with an average, or expected, defense. I am unsure if I want the value to be heavily dependent on the baserunners. It seems unfair to reward a pitcher for a hypothetical situation in which an aggressive baserunner runs into an out.