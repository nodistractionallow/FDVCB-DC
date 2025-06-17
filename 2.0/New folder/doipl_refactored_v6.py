import os
import sys
import random
from mainconnect import game # Assuming mainconnect.game is appropriately modified or its side effects handled
from tabulate import tabulate # Will be removed if no direct printing uses it
import copy

# dir_path and its cleaning will be handled by the main web application or not at all.
# For now, keeping it for CLI execution of this refactored script.
dir_path = os.path.join(os.getcwd(), "scores")
os.makedirs(dir_path, exist_ok=True)
# Clean scores folder before starting - this should be removed for web integration if mainconnect.game stops writing files.
for f in os.listdir(dir_path):
    os.remove(os.path.join(dir_path, f))

TEAMS = ['dc', 'csk', 'rcb', 'mi', 'kkr', 'pbks', 'rr', 'srh']

# These global trackers are for a specific stat not requested for web, will be removed.
battingf = 0
bowlingf = 0

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

def generate_league_schedule(team_list_arg):
    all_possible_matches = []
    for i_team_idx in range(len(team_list_arg)):
        for j_team_idx in range(i_team_idx + 1, len(team_list_arg)):
            all_possible_matches.append((team_list_arg[i_team_idx], team_list_arg[j_team_idx]))
    random.shuffle(all_possible_matches)
    scheduled_matches_final = []
    teams_in_last_scheduled_match = set()
    match_pool_copy = list(all_possible_matches)
    while len(scheduled_matches_final) < len(all_possible_matches):
        found_this_slot = False; best_match_found = None; candidate_match_idx_to_pop = -1
        for candidate_idx, candidate_match in enumerate(match_pool_copy):
            teamA, teamB = candidate_match
            if teamA not in teams_in_last_scheduled_match and teamB not in teams_in_last_scheduled_match:
                best_match_found = candidate_match; candidate_match_idx_to_pop = candidate_idx; found_this_slot = True; break
        if found_this_slot and best_match_found is not None: match_pool_copy.pop(candidate_match_idx_to_pop)
        elif not found_this_slot:
            if match_pool_copy: best_match_found = match_pool_copy.pop(0)
            else: break
        if best_match_found: scheduled_matches_final.append(best_match_found); teams_in_last_scheduled_match = {best_match_found[0], best_match_found[1]}
        elif not match_pool_copy and len(scheduled_matches_final) < len(all_possible_matches): break
    matches_with_rain_chance = set()
    if scheduled_matches_final:
        num_rain_matches = random.randint(1, 3); num_rain_matches = min(num_rain_matches, len(scheduled_matches_final))
        if num_rain_matches > 0:
            sample_count = min(num_rain_matches, len(scheduled_matches_final))
            if sample_count > 0:
                 rain_match_indices = random.sample(range(len(scheduled_matches_final)), sample_count)
                 for index in rain_match_indices: matches_with_rain_chance.add(scheduled_matches_final[index])
    return scheduled_matches_final, matches_with_rain_chance

commentary_lines = { # This could be loaded from an external JSON/config if it grows larger
    'start': ["It's a packed stadium today, folks! The atmosphere is electric!", "The players are ready, and the crowd is roaring for action!", "What a perfect day for some thrilling cricket!"],
    '0': ["Good ball! Dot ball, no run scored.", "Tight bowling, the batsman defends solidly.", "No run, excellent line and length from the bowler!"],
    '1': ["Quick single taken, good running between the wickets!", "Pushed for a single, smart cricket.", "One run added to the total, tidy shot."],
    '2': ["Nicely placed for a couple of runs!", "Two runs, good placement in the gap.", "Driven for two, excellent running!"],
    '3': ["Three runs! Brilliant effort in the field to stop the boundary.", "Rare three runs, well-judged by the batsmen.", "Three to the total, superb running!"],
    '4': ["FOUR! Cracked through the covers, what a shot!", "Boundary! Perfectly timed, races to the fence.", "FOUR runs! That’s a glorious cover drive!"],
    '6': ["SIX! Launched over the stands, what a hit!", "Huge SIX! That’s gone miles into the crowd!", "Maximum! Smashed with authority!"],
    'wicket': {'caught': ["Caught! Edged and taken!", "Caught! Simple catch for the fielder.", "Caught! What a grab! That was flying!", "Caught! The batsman walks, a good take in the field."], 'bowled': ["Bowled him! Right through the gate!", "Bowled! Timber! The stumps are a mess!", "Bowled! Cleaned him up, no answer to that delivery!"], 'lbw': ["LBW! That looked plumb! The umpire raises the finger.", "LBW! Trapped in front, that's got to be out!", "LBW! He's given him. Looked like it was hitting the stumps."], 'runOut': ["Run out! Terrible mix-up, and he's short of his ground!", "Run out! Direct hit! What a piece of fielding!", "Run out! They went for a risky single, and paid the price."], 'stumped': ["Stumped! Quick work by the keeper, he was out of his crease!", "Stumped! Fooled by the flight, and the bails are off in a flash.", "Stumped! Great take and stumping by the wicketkeeper."], 'hitwicket': ["Hit wicket! Oh dear, he's knocked his own bails off!", "Hit wicket! What a bizarre way to get out!", "Hit wicket! He's dislodged the bails with his bat/body."], 'general': ["OUT! That's a big wicket for the bowling side!", "WICKET! The batsman has to depart.", "GONE! A crucial breakthrough for the bowlers."]},
    'wide': ["Wide ball! The bowler strays down the leg side.", "Called wide, too far outside off stump.", "Extra run! Wide from the bowler."],
    'end': ["What a match that was, folks! A true spectacle!", "The crowd is buzzing after that thrilling finish!", "A game to remember for years to come!"],
    'innings_end': ["That’s the end of the innings. A solid total on the board!", "Innings wrapped up, setting up an exciting chase!", "End of the batting effort, now over to the bowlers!"],
    'no_ball_call': ["No Ball! The bowler has overstepped. Free hit coming up!", "That's a No Ball! An extra run and a free hit.", "No Ball called by the umpire. The next delivery is a free hit."],
    'free_hit_delivery': ["Free Hit delivery!", "Here comes the Free Hit...", "Batsman has a free license on this Free Hit!"],
    'no_ball_runs': ["And runs scored off the No Ball! Adding insult to injury.", "They pick up runs on the No Ball as well!", "The batsman cashes in on the No Ball delivery!"],
    'extras': {'B': ["Byes signalled! They sneak a single as the keeper misses.", "That's byes, well run by the batsmen.", "A bye taken as the ball evades everyone."], 'LB': ["Leg Byes! Off the pads and they run.", "Signalled as Leg Byes by the umpire.", "They get leg-byes for that deflection."]}
}

def get_points_table(points_data, team_list_arg):
    points_table_data = []
    for team_key in team_list_arg:
        data = points_data.get(team_key)
        if not data: continue
        nrr = 0
        if data['ballsFaced'] > 0 and data['ballsBowled'] > 0:
            nrr = (data['runsScored'] / data['ballsFaced']) * 6 - (data['runsConceded'] / data['ballsBowled']) * 6
        row_dict = {"Team": team_key.upper(), "Played": data['P'], "Won": data['W'], "Lost": data['L'], "Tied": data['T'], "SO": data['SO'], "NRR": round(nrr, 2), "Points": data['pts']}
        points_table_data.append(row_dict)
    points_table_data = sorted(points_table_data, key=lambda x: (x["Points"], x["NRR"]), reverse=True)
    return points_table_data

def get_top_players(batting_info_data, bowling_info_data):
    top_batsmen_list = []
    for player_name, stats in batting_info_data.items():
        outs = sum(1 for ball_log_entry in stats['ballLog'] if "W" in ball_log_entry)
        avg = round(stats['runs'] / outs, 2) if outs else float('inf')
        sr = round((stats['runs'] / stats['balls']) * 100, 2) if stats['balls'] else 0
        top_batsmen_list.append({"Player": player_name, "Runs": stats['runs'], "Avg": avg, "SR": sr})
    top_batsmen_list = sorted(top_batsmen_list, key=lambda x: x["Runs"], reverse=True)[:3]
    top_bowlers_list = []
    for player_name, stats in bowling_info_data.items():
        economy = round((stats['runs'] / stats['balls']) * 6, 2) if stats['balls'] else float('inf')
        top_bowlers_list.append({"Player": player_name, "Wickets": stats['wickets'], "Economy": economy})
    top_bowlers_list = sorted(top_bowlers_list, key=lambda x: (x["Wickets"], -x["Economy"]), reverse=True)[:3]
    return {"top_batsmen": top_batsmen_list, "top_bowlers": top_bowlers_list}

def get_match_commentary(innings_log):
    commentary_list = []
    i=0
    while i < len(innings_log):
        event_data = innings_log[i]; event_text = event_data['event']; current_commentary_line = ""
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
                    event_text = next_event_data['event']; current_commentary_line = f"Nb ({total_nb_runs})! {no_ball_suffix}"; i += 1; consolidated_nb_commentary = True
            if not consolidated_nb_commentary: current_commentary_line = f"Nb (1)! {no_ball_suffix}"
        elif event_type == "WIDE": current_commentary_line = random.choice(commentary_lines['wide'])
        elif event_type == "EXTRAS" and extras_type in commentary_lines['extras']:
            actual_extras_runs = event_data.get('runs_off_extras', runs_this_ball_current_event)
            base_commentary = random.choice(commentary_lines['extras'][extras_type])
            if actual_extras_runs > 0: base_commentary += f" {actual_extras_runs} run{'s' if actual_extras_runs > 1 else ''}."
            current_commentary_line = base_commentary
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
            if is_fh_delivery and not consolidated_nb_commentary : current_commentary_line = random.choice(commentary_lines['free_hit_delivery']) + " " + base_commentary
            else: current_commentary_line = base_commentary
        commentary_list.append(f"Ball {event_data.get('balls', 'N/A')}: {event_text} - {current_commentary_line}"); i += 1
    return commentary_list

def run_league_match(team1, team2, is_rain_match, current_points, current_batting_info, current_bowling_info):
    # Handles a single league match, including potential rain cancellation.
    # Returns: resList (match details or None if fully rained out), updated_points, updated_batting_info, updated_bowling_info

    # Print statements here are for CLI mode and should be removed for web version
    print(f"\nMatch: {team1.upper()} vs {team2.upper()}")
    if is_rain_match and random.random() < 0.65: # 65% chance of washout if rain is expected
        print(f"Match {team1.upper()} vs {team2.upper()} cancelled due to rain. Points shared.")
        # Update points for cancelled match
        current_points[team1]['P'] += 1
        current_points[team2]['P'] += 1
        current_points[team1]['T'] += 1
        current_points[team2]['T'] += 1
        current_points[team1]['pts'] += 1
        current_points[team2]['pts'] += 1
        # NRR components are NOT updated as no play occurred.

        # Create a minimal resList for a cancelled match
        resList = {
            'winner': "cancelled",
            'winMsg': f"Match between {team1.upper()} and {team2.upper()} cancelled due to rain.",
            'innings1BatTeam': team1, 'innings2BatTeam': team2, # Keep track of who was scheduled
            'innings1Runs': 0, 'innings1Balls': 0, 'innings1Battracker': {}, 'innings1Bowltracker': {}, 'innings1Log': [],
            'innings2Runs': 0, 'innings2Balls': 0, 'innings2Battracker': {}, 'innings2Bowltracker': {}, 'innings2Log': [],
            'superOverPlayed': False,
            'matchID': f"{team1}v{team2}_group" # Consistent ID for cancelled matches
        }
        return resList, current_points, current_batting_info, current_bowling_info

    # If not rained out, proceed with the match
    try:
        # CLI specific input/print
        input("Press Enter to start the match...")
        print(random.choice(commentary_lines['start']))

        resList = game(False, team1, team2) # Actual game simulation

        # Commentary generation (will be part of what's returned for web)
        resList['innings1_full_commentary'] = get_match_commentary(resList['innings1Log'])
        resList['innings2_full_commentary'] = get_match_commentary(resList['innings2Log'])

        # Print CLI results (will be removed/handled differently for web)
        print("Sample Innings 1 Commentary (first 3 lines):")
        for line in resList['innings1_full_commentary'][:3]: print(line)
        print("Sample Innings 2 Commentary (first 3 lines):")
        for line in resList['innings2_full_commentary'][:3]: print(line)
        if resList.get('superOverPlayed', False) and resList.get('superOverDetails'):
            print("--- Super Over Details ---"); [print(detail) for detail in resList['superOverDetails']]; print("-------------------------")
        print(f"\nResult: {resList['winMsg']}")
        print(random.choice(commentary_lines['end']))

        # Update batting stats
        for bat_map_key in ['innings1Battracker', 'innings2Battracker']:
            bat_tracker = resList[bat_map_key]
            for player, stats in bat_tracker.items():
                if player not in current_batting_info:
                    current_batting_info[player] = copy.deepcopy(stats)
                    current_batting_info[player]['innings'] = 1
                    current_batting_info[player]['scoresArray'] = [int(stats['runs'])]
                else:
                    current_batting_info[player]['balls'] += stats['balls']
                    current_batting_info[player]['runs'] += stats['runs']
                    current_batting_info[player]['ballLog'] += stats['ballLog']
                    current_batting_info[player]['innings'] += 1
                    current_batting_info[player]['scoresArray'].append(int(stats['runs']))

        # Update bowling stats
        for bowl_map_key in ['innings1Bowltracker', 'innings2Bowltracker']:
            bowl_tracker = resList[bowl_map_key]
            for player, stats in bowl_tracker.items():
                if player not in current_bowling_info:
                    current_bowling_info[player] = copy.deepcopy(stats)
                    current_bowling_info[player]['matches'] = 1
                else:
                    current_bowling_info[player]['balls'] += stats['balls']
                    current_bowling_info[player]['runs'] += stats['runs']
                    current_bowling_info[player]['ballLog'] += stats['ballLog']
                    current_bowling_info[player]['wickets'] += stats['wickets']
                    current_bowling_info[player]['noballs'] = current_bowling_info[player].get('noballs', 0) + stats.get('noballs', 0)
                    current_bowling_info[player]['matches'] += 1

        # Points Table Update (using team1, team2 from schedule for P, and actual teams from resList for stats)
        teamA_actual = resList['innings1BatTeam']
        teamB_actual = resList['innings2BatTeam']

        current_points[team1]['P'] += 1
        current_points[team2]['P'] += 1

        if resList.get('superOverPlayed', False):
            if teamA_actual in current_points: current_points[teamA_actual]['SO'] += 1
            if teamB_actual in current_points: current_points[teamB_actual]['SO'] += 1
            # Note: Original SO count logic was duplicated. Corrected to ensure it applies based on actual play.

        winner_status = resList.get('winner')

        if winner_status == "tie": # Tie but Super Over decided winner, or just a plain tie if SO not played (handled by mainconnect.game)
            current_points[teamA_actual]['T'] += 1
            current_points[teamB_actual]['T'] += 1
            current_points[teamA_actual]['pts'] += 1
            current_points[teamB_actual]['pts'] += 1
            # NRR Updates for tie
            current_points[teamA_actual]['runsScored'] += resList['innings1Runs']
            current_points[teamB_actual]['runsScored'] += resList['innings2Runs']
            current_points[teamA_actual]['runsConceded'] += resList['innings2Runs']
            current_points[teamB_actual]['runsConceded'] += resList['innings1Runs']
            current_points[teamA_actual]['ballsFaced'] += resList['innings1Balls']
            current_points[teamB_actual]['ballsFaced'] += resList['innings2Balls']
            current_points[teamA_actual]['ballsBowled'] += resList['innings2Balls']
            current_points[teamB_actual]['ballsBowled'] += resList['innings1Balls']
        else: # Actual win/loss (winner_status is the winning team name)
            loser_actual = teamA_actual if winner_status == teamB_actual else teamB_actual
            if winner_status in current_points:
                current_points[winner_status]['W'] += 1
                current_points[winner_status]['pts'] += 2
            if loser_actual in current_points:
                current_points[loser_actual]['L'] += 1
            # NRR Updates for win/loss
            current_points[teamA_actual]['runsScored'] += resList['innings1Runs']
            current_points[teamB_actual]['runsScored'] += resList['innings2Runs']
            current_points[teamA_actual]['runsConceded'] += resList['innings2Runs']
            current_points[teamB_actual]['runsConceded'] += resList['innings1Runs']
            current_points[teamA_actual]['ballsFaced'] += resList['innings1Balls']
            current_points[teamB_actual]['ballsFaced'] += resList['innings2Balls']
            current_points[teamA_actual]['ballsBowled'] += resList['innings2Balls']
            current_points[teamB_actual]['ballsBowled'] += resList['innings1Balls']

        return resList, current_points, current_batting_info, current_bowling_info

    except Exception as e:
        print(f"Error during match {team1.upper()} vs {team2.upper()}: {str(e)}") # CLI
        # For web, this error should be logged and potentially returned
        # Return original state if match failed critically
        return None, current_points, current_batting_info, current_bowling_info


def playoffs(team1, team2, matchtag, current_batting_info, current_bowling_info):
    print(f"\n{matchtag.upper()} - {team1.upper()} vs {team2.upper()}")
    try:
        input("Press Enter to start the playoff match...")
        print(random.choice(commentary_lines['start']))
        res = game(False, team1.lower(), team2.lower(), matchtag)
        res['innings1_full_commentary'] = get_match_commentary(res['innings1Log'])
        res['innings2_full_commentary'] = get_match_commentary(res['innings2Log'])
        print("Sample Innings 1 Commentary (first 3 lines):")
        for line in res['innings1_full_commentary'][:3]: print(line)
        print("Sample Innings 2 Commentary (first 3 lines):")
        for line in res['innings2_full_commentary'][:3]: print(line)
        if res.get('superOverPlayed', False) and res.get('superOverDetails'):
            print("--- Super Over Details ---"); [print(detail) for detail in res['superOverDetails']]; print("-------------------------")
        print(f"\nResult: {res['winMsg'].upper()}"); print(random.choice(commentary_lines['end']))
        winner = res['winner']; loser = team1 if winner == team2 else team2
        for bat_map_key in ['innings1Battracker', 'innings2Battracker']:
            tracker = res[bat_map_key]
            for player, stats in tracker.items():
                if player not in current_batting_info: current_batting_info[player] = copy.deepcopy(stats); current_batting_info[player]['innings'] = 1; current_batting_info[player]['scoresArray'] = [int(stats['runs'])]
                else: current_batting_info[player]['balls'] += stats['balls']; current_batting_info[player]['runs'] += stats['runs']; current_batting_info[player]['ballLog'] += stats['ballLog']; current_batting_info[player]['innings'] += 1; current_batting_info[player]['scoresArray'].append(int(stats['runs']))
        for bowl_map_key in ['innings1Bowltracker', 'innings2Bowltracker']:
            tracker = res[bowl_map_key]
            for player, stats in tracker.items():
                if player not in current_bowling_info: current_bowling_info[player] = copy.deepcopy(stats); current_bowling_info[player]['matches'] = 1
                else: current_bowling_info[player]['balls'] += stats['balls']; current_bowling_info[player]['runs'] += stats['runs']; current_bowling_info[player]['ballLog'] += stats['ballLog']; current_bowling_info[player]['wickets'] += stats['wickets']; current_bowling_info[player]['noballs'] = current_bowling_info[player].get('noballs', 0) + stats.get('noballs', 0); current_bowling_info[player]['matches'] += 1
        input("Press Enter to continue...")
        return winner, loser, current_batting_info, current_bowling_info, res
    except Exception as e:
        print(f"Error during {matchtag.upper()}: {str(e)}"); input("Press Enter to continue or Ctrl+C to exit...")
        return team1, team2, current_batting_info, current_bowling_info, None

if __name__ == "__main__":
    points, battingInfo, bowlingInfo = initialize_tournament_data(TEAMS)
    scheduled_matches_final, matches_with_rain_chance = generate_league_schedule(TEAMS)

    all_league_match_results = []

    for team1_sched, team2_sched in scheduled_matches_final: # Renamed to avoid conflict with func params
        match_is_rain_affected = (team1_sched, team2_sched) in matches_with_rain_chance

        # MODIFIED: Call run_league_match
        resList_match, points, battingInfo, bowlingInfo = run_league_match(
            team1_sched, team2_sched, match_is_rain_affected,
            points, battingInfo, bowlingInfo
        )

        if resList_match: # If match was played (not an internal error in run_league_match)
            all_league_match_results.append(resList_match)
            # battingf and bowlingf update - to be removed later
            if resList_match.get('winner') != "cancelled" and "runs" in resList_match.get('winMsg',''): battingf += 1
            elif resList_match.get('winner') != "cancelled": bowlingf += 1

        # CLI display updates (will be removed for web)
        current_points_table = get_points_table(points, TEAMS)
        print("\n(Refactored) Current Points Table Data:")
        for row in current_points_table: print(row)

        top_players_stats = get_top_players(battingInfo, bowlingInfo)
        print("\n(Refactored) Top Players Data:")
        print(top_players_stats)

        if resList_match and resList_match.get('winner') != "cancelled": # Don't pause for cancelled matches
             input("Press Enter to continue to the next match...") # CLI

    final_league_points_table = get_points_table(points, TEAMS) # Renamed for clarity
    print("\n(Refactored) Final League Points Table Data:")
    for row in final_league_points_table: print(row)

    points_for_playoff_ranking = []
    for team_name_key in TEAMS:
        team_data = points[team_name_key]
        nrr_val = 0
        if team_data['ballsFaced'] > 0 and team_data['ballsBowled'] > 0: nrr_val = (team_data['runsScored'] / team_data['ballsFaced']) * 6 - (team_data['runsConceded'] / team_data['ballsBowled']) * 6
        elif team_data['ballsFaced'] > 0: nrr_val = (team_data['runsScored'] / team_data['ballsFaced']) * 6
        elif team_data['ballsBowled'] > 0: nrr_val = - (team_data['runsConceded'] / team_data['ballsBowled']) * 6
        points_for_playoff_ranking.append([team_name_key, team_data['pts'], nrr_val])
    pointsTabulate = sorted(points_for_playoff_ranking, key=lambda x: (x[1], x[2]), reverse=True)

    all_playoff_match_results = []

    if len(pointsTabulate) >= 4:
        q1_teams = [pointsTabulate[0][0], pointsTabulate[1][0]]; elim_teams = [pointsTabulate[2][0], pointsTabulate[3][0]]; finalists = []
        winnerQ1, loserQ1, battingInfo, bowlingInfo, q1_res = playoffs(q1_teams[0], q1_teams[1], "Qualifier 1", battingInfo, bowlingInfo)
        if q1_res: all_playoff_match_results.append(q1_res); finalists.append(winnerQ1)

        winnerElim, _, battingInfo, bowlingInfo, elim_res = playoffs(elim_teams[0], elim_teams[1], "Eliminator", battingInfo, bowlingInfo)
        if elim_res: all_playoff_match_results.append(elim_res)

        winnerQ2, _, battingInfo, bowlingInfo, q2_res = playoffs(winnerElim, loserQ1, "Qualifier 2", battingInfo, bowlingInfo)
        if q2_res: all_playoff_match_results.append(q2_res); finalists.append(winnerQ2)

        if len(finalists) == 2:
            finalWinner, _, battingInfo, bowlingInfo, final_res = playoffs(finalists[0], finalists[1], "Final", battingInfo, bowlingInfo)
            if final_res: all_playoff_match_results.append(final_res)
            print(f"\n🏆 {finalWinner.upper()} WINS THE IPL!!!")
        else: print("Could not determine two finalists for the Final match.")
    else: print("Not enough teams qualified for playoffs.")

    # File writing for batStats.txt and bowlStats.txt will be removed in Step 6
    # For now, they use the final state of battingInfo and bowlingInfo
    battingTabulate = []
    for b, c_stats in battingInfo.items(): # Use .items() for dict iteration
        outs = sum(1 for bl in c_stats['ballLog'] if "W" in bl); avg = round(c_stats['runs'] / outs, 2) if outs else "NA"; sr = round((c_stats['runs'] / c_stats['balls']) * 100, 2) if c_stats['balls'] else "NA"
        battingTabulate.append([b, c_stats['innings'], c_stats['runs'], avg, max(c_stats['scoresArray']) if c_stats['scoresArray'] else 0, sr, c_stats['balls']])
    battingTabulate = sorted(battingTabulate, key=lambda x: x[2], reverse=True)

    bowlingTabulate = []
    for b, c_stats in bowlingInfo.items(): # Use .items() for dict iteration
        overs = f"{c_stats['balls'] // 6}.{c_stats['balls'] % 6}" if c_stats['balls'] else "0"; economy = round((c_stats['runs'] / c_stats['balls']) * 6, 2) if c_stats['balls'] else "NA"; noballs = c_stats.get('noballs', 0)
        bowlingTabulate.append([b, c_stats['wickets'], overs, c_stats['runs'], noballs, economy])
    bowlingTabulate = sorted(bowlingTabulate, key=lambda x: x[1], reverse=True)

    # The following stdout redirections and file writings will be removed in a later step.
    with open(os.path.join(dir_path, "batStats.txt"), "w") as f: sys.stdout = f; print(tabulate(battingTabulate, headers=["Player", "Innings", "Runs", "Average", "Highest", "SR", "Balls"], tablefmt="grid")); sys.stdout = sys.__stdout__
    with open(os.path.join(dir_path, "bowlStats.txt"), "w") as f: sys.stdout = f; print(tabulate(bowlingTabulate, headers=["Player", "Wickets", "Overs", "Runs Conceded", "NB", "Economy"], tablefmt="grid")); sys.stdout = sys.__stdout__

    print("bat", battingf, "bowl", bowlingf)
    input("\nPress Enter to exit...")
else:
    pass
