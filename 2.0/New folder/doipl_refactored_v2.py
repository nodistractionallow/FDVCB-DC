import os
import sys
import random
from mainconnect import game
from tabulate import tabulate
import copy

# Ensure scores directory exists
dir_path = os.path.join(os.getcwd(), "scores")
os.makedirs(dir_path, exist_ok=True)

# Clean scores folder before starting
for f in os.listdir(dir_path):
    os.remove(os.path.join(dir_path, f))

TEAMS = ['dc', 'csk', 'rcb', 'mi', 'kkr', 'pbks', 'rr', 'srh']

battingf = 0 # Will be refactored/removed
bowlingf = 0 # Will be refactored/removed

def initialize_tournament_data(team_list_arg):
    points_data = {}
    battingInfo_data = {}
    bowlingInfo_data = {}
    for team_key_func in team_list_arg:
        points_data[team_key_func] = {
            "P": 0, "W": 0, "L": 0, "T": 0, "SO": 0,
            "runsScored": 0, "ballsFaced": 0,
            "runsConceded": 0, "ballsBowled": 0,
            "pts": 0
        }
    return points_data, battingInfo_data, bowlingInfo_data

def generate_league_schedule(team_list_arg): # NEW FUNCTION for Step 2
    all_possible_matches = []
    for i_team_idx in range(len(team_list_arg)):
        for j_team_idx in range(i_team_idx + 1, len(team_list_arg)):
            all_possible_matches.append((team_list_arg[i_team_idx], team_list_arg[j_team_idx]))

    random.shuffle(all_possible_matches)

    scheduled_matches_final = []
    teams_in_last_scheduled_match = set()
    match_pool_copy = list(all_possible_matches)

    while len(scheduled_matches_final) < len(all_possible_matches):
        found_this_slot = False
        best_match_found = None
        candidate_match_idx_to_pop = -1
        for candidate_idx, candidate_match in enumerate(match_pool_copy):
            teamA, teamB = candidate_match
            if teamA not in teams_in_last_scheduled_match and teamB not in teams_in_last_scheduled_match:
                best_match_found = candidate_match
                candidate_match_idx_to_pop = candidate_idx
                found_this_slot = True
                break
        if found_this_slot and best_match_found is not None:
            match_pool_copy.pop(candidate_match_idx_to_pop)
        elif not found_this_slot:
            if match_pool_copy:
                best_match_found = match_pool_copy.pop(0)
            else:
                # This condition implies the pool is empty but not all matches scheduled.
                # This can happen if the last remaining matches all involve teams that played the previous match.
                # The original code had a bug here; if match_pool_copy is empty, this loop should terminate.
                break

        if best_match_found:
            scheduled_matches_final.append(best_match_found)
            teams_in_last_scheduled_match = {best_match_found[0], best_match_found[1]}
        elif not match_pool_copy and len(scheduled_matches_final) < len(all_possible_matches):
            # This specific error print might be too strong if the above break handles it.
            # print("Error: Match pool empty but not all matches scheduled. Breaking.")
            break # Break if no match found and pool is empty.

    matches_with_rain_chance = set()
    if scheduled_matches_final:
        num_rain_matches = random.randint(1, 3)
        num_rain_matches = min(num_rain_matches, len(scheduled_matches_final))
        if num_rain_matches > 0:
            sample_count = min(num_rain_matches, len(scheduled_matches_final))
            if sample_count > 0:
                 rain_match_indices = random.sample(range(len(scheduled_matches_final)), sample_count)
                 for index in rain_match_indices:
                    matches_with_rain_chance.add(scheduled_matches_final[index])

    return scheduled_matches_final, matches_with_rain_chance

# Enhanced commentary lines for different events
commentary_lines = {
    'start': ["It's a packed stadium today, folks! The atmosphere is electric!", "The players are ready, and the crowd is roaring for action!", "What a perfect day for some thrilling cricket!"],
    '0': ["Good ball! Dot ball, no run scored.", "Tight bowling, the batsman defends solidly.", "No run, excellent line and length from the bowler!"],
    '1': ["Quick single taken, good running between the wickets!", "Pushed for a single, smart cricket.", "One run added to the total, tidy shot."],
    '2': ["Nicely placed for a couple of runs!", "Two runs, good placement in the gap.", "Driven for two, excellent running!"],
    '3': ["Three runs! Brilliant effort in the field to stop the boundary.", "Rare three runs, well-judged by the batsmen.", "Three to the total, superb running!"],
    '4': ["FOUR! Cracked through the covers, what a shot!", "Boundary! Perfectly timed, races to the fence.", "FOUR runs! That’s a glorious cover drive!"],
    '6': ["SIX! Launched over the stands, what a hit!", "Huge SIX! That’s gone miles into the crowd!", "Maximum! Smashed with authority!"],
    'wicket': {
        'caught': ["Caught! Edged and taken!", "Caught! Simple catch for the fielder.", "Caught! What a grab! That was flying!", "Caught! The batsman walks, a good take in the field."],
        'bowled': ["Bowled him! Right through the gate!", "Bowled! Timber! The stumps are a mess!", "Bowled! Cleaned him up, no answer to that delivery!"],
        'lbw': ["LBW! That looked plumb! The umpire raises the finger.", "LBW! Trapped in front, that's got to be out!", "LBW! He's given him. Looked like it was hitting the stumps."],
        'runOut': ["Run out! Terrible mix-up, and he's short of his ground!", "Run out! Direct hit! What a piece of fielding!", "Run out! They went for a risky single, and paid the price."],
        'stumped': ["Stumped! Quick work by the keeper, he was out of his crease!", "Stumped! Fooled by the flight, and the bails are off in a flash.", "Stumped! Great take and stumping by the wicketkeeper."],
        'hitwicket': ["Hit wicket! Oh dear, he's knocked his own bails off!", "Hit wicket! What a bizarre way to get out!", "Hit wicket! He's dislodged the bails with his bat/body."],
        'general': ["OUT! That's a big wicket for the bowling side!", "WICKET! The batsman has to depart.", "GONE! A crucial breakthrough for the bowlers."]},
    'wide': ["Wide ball! The bowler strays down the leg side.", "Called wide, too far outside off stump.", "Extra run! Wide from the bowler."],
    'end': ["What a match that was, folks! A true spectacle!", "The crowd is buzzing after that thrilling finish!", "A game to remember for years to come!"],
    'innings_end': ["That’s the end of the innings. A solid total on the board!", "Innings wrapped up, setting up an exciting chase!", "End of the batting effort, now over to the bowlers!"],
    'no_ball_call': ["No Ball! The bowler has overstepped. Free hit coming up!", "That's a No Ball! An extra run and a free hit.", "No Ball called by the umpire. The next delivery is a free hit."],
    'free_hit_delivery': ["Free Hit delivery!", "Here comes the Free Hit...", "Batsman has a free license on this Free Hit!"],
    'no_ball_runs': ["And runs scored off the No Ball! Adding insult to injury.", "They pick up runs on the No Ball as well!", "The batsman cashes in on the No Ball delivery!"],
    'extras': {
        'B': ["Byes signalled! They sneak a single as the keeper misses.", "That's byes, well run by the batsmen.", "A bye taken as the ball evades everyone."],
        'LB': ["Leg Byes! Off the pads and they run.", "Signalled as Leg Byes by the umpire.", "They get leg-byes for that deflection."]}
}

def display_points_table(points_arg):
    pointsTabulate = []
    for team_key in points_arg:
        data = points_arg[team_key]
        nrr = 0
        if data['ballsFaced'] > 0 and data['ballsBowled'] > 0:
            nrr = (data['runsScored'] / data['ballsFaced']) * 6 - (data['runsConceded'] / data['ballsBowled']) * 6
        row = [team_key.upper(), data['P'], data['W'], data['L'], data['T'], data['SO'], round(nrr, 2), data['pts']]
        pointsTabulate.append(row)
    pointsTabulate = sorted(pointsTabulate, key=lambda x: (x[7], x[6]), reverse=True)
    print("\nCurrent Points Table:")
    print(tabulate(pointsTabulate, headers=["Team", "Played", "Won", "Lost", "Tied", "SO", "NRR", "Points"], tablefmt="grid"))

def display_top_players(battingInfo_arg, bowlingInfo_arg):
    battingTabulate = []
    for b in battingInfo_arg:
        c = battingInfo_arg[b]
        outs = sum(1 for bl in c['ballLog'] if "W" in bl)
        avg = round(c['runs'] / outs, 2) if outs else float('inf')
        sr = round((c['runs'] / c['balls']) * 100, 2) if c['balls'] else 0
        battingTabulate.append([b, c['runs'], avg, sr])
    battingTabulate = sorted(battingTabulate, key=lambda x: x[1], reverse=True)[:3]
    print("\nTop 3 Batsmen:")
    print(tabulate(battingTabulate, headers=["Player", "Runs", "Average", "Strike Rate"], tablefmt="grid"))
    bowlingTabulate = []
    for b in bowlingInfo_arg:
        c = bowlingInfo_arg[b]
        economy = round((c['runs'] / c['balls']) * 6, 2) if c['balls'] else float('inf')
        bowlingTabulate.append([b, c['wickets'], economy])
    bowlingTabulate = sorted(bowlingTabulate, key=lambda x: x[1], reverse=True)[:3]
    print("\nTop 3 Bowlers:")
    print(tabulate(bowlingTabulate, headers=["Player", "Wickets", "Economy"], tablefmt="grid"))

def display_scorecard(bat_tracker, bowl_tracker, team_name, innings_num):
    print(f"\n--- {team_name.upper()} Scorecard: Innings {innings_num} ---")
    batsmanTabulate = []
    for player_name_key in bat_tracker:
        data = bat_tracker[player_name_key]
        runs_scored = data['runs']
        balls_faced = data['balls']
        how_out_status = data.get('how_out_string', 'DNB')
        sr_val = 'NA'
        if balls_faced > 0: sr_val = round((runs_scored / balls_faced) * 100, 2)
        elif how_out_status not in ['DNB', 'Did Not Bat']: sr_val = '-'
        batsmanTabulate.append([player_name_key, runs_scored, balls_faced, sr_val, how_out_status])
    print("\nBatting:")
    print(tabulate(batsmanTabulate, headers=["Player", "Runs", "Balls", "SR", "How Out"], tablefmt="grid"))
    bowlerTabulate = []
    for player in bowl_tracker:
        data = bowl_tracker[player]
        runs_conceded = data['runs']
        balls_bowled = data['balls']
        wickets_taken = data['wickets']
        noballs_bowled = data.get('noballs', 0)
        overs_str = f"{balls_bowled // 6}.{balls_bowled % 6}" if balls_bowled else "0.0"
        economy_rate = round((runs_conceded / balls_bowled) * 6, 2) if balls_bowled else 'NA'
        bowlerTabulate.append([player, overs_str, runs_conceded, wickets_taken, noballs_bowled, economy_rate])
    print("\nBowling:")
    print(tabulate(bowlerTabulate, headers=["Player", "Overs", "Runs", "Wickets", "NB", "Economy"], tablefmt="grid"))

def display_ball_by_ball(innings_log, innings_num, team_name, runs, balls, wickets, bat_tracker, bowl_tracker):
    print(f"\n--- Innings {innings_num}: {team_name} Batting ---")
    i=0
    while i < len(innings_log):
        event_data = innings_log[i]; event_text = event_data['event']; commentary = ""
        event_type = event_data.get('type'); original_event_type = event_data.get('original_event_type')
        is_fh_delivery = event_data.get('is_free_hit_delivery', False); extras_type = event_data.get('extras_type')
        runs_this_ball_current_event = event_data.get('runs_this_ball', 0); consolidated_nb_commentary = False
        no_ball_suffix = random.choice(commentary_lines['no_ball_call']).split('.')[1].strip()
        if event_type == "NO_BALL_CALL":
            total_nb_runs = 1
            if i + 1 < len(innings_log):
                next_event_data = innings_log[i+1]
                if next_event_data.get('original_event_type') == "NB" and next_event_data.get('is_free_hit_delivery'):
                    runs_off_nb_delivery = next_event_data.get('runs_this_ball', 0); total_nb_runs += runs_off_nb_delivery
                    event_text = next_event_data['event']; commentary = f"Nb ({total_nb_runs})! {no_ball_suffix}"; i += 1; consolidated_nb_commentary = True
            if not consolidated_nb_commentary: commentary = f"Nb (1)! {no_ball_suffix}"
        elif event_type == "WIDE": commentary = random.choice(commentary_lines['wide'])
        elif event_type == "EXTRAS" and extras_type in commentary_lines['extras']:
            actual_extras_runs = event_data.get('runs_off_extras', runs_this_ball_current_event)
            base_commentary = random.choice(commentary_lines['extras'][extras_type])
            if actual_extras_runs > 0: base_commentary += f" {actual_extras_runs} run{'s' if actual_extras_runs > 1 else ''}."
            commentary = base_commentary
        else:
            out_type = event_data.get('out_type'); is_not_out_on_fh = event_data.get('is_dismissal') == False and is_fh_delivery
            base_commentary = ""; outcome_runs_str = str(runs_this_ball_current_event)
            if out_type and not is_not_out_on_fh:
                if out_type in commentary_lines['wicket']: base_commentary = random.choice(commentary_lines['wicket'][out_type])
                else: base_commentary = random.choice(commentary_lines['wicket']['general']) + f" ({out_type})"
            elif is_not_out_on_fh:
                run_commentary = random.choice(commentary_lines.get(outcome_runs_str, commentary_lines['0']))
                base_commentary = f"Phew! {run_commentary} (Not out on Free Hit!)"
            else: base_commentary = random.choice(commentary_lines.get(outcome_runs_str, commentary_lines['0']))
            if is_fh_delivery and not consolidated_nb_commentary : commentary = random.choice(commentary_lines['free_hit_delivery']) + " " + base_commentary
            else: commentary = base_commentary
        print(f"Ball {event_data.get('balls', 'N/A')}: {event_text} - {commentary}"); i += 1
    overs = f"{balls // 6}.{balls % 6}"; print(f"\nInnings Total: {runs}/{wickets} in {overs} overs")
    print(random.choice(commentary_lines['innings_end'])); display_scorecard(bat_tracker, bowl_tracker, team_name, innings_num)

def playoffs(team1, team2, matchtag, current_batting_info, current_bowling_info):
    print(f"\n{matchtag.upper()} - {team1.upper()} vs {team2.upper()}")
    try:
        input("Press Enter to start the playoff match...")
        print(random.choice(commentary_lines['start']))
        res = game(False, team1.lower(), team2.lower(), matchtag)
        for innings, team_key, runs_key, balls_key, bat_tracker_key, bowl_tracker_key in [
            ('innings1Log', 'innings1BatTeam', 'innings1Runs', 'innings1Balls', 'innings1Battracker', 'innings1Bowltracker'),
            ('innings2Log', 'innings2BatTeam', 'innings2Runs', 'innings2Balls', 'innings2Battracker', 'innings2Bowltracker')]:
            display_ball_by_ball(res[innings], 1 if innings == 'innings1Log' else 2, res[team_key], res[runs_key], res[balls_key], max([event['wickets'] for event in res[innings]], default=0), res[bat_tracker_key], res[bowl_tracker_key])
        if res.get('superOverPlayed', False) and res.get('superOverDetails'):
            print("--- Super Over Details ---"); [print(detail) for detail in res['superOverDetails']]; print("-------------------------")
        print(f"\nResult: {res['winMsg'].upper()}"); print(random.choice(commentary_lines['end']))
        winner = res['winner']; loser = team1 if winner == team2 else team2
        for bat_map in ['innings1Battracker', 'innings2Battracker']:
            tracker = res[bat_map]
            for player in tracker:
                if player not in current_batting_info:
                    current_batting_info[player] = copy.deepcopy(tracker[player]); current_batting_info[player]['innings'] = 1; current_batting_info[player]['scoresArray'] = [int(tracker[player]['runs'])]
                else:
                    current_batting_info[player]['balls'] += tracker[player]['balls']; current_batting_info[player]['runs'] += tracker[player]['runs']
                    current_batting_info[player]['ballLog'] += tracker[player]['ballLog']; current_batting_info[player]['innings'] += 1; current_batting_info[player]['scoresArray'].append(int(tracker[player]['runs']))
        for bowl_map in ['innings1Bowltracker', 'innings2Bowltracker']:
            tracker = res[bowl_map]
            for player in tracker:
                if player not in current_bowling_info:
                    current_bowling_info[player] = copy.deepcopy(tracker[player]); current_bowling_info[player]['matches'] = 1
                else:
                    current_bowling_info[player]['balls'] += tracker[player]['balls']; current_bowling_info[player]['runs'] += tracker[player]['runs']
                    current_bowling_info[player]['ballLog'] += tracker[player]['ballLog']; current_bowling_info[player]['wickets'] += tracker[player]['wickets']
                    current_bowling_info[player]['noballs'] = current_bowling_info[player].get('noballs', 0) + tracker[player].get('noballs', 0); current_bowling_info[player]['matches'] += 1
        input("Press Enter to continue...")
        return winner, loser, current_batting_info, current_bowling_info
    except Exception as e:
        print(f"Error during {matchtag.upper()}: {str(e)}"); input("Press Enter to continue or Ctrl+C to exit...")
        return team1, team2, current_batting_info, current_bowling_info

if __name__ == "__main__":
    points, battingInfo, bowlingInfo = initialize_tournament_data(TEAMS)

    # MODIFIED: Call generate_league_schedule
    scheduled_matches_final, matches_with_rain_chance = generate_league_schedule(TEAMS)

    for team1, team2 in scheduled_matches_final:
        current_match_tuple = (team1, team2)
        rain_expected_for_this_match = current_match_tuple in matches_with_rain_chance
        print(f"\nMatch: {team1.upper()} vs {team2.upper()}")
        try:
            input("Press Enter to start the match...")
            print(random.choice(commentary_lines['start']))
            resList = game(False, team1, team2) # Assuming game() is okay for now
            for innings, team_key, runs_key, balls_key, bat_tracker_key, bowl_tracker_key in [
                ('innings1Log', 'innings1BatTeam', 'innings1Runs', 'innings1Balls', 'innings1Battracker', 'innings1Bowltracker'),
                ('innings2Log', 'innings2BatTeam', 'innings2Runs', 'innings2Balls', 'innings2Battracker', 'innings2Bowltracker')]:
                display_ball_by_ball(resList[innings], 1 if innings == 'innings1Log' else 2, resList[team_key], resList[runs_key], resList[balls_key], max([event['wickets'] for event in resList[innings]], default=0), resList[bat_tracker_key], resList[bowl_tracker_key])
            if resList.get('superOverPlayed', False) and resList.get('superOverDetails'):
                print("--- Super Over Details ---"); [print(detail) for detail in resList['superOverDetails']]; print("-------------------------")
            print(f"\nResult: {resList['winMsg']}"); print(random.choice(commentary_lines['end']))
            if "runs" in resList['winMsg']: battingf += 1
            else: bowlingf += 1
            for bat_map in [('innings1Battracker', 'innings1BatTeam'), ('innings2Battracker', 'innings2BatTeam')]:
                bat_tracker = resList[bat_map[0]]
                for player in bat_tracker:
                    if player not in battingInfo: battingInfo[player] = copy.deepcopy(bat_tracker[player]); battingInfo[player]['innings'] = 1; battingInfo[player]['scoresArray'] = [int(battingInfo[player]['runs'])]
                    else: battingInfo[player]['balls'] += bat_tracker[player]['balls']; battingInfo[player]['runs'] += bat_tracker[player]['runs']; battingInfo[player]['ballLog'] += bat_tracker[player]['ballLog']; battingInfo[player]['innings'] += 1; battingInfo[player]['scoresArray'].append(int(bat_tracker[player]['runs']))
            for bowl_map in [('innings1Bowltracker',), ('innings2Bowltracker',)]:
                bowl_tracker = resList[bowl_map[0]]
                for player in bowl_tracker:
                    if player not in bowlingInfo: bowlingInfo[player] = copy.deepcopy(bowl_tracker[player]); bowlingInfo[player]['matches'] = 1
                    else: bowlingInfo[player]['balls'] += bowl_tracker[player]['balls']; bowlingInfo[player]['runs'] += bowl_tracker[player]['runs']; bowlingInfo[player]['ballLog'] += bowl_tracker[player]['ballLog']; bowlingInfo[player]['wickets'] += bowl_tracker[player]['wickets']; bowlingInfo[player]['noballs'] = bowlingInfo[player].get('noballs', 0) + bowl_tracker[player].get('noballs', 0); bowlingInfo[player]['matches'] += 1
            teamA_actual = resList['innings1BatTeam']; teamB_actual = resList['innings2BatTeam']
            if resList.get('superOverPlayed', False):
                if teamA_actual in points: points[teamA_actual]['SO'] += 1
                if teamB_actual in points: points[teamB_actual]['SO'] += 1
            winner_status = resList.get('winner')
            points[team1]['P'] += 1; points[team2]['P'] += 1
            if resList.get('superOverPlayed', False): # This SO logic might need review based on actual game rules for SO points/NRR
                teamA_actual_for_so = resList.get('innings1BatTeam'); teamB_actual_for_so = resList.get('innings2BatTeam')
                if teamA_actual_for_so and teamB_actual_for_so:
                     if teamA_actual_for_so in points: points[teamA_actual_for_so]['SO'] += 1
                     if teamB_actual_for_so in points: points[teamB_actual_for_so]['SO'] += 1
                elif team1 in points and team2 in points: points[team1]['SO'] +=1; points[team2]['SO'] +=1
            if winner_status == "cancelled":
                points[team1]['T'] += 1; points[team2]['T'] += 1; points[team1]['pts'] += 1; points[team2]['pts'] += 1
                print(f"Match {team1.upper()} vs {team2.upper()} cancelled. Points shared.")
            elif winner_status == "tie":
                teamA_actual = resList['innings1BatTeam']; teamB_actual = resList['innings2BatTeam']
                teamARuns, teamABalls = resList['innings1Runs'], resList['innings1Balls']; teamBRuns, teamBBalls = resList['innings2Runs'], resList['innings2Balls']
                points[teamA_actual]['T'] += 1; points[teamB_actual]['T'] += 1; points[teamA_actual]['pts'] += 1; points[teamB_actual]['pts'] += 1
                points[teamA_actual]['runsScored'] += teamARuns; points[teamB_actual]['runsScored'] += teamBRuns
                points[teamA_actual]['runsConceded'] += teamBRuns; points[teamB_actual]['runsConceded'] += teamARuns
                points[teamA_actual]['ballsFaced'] += teamABalls; points[teamB_actual]['ballsFaced'] += teamBBalls
                points[teamA_actual]['ballsBowled'] += teamBBalls; points[teamB_actual]['ballsBowled'] += teamABalls
            else:
                teamA_actual = resList['innings1BatTeam']; teamB_actual = resList['innings2BatTeam']
                teamARuns, teamABalls = resList['innings1Runs'], resList['innings1Balls']; teamBRuns, teamBBalls = resList['innings2Runs'], resList['innings2Balls']
                loser = team1 if winner_status == team2 else team2
                if winner_status in points: points[winner_status]['W'] += 1; points[winner_status]['pts'] += 2
                if loser in points: points[loser]['L'] += 1
                points[teamA_actual]['runsScored'] += teamARuns; points[teamB_actual]['runsScored'] += teamBRuns
                points[teamA_actual]['runsConceded'] += teamBRuns; points[teamB_actual]['runsConceded'] += teamARuns
                points[teamA_actual]['ballsFaced'] += teamABalls; points[teamB_actual]['ballsFaced'] += teamBBalls
                points[teamA_actual]['ballsBowled'] += teamBBalls; points[teamB_actual]['ballsBowled'] += teamABalls
            display_points_table(points); display_top_players(battingInfo, bowlingInfo)
            input("Press Enter to continue to the next match...")
        except Exception as e:
            print(f"Error during match {team1.upper()} vs {team2.upper()}: {str(e)}"); input("Press Enter to continue or Ctrl+C to exit...")
            continue
    display_points_table(points)
    points_for_playoff_ranking = []
    for team_name_key in TEAMS:
        team_data = points[team_name_key]
        nrr_val = 0
        if team_data['ballsFaced'] > 0 and team_data['ballsBowled'] > 0: nrr_val = (team_data['runsScored'] / team_data['ballsFaced']) * 6 - (team_data['runsConceded'] / team_data['ballsBowled']) * 6
        elif team_data['ballsFaced'] > 0: nrr_val = (team_data['runsScored'] / team_data['ballsFaced']) * 6
        elif team_data['ballsBowled'] > 0: nrr_val = - (team_data['runsConceded'] / team_data['ballsBowled']) * 6
        points_for_playoff_ranking.append([team_name_key, team_data['pts'], nrr_val])
    pointsTabulate = sorted(points_for_playoff_ranking, key=lambda x: (x[1], x[2]), reverse=True)
    if len(pointsTabulate) >= 4:
        q1 = [pointsTabulate[0][0], pointsTabulate[1][0]]; elim = [pointsTabulate[2][0], pointsTabulate[3][0]]; finalists = []
        winnerQ1, loserQ1, battingInfo, bowlingInfo = playoffs(q1[0], q1[1], "Qualifier 1", battingInfo, bowlingInfo); finalists.append(winnerQ1)
        winnerElim, _, battingInfo, bowlingInfo = playoffs(elim[0], elim[1], "Eliminator", battingInfo, bowlingInfo)
        winnerQ2, _, battingInfo, bowlingInfo = playoffs(winnerElim, loserQ1, "Qualifier 2", battingInfo, bowlingInfo); finalists.append(winnerQ2)
        if len(finalists) == 2:
            finalWinner, _, battingInfo, bowlingInfo = playoffs(finalists[0], finalists[1], "Final", battingInfo, bowlingInfo)
            print(f"\n🏆 {finalWinner.upper()} WINS THE IPL!!!")
        else: print("Could not determine two finalists for the Final match.")
    else: print("Not enough teams qualified for playoffs.")
    battingTabulate = []
    for b in battingInfo:
        c = battingInfo[b]; outs = sum(1 for bl in c['ballLog'] if "W" in bl); avg = round(c['runs'] / outs, 2) if outs else "NA"; sr = round((c['runs'] / c['balls']) * 100, 2) if c['balls'] else "NA"
        battingTabulate.append([b, c['innings'], c['runs'], avg, max(c['scoresArray']), sr, c['balls']])
    battingTabulate = sorted(battingTabulate, key=lambda x: x[2], reverse=True)
    bowlingTabulate = []
    for b in bowlingInfo:
        c = bowlingInfo[b]; overs = f"{c['balls'] // 6}.{c['balls'] % 6}" if c['balls'] else "0"; economy = round((c['runs'] / c['balls']) * 6, 2) if c['balls'] else "NA"; noballs = c.get('noballs', 0)
        bowlingTabulate.append([b, c['wickets'], overs, c['runs'], noballs, economy])
    bowlingTabulate = sorted(bowlingTabulate, key=lambda x: x[1], reverse=True)
    with open(os.path.join(dir_path, "batStats.txt"), "w") as f: sys.stdout = f; print(tabulate(battingTabulate, headers=["Player", "Innings", "Runs", "Average", "Highest", "SR", "Balls"], tablefmt="grid")); sys.stdout = sys.__stdout__
    with open(os.path.join(dir_path, "bowlStats.txt"), "w") as f: sys.stdout = f; print(tabulate(bowlingTabulate, headers=["Player", "Wickets", "Overs", "Runs Conceded", "NB", "Economy"], tablefmt="grid")); sys.stdout = sys.__stdout__
    print("bat", battingf, "bowl", bowlingf)
    input("\nPress Enter to exit...")
else:
    pass
