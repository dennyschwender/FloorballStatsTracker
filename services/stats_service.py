"""
Statistics calculation for player and goalie performance metrics
"""
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
    GS Goalie = (0.10 * Saves) - (0.25 * Goals Conceded)
    """
    return (0.10 * saves) - (0.25 * goals_conceded)


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
                        'game_score': 0
                    }
                
                # Extract stats for this player in this game
                goals = game.get('goals', {}).get(player, 0)
                assists = game.get('assists', {}).get(player, 0)
                plusminus = game.get('plusminus', {}).get(player, 0)
                errors = game.get('unforced_errors', {}).get(player, 0)
                sog = game.get('shots_on_goal', {}).get(player, 0)
                penalties_drawn = game.get('penalties_drawn', {}).get(player, 0)
                penalties_taken = game.get('penalties_taken', {}).get(player, 0)
                
                # Accumulate totals
                player_stats[player]['plusminus'] += plusminus
                player_stats[player]['goals'] += goals
                player_stats[player]['assists'] += assists
                player_stats[player]['unforced_errors'] += errors
                player_stats[player]['shots_on_goal'] += sog
                player_stats[player]['penalties_taken'] += penalties_taken
                player_stats[player]['penalties_drawn'] += penalties_drawn
                
                # Calculate game score for this game
                game_calculated['game_scores'][player] = calculate_game_score(
                    goals, assists, plusminus, errors, sog, penalties_drawn, penalties_taken
                )
        
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
        
        games_with_stats.append((game, game_calculated))
    
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
