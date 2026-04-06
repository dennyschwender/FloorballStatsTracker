/**
 * PlayerTrendsUI - Handles player performance trends visualization
 * Displays trajectory charts, consistency charts, and outlier tables
 */
class PlayerTrendsUI {
    constructor() {
        this.selectedPlayers = [];
        this.season = new URLSearchParams(window.location.search).get('season') || '';
        this.team = new URLSearchParams(window.location.search).get('team') || '';
        this.allPlayers = [];
        this.trajectoryChartInstance = null;
        this.consistencyChartInstance = null;

        // DOM elements
        this.playerSearch = document.getElementById('player-trends-search');
        this.playerSuggestions = document.getElementById('player-trends-suggestions');
        this.selectedPlayersContainer = document.getElementById('player-trends-selected');
        this.showTrendsBtn = document.getElementById('show-trends-btn');
        this.trendsLoading = document.getElementById('trends-loading');
        this.trajectoryCanvas = document.getElementById('player-trends-trajectory-chart');
        this.consistencyCanvas = document.getElementById('player-trends-consistency-chart');
        this.outliersTable = document.getElementById('player-trends-outliers-table');
        this.messageElement = document.getElementById('player-trends-message');
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

        if (this.showTrendsBtn) {
            this.showTrendsBtn.addEventListener('click', () => this.fetchAndRenderCharts());
        }

        // Initialize UI state
        this.updateShowTrendsButton();
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
            this.updateShowTrendsButton();
        }
    }

    removeSelectedPlayer(player) {
        this.selectedPlayers = this.selectedPlayers.filter(p => p !== player);
        this.renderSelectedPlayers();
        this.updateShowTrendsButton();
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

    updateShowTrendsButton() {
        if (this.showTrendsBtn) {
            this.showTrendsBtn.disabled = this.selectedPlayers.length === 0;
        }
    }

    fetchAndRenderCharts() {
        if (this.selectedPlayers.length === 0) {
            this.showMessage('Select at least one player', 'alert-warning');
            return;
        }

        if (!this.season || !this.team) {
            this.showMessage('Season and team parameters are required', 'alert-warning');
            return;
        }

        this.showTrendsBtn.disabled = true;
        if (this.trendsLoading) {
            this.trendsLoading.style.display = 'inline-block';
        }
        this.hideMessage();

        // Build query parameters
        const params = new URLSearchParams();
        params.append('season', this.season);
        params.append('team', this.team);
        this.selectedPlayers.forEach(player => params.append('players', player));

        // Fetch player trends data
        fetch(`/api/player-trends?${params}`)
            .then(response => {
                if (!response.ok) {
                    return response.json().then(data => {
                        throw new Error(data.error || 'Failed to load player trends');
                    });
                }
                return response.json();
            })
            .then(data => {
                if (this.trendsLoading) {
                    this.trendsLoading.style.display = 'none';
                }
                this.showTrendsBtn.disabled = false;

                if (!data.success || !data.data || Object.keys(data.data).length === 0) {
                    this.showMessage('No data found for selected players', 'alert-info');
                } else {
                    this.renderCharts(data.data);
                }
            })
            .catch(error => {
                if (this.trendsLoading) {
                    this.trendsLoading.style.display = 'none';
                }
                this.showTrendsBtn.disabled = false;
                this.showMessage(`Error: ${error.message}`, 'alert-danger');
            });
    }

    renderCharts(trendsData) {
        this.hideMessage();

        // Render trajectory chart
        this.renderTrajectoryChart(trendsData);

        // Render consistency chart
        this.renderConsistencyChart(trendsData);

        // Render outliers table
        this.renderOutliersTable(trendsData);
    }

    renderTrajectoryChart(trendsData) {
        const colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#C9CBCF', '#FF6384', '#FFA500', '#00CED1'];
        const datasets = [];

        // Build datasets for each player
        Object.entries(trendsData).forEach((entry, index) => {
            const playerName = entry[0];
            const trends = entry[1];

            if (trends.insufficient_data) {
                return; // Skip players with insufficient data
            }

            const gameNumbers = trends.game_scores.map((_, i) => i + 1);

            datasets.push({
                label: playerName,
                data: trends.game_scores,
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

        // Create labels (game numbers)
        const maxGames = Math.max(...Object.values(trendsData).map(t => t.game_scores.length));
        const labels = Array.from({ length: maxGames }, (_, i) => `Game ${i + 1}`);

        // Destroy old chart if exists
        if (this.trajectoryChartInstance) {
            this.trajectoryChartInstance.destroy();
        }

        // Create new chart
        if (this.trajectoryCanvas && datasets.length > 0) {
            this.trajectoryChartInstance = new Chart(this.trajectoryCanvas, {
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
                            text: 'Player Performance Trajectory'
                        },
                        legend: {
                            display: true,
                            position: 'top'
                        }
                    },
                    scales: {
                        y: {
                            title: {
                                display: true,
                                text: 'Game Score'
                            }
                        },
                        x: {
                            title: {
                                display: true,
                                text: 'Game Number'
                            }
                        }
                    }
                }
            });
        }
    }

    renderConsistencyChart(trendsData) {
        const colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#C9CBCF', '#FF6384', '#FFA500', '#00CED1'];
        const datasets = [];
        const playerLabels = [];

        // Build box plot data for each player
        Object.entries(trendsData).forEach((entry, index) => {
            const playerName = entry[0];
            const trends = entry[1];

            if (trends.insufficient_data) {
                return; // Skip players with insufficient data
            }

            playerLabels.push(playerName);

            // Calculate quartiles and whiskers
            const scores = [...trends.game_scores].sort((a, b) => a - b);
            const n = scores.length;
            const q1Index = Math.floor(n * 0.25);
            const q3Index = Math.floor(n * 0.75);
            const medianIndex = Math.floor(n * 0.5);

            const q1 = scores[q1Index];
            const median = scores[medianIndex];
            const q3 = scores[q3Index];
            const min = Math.min(...scores);
            const max = Math.max(...scores);

            // For box plot in Chart.js, we'll create a custom bar chart representation
            // Store box plot data in dataset for rendering
            datasets.push({
                label: playerName,
                data: [
                    { x: playerName, q1, median, q3, min, max, mean: trends.mean_score }
                ],
                backgroundColor: colors[index % colors.length],
                borderColor: colors[index % colors.length],
                borderWidth: 1
            });
        });

        // Destroy old chart if exists
        if (this.consistencyChartInstance) {
            this.consistencyChartInstance.destroy();
        }

        // Create custom box plot visualization
        if (this.consistencyCanvas && datasets.length > 0) {
            const ctx = this.consistencyCanvas.getContext('2d');
            const rect = this.consistencyCanvas.parentElement.getBoundingClientRect();
            const canvasWidth = Math.max(rect.width, 600);
            const canvasHeight = 400;

            // Set canvas dimensions
            this.consistencyCanvas.width = canvasWidth;
            this.consistencyCanvas.height = canvasHeight;

            // Clear canvas
            ctx.clearRect(0, 0, canvasWidth, canvasHeight);

            // Draw box plots manually
            const boxPlotData = datasets.map((ds, idx) => ({
                label: playerLabels[idx],
                ...ds.data[0]
            }));

            this.drawBoxPlots(ctx, boxPlotData, canvasWidth, canvasHeight);
        }
    }

    drawBoxPlots(ctx, boxPlotData, canvasWidth, canvasHeight) {
        const padding = 40;
        const boxWidth = 60;
        const spacing = (canvasWidth - 2 * padding) / (boxPlotData.length || 1);
        const yScale = (canvasHeight - 2 * padding) / (Math.max(...boxPlotData.map(d => d.max)) || 10);

        const colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40'];

        // Draw axes
        ctx.strokeStyle = '#333';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(padding, canvasHeight - padding);
        ctx.lineTo(canvasWidth - padding, canvasHeight - padding);
        ctx.stroke();

        ctx.beginPath();
        ctx.moveTo(padding, padding);
        ctx.lineTo(padding, canvasHeight - padding);
        ctx.stroke();

        // Draw box plots
        boxPlotData.forEach((data, idx) => {
            const x = padding + (idx + 0.5) * spacing;
            const yMin = canvasHeight - padding - data.min * yScale;
            const yQ1 = canvasHeight - padding - data.q1 * yScale;
            const yMedian = canvasHeight - padding - data.median * yScale;
            const yQ3 = canvasHeight - padding - data.q3 * yScale;
            const yMax = canvasHeight - padding - data.max * yScale;

            const color = colors[idx % colors.length];

            // Draw whiskers (min to max)
            ctx.strokeStyle = color;
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(x, yMin);
            ctx.lineTo(x, yMax);
            ctx.stroke();

            // Draw box (Q1 to Q3)
            ctx.fillStyle = color + '40';
            ctx.strokeStyle = color;
            ctx.lineWidth = 2;
            ctx.fillRect(x - boxWidth / 2, yQ3, boxWidth, yQ1 - yQ3);
            ctx.strokeRect(x - boxWidth / 2, yQ3, boxWidth, yQ1 - yQ3);

            // Draw median line
            ctx.strokeStyle = '#000';
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(x - boxWidth / 2, yMedian);
            ctx.lineTo(x + boxWidth / 2, yMedian);
            ctx.stroke();

            // Draw label
            ctx.fillStyle = '#333';
            ctx.font = '12px Arial';
            ctx.textAlign = 'center';
            ctx.fillText(data.label, x, canvasHeight - padding + 25);
        });

        // Draw y-axis labels
        ctx.fillStyle = '#666';
        ctx.font = '12px Arial';
        ctx.textAlign = 'right';
        for (let i = 0; i <= 10; i++) {
            const value = (i * Math.max(...boxPlotData.map(d => d.max))) / 10;
            const y = canvasHeight - padding - value * yScale;
            ctx.fillText(value.toFixed(1), padding - 10, y + 4);
        }
    }

    renderOutliersTable(trendsData) {
        let html = '';

        // Check if there are any outliers
        const hasOutliers = Object.values(trendsData).some(t => t.outliers && t.outliers.length > 0);

        if (!hasOutliers) {
            html = '<p class="text-muted">No significant outliers found (|z-score| > 1.0)</p>';
        } else {
            html += '<div class="table-responsive"><table class="table table-sm table-striped">';
            html += '<thead><tr><th>Player</th><th>Game ID</th><th>Score</th><th>Z-Score</th><th>Type</th></tr></thead>';
            html += '<tbody>';

            Object.entries(trendsData).forEach(entry => {
                const playerName = entry[0];
                const trends = entry[1];

                if (trends.outliers && trends.outliers.length > 0) {
                    trends.outliers.forEach(outlier => {
                        const badgeClass = outlier.type === 'high' ? 'bg-success' : 'bg-danger';
                        html += `<tr>
                            <td>${playerName}</td>
                            <td>${outlier.game_id}</td>
                            <td>${outlier.score.toFixed(2)}</td>
                            <td>${outlier.z_score.toFixed(2)}</td>
                            <td><span class="badge ${badgeClass}">${outlier.type.toUpperCase()}</span></td>
                        </tr>`;
                    });
                }
            });

            html += '</tbody></table></div>';
        }

        this.outliersTable.innerHTML = html;
    }

    showMessage(text, type = 'alert-info') {
        this.messageElement.textContent = text;
        this.messageElement.className = `alert ${type}`;
        this.messageElement.style.display = 'block';
    }

    hideMessage() {
        this.messageElement.style.display = 'none';
    }
}

/**
 * LineupAnalysisUI - Handles lineup combination analysis
 * Displays sortable table of lineup combinations and their performance metrics
 */
class LineupAnalysisUI {
    constructor() {
        this.combos = [];
        this.filteredCombos = [];
        this.season = new URLSearchParams(window.location.search).get('season') || '';
        this.team = new URLSearchParams(window.location.search).get('team') || '';
        this.selectedSize = 'all';
        this.sortColumn = 'avg_aggregate_game_score';
        this.sortAscending = false;

        // DOM elements
        this.sizeSelector = document.getElementById('lineup-combo-size');
        this.tableBody = document.getElementById('lineup-combos-table-body');
        this.messageElement = document.getElementById('lineup-analysis-message');
        this.loadingElement = document.getElementById('lineup-loading');
    }

    init() {
        // Attach event listeners
        if (this.sizeSelector) {
            this.sizeSelector.addEventListener('change', (e) => {
                this.selectedSize = e.target.value;
                this.filterBySize(this.selectedSize);
            });
        }

        // Fetch combos on page load
        this.fetchCombos(5, 7, 10);
    }

    fetchCombos(comboSizeMin, comboSizeMax, limit) {
        if (!this.season || !this.team) {
            this.showMessage('Season and team parameters are required', 'alert-warning');
            return;
        }

        if (this.loadingElement) {
            this.loadingElement.style.display = 'inline-block';
        }
        this.hideMessage();

        const params = new URLSearchParams();
        params.append('season', this.season);
        params.append('team', this.team);
        params.append('combo_size_range', `${comboSizeMin},${comboSizeMax}`);
        params.append('limit', limit.toString());

        fetch(`/api/lineup-combos?${params}`)
            .then(response => {
                if (!response.ok) {
                    return response.json().then(data => {
                        throw new Error(data.error || 'Failed to load lineup combos');
                    });
                }
                return response.json();
            })
            .then(data => {
                if (this.loadingElement) {
                    this.loadingElement.style.display = 'none';
                }

                if (!data.success || !Array.isArray(data.data) || data.data.length === 0) {
                    this.showMessage('No lineup combinations found', 'alert-info');
                    this.combos = [];
                    this.filteredCombos = [];
                } else {
                    this.combos = data.data;
                    this.filterBySize(this.selectedSize);
                    this.renderCombosTable(this.filteredCombos);
                }
            })
            .catch(error => {
                if (this.loadingElement) {
                    this.loadingElement.style.display = 'none';
                }
                this.showMessage(`Error: ${error.message}`, 'alert-danger');
            });
    }

    filterBySize(sizeOrAll) {
        if (sizeOrAll === 'all') {
            this.filteredCombos = [...this.combos];
        } else {
            const size = parseInt(sizeOrAll);
            this.filteredCombos = this.combos.filter(c => c.combo_size === size);
        }

        // Re-sort after filtering
        this.sortTable(this.sortColumn);
        this.renderCombosTable(this.filteredCombos);
    }

    sortTable(columnName) {
        if (this.sortColumn === columnName) {
            // Toggle sort direction if clicking same column
            this.sortAscending = !this.sortAscending;
        } else {
            // New column, default to descending
            this.sortColumn = columnName;
            this.sortAscending = false;
        }

        this.filteredCombos.sort((a, b) => {
            let aVal = a[columnName];
            let bVal = b[columnName];

            // Handle special cases
            if (columnName === 'players') {
                // Sort by number of players
                aVal = a.players.length;
                bVal = b.players.length;
            } else if (typeof aVal === 'string' && typeof bVal === 'string') {
                // String comparison
                aVal = aVal.toLowerCase();
                bVal = bVal.toLowerCase();
                return this.sortAscending ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
            } else if (typeof aVal === 'number' && typeof bVal === 'number') {
                // Numeric comparison
                return this.sortAscending ? aVal - bVal : bVal - aVal;
            }

            return 0;
        });

        this.renderCombosTable(this.filteredCombos);
    }

    renderCombosTable(combos) {
        if (!combos || combos.length === 0) {
            this.tableBody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No combos available</td></tr>';
            return;
        }

        // Calculate performance metrics for coloring
        const scores = combos.map(c => c.avg_aggregate_game_score);
        const maxScore = Math.max(...scores);
        const minScore = Math.min(...scores);
        const scoreRange = maxScore - minScore || 1;

        let html = '';

        combos.forEach((combo, idx) => {
            // Determine row color based on performance
            const normalizedScore = (combo.avg_aggregate_game_score - minScore) / scoreRange;
            let rowColor = 'rgba(255, 255, 255, 1)';

            if (normalizedScore >= 0.8) {
                rowColor = 'rgba(40, 167, 69, 0.1)'; // Green for top performers
            } else if (normalizedScore >= 0.6) {
                rowColor = 'rgba(23, 162, 184, 0.1)'; // Cyan for good performers
            } else if (normalizedScore <= 0.2) {
                rowColor = 'rgba(220, 53, 69, 0.1)'; // Red for bottom performers
            } else if (normalizedScore <= 0.4) {
                rowColor = 'rgba(255, 193, 7, 0.1)'; // Yellow for below average
            }

            const playersList = combo.players.join(', ');
            const gameCount = combo.games_played_together || 0;

            html += `<tr style="background-color: ${rowColor};">
                <td><small>${combo.combo_size}</small></td>
                <td><small>${playersList}</small></td>
                <td class="text-center"><small>${gameCount}</small></td>
                <td class="text-center"><small>${combo.win_percentage.toFixed(1)}%</small></td>
                <td class="text-center"><small>${combo.avg_goal_differential.toFixed(2)}</small></td>
                <td class="text-center"><small><strong>${combo.avg_aggregate_game_score.toFixed(2)}</strong></small></td>
            </tr>`;
        });

        this.tableBody.innerHTML = html;

        // Attach click handlers to table headers for sorting
        this.attachSortHandlers();
    }

    attachSortHandlers() {
        // Get the table element
        const table = document.querySelector('#lineup-combos-table');
        if (!table) return;

        const headers = table.querySelectorAll('thead th');
        const columnMap = {
            0: 'combo_size',
            1: 'players',
            2: 'games_played_together',
            3: 'win_percentage',
            4: 'avg_goal_differential',
            5: 'avg_aggregate_game_score'
        };

        const self = this;
        headers.forEach((header, index) => {
            header.style.cursor = 'pointer';
            header.addEventListener('click', () => {
                const columnName = columnMap[index];
                if (columnName) {
                    self.sortTable(columnName);
                }
            });
        });
    }

    showMessage(text, type = 'alert-info') {
        this.messageElement.textContent = text;
        this.messageElement.className = `alert ${type}`;
        this.messageElement.style.display = 'block';
    }

    hideMessage() {
        this.messageElement.style.display = 'none';
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    // Initialize Player Trends UI
    const playerTrendsUI = new PlayerTrendsUI();

    // Try to fetch all available players from the page or API
    // For now, we'll populate with players from the stats if available
    if (window.allPlayers && Array.isArray(window.allPlayers)) {
        playerTrendsUI.allPlayers = window.allPlayers;
    }

    playerTrendsUI.init();

    // Initialize Lineup Analysis UI
    const lineupAnalysisUI = new LineupAnalysisUI();
    lineupAnalysisUI.init();
});
