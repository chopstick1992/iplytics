import requests
import json
import os.path
import csv

def master_csv():
    return 'data/master.csv'

def download_scorecard(year, game, redo=False):
    
    fname = 'data/extracts/%d-%02d.json' % (year, game)
        
    if os.path.isfile(fname) and not redo:
        return fname
        
    url = 'http://datacdn.iplt20.com/dynamic/data/core/cricket/2012/ipl%d/ipl%d-%02d/scoring.js' % (year, year, game)
    r = requests.get(url)
    if r.text.startswith('onScoring(') and r.text.endswith(');'):
        content = r.text[10:-2]
        f = open(fname, 'w')
        f.write(content)
        f.close()
        return fname
    return ''

def extract_stats(filename):
    content = json.load(open(filename))
    matchInfo = content['matchInfo']
    common = {
        'year' : int(content['matchId']['tournamentId']['name'][3:]),
        'game' : int(content['matchId']['name'][-2:]),
        'venueID' :  matchInfo['venue']['id'],
        'venueName' : matchInfo['venue']['fullName'],
    }
    
    if matchInfo['matchStatus']['text'] == 'Match abandoned without a ball bowled':
        return []

    players = extract_players(matchInfo['teams'][0],
                              matchInfo['battingOrder'][0])
    players.update(extract_players(matchInfo['teams'][1],
                                   matchInfo['battingOrder'][1]))

    inn1 = extract_innings(content['innings'][0]) 
    inn2 = extract_innings(content['innings'][1])
    
    rows = []
    for playerId in players:
        row = dict(players[playerId], **common)
        row = dict(row, **inn1.get(playerId, {}))
        row = dict(row, **inn2.get(playerId, {}))
        rows.append(row)

    schema = dict.fromkeys(reduce(list.__add__, 
                                  [row.keys() for row in rows]))
    ret = [dict(schema, **row) for row in rows]

    return ret

def extract_players(team, battingOrder):
    ret = {}
    common = {
        'teamID' : team['team']['id'],
        'teamName' : team['team']['abbreviation'],
        'bat_innings' : battingOrder + 1
    }
    
    for player in team['players']:
        ret[player['id']] = {
            'playerID' : player['id'],
            'playerName' : player['shortName'],
        }
        ret[player['id']].update(common)

    return ret

def extract_innings(innings):

    ret = {}
    for bt in innings['scorecard']['battingStats']:
        out = '*'
        if 'mod' in bt: 
            out = bt['mod']['dismissedMethod'] 
        data = {
            'bat_r':bt['r'], 'bat_b':bt['b'],
            'bat_sr':bt.get('sr', None),
            'bat_4s':bt['4s'], 'bat_6s':bt['6s'], 'bat_out':out,
        }
        ret[bt['playerId']] = data
    
    for bl in innings['scorecard']['bowlingStats']:
        data = {
            'bowl_r':bl['r'], 'bowl_w':bl['w'], 'bowl_ov':bl['ov'],
            'bowl_e':bl['e'], 'bowl_nb':bl['nb'], 'bowl_d':bl['d'],
            'bowl_md':bl['maid'], 'bowl_wd':bl['wd']
        }
        ret[bl['playerId']] = data

    return ret

def make_csv(rows):
    mastercsv = master_csv()

    writeHeader = False
    if not os.path.isfile(mastercsv):
        writeHeader = True

    fh = open(mastercsv, 'a')
    csvwriter = csv.writer(fh)
    
    keys = rows[0].keys()
    keys.sort()
    if writeHeader:
        csvwriter.writerow(keys)

    for row in rows:
        row_list = [row[key] for key in keys]
        csvwriter.writerow(row_list)

    fh.close()

def data_exists(year, game):

    mastercsv = master_csv()

    if not os.path.isfile(mastercsv):
        return False

    fh = open(mastercsv)
    csvreader = csv.DictReader(fh)
    count = sum([1 for row in csvreader 
                 if row['year'] == str(year)
                 and row['game'] == str(game)])

    return count == 22

def detl():
    games = {
        2014 : 60,
        2013 : 76,
        2012 : 76
    }
    for year in games:
        for game in range(1, games[year]+1):

            print 'Processing %d %02d' % (year, game)
            
            if data_exists(year, game):
                print('\tData is already loaded\n')
                continue

            print '\tDownloading...',
            f = download_scorecard(year, game)
            print 'done'
            
            print '\tExtracting...',
            rows = extract_stats(f)
            print 'done'

            print '\tTransforming & loading...',
            if len(rows):
                make_csv(rows)
                print 'done'
            else:
                print 'nothing to load, match probably abandoned.'

if __name__ == '__main__':
    detl()
