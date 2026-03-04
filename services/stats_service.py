"""
Statistics calculation for player and goalie performance metrics
"""
from statistics import median
from config import PERIODS


def calculate_game_score(goals, assists, plusminus, errors, sog=0, penalties_drawn=0, penalties_taken=0):
    """
    Calculate Game Score for a player (skater)
    GS = (1.5 * G) + (1.0 * A) + (0.1 * SOG) + (0.3 * PM) + (0.15 * PD) - (0.15 * PT) - (0.2 * Errors)
    """
    return (1.5 * goals) + (1.0 * assists) + (0.1 * sog) + (0.3 * plusminus) + \
           (0.15 * penalties_drawn) - (0.15 * penalties_taken) - (0.2 * errors)


def calculate_goalie_game_score(saves, goals_conceded):
    """
    Calculate Game Score for a goalie
    GS Goalie = (0.15 * Saves) - (0.40 * Goals Conceded)
    """
    return (0.15 * saves) - (0.40 * goals_conceded)


def recalculate_game_scores(game):
    """
    Recalculate game scores for all players and goalies in a single game.
    Updates the game dict in-place with 'game_scores' and 'goalie_game_scores' fields.
    
    Args:
        game: Game dictionary to recalculate scores for
    """
    # Initialize game score dictionaries if they don't exist
    if 'game_scores' not in game:
        game['game_scores'] = {}
    if 'goalie_game_scores' not in game:
        game['goalie_game_scores'] = {}
    
    # Calculate game scores for all players in all lines
    for line in game.get('lines', []):
        for player in line:
            goals = game.get('goals', {}).get(player, 0)
            assists = game.get('assists', {}).get(player, 0)
            plusminus = game.get('plusminus', {}).get(player, 0)
            errors = game.get('unforced_errors', {}).get(player, 0)
            sog = game.get('shots_on_goal', {}).get(player, 0)
            penalties_drawn = game.get('penalties_drawn', {}).get(player, 0)
            penalties_taken = game.get('penalties_taken', {}).get(player, 0)
            
            game['game_scores'][player] = calculate_game_score(
                goals, assists, plusminus, errors, sog, penalties_drawn, penalties_taken
            )
    
    # Calculate game scores for all goalies
    for goalie in game.get('goalies', []):
        saves = game.get('saves', {}).get(goalie, 0)
        goals_conceded = game.get('goals_conceded', {}).get(goalie, 0)
        
        game['goalie_game_scores'][goalie] = calculate_goalie_game_score(saves, goals_conceded)


def calculate_stats_optimized(games_sorted, hide_zero_stats=False):
    """
    Pre-calculate all player and goalie stats in a single pass through games.
    This reduces complexity from O(n*m*7) to O(n+m) where n=games, m=players.
    
    Returns:
        dict: {
            'players': [...],
            'player_totals': {...},
            'goalies': [...],
            'goalie_data': {...},
            'opponent_goalie_data': {...},
            'games_with_calculated_stats': [...]
        }
    """
    # Initialize data structures
    player_stats = {}  # player -> stats dict
    player_game_values = {}  # player -> lists of per-game values for median calculation
    goalie_stats = {}  # goalie -> stats dict
    opponent_goalie_stats = {
        'games': [],
        'total_saves': 0,
        'total_goals_conceded': 0,
        'average_save_percentage': 0
    }
    
    # Single pass through games to collect all stats
    games_with_stats = []
    
    for game in games_sorted:
        # Skip games excluded from statistics
        if game.get('exclude_from_stats', False):
            continue
            
        # Add calculated fields to game
        game_calculated = {
            'game_scores': {},
            'save_percentages': {},
            'goalie_game_scores': {},
            'opponent_save_percentage': None
        }
        
        # Process players in this game
        for line in game.get('lines', []):
            for player in line:
                # Initialize player stats if needed
                if player not in player_stats:
                    player_stats[player] = {
                        'plusminus': 0,
                        'goals': 0,
                        'assists': 0,
                        'unforced_errors': 0,
                        'shots_on_goal': 0,
                        'penalties_taken': 0,
                        'penalties_drawn': 0,
                        'block_shots': 0,
                        'stolen_balls': 0,
                        'game_score': 0
                    }
                    player_game_values[player] = {
                        'plusminus': [],
                        'goals': [],
                        'assists': [],
                        'goals_assists': [],
                        'unforced_errors': [],
                        'shots_on_goal': [],
                        'penalties_taken': [],
                        'penalties_drawn': [],
                        'block_shots': [],
                        'stolen_balls': [],
                        'game_score': []
                    }
                
                # Extract stats for this player in this game
                goals = game.get('goals', {}).get(player, 0)
                assists = game.get('assists', {}).get(player, 0)
                plusminus = game.get('plusminus', {}).get(player, 0)
                errors = game.get('unforced_errors', {}).get(player, 0)
                sog = game.get('shots_on_goal', {}).get(player, 0)
                penalties_drawn = game.get('penalties_drawn', {}).get(player, 0)
                penalties_taken = game.get('penalties_taken', {}).get(player, 0)
                block_shots = game.get('block_shots', {}).get(player, 0)
                stolen_balls = game.get('stolen_balls', {}).get(player, 0)
                
                # Accumulate totals
                player_stats[player]['plusminus'] += plusminus
                player_stats[player]['goals'] += goals
                player_stats[player]['assists'] += assists
                player_stats[player]['unforced_errors'] += errors
                player_stats[player]['shots_on_goal'] += sog
                player_stats[player]['penalties_taken'] += penalties_taken
                player_stats[player]['penalties_drawn'] += penalties_drawn
                player_stats[player]['block_shots'] += block_shots
                player_stats[player]['stolen_balls'] += stolen_balls
                
                # Track per-game values for median calculation
                player_game_values[player]['plusminus'].append(plusminus)
                player_game_values[player]['goals'].append(goals)
                player_game_values[player]['assists'].append(assists)
                player_game_values[player]['goals_assists'].append(goals + assists)
                player_game_values[player]['unforced_errors'].append(errors)
                player_game_values[player]['shots_on_goal'].append(sog)
                player_game_values[player]['penalties_taken'].append(penalties_taken)
                player_game_values[player]['penalties_drawn'].append(penalties_drawn)
                player_game_values[player]['block_shots'].append(block_shots)
                player_game_values[player]['stolen_balls'].append(stolen_balls)
                
                # Calculate game score for this game
                game_score = calculate_game_score(
                    goals, assists, plusminus, errors, sog, penalties_drawn, penalties_taken
                )
                game_calculated['game_scores'][player] = game_score
                player_game_values[player]['game_score'].append(game_score)
        
        # Process goalies in this game
        for goalie in game.get('goalies', []):
            # Initialize goalie stats if needed
            if goalie not in goalie_stats:
                goalie_stats[goalie] = {
                    'games': [],
                    'total_saves': 0,
                    'total_goals_conceded': 0,
                    'average_save_percentage': 0,
                    'game_score': 0
                }
            
            saves = game.get('saves', {}).get(goalie, 0)
            goals_conceded = game.get('goals_conceded', {}).get(goalie, 0)
            
            # FALLBACK: If goals_conceded is 0 but the goalie has saves recorded
            if goals_conceded == 0 and saves > 0:
                result = game.get('result', {})
                if result:
                    away_goals = sum(period_result.get('away', 0) for period_result in result.values())
                    if away_goals > 0:
                        goals_conceded = away_goals
            
            total_shots = saves + goals_conceded
            
            # Calculate save percentage
            if total_shots > 0:
                save_percentage = (saves / total_shots) * 100
                game_calculated['save_percentages'][goalie] = save_percentage
                goalie_stats[goalie]['games'].append(save_percentage)
                goalie_stats[goalie]['total_saves'] += saves
                goalie_stats[goalie]['total_goals_conceded'] += goals_conceded
            else:
                game_calculated['save_percentages'][goalie] = None
            
            # Calculate goalie game score
            game_calculated['goalie_game_scores'][goalie] = calculate_goalie_game_score(
                saves, goals_conceded
            )
        
        # Process opponent goalie if enabled
        if game.get('opponent_goalie_enabled', False):
            opponent_saves = game.get('opponent_goalie_saves', {}).get('Opponent Goalie', 0)
            opponent_goals_conceded = game.get('opponent_goalie_goals_conceded', {}).get('Opponent Goalie', 0)
            opponent_total_shots = opponent_saves + opponent_goals_conceded
            
            if opponent_total_shots > 0:
                opponent_save_percentage = (opponent_saves / opponent_total_shots) * 100
                game_calculated['opponent_save_percentage'] = opponent_save_percentage
                opponent_goalie_stats['games'].append(opponent_save_percentage)
                opponent_goalie_stats['total_saves'] += opponent_saves
                opponent_goalie_stats['total_goals_conceded'] += opponent_goals_conceded
        
        # Merge calculated stats into game object
        game['game_scores'] = game_calculated['game_scores']
        game['save_percentages'] = game_calculated['save_percentages']
        game['goalie_game_scores'] = game_calculated['goalie_game_scores']
        game['opponent_save_percentage'] = game_calculated['opponent_save_percentage']
        games_with_stats.append(game)
    
    # Calculate total game scores for all players
    for player, stats in player_stats.items():
        stats['game_score'] = calculate_game_score(
            stats['goals'],
            stats['assists'],
            stats['plusminus'],
            stats['unforced_errors'],
            stats['shots_on_goal'],
            stats['penalties_drawn'],
            stats['penalties_taken']
        )
    
    # Calculate median values for all players (excluding zeros)
    for player in player_stats.keys():
        game_values = player_game_values.get(player, {})
        
        # Filter out zeros for meaningful stats (keep zeros for plusminus since 0 is meaningful)
        plusminus_vals = game_values.get('plusminus', [])
        goals_assists_vals = [v for v in game_values.get('goals_assists', []) if v > 0]
        game_score_vals = [v for v in game_values.get('game_score', []) if v != 0]  # Exclude only zeros, keep negative values
        unforced_errors_vals = [v for v in game_values.get('unforced_errors', []) if v > 0]
        shots_on_goal_vals = [v for v in game_values.get('shots_on_goal', []) if v > 0]
        penalties_taken_vals = [v for v in game_values.get('penalties_taken', []) if v > 0]
        penalties_drawn_vals = [v for v in game_values.get('penalties_drawn', []) if v > 0]
        block_shots_vals = [v for v in game_values.get('block_shots', []) if v > 0]
        stolen_balls_vals = [v for v in game_values.get('stolen_balls', []) if v > 0]
        
        player_stats[player]['median_plusminus'] = median(plusminus_vals) if plusminus_vals else 0
        player_stats[player]['median_goals_assists'] = median(goals_assists_vals) if goals_assists_vals else 0
        player_stats[player]['median_game_score'] = median(game_score_vals) if game_score_vals else 0
        player_stats[player]['median_unforced_errors'] = median(unforced_errors_vals) if unforced_errors_vals else 0
        player_stats[player]['median_shots_on_goal'] = median(shots_on_goal_vals) if shots_on_goal_vals else 0
        player_stats[player]['median_penalties_taken'] = median(penalties_taken_vals) if penalties_taken_vals else 0
        player_stats[player]['median_penalties_drawn'] = median(penalties_drawn_vals) if penalties_drawn_vals else 0
        player_stats[player]['median_block_shots'] = median(block_shots_vals) if block_shots_vals else 0
        player_stats[player]['median_stolen_balls'] = median(stolen_balls_vals) if stolen_balls_vals else 0
        
        # Track non-zero game counts for average calculations
        player_stats[player]['nonzero_games'] = {
            'plusminus': len(plusminus_vals),
            'goals_assists': len(goals_assists_vals),
            'game_score': len(game_score_vals),
            'unforced_errors': len(unforced_errors_vals),
            'shots_on_goal': len(shots_on_goal_vals),
            'penalties_taken': len(penalties_taken_vals),
            'penalties_drawn': len(penalties_drawn_vals),
            'block_shots': len(block_shots_vals),
            'stolen_balls': len(stolen_balls_vals),
        }
        
        # Calculate averages excluding zeros
        player_stats[player]['avg_plusminus'] = (player_stats[player]['plusminus'] / len(plusminus_vals)) if plusminus_vals else 0
        player_stats[player]['avg_goals_assists'] = ((player_stats[player]['goals'] + player_stats[player]['assists']) / len(goals_assists_vals)) if goals_assists_vals else 0
        player_stats[player]['avg_game_score'] = (player_stats[player]['game_score'] / len(game_score_vals)) if game_score_vals else 0
        player_stats[player]['avg_unforced_errors'] = (player_stats[player]['unforced_errors'] / len(unforced_errors_vals)) if unforced_errors_vals else 0
        player_stats[player]['avg_shots_on_goal'] = (player_stats[player]['shots_on_goal'] / len(shots_on_goal_vals)) if shots_on_goal_vals else 0
        player_stats[player]['avg_penalties_taken'] = (player_stats[player]['penalties_taken'] / len(penalties_taken_vals)) if penalties_taken_vals else 0
        player_stats[player]['avg_penalties_drawn'] = (player_stats[player]['penalties_drawn'] / len(penalties_drawn_vals)) if penalties_drawn_vals else 0
        player_stats[player]['avg_block_shots'] = (player_stats[player]['block_shots'] / len(block_shots_vals)) if block_shots_vals else 0
        player_stats[player]['avg_stolen_balls'] = (player_stats[player]['stolen_balls'] / len(stolen_balls_vals)) if stolen_balls_vals else 0
    
    # Calculate average save percentages and total game scores for goalies
    for goalie, stats in goalie_stats.items():
        total_saves = stats['total_saves']
        total_goals_conceded = stats['total_goals_conceded']
        total_shots = total_saves + total_goals_conceded
        
        if total_shots > 0:
            stats['average_save_percentage'] = (total_saves / total_shots) * 100
        else:
            stats['average_save_percentage'] = None
        
        stats['game_score'] = calculate_goalie_game_score(total_saves, total_goals_conceded)
        
        # Calculate median save percentage and game score for goalies
        if stats.get('games'):
            stats['median_save_percentage'] = median(stats['games'])
        else:
            stats['median_save_percentage'] = None
        
        # For goalie game score median, we need to track per-game scores
        goalie_game_scores = []
        for game in games_with_stats:
            if goalie in game.get('goalie_game_scores', {}):
                score = game['goalie_game_scores'][goalie]
                goalie_game_scores.append(score)
        
        # Filter out zeros for median/average (keep negative values)
        # Use abs() to handle floating point precision issues
        goalie_game_scores_nonzero = [score for score in goalie_game_scores if abs(score) > 0.001]
        
        if goalie_game_scores_nonzero:
            stats['median_game_score'] = median(goalie_game_scores_nonzero)
            stats['avg_game_score'] = sum(goalie_game_scores_nonzero) / len(goalie_game_scores_nonzero)
        else:
            stats['median_game_score'] = 0
            stats['avg_game_score'] = 0
    
    # Calculate opponent goalie average
    opponent_total_saves = opponent_goalie_stats['total_saves']
    opponent_total_goals_conceded = opponent_goalie_stats['total_goals_conceded']
    opponent_total_shots = opponent_total_saves + opponent_total_goals_conceded
    
    if opponent_total_shots > 0:
        opponent_goalie_stats['average_save_percentage'] = (
            opponent_total_saves / opponent_total_shots
        ) * 100
    else:
        opponent_goalie_stats['average_save_percentage'] = None
    
    # Filter players if requested
    players = sorted(player_stats.keys())
    filtered_players = []
    
    for player in players:
        if hide_zero_stats:
            stats = player_stats[player]
            if (stats['plusminus'] == 0 and stats['goals'] == 0 and 
                stats['assists'] == 0 and stats['unforced_errors'] == 0 and
                stats['shots_on_goal'] == 0 and stats['penalties_taken'] == 0 and
                stats['penalties_drawn'] == 0):
                continue
        filtered_players.append(player)
    
    # Filter goalies if requested
    goalies = sorted(goalie_stats.keys())
    filtered_goalies = []
    
    for goalie in goalies:
        if hide_zero_stats:
            stats = goalie_stats[goalie]
            if stats['total_saves'] == 0 and stats['total_goals_conceded'] == 0:
                continue
        filtered_goalies.append(goalie)
    
    return {
        'players': filtered_players,
        'player_totals': player_stats,
        'goalies': filtered_goalies,
        'goalie_data': goalie_stats,
        'opponent_goalie_data': opponent_goalie_stats,
        'games_with_calculated_stats': games_with_stats
    }
