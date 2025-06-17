from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json
import os
import sys
import copy

NEW_FOLDER_PATH = os.path.join(os.path.dirname(__file__), 'New folder')
if NEW_FOLDER_PATH not in sys.path:
    sys.path.append(NEW_FOLDER_PATH)

try:
    from tournament_logic import (
        initialize_tournament_data,
        generate_league_schedule,
        run_league_match,
        get_points_table,
        get_top_players,
        playoffs_match_simulator,
        get_match_commentary,
        TEAMS
    )
except ImportError as e:
    print(f"Error importing tournament logic: {e}")
    raise

app = Flask(__name__)
app.secret_key = os.urandom(24)

TEAMS_DATA_FILE = os.path.join(NEW_FOLDER_PATH, 'teams', 'teams.json')

def load_team_display_data():
    try:
        with open(TEAMS_DATA_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        app.logger.error(f"{TEAMS_DATA_FILE} not found.")
        return {}
    except json.JSONDecodeError:
        app.logger.error(f"Could not decode JSON from {TEAMS_DATA_FILE}.")
        return {}

def _prepare_batting_scorecard_display(batter_tracker):
    batting_card = []
    if not batter_tracker: return batting_card
    for player_initials, stats in batter_tracker.items():
        sr = 0
        if stats.get('balls', 0) > 0:
            sr = round((stats.get('runs', 0) / stats['balls']) * 100, 2)
        out_str = stats.get('how_out_string', 'Not out')
        if not stats.get('ballLog'):
             out_str = "Did Not Bat"
        elif "W" not in "".join(str(x) for x in stats.get('ballLog',[])):
            if stats.get('balls',0) > 0 : out_str = "Not out"
            else: out_str = "Did Not Bat"
        batting_card.append({
            "player": player_initials,
            "runs": stats.get('runs', 0),
            "balls": stats.get('balls', 0),
            "sr": sr,
            "how_out": out_str
        })
    return batting_card

def _prepare_bowling_scorecard_display(bowler_tracker):
    bowling_card = []
    if not bowler_tracker: return bowling_card
    for player_initials, stats in bowler_tracker.items():
        overs_str = "0.0"
        if stats.get('balls', 0) > 0:
            overs = stats['balls'] // 6
            balls_in_over = stats['balls'] % 6
            overs_str = f"{overs}.{balls_in_over}"
        economy = 0
        if stats.get('balls', 0) > 0:
            economy = round((stats.get('runs', 0) / stats['balls']) * 6, 2)
        bowling_card.append({
            "player": player_initials,
            "overs": overs_str,
            "runs_conceded": stats.get('runs', 0),
            "wickets": stats.get('wickets', 0),
            "noballs": stats.get('noballs', 0),
            "economy": economy
        })
    return bowling_card

@app.route('/')
def home():
    tournament_in_session = 'tournament_data' in session
    return render_template('tournament_home.html', tournament_in_session=tournament_in_session)

@app.route('/tournament/new', methods=['POST', 'GET'])
def new_tournament():
    team_list = TEAMS
    points, batting_info, bowling_info = initialize_tournament_data(team_list)
    scheduled_matches, rain_matches = generate_league_schedule(team_list)
    session['tournament_data'] = {
        'team_list': team_list, 'points_table_raw': points, 'batting_info': batting_info,
        'bowling_info': bowling_info, 'scheduled_fixtures': scheduled_matches,
        'rain_affected_matches': [tuple(m) for m in rain_matches],
        'played_match_results': [], 'current_fixture_index': 0, 'league_complete': False,
        'playoff_teams': [], 'playoff_fixtures': [], 'playoff_results': [], 'tournament_winner': None
    }
    app.logger.info("New tournament initialized.")
    return redirect(url_for('tournament_dashboard'))

def _determine_playoff_fixtures(current_tournament_data):
    if not current_tournament_data.get('league_complete'): return
    if not current_tournament_data.get('playoff_fixtures') and not current_tournament_data.get('playoff_teams'):
        ranked_teams_for_playoffs = get_points_table(current_tournament_data['points_table_raw'], current_tournament_data['team_list'])
        if len(ranked_teams_for_playoffs) >= 4:
            current_tournament_data['playoff_teams'] = [team_info['Team'].lower() for team_info in ranked_teams_for_playoffs[:4]]
            pf = [
                {"name": "Qualifier 1", "team1_code": current_tournament_data['playoff_teams'][0], "team2_code": current_tournament_data['playoff_teams'][1], "winner": None, "played": False, "res_list_id": None},
                {"name": "Eliminator", "team1_code": current_tournament_data['playoff_teams'][2], "team2_code": current_tournament_data['playoff_teams'][3], "winner": None, "played": False, "res_list_id": None},
            ]
            current_tournament_data['playoff_fixtures'] = pf
            app.logger.info(f"Initial playoff fixtures set: {pf}")
        else:
            app.logger.warning("Not enough teams for playoffs after league completion.")
            current_tournament_data['tournament_winner'] = "N/A (Not enough teams)"
            return
    q1_result = next((f for f in current_tournament_data['playoff_fixtures'] if f['name'] == "Qualifier 1" and f['played']), None)
    elim_result = next((f for f in current_tournament_data['playoff_fixtures'] if f['name'] == "Eliminator" and f['played']), None)
    q2_fixture = next((f for f in current_tournament_data['playoff_fixtures'] if f['name'] == "Qualifier 2"), None)
    if q1_result and elim_result and not q2_fixture:
        q1_winner = q1_result['winner']
        q1_loser = q1_result['team1_code'] if q1_result['team1_code'] != q1_winner else q1_result['team2_code']
        elim_winner = elim_result['winner']
        if q1_loser and elim_winner:
            current_tournament_data['playoff_fixtures'].append(
                {"name": "Qualifier 2", "team1_code": q1_loser, "team2_code": elim_winner, "winner": None, "played": False, "res_list_id": None}
            )
            app.logger.info(f"Qualifier 2 fixture added: {q1_loser} vs {elim_winner}")
    q2_result = next((f for f in current_tournament_data['playoff_fixtures'] if f['name'] == "Qualifier 2" and f['played']), None)
    final_fixture = next((f for f in current_tournament_data['playoff_fixtures'] if f['name'] == "Final"), None)
    if q1_result and q2_result and not final_fixture:
        q1_winner = q1_result['winner']
        q2_winner = q2_result['winner']
        if q1_winner and q2_winner:
            current_tournament_data['playoff_fixtures'].append(
                {"name": "Final", "team1_code": q1_winner, "team2_code": q2_winner, "winner": None, "played": False, "res_list_id": None}
            )
            app.logger.info(f"Final fixture added: {q1_winner} vs {q2_winner}")

@app.route('/tournament/dashboard')
def tournament_dashboard():
    if 'tournament_data' not in session:
        return redirect(url_for('home', error="No tournament in progress."))
    tournament_data = session['tournament_data']
    if tournament_data.get('league_complete', False) and not tournament_data.get('tournament_winner'):
        _determine_playoff_fixtures(tournament_data)
        session['tournament_data'] = tournament_data
    points_table_display = get_points_table(tournament_data['points_table_raw'], tournament_data['team_list'])
    current_fixture_idx = tournament_data.get('current_fixture_index', 0)
    upcoming_fixtures_display = []
    if not tournament_data.get('league_complete', False) and tournament_data['scheduled_fixtures']:
        for i in range(current_fixture_idx, min(current_fixture_idx + 5, len(tournament_data['scheduled_fixtures']))):
            match_teams = tournament_data['scheduled_fixtures'][i]
            match_teams_tuple = tuple(match_teams)
            is_rain = any(tuple(rm) == match_teams_tuple for rm in tournament_data['rain_affected_matches'])
            upcoming_fixtures_display.append({'id': i, 'team1_code': match_teams[0], 'team2_code': match_teams[1],'is_rain_affected': is_rain})
    team_display_data = load_team_display_data()
    return render_template('tournament_dashboard.html',
                           points_table=points_table_display,
                           upcoming_fixtures=upcoming_fixtures_display,
                           played_matches=tournament_data['played_match_results'],
                           team_data_all=team_display_data,
                           league_complete=tournament_data.get('league_complete', False),
                           current_fixture_idx=current_fixture_idx,
                           total_fixtures=len(tournament_data['scheduled_fixtures']),
                           playoff_fixtures=tournament_data.get('playoff_fixtures', []),
                           tournament_winner=tournament_data.get('tournament_winner'))

@app.route('/tournament/simulate_round', methods=['POST'])
def simulate_round():
    if 'tournament_data' not in session: return jsonify({"error": "No tournament in progress"}), 400
    tournament_data = session['tournament_data']
    num_matches_to_play = 4
    matches_simulated_this_round = 0; round_results_summary = []
    for _ in range(num_matches_to_play):
        current_fixture_idx = tournament_data.get('current_fixture_index', 0)
        if current_fixture_idx >= len(tournament_data['scheduled_fixtures']):
            tournament_data['league_complete'] = True; break
        match_info_tuple = tuple(tournament_data['scheduled_fixtures'][current_fixture_idx])
        team1, team2 = match_info_tuple
        is_rain = any(tuple(rm) == match_info_tuple for rm in tournament_data['rain_affected_matches'])
        app.logger.info(f"Simulating (round): {team1} vs {team2}, Rain: {is_rain}")
        match_result, updated_points, updated_batting_info, updated_bowling_info = run_league_match(
            team1, team2, is_rain, copy.deepcopy(tournament_data['points_table_raw']),
            copy.deepcopy(tournament_data['batting_info']), copy.deepcopy(tournament_data['bowling_info']), web_mode=True )
        if match_result:
            tournament_data['points_table_raw'] = updated_points; tournament_data['batting_info'] = updated_batting_info
            tournament_data['bowling_info'] = updated_bowling_info; tournament_data['played_match_results'].append(match_result)
            round_results_summary.append(f"{match_result.get('winMsg', 'Match completed.')}")
        else: round_results_summary.append(f"Error simulating {team1} vs {team2}.")
        tournament_data['current_fixture_index'] += 1; matches_simulated_this_round +=1
    if tournament_data['current_fixture_index'] >= len(tournament_data['scheduled_fixtures']):
        tournament_data['league_complete'] = True; _determine_playoff_fixtures(tournament_data)
    session['tournament_data'] = tournament_data
    return jsonify({"message": f"{matches_simulated_this_round} matches simulated.", "round_summary": round_results_summary,
                    "league_complete": tournament_data['league_complete'], "playoffs_setup": bool(tournament_data.get('playoff_fixtures'))})

@app.route('/tournament/simulate_playoff_match/<path:fixture_name_encoded>', methods=['POST'])
def simulate_playoff_match(fixture_name_encoded):
    fixture_name = fixture_name_encoded.replace("_", " ")
    if 'tournament_data' not in session: return jsonify({"error": "No tournament"}), 400
    tournament_data = session['tournament_data']
    if not tournament_data.get('league_complete', False): return jsonify({"error": "League not complete"}), 400
    fixture_to_play = None; fixture_idx = -1
    for idx, fix in enumerate(tournament_data.get('playoff_fixtures', [])):
        if fix['name'] == fixture_name and not fix['played']: fixture_to_play = fix; fixture_idx = idx; break
    if not fixture_to_play: return jsonify({"error": f"Playoff fixture '{fixture_name}' not found or already played."}), 404
    team1 = fixture_to_play['team1_code']; team2 = fixture_to_play['team2_code']
    app.logger.info(f"Simulating Playoff: {fixture_name} - {team1} vs {team2}")
    winner, loser, updated_batting, updated_bowling, res_list = playoffs_match_simulator(
        team1, team2, fixture_name, copy.deepcopy(tournament_data['batting_info']),
        copy.deepcopy(tournament_data['bowling_info']), web_mode=True)
    if res_list:
        tournament_data['batting_info'] = updated_batting; tournament_data['bowling_info'] = updated_bowling
        tournament_data['playoff_fixtures'][fixture_idx]['played'] = True
        tournament_data['playoff_fixtures'][fixture_idx]['winner'] = winner
        res_list_id = f"playoff_{fixture_name.replace(' ', '_').lower()}"
        res_list['matchID'] = res_list_id
        tournament_data['played_match_results'].append(res_list)
        tournament_data['playoff_fixtures'][fixture_idx]['res_list_id'] = res_list_id
        if fixture_name == "Final": tournament_data['tournament_winner'] = winner; app.logger.info(f"Tournament Winner: {winner}")
        _determine_playoff_fixtures(tournament_data)
        session['tournament_data'] = tournament_data
        return jsonify({"message": f"{fixture_name} simulated. Winner: {winner}", "tournament_winner": tournament_data['tournament_winner']})
    else: return jsonify({"error": f"Error simulating {fixture_name}"}), 500

@app.route('/tournament/match/<int:match_idx>')
def match_detail(match_idx):
    if 'tournament_data' not in session: return redirect(url_for('home', error="No tournament data in session."))
    tournament_data = session['tournament_data']; played_matches = tournament_data.get('played_match_results', [])
    if 0 <= match_idx < len(played_matches):
        match_result = played_matches[match_idx]; team_display_data = load_team_display_data()
        innings1_bat_card = _prepare_batting_scorecard_display(match_result.get('innings1Battracker', {}))
        innings1_bowl_card = _prepare_bowling_scorecard_display(match_result.get('innings1Bowltracker', {}))
        innings2_bat_card = _prepare_batting_scorecard_display(match_result.get('innings2Battracker', {}))
        innings2_bowl_card = _prepare_bowling_scorecard_display(match_result.get('innings2Bowltracker', {}))
        # Calculate fallen wickets for summary string
        inn1_wickets_fallen = sum(1 for p_stats in match_result.get('innings1Battracker', {}).values() if "W" in "".join(str(x) for x in p_stats.get('ballLog',[])) )
        inn2_wickets_fallen = sum(1 for p_stats in match_result.get('innings2Battracker', {}).values() if "W" in "".join(str(x) for x in p_stats.get('ballLog',[])) )

        scorecard_data = {
            "team1_code": match_result.get('innings1BatTeam', 'TBC').upper(),
            "team2_code": match_result.get('innings2BatTeam', 'TBC').upper(),
            "team1_display": team_display_data.get(match_result.get('innings1BatTeam',''), {}),
            "team2_display": team_display_data.get(match_result.get('innings2BatTeam',''), {}),
            "toss_msg": match_result.get('tossMsg', 'N/A'),
            "match_id_display": match_result.get('matchID', f"Match {match_idx+1}"),
            "win_msg": match_result.get('winMsg', 'Result pending'),
            "winner_code": match_result.get('winner', None),
            "innings1_score_summary": f"{match_result.get('innings1Runs',0)}/{inn1_wickets_fallen} ({match_result.get('innings1Balls',0)//6}.{match_result.get('innings1Balls',0)%6} Ov)",
            "innings2_score_summary": f"{match_result.get('innings2Runs',0)}/{inn2_wickets_fallen} ({match_result.get('innings2Balls',0)//6}.{match_result.get('innings2Balls',0)%6} Ov)",
            "batting_card_inn1": innings1_bat_card, "bowling_card_inn1": innings1_bowl_card,
            "batting_card_inn2": innings2_bat_card, "bowling_card_inn2": innings2_bowl_card,
        }
        innings1_commentary = get_match_commentary(match_result.get('innings1Log', []))
        innings2_commentary = get_match_commentary(match_result.get('innings2Log', []))
        return render_template('match_detail.html', scorecard=scorecard_data, commentary_inn1=innings1_commentary, commentary_inn2=innings2_commentary)
    else: return redirect(url_for('tournament_dashboard', error="Match not found."))

@app.route('/tournament/stats') # NEW ROUTE
def player_stats():
    if 'tournament_data' not in session:
        return redirect(url_for('home', error="No tournament data in session."))

    tournament_data = session['tournament_data']
    batting_info = tournament_data.get('batting_info', {})
    bowling_info = tournament_data.get('bowling_info', {})

    if not batting_info and not bowling_info:
        # Could show a message or redirect with info
        return render_template('player_stats.html', top_players_data=None, team_data_all=load_team_display_data(), error_msg="No player statistics available yet.")

    top_players_data = get_top_players(batting_info, bowling_info)
    team_display_data = load_team_display_data()

    return render_template('player_stats.html',
                           top_players_data=top_players_data,
                           team_data_all=team_display_data)

if __name__ == '__main__':
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    if not os.path.exists(template_dir): os.makedirs(template_dir)

    dummy_home = os.path.join(template_dir, 'tournament_home.html')
    if not os.path.exists(dummy_home):
        with open(dummy_home, 'w') as f: f.write('<h1>Home</h1><form action="{{ url_for(\'new_tournament\') }}" method="post"><button type="submit">New Tournament</button></form>{% if tournament_in_session %}<p><a href="{{ url_for(\'tournament_dashboard\') }}">Resume Tournament</a></p>{% endif %}<p><a href="{{ url_for(\'player_stats\') }}">View Player Stats</a></p>')

    dummy_dashboard = os.path.join(template_dir, 'tournament_dashboard.html')
    if not os.path.exists(dummy_dashboard):
        with open(dummy_dashboard, 'w') as f:
            f.write('''<h1>Dashboard</h1>
                       <p><a href="{{ url_for('player_stats') }}">View Player Stats</a></p>
                       <h2>Points Table</h2> <pre>{{ points_table | tojson(indent=2) }}</pre>
                       <h2>Upcoming Matches</h2> <pre>{{ upcoming_fixtures | tojson(indent=2) }}</pre>
                       <form action="{{ url_for(\'simulate_next_league_match\') }}" method="post"><button type="submit">Simulate Next Match</button></form>
                       <form action="{{ url_for(\'simulate_round\') }}" method="post"><button type="submit">Simulate Round (4 Matches)</button></form>
                       <h3>Playoffs</h3>
                       {% if playoff_fixtures %}
                           <ul>
                           {% for fixture in playoff_fixtures %}
                               <li>{{ fixture.name }}: {{ fixture.team1_code }} vs {{ fixture.team2_code }}
                                  {% if fixture.played %} (Winner: {{ fixture.winner }})
                                  {% else %} <form action="{{ url_for(\'simulate_playoff_match\', fixture_name_encoded=fixture.name.replace(\' \', \'_\')) }}" method="post" style="display:inline;"><button type="submit">Simulate {{fixture.name}}</button></form>
                                  {% endif %}
                               </li>
                           {% endfor %}
                           </ul>
                       {% elif league_complete %}
                           <p>League complete. Playoffs to be determined or in progress.</p>
                       {% endif %}
                       {% if tournament_winner %}<h2>Winner: {{ tournament_winner }}</h2>{% endif %}
                       <h3>Played Matches</h3><pre>{{ played_matches | tojson(indent=2) }}</pre>''')

    dummy_match_detail = os.path.join(template_dir, 'match_detail.html')
    if not os.path.exists(dummy_match_detail):
        with open(dummy_match_detail, 'w') as f:
            f.write('<h1>Match Detail</h1><h2>{{ scorecard.match_id_display }}</h2><p>{{ scorecard.win_msg }}</p>')
            f.write('<h3>Commentary Innings 1:</h3><ul>{% for c in commentary_inn1 %}<li>{{c}}</li>{% endfor %}</ul>')
            f.write('<h3>Commentary Innings 2:</h3><ul>{% for c in commentary_inn2 %}<li>{{c}}</li>{% endfor %}</ul>')
            f.write('<pre>{{ scorecard | tojson(indent=2) }}</pre>')
            f.write('<p><a href="{{ url_for(\'tournament_dashboard\') }}">Back to Dashboard</a></p>')

    dummy_player_stats = os.path.join(template_dir, 'player_stats.html') # New dummy template
    if not os.path.exists(dummy_player_stats):
        with open(dummy_player_stats, 'w') as f:
            f.write('''<!DOCTYPE html>
<html>
<head><title>Player Stats</title></head>
<body>
    <h1>Player Statistics</h1>
    {% if error_msg %}<p style="color:red;">{{ error_msg }}</p>{% endif %}
    <h2>Top Batsmen</h2>
    {% if top_players_data and top_players_data.top_batsmen %}
        <ul>
        {% for batsman in top_players_data.top_batsmen %}
            <li>{{ batsman.Player }} - Runs: {{ batsman.Runs }}, Avg: {{ batsman.Avg }}, SR: {{ batsman.SR }}</li>
        {% endfor %}
        </ul>
    {% else %}
        <p>No batting statistics available yet.</p>
    {% endif %}

    <h2>Top Bowlers</h2>
    {% if top_players_data and top_players_data.top_bowlers %}
        <ul>
        {% for bowler in top_players_data.top_bowlers %}
            <li>{{ bowler.Player }} - Wickets: {{ bowler.Wickets }}, Economy: {{ bowler.Economy }}</li>
        {% endfor %}
        </ul>
    {% else %}
        <p>No bowling statistics available yet.</p>
    {% endif %}
    <p><a href="{{ url_for('tournament_dashboard') }}">Back to Dashboard</a></p>
    <p><a href="{{ url_for('home') }}">Home</a></p>
</body>
</html>''')

    app.run(debug=True, port=5001)
