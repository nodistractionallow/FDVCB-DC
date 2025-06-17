import os
import sys
import random
# MODIFIED: Import from the newly named match_simulation_engine
from match_simulation_engine import game
from tabulate import tabulate
import copy

TEAMS = ['dc', 'csk', 'rcb', 'mi', 'kkr', 'pbks', 'rr', 'srh']

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

commentary_lines = {
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

def run_league_match(team1, team2, is_rain_match, current_points, current_batting_info, current_bowling_info, web_mode=True):
    if not web_mode: print(f"\nMatch: {team1.upper()} vs {team2.upper()}")
    if is_rain_match and random.random() < 0.65:
        if not web_mode: print(f"Match {team1.upper()} vs {team2.upper()} cancelled due to rain. Points shared.")
        current_points[team1]['P'] += 1; current_points[team2]['P'] += 1
        current_points[team1]['T'] += 1; current_points[team2]['T'] += 1
        current_points[team1]['pts'] += 1; current_points[team2]['pts'] += 1
        resList = {'winner': "cancelled", 'winMsg': f"Match between {team1.upper()} and {team2.upper()} cancelled due to rain.",
                   'innings1BatTeam': team1, 'innings2BatTeam': team2, 'innings1Runs': 0, 'innings1Balls': 0,
                   'innings1Battracker': {}, 'innings1Bowltracker': {}, 'innings1Log': [], 'innings2Runs': 0, 'innings2Balls': 0,
                   'innings2Battracker': {}, 'innings2Bowltracker': {}, 'innings2Log': [], 'superOverPlayed': False,
                   'matchID': f"{team1}v{team2}_group", 'innings1_full_commentary': ["Match cancelled due to rain."], 'innings2_full_commentary': []}
        return resList, current_points, current_batting_info, current_bowling_info
    try:
        if not web_mode: input("Press Enter to start the match..."); print(random.choice(commentary_lines['start']))
        resList = game(manual=False, sentTeamOne=team1, sentTeamTwo=team2, switch="group", write_to_file=not web_mode)
        resList['innings1_full_commentary'] = get_match_commentary(resList['innings1Log'])
        resList['innings2_full_commentary'] = get_match_commentary(resList['innings2Log'])
        if not web_mode:
            print("Sample Innings 1 Commentary (first 3 lines):"); [print(line) for line in resList['innings1_full_commentary'][:3]]
            print("Sample Innings 2 Commentary (first 3 lines):"); [print(line) for line in resList['innings2_full_commentary'][:3]]
            if resList.get('superOverPlayed', False) and resList.get('superOverDetails'): print("--- Super Over Details ---"); [print(detail) for detail in resList['superOverDetails']]; print("-------------------------")
            print(f"\nResult: {resList['winMsg']}"); print(random.choice(commentary_lines['end']))
        for bat_map_key in ['innings1Battracker', 'innings2Battracker']:
            bat_tracker = resList[bat_map_key]
            for player, stats in bat_tracker.items():
                if player not in current_batting_info: current_batting_info[player] = copy.deepcopy(stats); current_batting_info[player]['innings'] = 1; current_batting_info[player]['scoresArray'] = [int(stats['runs'])]
                else: current_batting_info[player]['balls'] += stats['balls']; current_batting_info[player]['runs'] += stats['runs']; current_batting_info[player]['ballLog'] += stats['ballLog']; current_batting_info[player]['innings'] += 1; current_batting_info[player]['scoresArray'].append(int(stats['runs']))
        for bowl_map_key in ['innings1Bowltracker', 'innings2Bowltracker']:
            bowl_tracker = resList[bowl_map_key]
            for player, stats in bowl_tracker.items():
                if player not in current_bowling_info: current_bowling_info[player] = copy.deepcopy(stats); current_bowling_info[player]['matches'] = 1
                else: current_bowling_info[player]['balls'] += stats['balls']; current_bowling_info[player]['runs'] += stats['runs']; current_bowling_info[player]['ballLog'] += stats['ballLog']; current_bowling_info[player]['wickets'] += stats['wickets']; current_bowling_info[player]['noballs'] = current_bowling_info[player].get('noballs', 0) + stats.get('noballs', 0); current_bowling_info[player]['matches'] += 1
        teamA_actual = resList['innings1BatTeam']; teamB_actual = resList['innings2BatTeam']
        current_points[team1]['P'] += 1; current_points[team2]['P'] += 1
        if resList.get('superOverPlayed', False):
            if teamA_actual in current_points: current_points[teamA_actual]['SO'] += 1
            if teamB_actual in current_points: current_points[teamB_actual]['SO'] += 1
        winner_status = resList.get('winner')
        if winner_status == "tie":
            current_points[teamA_actual]['T'] += 1; current_points[teamB_actual]['T'] += 1; current_points[teamA_actual]['pts'] += 1; current_points[teamB_actual]['pts'] += 1
            current_points[teamA_actual]['runsScored'] += resList['innings1Runs']; current_points[teamB_actual]['runsScored'] += resList['innings2Runs']; current_points[teamA_actual]['runsConceded'] += resList['innings2Runs']; current_points[teamB_actual]['runsConceded'] += resList['innings1Runs']; current_points[teamA_actual]['ballsFaced'] += resList['innings1Balls']; current_points[teamB_actual]['ballsFaced'] += resList['innings2Balls']; current_points[teamA_actual]['ballsBowled'] += resList['innings2Balls']; current_points[teamB_actual]['ballsBowled'] += resList['innings1Balls']
        else:
            if winner_status != "cancelled":
                loser_actual = teamA_actual if winner_status == teamB_actual else teamB_actual
                if winner_status in current_points: current_points[winner_status]['W'] += 1; current_points[winner_status]['pts'] += 2
                if loser_actual in current_points: current_points[loser_actual]['L'] += 1
            current_points[teamA_actual]['runsScored'] += resList['innings1Runs']; current_points[teamB_actual]['runsScored'] += resList['innings2Runs']; current_points[teamA_actual]['runsConceded'] += resList['innings2Runs']; current_points[teamB_actual]['runsConceded'] += resList['innings1Runs']; current_points[teamA_actual]['ballsFaced'] += resList['innings1Balls']; current_points[teamB_actual]['ballsFaced'] += resList['innings2Balls']; current_points[teamA_actual]['ballsBowled'] += resList['innings2Balls']; current_points[teamB_actual]['ballsBowled'] += resList['innings1Balls']
        return resList, current_points, current_batting_info, current_bowling_info
    except Exception as e:
        if not web_mode: print(f"Error during match {team1.upper()} vs {team2.upper()}: {str(e)}")
        return None, current_points, current_batting_info, current_bowling_info

def playoffs_match_simulator(team1, team2, matchtag, current_batting_info, current_bowling_info, web_mode=True):
    if not web_mode: print(f"\n{matchtag.upper()} - {team1.upper()} vs {team2.upper()}"); input("Press Enter to start the playoff match..."); print(random.choice(commentary_lines['start']))
    try:
        res = game(manual=False, sentTeamOne=team1.lower(), sentTeamTwo=team2.lower(), switch=matchtag, write_to_file=not web_mode)
        res['innings1_full_commentary'] = get_match_commentary(res['innings1Log'])
        res['innings2_full_commentary'] = get_match_commentary(res['innings2Log'])
        if not web_mode:
            print("Sample Innings 1 Commentary (first 3 lines):"); [print(line) for line in res['innings1_full_commentary'][:3]]
            print("Sample Innings 2 Commentary (first 3 lines):"); [print(line) for line in res['innings2_full_commentary'][:3]]
            if res.get('superOverPlayed', False) and res.get('superOverDetails'): print("--- Super Over Details ---"); [print(detail) for detail in res['superOverDetails']]; print("-------------------------")
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
        if not web_mode: input("Press Enter to continue...")
        return winner, loser, current_batting_info, current_bowling_info, res
    except Exception as e:
        if not web_mode: print(f"Error during {matchtag.upper()}: {str(e)}"); input("Press Enter to continue or Ctrl+C to exit...")
        return team1, team2, current_batting_info, current_bowling_info, None

def simulate_tournament_league_phase(team_list, web_mode=True):
    points, battingInfo, bowlingInfo = initialize_tournament_data(team_list)
    scheduled_matches, matches_with_rain = generate_league_schedule(team_list)
    all_league_match_results = []

    for team1_sched, team2_sched in scheduled_matches:
        match_is_rain_affected = (team1_sched, team2_sched) in matches_with_rain
        resList_match, points, battingInfo, bowlingInfo = run_league_match(
            team1_sched, team2_sched, match_is_rain_affected,
            points, battingInfo, bowlingInfo, web_mode
        )
        if resList_match: all_league_match_results.append(resList_match)
        if not web_mode:
            current_points_table = get_points_table(points, team_list)
            print("\n(CLI) Current Points Table Data:")
            if 'tabulate' in sys.modules: print(tabulate(current_points_table, headers="keys", tablefmt="grid"))
            else: [print(row) for row in current_points_table]
            top_players_stats = get_top_players(battingInfo, bowlingInfo)
            print("\n(CLI) Top Players Data:")
            if 'tabulate' in sys.modules:
                print(tabulate(top_players_stats["top_batsmen"], headers="keys", tablefmt="grid"))
                print(tabulate(top_players_stats["top_bowlers"], headers="keys", tablefmt="grid"))
            else: print(top_players_stats)
            if resList_match and resList_match.get('winner') != "cancelled":
                 input("Press Enter to continue to the next match...")
    return points, battingInfo, bowlingInfo, all_league_match_results

def simulate_tournament_playoffs(points_data, batting_info_data, bowling_info_data, team_list_arg, web_mode=True):
    if not web_mode:
        final_league_points_table = get_points_table(points_data, team_list_arg)
        print("\n(CLI) Final League Points Table Data:")
        if 'tabulate' in sys.modules: print(tabulate(final_league_points_table, headers="keys", tablefmt="grid"))
        else: [print(row) for row in final_league_points_table]
    points_for_ranking = []
    for team_name_key in team_list_arg:
        team_data = points_data[team_name_key]
        nrr_val = 0
        if team_data['ballsFaced'] > 0 and team_data['ballsBowled'] > 0: nrr_val = (team_data['runsScored'] / team_data['ballsFaced']) * 6 - (team_data['runsConceded'] / team_data['ballsBowled']) * 6
        elif team_data['ballsFaced'] > 0: nrr_val = (team_data['runsScored'] / team_data['ballsFaced']) * 6
        elif team_data['ballsBowled'] > 0: nrr_val = - (team_data['runsConceded'] / team_data['ballsBowled']) * 6
        points_for_ranking.append([team_name_key, team_data['pts'], nrr_val])
    ranked_teams = sorted(points_for_ranking, key=lambda x: (x[1], x[2]), reverse=True)
    all_playoff_match_results = []
    tournament_winner = None
    if len(ranked_teams) >= 4:
        q1_teams = [ranked_teams[0][0], ranked_teams[1][0]]; elim_teams = [ranked_teams[2][0], ranked_teams[3][0]]; finalists = []
        winnerQ1, loserQ1, batting_info_data, bowling_info_data, q1_res = playoffs_match_simulator(q1_teams[0], q1_teams[1], "Qualifier 1", batting_info_data, bowling_info_data, web_mode)
        if q1_res: all_playoff_match_results.append(q1_res); finalists.append(winnerQ1)
        winnerElim, _, batting_info_data, bowling_info_data, elim_res = playoffs_match_simulator(elim_teams[0], elim_teams[1], "Eliminator", batting_info_data, bowling_info_data, web_mode)
        if elim_res: all_playoff_match_results.append(elim_res)
        winnerQ2, _, batting_info_data, bowling_info_data, q2_res = playoffs_match_simulator(winnerElim, loserQ1, "Qualifier 2", batting_info_data, bowling_info_data, web_mode)
        if q2_res: all_playoff_match_results.append(q2_res); finalists.append(winnerQ2)
        if len(finalists) == 2:
            tournament_winner, _, batting_info_data, bowling_info_data, final_res = playoffs_match_simulator(finalists[0], finalists[1], "Final", batting_info_data, bowling_info_data, web_mode)
            if final_res: all_playoff_match_results.append(final_res)
            if not web_mode: print(f"\n🏆 {tournament_winner.upper()} WINS THE IPL!!!")
        else:
            if not web_mode: print("Could not determine two finalists for the Final match.")
    else:
        if not web_mode: print("Not enough teams qualified for playoffs.")
    return batting_info_data, bowling_info_data, all_playoff_match_results, tournament_winner

if __name__ == "__main__":
    is_web_mode = True

    points, battingInfo, bowlingInfo, league_match_results = simulate_tournament_league_phase(TEAMS, web_mode=is_web_mode)
    battingInfo, bowlingInfo, playoff_match_results, tournament_champion = simulate_tournament_playoffs(points, battingInfo, bowlingInfo, TEAMS, web_mode=is_web_mode)

    if not is_web_mode:
        print("\n--- Tournament Simulation Complete (CLI Mode) ---")
        print(f"Champion: {tournament_champion}")
        print("\nFinal Points Table:")
        final_table_data = get_points_table(points, TEAMS)
        if 'tabulate' in sys.modules: print(tabulate(final_table_data, headers="keys", tablefmt="grid"))
        else: [print(row) for row in final_table_data]
        print("\nTop Players:")
        top_players = get_top_players(battingInfo, bowlingInfo)
        print("Batsmen:")
        if 'tabulate' in sys.modules: print(tabulate(top_players["top_batsmen"], headers="keys", tablefmt="grid"))
        else: [print(p) for p in top_players["top_batsmen"]]
        print("Bowlers:")
        if 'tabulate' in sys.modules: print(tabulate(top_players["top_bowlers"], headers="keys", tablefmt="grid"))
        else: [print(p) for p in top_players["top_bowlers"]]
    else:
        print("Tournament simulation complete (web_mode=True). Winner: " + str(tournament_champion))
else:
    pass
