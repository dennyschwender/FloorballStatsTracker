/**
 * StatsChartUI - Handles player picker, stat selector, and chart rendering
 */
class StatsChartUI {
    constructor(allPlayers) {
        this.allPlayers = allPlayers || [];
        this.selectedPlayers = [];
        this.currentStatType = 'game_score';
        this.chartInstance = null;

        // DOM elements
        this.playerSearch = document.getElementById('player-search');
        this.playerSuggestions = document.getElementById('player-suggestions');
        this.selectedPlayersContainer = document.getElementById('selected-players');
        this.statRadios = document.querySelectorAll('input[name="stat-selector"]');
        this.showChartBtn = document.getElementById('show-chart-btn');
        this.chartLoading = document.getElementById('chart-loading');
        this.chartContainer = document.getElementById('chart-container');
        this.chartMessage = document.getElementById('chart-message');
        this.chartCanvas = document.getElementById('stats-chart');
    }

    init() {
        // Attach event listeners
        if (this.playerSearch) {
            this.playerSearch.addEventListener('input', (e) => this.handlePlayerSearch(e));
            this.playerSearch.addEventListener('blur', () => setTimeout(() => this.hidePlayerSuggestions(), 200));
        }

        if (this.playerSuggestions) {
            this.playerSuggestions.addEventListener('click', (e) => this.handlePlayerSelect(e));
        }

        this.statRadios.forEach(radio => {
            radio.addEventListener('change', (e) => this.handleStatTypeChange(e));
        });

        if (this.showChartBtn) {
            this.showChartBtn.addEventListener('click', () => this.fetchAndRenderChart());
        }
    }

    handlePlayerSearch(e) {
        const query = e.target.value.toLowerCase().trim();

        if (!query) {
            this.hidePlayerSuggestions();
            return;
        }

        // Filter players based on query
        const filtered = this.allPlayers.filter(p =>
            p.toLowerCase().includes(query) &&
            !this.selectedPlayers.includes(p)
        );

        // Display suggestions
        this.playerSuggestions.innerHTML = '';
        filtered.slice(0, 10).forEach(player => {
            const suggestion = document.createElement('button');
            suggestion.type = 'button';
            suggestion.className = 'list-group-item list-group-item-action';
            suggestion.textContent = player;
            suggestion.dataset.player = player;
            this.playerSuggestions.appendChild(suggestion);
        });

        this.playerSuggestions.style.display = filtered.length > 0 ? 'block' : 'none';
    }

    handlePlayerSelect(e) {
        if (e.target.dataset && e.target.dataset.player) {
            const player = e.target.dataset.player;
            this.addSelectedPlayer(player);
            this.playerSearch.value = '';
            this.hidePlayerSuggestions();
        }
    }

    addSelectedPlayer(player) {
        if (!this.selectedPlayers.includes(player)) {
            this.selectedPlayers.push(player);
            this.renderSelectedPlayers();
            this.updateShowChartButton();
        }
    }

    removeSelectedPlayer(player) {
        this.selectedPlayers = this.selectedPlayers.filter(p => p !== player);
        this.renderSelectedPlayers();
        this.updateShowChartButton();
    }

    renderSelectedPlayers() {
        this.selectedPlayersContainer.innerHTML = '';

        this.selectedPlayers.forEach(player => {
            const pill = document.createElement('div');
            pill.className = 'badge bg-primary d-flex align-items-center gap-2';
            pill.style.fontSize = '0.95rem';
            pill.style.padding = '0.5rem 0.75rem';

            const label = document.createElement('span');
            label.textContent = player;

            const closeBtn = document.createElement('button');
            closeBtn.type = 'button';
            closeBtn.className = 'btn-close btn-close-white';
            closeBtn.style.padding = '0';
            closeBtn.style.fontSize = '0.75rem';
            closeBtn.dataset.player = player;

            // Use addEventListener instead of onclick
            closeBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.removeSelectedPlayer(player);
            });

            pill.appendChild(label);
            pill.appendChild(closeBtn);
            this.selectedPlayersContainer.appendChild(pill);
        });
    }

    hidePlayerSuggestions() {
        this.playerSuggestions.style.display = 'none';
    }

    handleStatTypeChange(e) {
        this.currentStatType = e.target.value;
    }

    updateShowChartButton() {
        this.showChartBtn.disabled = this.selectedPlayers.length === 0;
    }

    fetchAndRenderChart() {
        if (this.selectedPlayers.length === 0) {
            this.showMessage('Select at least one player', 'alert-warning');
            return;
        }

        this.showChartBtn.disabled = true;
        this.chartLoading.style.display = 'inline-block';
        this.hideMessage();

        // Get current filter values from the page URL
        const season = new URLSearchParams(window.location.search).get('season') || '';
        const team = new URLSearchParams(window.location.search).get('team') || '';
        const lastNGames = new URLSearchParams(window.location.search).get('last_n_games') || '';

        // Build query parameters
        const params = new URLSearchParams();
        params.append('season', season);
        params.append('team', team);
        this.selectedPlayers.forEach(player => params.append('players', player));
        if (lastNGames) {
            params.append('last_n_games', lastNGames);
        }

        // Fetch chart data
        fetch(`/api/chart-data?${params}`)
            .then(response => {
                if (!response.ok) {
                    return response.json().then(data => {
                        throw new Error(data.error || 'Failed to load chart data');
                    });
                }
                return response.json();
            })
            .then(data => {
                this.chartLoading.style.display = 'none';
                this.showChartBtn.disabled = false;

                if (data.games.length === 0) {
                    this.showMessage('No games found for the selected filters', 'alert-info');
                    this.hideChartContainer();
                } else {
                    this.renderChart(data);
                }
            })
            .catch(error => {
                this.chartLoading.style.display = 'none';
                this.showChartBtn.disabled = false;
                this.showMessage(`Error: ${error.message}`, 'alert-danger');
                this.hideChartContainer();
            });
    }

    renderChart(data) {
        this.hideMessage();
        this.chartContainer.style.display = 'block';

        const labels = data.games.map(g => {
            const date = new Date(g.date);
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        });

        // Destroy previous chart if it exists
        if (this.chartInstance) {
            this.chartInstance.destroy();
        }

        // Render appropriate chart type
        if (this.currentStatType === 'game_score') {
            this.renderLineChart(labels, data);
        } else if (this.currentStatType === 'goals_assists') {
            this.renderBarChart(labels, data);
        }
    }

    renderLineChart(labels, data) {
        const colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#C9CBCF', '#FF6384'];
        const datasets = [];

        data.players.forEach((player, index) => {
            const playerData = data.games.map(game => {
                return game[player] ? game[player].game_score : null;
            });

            datasets.push({
                label: player,
                data: playerData,
                borderColor: colors[index % colors.length],
                backgroundColor: colors[index % colors.length] + '20',
                borderWidth: 2,
                fill: false,
                tension: 0.3,
                pointBackgroundColor: colors[index % colors.length],
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6
            });
        });

        this.chartInstance = new Chart(this.chartCanvas, {
            type: 'line',
            data: {
                labels: labels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Game Score Trend'
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Game Score'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Date'
                        }
                    }
                }
            }
        });
    }

    renderBarChart(labels, data) {
        const colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#C9CBCF', '#FF6384'];
        const datasets = [];

        data.players.forEach((player, playerIndex) => {
            const goalsData = data.games.map(g => (g[player] ? g[player].goals : 0));
            const assistsData = data.games.map(g => (g[player] ? g[player].assists : 0));

            datasets.push({
                label: `${player} - Goals`,
                data: goalsData,
                backgroundColor: colors[playerIndex % colors.length],
                stack: `stack-${playerIndex}`
            });

            datasets.push({
                label: `${player} - Assists`,
                data: assistsData,
                backgroundColor: colors[playerIndex % colors.length] + '80',
                stack: `stack-${playerIndex}`
            });
        });

        this.chartInstance = new Chart(this.chartCanvas, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Goals & Assists by Game'
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    x: {
                        stacked: false
                    },
                    y: {
                        stacked: true,
                        beginAtZero: true
                    }
                }
            }
        });
    }

    showMessage(message, alertClass = 'alert-info') {
        this.chartMessage.textContent = message;
        this.chartMessage.className = `alert ${alertClass}`;
        this.chartMessage.style.display = 'block';
    }

    hideMessage() {
        this.chartMessage.style.display = 'none';
    }

    hideChartContainer() {
        this.chartContainer.style.display = 'none';
    }
}
