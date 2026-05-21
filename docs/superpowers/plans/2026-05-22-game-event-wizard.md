# Game Event Wizard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a floating "＋ Event" button in edit mode that opens a step-by-step modal wizard for logging goals, penalties, saves, shots on goal, and period changes — all via a single new `POST /event/<game_id>` endpoint with atomic undo support.

**Architecture:** New `record_event` route in `routes/game_routes.py` handles all event types atomically (one undo snapshot per event). Frontend is pure JS in `game_details.html` — a step-machine renders wizard steps inside a Bootstrap modal triggered by a fixed FAB button shown only in edit mode.

**Tech Stack:** Flask (Python), Bootstrap 5 modal, vanilla JS, existing `_game_stats_response` / `updateStatCells` / `updateScore` helpers, existing `undo_store` / `ensure_game_stats` / `ensure_player_stats` utilities.

---

### Task 1: Backend — `record_event` endpoint (TDD)

**Files:**
- Create: `tests/test_event_endpoint.py`
- Modify: `routes/game_routes.py` (add route after the `/undo/` route at end of file)

- [ ] **Step 1: Create test file with failing tests**

```python
# tests/test_event_endpoint.py
import json
import pytest
from tests.test_actions import _write_games, _read_games, make_sample_game

AJAX = {'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/json'}


def _post(client, game_id, payload):
    return client.post(
        f'/event/{game_id}',
        data=json.dumps(payload),
        headers=AJAX,
        content_type='application/json',
    )


# ── goal / our team ───────────────────────────────────────────────────────────

def test_event_goal_ours_increments_scorer(client):
    _write_games([make_sample_game()])
    rv = _post(client, 0, {'type': 'goal', 'team': 'ours', 'scorer': 'P1',
                            'plusminus_players': ['P1']})
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['ok'] is True
    assert data['stats']['goals'].get('P1', 0) == 1


def test_event_goal_ours_increments_assist(client):
    _write_games([make_sample_game()])
    rv = _post(client, 0, {'type': 'goal', 'team': 'ours', 'scorer': 'P1',
                            'assist': 'P2', 'plusminus_players': []})
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['stats']['assists'].get('P2', 0) == 1


def test_event_goal_ours_updates_plusminus(client):
    _write_games([make_sample_game()])
    rv = _post(client, 0, {'type': 'goal', 'team': 'ours', 'scorer': 'P1',
                            'plusminus_players': ['P1', 'P2', 'P3']})
    data = rv.get_json()
    assert data['stats']['plusminus'].get('P1', 0) == 1
    assert data['stats']['plusminus'].get('P2', 0) == 1
    assert data['stats']['plusminus'].get('P3', 0) == 1


def test_event_goal_ours_updates_home_result(client):
    _write_games([make_sample_game()])
    rv = _post(client, 0, {'type': 'goal', 'team': 'ours', 'scorer': 'P1',
                            'plusminus_players': []})
    data = rv.get_json()
    assert data['result']['1']['home'] == 1


def test_event_goal_ours_increments_opponent_goalie_conceded_when_enabled(client):
    _write_games([make_sample_game(opponent_goalie_enabled=True)])
    rv = _post(client, 0, {'type': 'goal', 'team': 'ours', 'scorer': 'P1',
                            'plusminus_players': []})
    data = rv.get_json()
    assert data['stats']['opponent_goalie_goals_conceded'].get('Opponent Goalie', 0) == 1


# ── goal / opponent ───────────────────────────────────────────────────────────

def test_event_goal_opponent_decrements_plusminus(client):
    _write_games([make_sample_game()])
    rv = _post(client, 0, {'type': 'goal', 'team': 'opponent',
                            'plusminus_players': ['P1', 'P2']})
    data = rv.get_json()
    assert data['stats']['plusminus'].get('P1', 0) == -1
    assert data['stats']['plusminus'].get('P2', 0) == -1


def test_event_goal_opponent_increments_goalie_conceded(client):
    _write_games([make_sample_game()])
    rv = _post(client, 0, {'type': 'goal', 'team': 'opponent',
                            'plusminus_players': [], 'goalie': 'G1'})
    data = rv.get_json()
    assert data['stats']['goals_conceded'].get('G1', 0) == 1
    assert data['result']['1']['away'] == 1


def test_event_goal_opponent_no_goalie_still_ok(client):
    _write_games([make_sample_game()])
    rv = _post(client, 0, {'type': 'goal', 'team': 'opponent',
                            'plusminus_players': []})
    assert rv.status_code == 200


# ── penalty ───────────────────────────────────────────────────────────────────

def test_event_penalty_taken(client):
    _write_games([make_sample_game()])
    rv = _post(client, 0, {'type': 'penalty', 'subtype': 'taken', 'player': 'P1'})
    data = rv.get_json()
    assert data['stats']['penalties_taken'].get('P1', 0) == 1


def test_event_penalty_drawn(client):
    _write_games([make_sample_game()])
    rv = _post(client, 0, {'type': 'penalty', 'subtype': 'drawn', 'player': 'P2'})
    data = rv.get_json()
    assert data['stats']['penalties_drawn'].get('P2', 0) == 1


def test_event_penalty_missing_player_returns_400(client):
    _write_games([make_sample_game()])
    rv = _post(client, 0, {'type': 'penalty', 'subtype': 'taken'})
    assert rv.status_code == 400


# ── save ─────────────────────────────────────────────────────────────────────

def test_event_save_our_goalie(client):
    _write_games([make_sample_game()])
    rv = _post(client, 0, {'type': 'save', 'player': 'G1'})
    data = rv.get_json()
    assert data['stats']['saves'].get('G1', 0) == 1


def test_event_save_opponent_goalie(client):
    _write_games([make_sample_game(opponent_goalie_enabled=True)])
    rv = _post(client, 0, {'type': 'save', 'player': 'Opponent Goalie'})
    data = rv.get_json()
    assert data['stats']['opponent_goalie_saves'].get('Opponent Goalie', 0) == 1


# ── shot on goal ─────────────────────────────────────────────────────────────

def test_event_shot_on_goal(client):
    _write_games([make_sample_game()])
    rv = _post(client, 0, {'type': 'shot_on_goal', 'player': 'P3'})
    data = rv.get_json()
    assert data['stats']['shots_on_goal'].get('P3', 0) == 1


# ── period change ─────────────────────────────────────────────────────────────

def test_event_period_change_advances_period(client):
    _write_games([make_sample_game()])  # current_period = '1'
    rv = _post(client, 0, {'type': 'period_change'})
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['current_period'] == '2'
    g = _read_games()[0]
    assert g['current_period'] == '2'


def test_event_period_change_does_not_exceed_OT(client):
    game = make_sample_game()
    game['current_period'] = 'OT'
    _write_games([game])
    rv = _post(client, 0, {'type': 'period_change'})
    data = rv.get_json()
    assert data['current_period'] == 'OT'


# ── error cases ───────────────────────────────────────────────────────────────

def test_event_unknown_type_returns_400(client):
    _write_games([make_sample_game()])
    rv = _post(client, 0, {'type': 'flying_saucer'})
    assert rv.status_code == 400


def test_event_game_not_found_returns_404(client):
    _write_games([])
    rv = _post(client, 999, {'type': 'period_change'})
    assert rv.status_code == 404


def test_event_response_contains_stats_and_result(client):
    _write_games([make_sample_game()])
    rv = _post(client, 0, {'type': 'shot_on_goal', 'player': 'P1'})
    data = rv.get_json()
    assert 'stats' in data
    assert 'result' in data
    assert 'ok' in data
```

- [ ] **Step 2: Run tests to confirm they all fail**

```bash
pytest tests/test_event_endpoint.py -v 2>&1 | head -30
```
Expected: all fail with 404 (route not registered yet).

- [ ] **Step 3: Add `record_event` to `routes/game_routes.py`**

Add this function after the existing `/undo/<game_id>` route (at end of file). All imports are already present at the top of `game_routes.py`.

```python
@game_bp.route('/event/<int:game_id>', methods=['POST'])
def record_event(game_id):
    """Atomic multi-stat event endpoint for the game wizard."""
    payload = request.get_json(silent=True) or {}
    event_type = payload.get('type')

    games = load_games()
    game = find_game_by_id(games, game_id)
    if not game:
        abort(404)
    require_edit(game)

    ensure_game_stats(game)

    period = game.get('current_period', '1')
    if 'result' not in game:
        game['result'] = {p: {'home': 0, 'away': 0} for p in PERIODS}

    undo_store.push(game_id, game)

    if event_type == 'goal':
        team = payload.get('team')
        plusminus_players = payload.get('plusminus_players', [])

        if team == 'ours':
            scorer = payload.get('scorer')
            assist = payload.get('assist')
            if scorer:
                ensure_player_stats(game, scorer)
                game['goals'][scorer] += 1
            if period not in game['result']:
                game['result'][period] = {'home': 0, 'away': 0}
            game['result'][period]['home'] += 1
            if assist:
                ensure_player_stats(game, assist)
                game['assists'][assist] += 1
            for p in plusminus_players:
                ensure_player_stats(game, p)
                game['plusminus'][p] += 1
            if game.get('opponent_goalie_enabled', False):
                if 'opponent_goalie_goals_conceded' not in game:
                    game['opponent_goalie_goals_conceded'] = {}
                if 'Opponent Goalie' not in game['opponent_goalie_goals_conceded']:
                    game['opponent_goalie_goals_conceded']['Opponent Goalie'] = 0
                game['opponent_goalie_goals_conceded']['Opponent Goalie'] += 1

        elif team == 'opponent':
            goalie = payload.get('goalie')
            for p in plusminus_players:
                ensure_player_stats(game, p)
                game['plusminus'][p] -= 1
            if goalie:
                if 'goals_conceded' not in game:
                    game['goals_conceded'] = {}
                if goalie not in game['goals_conceded']:
                    game['goals_conceded'][goalie] = 0
                game['goals_conceded'][goalie] += 1
                if period not in game['result']:
                    game['result'][period] = {'home': 0, 'away': 0}
                game['result'][period]['away'] += 1
        else:
            return jsonify({'ok': False, 'error': 'goal requires team=ours|opponent'}), 400

        recalculate_game_scores(game)

    elif event_type == 'penalty':
        subtype = payload.get('subtype')
        player = payload.get('player')
        if not player:
            return jsonify({'ok': False, 'error': 'penalty requires player'}), 400
        ensure_player_stats(game, player)
        if subtype == 'taken':
            game['penalties_taken'][player] += 1
        elif subtype == 'drawn':
            game['penalties_drawn'][player] += 1
        else:
            return jsonify({'ok': False, 'error': 'penalty requires subtype=taken|drawn'}), 400

    elif event_type == 'save':
        player = payload.get('player')
        if not player:
            return jsonify({'ok': False, 'error': 'save requires player'}), 400
        if player == 'Opponent Goalie':
            if 'opponent_goalie_saves' not in game:
                game['opponent_goalie_saves'] = {}
            if 'Opponent Goalie' not in game['opponent_goalie_saves']:
                game['opponent_goalie_saves']['Opponent Goalie'] = 0
            game['opponent_goalie_saves']['Opponent Goalie'] += 1
        else:
            if 'saves' not in game:
                game['saves'] = {}
            if player not in game['saves']:
                game['saves'][player] = 0
            game['saves'][player] += 1

    elif event_type == 'shot_on_goal':
        player = payload.get('player')
        if not player:
            return jsonify({'ok': False, 'error': 'shot_on_goal requires player'}), 400
        ensure_player_stats(game, player)
        game['shots_on_goal'][player] += 1

    elif event_type == 'period_change':
        current = game.get('current_period', '1')
        idx = PERIODS.index(current) if current in PERIODS else 0
        game['current_period'] = PERIODS[min(idx + 1, len(PERIODS) - 1)]

    else:
        return jsonify({'ok': False, 'error': f'unknown event type: {event_type}'}), 400

    for i, g in enumerate(games):
        if g.get('id') == game_id:
            games[i] = game
            break
    save_games(games)

    resp = _game_stats_response(game)
    resp['current_period'] = game.get('current_period', '1')
    return jsonify(resp)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_event_endpoint.py -v
```
Expected: all pass.

- [ ] **Step 5: Run full test suite**

```bash
pytest tests/ -v --ignore=tests/test_web_pages.py --ignore=tests/test_app_info.py
```
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add tests/test_event_endpoint.py routes/game_routes.py
git commit -m "feat: add POST /event/<game_id> endpoint for atomic game events"
```

---

### Task 2: Template — JS data variables, FAB button, modal shell

**Files:**
- Modify: `templates/game_details.html`

- [ ] **Step 1: Add JS data variables**

In `templates/game_details.html`, find the first `<script nonce="{{ g.csp_nonce }}">` block in `{% block scripts %}`. It starts with:
```javascript
(function () {
    'use strict';

    var GAME_ID = {{ game_id }};
```

Add three lines immediately after `var GAME_ID = {{ game_id }};`:

```javascript
    var GAME_ID = {{ game_id }};
    var GAME_LINES = {{ game.lines | tojson }};
    var GAME_GOALIES = {{ (game.goalies or []) | tojson }};
    var GAME_CURRENT_PERIOD = {{ (game.current_period or '1') | tojson }};
    var OPPONENT_GOALIE_ENABLED = {{ 'true' if game.get('opponent_goalie_enabled') else 'false' }};
```

- [ ] **Step 2: Add FAB button HTML**

In `game_details.html`, find the block:
```html
    {% if request.args.get('edit') == '1' %}
    <div class="mb-3 d-flex justify-content-between flex-wrap gap-2">
```
(around line 183 — the section that renders "Exit Edit Mode" and undo button).

Just before `{% endblock %}` that closes the content block (at end of body, before `{% block scripts %}`), add:

```html
{% if request.args.get('edit') == '1' %}
<button id="addEventFab"
        class="btn btn-primary rounded-pill shadow"
        style="position:fixed;bottom:1.5rem;right:1.5rem;z-index:1050;font-size:1.1rem;padding:.55rem 1.2rem;"
        data-bs-toggle="modal" data-bs-target="#eventWizardModal">
    ＋ {{ g.t.get('event', 'Event') }}
</button>
{% endif %}
```

- [ ] **Step 3: Add modal shell HTML**

Immediately after the FAB block (still before `{% endblock %}`), add:

```html
<div class="modal fade" id="eventWizardModal" tabindex="-1"
     aria-labelledby="eventWizardTitle" aria-hidden="true">
  <div class="modal-dialog modal-dialog-centered">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title" id="eventWizardTitle">Add Event</h5>
        <button type="button" class="btn-close"
                data-bs-dismiss="modal" aria-label="Close"></button>
      </div>
      <div class="modal-body" id="eventWizardBody"></div>
      <div class="modal-footer d-flex" id="eventWizardFooter"></div>
    </div>
  </div>
</div>
```

- [ ] **Step 4: Verify template renders without errors**

```bash
pytest tests/test_template_regression.py -v
```
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add templates/game_details.html
git commit -m "feat(wizard): add FAB and modal shell to game_details template"
```

---

### Task 3: Wizard JS — step machine, renderers, submit

**Files:**
- Modify: `templates/game_details.html` (new `<script nonce>` block at end of `{% block scripts %}`)

**Security note:** All dynamic content inserted into the DOM via `innerHTML` or `textContent` must use the `escHtml` helper defined below to prevent XSS from player names or other user-supplied data embedded via Jinja2.

- [ ] **Step 1: Add wizard script block**

At the very end of `{% block scripts %}`, just before `{% endblock %}`, add:

```html
<script nonce="{{ g.csp_nonce }}">
(function () {
    'use strict';

    // ── XSS-safe escape helper ────────────────────────────────────────────────
    function escHtml(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    // ── Step machine state ────────────────────────────────────────────────────
    var wizard = { steps: [], idx: 0, selections: {}, eventType: null };

    function allPlayers() {
        var seen = {};
        var result = [];
        (window.GAME_LINES || []).forEach(function (line) {
            line.forEach(function (p) {
                if (p && !seen[p]) { seen[p] = true; result.push(p); }
            });
        });
        return result;
    }

    function allGoalies() {
        var goalies = (window.GAME_GOALIES || []).slice();
        if (window.OPPONENT_GOALIE_ENABLED) goalies.push('Opponent Goalie');
        return goalies;
    }

    // ── Step builders ─────────────────────────────────────────────────────────
    function buildSteps(eventType) {
        var players = allPlayers();
        var goalies = allGoalies();

        var stepSets = {
            goal_type: [
                { key: 'team', title: 'Which team scored?', type: 'chips',
                  options: [
                    { value: 'ours', label: '&#x26BD; Our team' },
                    { value: 'opponent', label: '&#x26BD; Opponent' }
                  ] },
                { key: '__goal_branch', title: '', type: 'goal_branch' }
            ],
            penalty: [
                { key: 'subtype', title: 'Penalty type', type: 'chips',
                  options: [
                    { value: 'taken', label: '&#x1F7E5; Taken' },
                    { value: 'drawn', label: '&#x2705; Drawn' }
                  ] },
                { key: 'player', title: 'Which player?', type: 'player-list', options: players },
                { key: '__confirm', title: 'Confirm penalty', type: 'confirm' }
            ],
            save: [
                { key: 'player', title: 'Which goalie made the save?',
                  type: 'player-list', options: goalies },
                { key: '__confirm', title: 'Confirm save', type: 'confirm' }
            ],
            shot_on_goal: [
                { key: 'player', title: 'Who took the shot?',
                  type: 'player-list', options: players },
                { key: '__confirm', title: 'Confirm shot', type: 'confirm' }
            ],
            period_change: [
                { key: '__confirm', title: 'Advance Period', type: 'period-confirm' }
            ]
        };
        return stepSets[eventType] || [];
    }

    function buildGoalSteps(team) {
        var players = allPlayers();
        var ourGoalies = (window.GAME_GOALIES || []);
        if (team === 'ours') {
            return [
                { key: 'scorer', title: 'Who scored?', type: 'player-list', options: players },
                { key: 'assist', title: 'Assist? (optional)', type: 'player-list',
                  options: ['\u2014 No assist \u2014'].concat(players) },
                { key: 'plusminus_players', title: 'Who was on ice? (+1)',
                  type: 'line-plusminus' },
                { key: '__confirm', title: 'Confirm goal', type: 'confirm' }
            ];
        }
        return [
            { key: 'plusminus_players', title: 'Who was on ice? (\u22121)',
              type: 'line-plusminus' },
            { key: 'goalie', title: 'Which goalie conceded?', type: 'player-list',
              options: ['\u2014 No goalie \u2014'].concat(ourGoalies) },
            { key: '__confirm', title: 'Confirm opponent goal', type: 'confirm' }
        ];
    }

    // ── Renderers ─────────────────────────────────────────────────────────────
    function renderChips(step) {
        var frag = document.createDocumentFragment();
        var wrap = document.createElement('div');
        wrap.className = 'd-flex flex-wrap gap-2 py-1';
        step.options.forEach(function (opt) {
            var btn = document.createElement('button');
            btn.type = 'button';
            var isSelected = wizard.selections[step.key] === opt.value;
            btn.className = 'btn ' + (isSelected ? 'btn-primary' : 'btn-outline-secondary') +
                ' wizard-chip';
            btn.dataset.key = step.key;
            btn.dataset.value = opt.value;
            // label is safe (hardcoded in buildSteps, only HTML entity refs)
            btn.innerHTML = opt.label;
            wrap.appendChild(btn);
        });
        frag.appendChild(wrap);
        return frag;
    }

    function renderPlayerList(step) {
        var wrap = document.createElement('div');
        wrap.className = 'd-flex flex-wrap gap-2 py-1';
        var selected = wizard.selections[step.key];
        step.options.forEach(function (opt) {
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'btn btn-sm ' +
                (selected === opt ? 'btn-primary' : 'btn-outline-secondary') +
                ' wizard-chip';
            btn.dataset.key = step.key;
            btn.dataset.value = opt;
            btn.textContent = opt;
            wrap.appendChild(btn);
        });
        return wrap;
    }

    function renderLinePlusminus(step) {
        var selected = wizard.selections[step.key];
        if (!Array.isArray(selected)) {
            selected = allPlayers().slice();
            wizard.selections[step.key] = selected;
        }
        var container = document.createElement('div');
        (window.GAME_LINES || []).forEach(function (line, lineIdx) {
            var nonEmpty = line.filter(function (p) { return p; });
            if (!nonEmpty.length) return;
            var allOn = nonEmpty.every(function (p) { return selected.indexOf(p) >= 0; });

            var card = document.createElement('div');
            card.className = 'mb-2 border rounded';

            var hdr = document.createElement('div');
            hdr.className = 'd-flex align-items-center justify-content-between p-2 bg-light';
            hdr.style.cursor = 'pointer';
            hdr.dataset.lineIdx = String(lineIdx);
            hdr.classList.add('wizard-line-header');

            var lbl = document.createElement('strong');
            lbl.textContent = 'Line ' + (lineIdx + 1);
            var badge = document.createElement('span');
            badge.className = 'badge ' + (allOn ? 'bg-primary' : 'bg-secondary');
            badge.textContent = allOn ? 'All on' : 'Some off';
            hdr.appendChild(lbl);
            hdr.appendChild(badge);

            var chips = document.createElement('div');
            chips.className = 'd-flex flex-wrap gap-2 p-2';
            nonEmpty.forEach(function (p) {
                var on = selected.indexOf(p) >= 0;
                var btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'btn btn-sm ' + (on ? 'btn-primary' : 'btn-outline-secondary') +
                    ' wizard-pm-chip';
                btn.dataset.player = p;
                btn.textContent = p;
                chips.appendChild(btn);
            });

            card.appendChild(hdr);
            card.appendChild(chips);
            container.appendChild(card);
        });
        if (!container.children.length) {
            var msg = document.createElement('p');
            msg.className = 'text-muted';
            msg.textContent = 'No lines configured.';
            container.appendChild(msg);
        }
        return container;
    }

    function renderConfirm() {
        var s = wizard.selections;
        var lines = [];
        if (s.team) lines.push('Team: ' + (s.team === 'ours' ? 'Our team' : 'Opponent'));
        if (s.scorer) lines.push('Scorer: ' + s.scorer);
        if (s.assist && s.assist !== '\u2014 No assist \u2014') lines.push('Assist: ' + s.assist);
        if (Array.isArray(s.plusminus_players) && s.plusminus_players.length)
            lines.push('On ice (\u00b1): ' + s.plusminus_players.join(', '));
        if (s.goalie && s.goalie !== '\u2014 No goalie \u2014') lines.push('Goalie: ' + s.goalie);
        if (s.player) lines.push('Player: ' + s.player);
        if (s.subtype) lines.push('Type: ' + s.subtype);

        var ul = document.createElement('ul');
        ul.className = 'list-unstyled mb-0';
        if (lines.length) {
            lines.forEach(function (l) {
                var li = document.createElement('li');
                li.className = 'py-1 border-bottom';
                li.textContent = l;
                ul.appendChild(li);
            });
        } else {
            var li = document.createElement('li');
            li.className = 'text-muted';
            li.textContent = 'Ready to submit.';
            ul.appendChild(li);
        }
        return ul;
    }

    function renderPeriodConfirm() {
        var cur = window.GAME_CURRENT_PERIOD || '1';
        var periods = ['1', '2', '3', 'OT'];
        var idx = periods.indexOf(cur);
        var next = (idx >= 0 && idx < periods.length - 1) ? periods[idx + 1] : cur;
        var label = function (p) { return p === 'OT' ? 'OT' : 'Period ' + p; };
        var p = document.createElement('p');
        p.className = 'mb-0';
        if (cur === next) {
            p.textContent = 'Already at ' + label(cur) + ' (final period).';
        } else {
            p.textContent = 'Advance from ' + label(cur) + ' to ' + label(next) + '?';
        }
        return p;
    }

    // ── renderStep ────────────────────────────────────────────────────────────
    function renderStep(idx) {
        var step = wizard.steps[idx];
        var body = document.getElementById('eventWizardBody');
        var footer = document.getElementById('eventWizardFooter');
        var title = document.getElementById('eventWizardTitle');
        if (!step || !body || !footer) return;

        title.textContent = step.title || 'Add Event';

        // Handle invisible branch step
        if (step.type === 'goal_branch') {
            var team = wizard.selections['team'];
            if (!team) { wizard.idx = Math.max(0, idx - 1); renderStep(wizard.idx); return; }
            var branchSteps = buildGoalSteps(team);
            wizard.steps = wizard.steps.slice(0, idx).concat(branchSteps);
            renderStep(idx);
            return;
        }

        body.textContent = ''; // clear safely (no innerHTML)

        var content;
        if (step.type === 'chips')            content = renderChips(step);
        else if (step.type === 'player-list') content = renderPlayerList(step);
        else if (step.type === 'line-plusminus') content = renderLinePlusminus(step);
        else if (step.type === 'confirm')     content = renderConfirm();
        else if (step.type === 'period-confirm') content = renderPeriodConfirm();

        if (content) body.appendChild(content);

        // Footer
        footer.textContent = '';
        if (idx > 0) {
            var backBtn = document.createElement('button');
            backBtn.type = 'button';
            backBtn.className = 'btn btn-outline-secondary';
            backBtn.textContent = '\u2190 Back';
            backBtn.addEventListener('click', function () {
                wizard.idx = Math.max(0, wizard.idx - 1);
                renderStep(wizard.idx);
            });
            footer.appendChild(backBtn);
        }

        var isLast = (step.type === 'confirm' || step.type === 'period-confirm');
        var actionBtn = document.createElement('button');
        actionBtn.type = 'button';
        actionBtn.id = isLast ? 'wizardSave' : 'wizardNext';
        actionBtn.className = (isLast ? 'btn btn-success' : 'btn btn-primary') + ' ms-auto';
        actionBtn.textContent = isLast ? '\u2713 Save' : 'Next \u2192';
        if (isLast) {
            actionBtn.addEventListener('click', submitEvent);
        } else {
            actionBtn.addEventListener('click', function () {
                wizard.idx = Math.min(wizard.steps.length - 1, wizard.idx + 1);
                renderStep(wizard.idx);
            });
        }
        footer.appendChild(actionBtn);

        // Chip listeners (single-select)
        body.querySelectorAll('.wizard-chip').forEach(function (btn) {
            btn.addEventListener('click', function () {
                wizard.selections[btn.dataset.key] = btn.dataset.value;
                renderStep(idx);
            });
        });

        // plusminus individual chip listeners
        body.querySelectorAll('.wizard-pm-chip').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var player = btn.dataset.player;
                var arr = wizard.selections['plusminus_players'] || [];
                var pos = arr.indexOf(player);
                if (pos >= 0) arr.splice(pos, 1); else arr.push(player);
                wizard.selections['plusminus_players'] = arr;
                renderStep(idx);
            });
        });

        // plusminus line-header listeners (toggle all in line)
        body.querySelectorAll('.wizard-line-header').forEach(function (hdr) {
            hdr.addEventListener('click', function () {
                var lineIdx = parseInt(hdr.dataset.lineIdx, 10);
                var line = (window.GAME_LINES || [])[lineIdx] || [];
                var nonEmpty = line.filter(function (p) { return p; });
                var arr = wizard.selections['plusminus_players'] || [];
                var allOn = nonEmpty.every(function (p) { return arr.indexOf(p) >= 0; });
                if (allOn) {
                    arr = arr.filter(function (p) { return nonEmpty.indexOf(p) < 0; });
                } else {
                    nonEmpty.forEach(function (p) { if (arr.indexOf(p) < 0) arr.push(p); });
                }
                wizard.selections['plusminus_players'] = arr;
                renderStep(idx);
            });
        });
    }

    // ── Submit ────────────────────────────────────────────────────────────────
    function submitEvent() {
        var payload = Object.assign({}, wizard.selections);
        payload.type = wizard.eventType;

        // Normalise "no" sentinel values
        if (payload.assist === '\u2014 No assist \u2014') delete payload.assist;
        if (payload.goalie === '\u2014 No goalie \u2014') delete payload.goalie;
        delete payload.__confirm;
        delete payload.__goal_branch;

        var saveBtn = document.getElementById('wizardSave');
        if (saveBtn) { saveBtn.disabled = true; saveBtn.textContent = 'Saving\u2026'; }

        fetch('/event/' + window.GAME_ID, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'same-origin',
            body: JSON.stringify(payload)
        })
        .then(function (res) {
            if (!res.ok) throw new Error('HTTP ' + res.status);
            return res.json();
        })
        .then(function (data) {
            var modalEl = document.getElementById('eventWizardModal');
            var bsModal = bootstrap.Modal.getInstance(modalEl);
            if (bsModal) bsModal.hide();

            if (data.stats) window.updateStatCells(data.stats);
            if (data.result) window.updateScore(data.result);

            if (payload.type === 'period_change') {
                // Period buttons are server-rendered; reload to reflect new period
                window.location.reload();
                return;
            }

            if (window.showUndoToast) {
                window.showUndoToast(payload.type.replace(/_/g, ' '));
            }
        })
        .catch(function () {
            if (saveBtn) { saveBtn.disabled = false; saveBtn.textContent = '\u2713 Save'; }
            if (window.showToast) window.showToast('Failed to save event \u2014 check connection', 'danger', 4000);
        });
    }

    // ── Event type picker (first screen) ─────────────────────────────────────
    var eventTypes = [
        { value: 'goal_type',     label: '\u26BD Goal' },
        { value: 'penalty',       label: '\uD83D\uDFE5 Penalty' },
        { value: 'save',          label: '\uD83E\uDDE4 Save' },
        { value: 'shot_on_goal',  label: '\uD83C\uDFAF Shot on goal' },
        { value: 'period_change', label: '\u23ED Period change' }
    ];

    function showEventTypePicker() {
        wizard.steps = [];
        wizard.idx = 0;
        wizard.selections = {};
        wizard.eventType = null;

        var body = document.getElementById('eventWizardBody');
        var footer = document.getElementById('eventWizardFooter');
        var title = document.getElementById('eventWizardTitle');
        if (!body || !footer || !title) return;

        title.textContent = 'Add Event';
        footer.textContent = '';
        body.textContent = '';

        var grid = document.createElement('div');
        grid.className = 'd-grid gap-2';
        eventTypes.forEach(function (et) {
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'btn btn-outline-primary wizard-event-type';
            btn.dataset.eventType = et.value;
            btn.textContent = et.label;
            btn.addEventListener('click', function () {
                var evType = btn.dataset.eventType;
                wizard.eventType = evType === 'goal_type' ? 'goal' : evType;
                wizard.steps = buildSteps(evType);
                wizard.idx = 0;
                wizard.selections = {};
                renderStep(0);
            });
            grid.appendChild(btn);
        });
        body.appendChild(grid);
    }

    var modalEl = document.getElementById('eventWizardModal');
    if (modalEl) {
        modalEl.addEventListener('show.bs.modal', showEventTypePicker);
    }

})();
</script>
```

- [ ] **Step 2: Manual smoke test**

```bash
python app.py
```

Open `http://localhost:5000/game/<id>?edit=1` (use any game with players in lines).

Verify:
1. FAB "＋ Event" visible bottom-right
2. Click FAB → modal shows 5 event type buttons
3. Click "Goal" → team chips (Our team / Opponent) appear
4. Select "Our team" → scorer player-list appears
5. Select scorer → assist list appears (with "No assist" option at top)
6. Select assist (or No assist) → plusminus step: all lines expanded, all players pre-selected
7. Click a line header → toggles all players in that line
8. Click individual player chip → deselects/selects that player
9. Click Next → confirm screen shows summary
10. Click Save → modal closes, stat cells update, undo toast appears
11. Click Undo → stat reverts

Also test: Goal (opponent) → plusminus step (−1) → goalie picker → confirm → Save
Also test: Period change → confirm shows current→next → Save → page reloads with next period

- [ ] **Step 3: Run full test suite**

```bash
pytest tests/ -v --ignore=tests/test_web_pages.py --ignore=tests/test_app_info.py
```
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add templates/game_details.html
git commit -m "feat(wizard): add step-machine wizard JS with all event type flows"
```

---

### Task 4: Push and deploy

- [ ] **Step 1: Push to origin**

```bash
git push origin main
```

- [ ] **Step 2: Deploy**

```bash
ssh pi5 "~/dockerimages/updateDocker.sh FloorballStats"
```

- [ ] **Step 3: Smoke-test on production**

Open https://floorballstats.mennylenderr.ch/ (PIN 171717), navigate to a game in edit mode. Verify FAB visible, complete one goal wizard end-to-end, confirm stats update without full page reload.
