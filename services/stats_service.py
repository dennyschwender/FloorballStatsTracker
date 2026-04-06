"""
Statistics calculation for player and goalie performance metrics
"""
from statistics import median, mean, pstdev, StatisticsError
from itertools import combinations
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
        
        # Calculate averages: use total games for all stats except GS (Game Score keeps zero-exclusion)
        total_games = len(game_values.get('plusminus', []))
        player_stats[player]['avg_plusminus'] = (player_stats[player]['plusminus'] / total_games) if total_games else 0
        player_stats[player]['avg_goals_assists'] = ((player_stats[player]['goals'] + player_stats[player]['assists']) / total_games) if total_games else 0
        player_stats[player]['avg_game_score'] = (player_stats[player]['game_score'] / len(game_score_vals)) if game_score_vals else 0  # GS: exclude zero games
        player_stats[player]['avg_unforced_errors'] = (player_stats[player]['unforced_errors'] / total_games) if total_games else 0
        player_stats[player]['avg_shots_on_goal'] = (player_stats[player]['shots_on_goal'] / total_games) if total_games else 0
        player_stats[player]['avg_penalties_taken'] = (player_stats[player]['penalties_taken'] / total_games) if total_games else 0
        player_stats[player]['avg_penalties_drawn'] = (player_stats[player]['penalties_drawn'] / total_games) if total_games else 0
        player_stats[player]['avg_block_shots'] = (player_stats[player]['block_shots'] / total_games) if total_games else 0
        player_stats[player]['avg_stolen_balls'] = (player_stats[player]['stolen_balls'] / total_games) if total_games else 0
    
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


def calculate_player_trends(games, players=None):
    """
    Calculate player performance trends across games.

    Args:
        games: List of game dicts (already filtered by season/team/date range)
        players: Optional list of player names to include (default: all players in games)

    Returns:
        Dictionary mapping player name to trends data with:
        - game_scores: List of floats in chronological order
        - game_ids: List of game IDs in chronological order
        - mean_score: Mean Game Score
        - std_dev: Standard deviation
        - min_score: Minimum Game Score
        - max_score: Maximum Game Score
        - outliers: List of dicts with {game_id, score, z_score, type}
            where type is "high" or "low" and |z_score| > 1.0
        - insufficient_data: True if player in fewer than 3 games
    """
    if not games:
        return {}

    # Sort games by date to maintain chronological order
    sorted_games = sorted(games, key=lambda g: g.get('date', ''))

    # Step 1: Determine which players to analyze
    if players is None:
        # Extract all unique player names from games
        all_players = set()
        for game in sorted_games:
            game_scores = game.get('game_scores', {})
            all_players.update(game_scores.keys())
        players_to_analyze = sorted(all_players)
    else:
        players_to_analyze = players

    # Step 2: Build result dictionary
    result = {}

    for player_name in players_to_analyze:
        # Extract game scores for this player in chronological order
        game_scores = []
        game_ids = []

        for game in sorted_games:
            game_score_dict = game.get('game_scores', {})
            if player_name in game_score_dict:
                score = game_score_dict[player_name]
                game_scores.append(score)
                game_ids.append(game['id'])

        # Skip if player not in any game
        if not game_scores:
            continue

        # Calculate basic statistics
        min_score = min(game_scores)
        max_score = max(game_scores)
        mean_score = mean(game_scores)

        # Calculate standard deviation (handle case where all scores are identical)
        try:
            std_dev = pstdev(game_scores)
        except StatisticsError:
            # All scores are identical
            std_dev = 0.0

        # Identify outliers (|z_score| > 1.0)
        # Only calculate outliers if std_dev is meaningful (not too small)
        outliers = []
        if std_dev > 0.01:  # Only calculate outliers if std_dev is significant
            for game_id, score in zip(game_ids, game_scores):
                z_score = (score - mean_score) / std_dev
                if abs(z_score) > 1.0:
                    outlier_type = "high" if z_score > 0 else "low"
                    outliers.append({
                        'game_id': game_id,
                        'score': score,
                        'z_score': z_score,
                        'type': outlier_type
                    })

        # Check if insufficient data (fewer than 3 games)
        insufficient_data = len(game_scores) < 3

        # Build player result
        result[player_name] = {
            'game_scores': game_scores,
            'game_ids': game_ids,
            'mean_score': mean_score,
            'std_dev': std_dev,
            'min_score': min_score,
            'max_score': max_score,
            'outliers': outliers,
            'insufficient_data': insufficient_data
        }

    return result


def calculate_lineup_combinations(games, combo_size_range=(5, 7), limit=10):
    """
    Identify core player combinations and their performance metrics.

    Args:
        games: List of game dicts (filtered by season/team)
        combo_size_range: Tuple (min_size, max_size) for combo sizes (default: 5-7)
        limit: Max combos to return per combo size (default: 10)

    Returns:
        List of combo dicts sorted by avg_aggregate_game_score descending:
        [{
            "combo_id": "combo_1",
            "players": ["7 - Player Seven", "12 - Player Twelve", ...],
            "combo_size": 5,
            "games_played_together": 12,
            "wins": 9,
            "losses": 3,
            "win_percentage": 75.0,
            "avg_goal_differential": 2.1,
            "avg_aggregate_game_score": 42.3,
            "game_ids": [1, 2, 4, 5, ...]
        }]
    """
    # Handle empty games list
    if not games:
        return []

    # Get all unique players from games and calculate their total game scores
    player_total_scores = {}
    for game in games:
        game_scores = game.get('game_scores', {})
        for player, score in game_scores.items():
            if player not in player_total_scores:
                player_total_scores[player] = 0
            player_total_scores[player] += score

    # If no players found, return empty list
    if not player_total_scores:
        return []

    # Sort players by total game score (descending)
    sorted_players = sorted(player_total_scores.items(), key=lambda x: x[1], reverse=True)
    all_players = [player for player, _ in sorted_players]

    results = []
    combo_id_counter = 1

    min_size, max_size = combo_size_range

    # Process each combo size
    for combo_size in range(min_size, max_size + 1):
        # Generate combinations of this size from top players
        # We need enough players to form combos
        if len(all_players) < combo_size:
            continue

        combos_for_size = []

        # Generate all combinations of this size
        for combo_tuple in combinations(all_players, combo_size):
            combo_players = list(combo_tuple)
            combo_player_set = set(combo_players)

            # Find games where ALL players in combo were present
            games_played_together = []

            for game in games:
                game_scores = game.get('game_scores', {})
                # Check if all combo players are in this game's game_scores
                if all(player in game_scores for player in combo_players):
                    games_played_together.append(game)

            # Calculate metrics for games where all players were together
            if games_played_together:
                wins = 0
                losses = 0
                goal_differentials = []
                aggregate_scores = []
                game_ids = []

                for game in games_played_together:
                    game_ids.append(game['id'])

                    # Calculate final team and opponent goals from result field
                    result = game.get('result', {})
                    team_goals = 0
                    opponent_goals = 0

                    # Sum goals from all periods (1, 2, 3, OT)
                    for period in ['1', '2', '3', 'OT']:
                        if period in result:
                            team_goals += result[period].get('home', 0)
                            opponent_goals += result[period].get('away', 0)

                    # Count wins/losses
                    if team_goals > opponent_goals:
                        wins += 1
                    elif team_goals < opponent_goals:
                        losses += 1

                    # Calculate goal differential
                    goal_diff = team_goals - opponent_goals
                    goal_differentials.append(goal_diff)

                    # Calculate aggregate game score for this combo in this game
                    game_scores = game.get('game_scores', {})
                    combo_game_score = sum(game_scores.get(player, 0) for player in combo_players)
                    aggregate_scores.append(combo_game_score)

                # Calculate averages
                avg_goal_differential = mean(goal_differentials) if goal_differentials else 0
                avg_aggregate_game_score = mean(aggregate_scores) if aggregate_scores else 0

                # Calculate win percentage
                games_count = len(games_played_together)
                if games_count > 0:
                    win_percentage = (wins / games_count) * 100
                else:
                    win_percentage = 0
            else:
                # Combo never played together
                wins = 0
                losses = 0
                avg_goal_differential = 0
                avg_aggregate_game_score = 0
                win_percentage = 0
                game_ids = []

            # Build combo result dict
            combo_result = {
                'combo_id': f'combo_{combo_id_counter}',
                'players': sorted(combo_players),  # Sort player names for consistency
                'combo_size': combo_size,
                'games_played_together': len(games_played_together),
                'wins': wins,
                'losses': losses,
                'win_percentage': win_percentage,
                'avg_goal_differential': avg_goal_differential,
                'avg_aggregate_game_score': avg_aggregate_game_score,
                'game_ids': game_ids
            }

            combos_for_size.append(combo_result)
            combo_id_counter += 1

        # Sort combos for this size by avg_aggregate_game_score descending
        combos_for_size.sort(
            key=lambda x: x['avg_aggregate_game_score'],
            reverse=True
        )

        # Limit to specified number per combo size
        combos_for_size_limited = combos_for_size[:limit]

        results.extend(combos_for_size_limited)

    # Sort all results by avg_aggregate_game_score descending (across all combo sizes)
    results.sort(
        key=lambda x: x['avg_aggregate_game_score'],
        reverse=True
    )

    return results
