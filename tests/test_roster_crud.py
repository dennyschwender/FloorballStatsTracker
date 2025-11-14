"""Tests for roster CRUD operations"""
import json
import os
import pytest
from app import ROSTERS_DIR


def test_roster_add_player(client):
    """Test adding a new player to roster"""
    # Create initial roster
    roster_data = [
        {"id": "1", "number": "69", "surname": "Bazzuri", "name": "Andrea", "position": "A", "tesser": "U21", "nickname": "Andy"}
    ]
    roster_path = os.path.join(ROSTERS_DIR, 'roster_TestTeam.json')
    with open(roster_path, 'w') as f:
        json.dump(roster_data, f)
    
    # Add new player
    data = {
        'category': 'TestTeam',
        'number': '84',
        'surname': 'Belvederi',
        'name': 'Andrea',
        'position': 'A',
        'tesser': 'U21',
        'nickname': 'Belve'
    }
    response = client.post('/roster/add', data=data, follow_redirects=True)
    assert response.status_code == 200
    
    # Verify player was added
    with open(roster_path, 'r') as f:
        roster = json.load(f)
    assert len(roster) == 2
    assert any(p['surname'] == 'Belvederi' for p in roster)
    
    # Cleanup
    if os.path.exists(roster_path):
        os.remove(roster_path)


def test_roster_edit_player(client):
    """Test editing an existing player"""
    roster_data = [
        {"id": "1", "number": "69", "surname": "Bazzuri", "name": "Andrea", "position": "A", "tesser": "U21", "nickname": "Andy"}
    ]
    roster_path = os.path.join(ROSTERS_DIR, 'roster_TestTeam.json')
    with open(roster_path, 'w') as f:
        json.dump(roster_data, f)
    
    # Edit player
    data = {
        'category': 'TestTeam',
        'number': '70',  # Changed number
        'surname': 'Bazzuri',
        'name': 'Andrea',
        'position': 'D',  # Changed position
        'tesser': 'U21',
        'nickname': 'Andy'
    }
    response = client.post('/roster/edit/1?category=TestTeam', data=data, follow_redirects=True)
    assert response.status_code == 200
    
    # Verify changes
    with open(roster_path, 'r') as f:
        roster = json.load(f)
    player = next((p for p in roster if p['id'] == '1'), None)
    assert player is not None
    assert player['number'] == '70'
    assert player['position'] == 'D'
    
    # Cleanup
    if os.path.exists(roster_path):
        os.remove(roster_path)


def test_roster_delete_player(client):
    """Test deleting a single player"""
    roster_data = [
        {"id": "1", "number": "69", "surname": "Bazzuri", "name": "Andrea", "position": "A", "tesser": "U21", "nickname": "Andy"},
        {"id": "2", "number": "84", "surname": "Belvederi", "name": "Andrea", "position": "A", "tesser": "U21", "nickname": "Belve"}
    ]
    roster_path = os.path.join(ROSTERS_DIR, 'roster_TestTeam.json')
    with open(roster_path, 'w') as f:
        json.dump(roster_data, f)
    
    # Delete player
    response = client.get('/roster/delete/1?category=TestTeam', follow_redirects=True)
    assert response.status_code == 200
    
    # Verify player was deleted
    with open(roster_path, 'r') as f:
        roster = json.load(f)
    assert len(roster) == 1
    assert not any(p['id'] == '1' for p in roster)
    
    # Cleanup
    if os.path.exists(roster_path):
        os.remove(roster_path)


def test_roster_bulk_delete(client):
    """Test deleting multiple players at once"""
    roster_data = [
        {"id": "1", "number": "69", "surname": "Bazzuri", "name": "Andrea", "position": "A", "tesser": "U21", "nickname": "Andy"},
        {"id": "2", "number": "84", "surname": "Belvederi", "name": "Andrea", "position": "A", "tesser": "U21", "nickname": "Belve"},
        {"id": "3", "number": "79", "surname": "Biaggio", "name": "Filippo", "position": "A", "tesser": "U21", "nickname": "Pippo"}
    ]
    roster_path = os.path.join(ROSTERS_DIR, 'roster_TestTeam.json')
    with open(roster_path, 'w') as f:
        json.dump(roster_data, f)
    
    # Bulk delete players 1 and 2
    data = {
        'category': 'TestTeam',
        'player_ids': ['1', '2']
    }
    response = client.post('/roster/bulk_delete', 
                          data=json.dumps(data),
                          content_type='application/json')
    assert response.status_code == 200
    result = json.loads(response.data)
    assert result['success'] == True
    
    # Verify players were deleted
    with open(roster_path, 'r') as f:
        roster = json.load(f)
    assert len(roster) == 1
    assert roster[0]['id'] == '3'
    
    # Cleanup
    if os.path.exists(roster_path):
        os.remove(roster_path)


def test_roster_bulk_import(client):
    """Test importing players from text"""
    # Prepare empty roster
    roster_path = os.path.join(ROSTERS_DIR, 'roster_TestTeam.json')
    with open(roster_path, 'w') as f:
        json.dump([], f)
    
    # Import players (tab-separated format)
    import_text = """69\tBazzuri\tAndrea\tA\tU21\tAndy
84\tBelvederi\tAndrea\tA\tU21\tBelve
79\tBiaggio\tFilippo\tA\tU21\tPippo"""
    
    data = {
        'category': 'TestTeam',
        'bulk_data': import_text
    }
    response = client.post('/roster/bulk_import', data=data, follow_redirects=True)
    assert response.status_code == 200
    
    # Verify players were imported
    with open(roster_path, 'r') as f:
        roster = json.load(f)
    assert len(roster) == 3
    assert any(p['surname'] == 'Bazzuri' for p in roster)
    assert any(p['surname'] == 'Belvederi' for p in roster)
    assert any(p['surname'] == 'Biaggio' for p in roster)
    
    # Cleanup
    if os.path.exists(roster_path):
        os.remove(roster_path)


def test_api_roster_endpoint(client):
    """Test API endpoint for roster data"""
    roster_data = [
        {"id": "1", "number": "69", "surname": "Bazzuri", "name": "Andrea", "position": "A", "tesser": "U21", "nickname": "Andy"}
    ]
    roster_path = os.path.join(ROSTERS_DIR, 'roster_U21.json')
    with open(roster_path, 'w') as f:
        json.dump(roster_data, f)
    
    # Call API endpoint
    response = client.get('/api/roster/U21')
    assert response.status_code == 200
    assert response.content_type == 'application/json'
    
    data = json.loads(response.data)
    assert len(data) == 1
    assert data[0]['surname'] == 'Bazzuri'
    
    # Cleanup
    if os.path.exists(roster_path):
        os.remove(roster_path)
