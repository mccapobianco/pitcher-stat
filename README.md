# Running the code
This code was run using [Python 3.8.0](https://www.python.org/downloads/release/python-380/). To generate a value for all pitchers in 2019, use calculate_stat.py (i.e. run `python calculate_stat.py`). This will output the values to values.csv. To generate a matrix of hit probabilities based on launch angle and exit velocity, use scrape_hit_prob.py (i.e. run `python scrape_hit_prob.py`). This will output the values to hit_prob_matrix.csv.
___
# Explanation of statistic
## Overview
The statistic is the expected change in run expectancy. The expected number of runs is calculated before the plate appearance based on the situation (baserunners and outs). Then, the distribution of outcomes is calculated based on the batted ball (launch angle and exit veolcity). Then, the run expectation of each outcome is calculated. This value is multiplied by distribution of outcomes to determine the run expectation after the batted ball. The change is calculated by subtracting the after from the before (delta = before - after; higher values are better because pitchers are trying to minimize runs). The value outputted by this code is the season total of all batters faced for each pitcher. 
## Run expectation
Run expectation is calculated using the following run expectation matrix from [Fangraphs](https://library.fangraphs.com/misc/re24/):

| Runners | 0 Outs | 1 Out | 2 Outs |
|---|---|---|---|
| Empty | 0.461 | 0.243 | 0.095 |
| 1 | 0.831 | 0.489 | 0.214 |
| 2 | 1.068 | 0.644 | 0.305 |
| 1 2 | 1.373 | 0.908 | 0.343 |
| 3 | 1.426 | 0.865 | 0.413 |
| 1 3 | 1.798 | 1.140 | 0.471 |
| 2 3 | 1.920 | 1.352 | 0.570 |
| 1 2 3 | 2.282 | 1.520 | 0.736 |

## Hit probability
The hit distribution is calculated using a matrix stored in [hit_prob_matrix.csv](https://github.com/mccapobianco/pitcher-stat/blob/master/hit_prob_matrix.csv). This matrix is generated by [scrape_hit_prob.py](https://github.com/mccapobianco/pitcher-stat/blob/master/scrape_hit_prob.py) using data from [Baseball Savant](https://baseballsavant.mlb.com/statcast_hit_probability). In order to scrape this data from Baseball Savant, each row in the table needs to be clicked in order to expand the table. The script uses Selenium to do this automatically before scraping the webpage. The cells in the matrix are either filled with a tuple or is empty (an empty value means that no balls were hit with that angle and velocity). The tuple has 5 integer values: occurences, singles, doubles, triples, and homeruns (respectively).
## Future
This code is still a work in progress. Future ideas to improve this code include the following:
* Machine learning for hit probability: Some angle/velocity combinations do not appear in the hit probability matrix, but appear in the statcast pitch data. I do not know why this happens, but I would guess that there in a difference in rounding in the two places from where I retrieve my data. Currently these plate appearances are omitted. There are also some angle/velocity combinations with very few occurences. Small sample sizes can affect the data. For example, an angle/velocity combination that would result in an out 99 times out of 100 only occured one time and resulted in a hit. Instead of a hit probability of 1%, the small sample size results in a hit probability of 100%. Since these do not occur often, this should not have a major affect on the value. To correct these issues, I can use a machine learning algorithm to predict the distribution of outcomes.
* Run expectation based on opponent: Currently, the run expectation is based on league averages. However, these values can change based on the upcoming batters and the runners on base. For example, having a more skilled batter in the box increases the run expectation. 
* More advanced hit outcomes: Currently, the expected outcome of a hit is that all runners advance the same number of bases as the batter. However, this is often not the case. I would like to be able to predict where the runners would end up. One issue with this is that is depends heavily on the speed and aggressiveness of the baserunners. The intention of this statistic is to evaluate how the pitcher does with an average, or expected, defense. I am unsure if I want the value to be heavily dependent on the baserunners. It seems unfair to reward a pitcher for a hypothetical situation in which an aggressive baserunner runs into an out.