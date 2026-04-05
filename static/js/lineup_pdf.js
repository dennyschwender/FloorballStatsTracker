/**
 * Client-side PDF generation for the lineup page.
 * Depends on: jsPDF (window.jspdf), jsPDF-AutoTable
 * Reads: window.gameData, window.playerData (set inline in game_lineup.html)
 */

function generatePDF() {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF('p', 'mm', 'a4');

    const currentFormat = document.getElementById('formatSelect').value;

    // Common info
    const homeTeam = gameData.homeTeam;
    const awayTeam = gameData.awayTeam;
    const gameDate = gameData.date;
    const team = gameData.team;
    const referee1 = gameData.referee1;
    const referee2 = gameData.referee2;
    const referees = [referee1, referee2].filter(r => r).join(', ');

    // Starting Y position
    let yPos = 15;

    if (currentFormat === 'format-1') {
        // Format 1 - Simple List
        // Add title for Format 1
        doc.setFontSize(16);
        doc.text(`${homeTeam} vs ${awayTeam}`, 105, yPos, { align: 'center' });
        yPos += 6;
        doc.setFontSize(12);
        if (team) {
            doc.text(team, 105, yPos, { align: 'center' });
            yPos += 6;
        }
        if (gameDate) {
            doc.text(gameDate, 105, yPos, { align: 'center' });
            yPos += 6;
        }
        yPos += 4;

        doc.setFontSize(14);
        doc.text('Lineup', 14, yPos);
        yPos += 8;

        const lines = gameData.lines;
        const goalies = gameData.goalies;
        const pp1 = gameData.pp1;
        const pp2 = gameData.pp2;

        doc.setFontSize(10);

        // Lines
        lines.forEach((line, idx) => {
            if (yPos > 270) {
                doc.addPage();
                yPos = 20;
            }
            doc.setFontSize(11);
            doc.setFont(undefined, 'bold');
            doc.text(`Line ${idx + 1}`, 14, yPos);
            yPos += 6;

            doc.setFontSize(10);
            doc.setFont(undefined, 'normal');
            line.forEach(player => {
                const playerInfo = playerData[player] || {};
                const displayName = `${playerInfo.surname || ''} ${playerInfo.name || ''}`.trim() || player;
                doc.text(`  • ${displayName}`, 14, yPos);
                yPos += 5;
            });
            yPos += 3;
        });

        // Goalies
        if (goalies && goalies.length > 0) {
            if (yPos > 270) {
                doc.addPage();
                yPos = 20;
            }
            doc.setFontSize(11);
            doc.setFont(undefined, 'bold');
            doc.text('Goalies', 14, yPos);
            yPos += 6;

            doc.setFontSize(10);
            doc.setFont(undefined, 'normal');
            goalies.forEach(player => {
                const playerInfo = playerData[player] || {};
                const displayName = `${playerInfo.surname || ''} ${playerInfo.name || ''}`.trim() || player;
                doc.text(`  • ${displayName}`, 14, yPos);
                yPos += 5;
            });
            yPos += 3;
        }

        // Power Play formations
        if (pp1 && pp1.length > 0) {
            if (yPos > 270) {
                doc.addPage();
                yPos = 20;
            }
            doc.setFontSize(11);
            doc.setFont(undefined, 'bold');
            doc.text('PP1', 14, yPos);
            yPos += 6;

            doc.setFontSize(10);
            doc.setFont(undefined, 'normal');
            pp1.forEach((player, idx) => {
                const playerInfo = playerData[player] || {};
                const displayName = `${playerInfo.surname || ''} ${playerInfo.name || ''}`.trim() || player;
                doc.text(`  ${idx + 1}. ${displayName}`, 14, yPos);
                yPos += 5;
            });
            yPos += 3;
        }

        if (pp2 && pp2.length > 0) {
            if (yPos > 270) {
                doc.addPage();
                yPos = 20;
            }
            doc.setFontSize(11);
            doc.setFont(undefined, 'bold');
            doc.text('PP2', 14, yPos);
            yPos += 6;

            doc.setFontSize(10);
            doc.setFont(undefined, 'normal');
            pp2.forEach((player, idx) => {
                const playerInfo = playerData[player] || {};
                const displayName = `${playerInfo.surname || ''} ${playerInfo.name || ''}`.trim() || player;
                doc.text(`  ${idx + 1}. ${displayName}`, 14, yPos);
                yPos += 5;
            });
        }

    } else if (currentFormat === 'format-2') {
        // Format 2 - Match browser print layout exactly
        const lines = gameData.lines || [];
        const goalies = gameData.goalies || [];
        const pp1 = gameData.pp1 || [];
        const pp2 = gameData.pp2 || [];
        const bp1 = gameData.bp1 || [];
        const bp2 = gameData.bp2 || [];
        const sixvsfive = gameData.sixvsfive || [];
        const stressLine = gameData.stressLine || [];

        // Reduce margins for more space
        const leftMargin = 10;
        const rightMargin = 10;
        const pageWidth = 210 - leftMargin - rightMargin; // A4 width minus margins

        // Header table with game info
        doc.autoTable({
            body: [
                [{ content: 'Partita:', colSpan: 1 }, { content: `${homeTeam} - ${awayTeam}`, colSpan: 3 }],
                ['Data:', gameDate || '', 'Arbitri:', referees]
            ],
            startY: yPos,
            theme: 'plain',
            styles: {
                fontSize: 9,
                cellPadding: 2,
                lineWidth: 0.5,
                lineColor: 0,
                textColor: 0,
            },
            tableLineWidth: 0.5,
            tableLineColor: 0,
            columnStyles: {
                0: { cellWidth: 20, fontStyle: 'bold' },
                1: { cellWidth: 90 },
                2: { cellWidth: 20, fontStyle: 'bold' },
                3: { cellWidth: 60 },
            },
            margin: { left: leftMargin },
        });

        yPos = doc.lastAutoTable.finalY;

        // Lines table - full width
        const lineRows = [];
        if (lines && lines.length > 0) {
            lines.forEach((line, idx) => {
                const players = line.map(player => {
                    const playerInfo = playerData[player] || {};
                    const surname = playerInfo.surname || '';
                    const name = playerInfo.name || '';
                    // Abbreviate first name to initial
                    const initial = name ? name.charAt(0) + '.' : '';
                    return `${surname} ${initial}`.trim() || player;
                });
                lineRows.push([`${idx + 1}`, players.join('     ')]);
            });
        }

        if (lineRows.length > 0) {
            doc.autoTable({
                body: lineRows,
                startY: yPos,
                theme: 'plain',
                styles: {
                    fontSize: 8,
                    cellPadding: 2,
                    lineWidth: 0.5,
                    lineColor: 0,
                    textColor: 0,
                    overflow: 'visible',
                    cellWidth: 'wrap',
                    minCellHeight: 6,
                    valign: 'middle',
                },
                tableLineWidth: 0.5,
                tableLineColor: 0,
                columnStyles: {
                    0: { cellWidth: 10, fontStyle: 'bold', halign: 'center', fontSize: 10, valign: 'middle' },
                    1: { cellWidth: pageWidth - 10, overflow: 'visible', halign: 'left' },
                },
                margin: { left: leftMargin },
            });
            yPos = doc.lastAutoTable.finalY;
        }

        // Formations and sidebar side by side
        const formStartY = yPos;
        const formWidth = pageWidth * 0.70; // 70% for formations
        const sidebarWidth = pageWidth * 0.30; // 30% for sidebar
        const sidebarX = leftMargin + formWidth;

        // Helper to draw formation with player positions
        const drawFormation = (title, players, positionConfig, x, y, w, h) => {
            doc.setDrawColor(0);
            doc.setLineWidth(0.5);
            doc.rect(x, y, w, h);
            doc.setFontSize(8);
            doc.setFont(undefined, 'bold');
            doc.text(title, x + 2, y + 4);
            doc.setFont(undefined, 'normal');
            doc.setFontSize(6);

            // Always draw position lines to maintain grid structure
            positionConfig.forEach((pos, idx) => {
                const posX = x + pos.x;
                const posY = y + pos.y;
                doc.setDrawColor(0);
                doc.setLineWidth(0.3);
                doc.line(posX, posY, posX + pos.w, posY);

                // Add player name if available
                if (players && players[idx]) {
                    const playerInfo = playerData[players[idx]] || {};
                    const surname = playerInfo.surname || players[idx];
                    doc.text(surname, posX + pos.w / 2, posY - 1, { align: 'center', maxWidth: pos.w });
                }
            });
        };

        // Formations grid - 2x3 layout (70% width)
        const cellW = formWidth / 2;
        const cellH = 35;

        // PP formations (top row) - Grid: 5 cols x 5 rows
        // Positions: 4(col2,row1), 3(col4,row1), 5(col3,row2), 2(col4,row4), 1(col3,row5)
        const ppPos = [
            { x: cellW * 0.35, y: 30, w: cellW * 0.35 },  // Pos 1 (col3, row5) - bottom center
            { x: cellW * 0.60, y: 22, w: cellW * 0.30 },  // Pos 2 (col4, row4) - right mid
            { x: cellW * 0.60, y: 10, w: cellW * 0.30 },  // Pos 3 (col4, row1) - top right
            { x: cellW * 0.10, y: 10, w: cellW * 0.30 },  // Pos 4 (col2, row1) - top left
            { x: cellW * 0.35, y: 16, w: cellW * 0.30 },  // Pos 5 (col3, row2) - center
        ];

        drawFormation('PP1', pp1, ppPos, leftMargin, formStartY, cellW, cellH);
        drawFormation('PP2', pp2, ppPos, leftMargin + cellW, formStartY, cellW, cellH);

        // BP formations (middle row) - Grid: 5 cols x 5 rows
        // Positions: 1(col2,row4), 2(col4,row4), 3(col3,row3), 4(col4,row2)
        const bpPos = [
            { x: cellW * 0.10, y: 24, w: cellW * 0.30 },  // Pos 1 (col2, row4) - bottom left
            { x: cellW * 0.60, y: 24, w: cellW * 0.30 },  // Pos 2 (col4, row4) - bottom right
            { x: cellW * 0.35, y: 18, w: cellW * 0.30 },  // Pos 3 (col3, row3) - center
            { x: cellW * 0.60, y: 12, w: cellW * 0.30 },  // Pos 4 (col4, row2) - top right
        ];

        drawFormation('BP1', bp1, bpPos, leftMargin, formStartY + cellH, cellW, cellH);
        drawFormation('BP2', bp2, bpPos, leftMargin + cellW, formStartY + cellH, cellW, cellH);

        // 6vs5 and Stress Line (bottom row) - Grid: 5 cols x 5 rows
        // Positions: 1(col3,row3), 2(col4,row2), 3(col2,row2), 4(col2,row1), 5(col4,row1), 6(col3,row1)
        const sixVsPos = [
            { x: cellW * 0.35, y: 30, w: cellW * 0.30 },  // Pos 1 (col3, row5) - bottom center
            { x: cellW * 0.60, y: 24, w: cellW * 0.30 },  // Pos 2 (col4, row4) - right
            { x: cellW * 0.10, y: 16, w: cellW * 0.25 },  // Pos 3 (col2, row2) - left mid
            { x: cellW * 0.10, y: 10, w: cellW * 0.25 },  // Pos 4 (col2, row1) - top left
            { x: cellW * 0.60, y: 10, w: cellW * 0.25 },  // Pos 5 (col4, row1) - top right
            { x: cellW * 0.35, y: 10, w: cellW * 0.25 },  // Pos 6 (col3, row1) - top center
        ];

        drawFormation('6vs5', sixvsfive, sixVsPos, leftMargin, formStartY + cellH * 2, cellW, cellH);
        drawFormation('Stress Line', stressLine, sixVsPos, leftMargin + cellW, formStartY + cellH * 2, cellW, cellH);

        // Sidebar with Portieri and Notes (30% width, beside formations)
        const totalFormHeight = cellH * 3;
        doc.setDrawColor(0);
        doc.setLineWidth(0.5);
        doc.rect(sidebarX, formStartY, sidebarWidth, totalFormHeight);

        // Portieri section
        doc.setFontSize(9);
        doc.setFont(undefined, 'bold');
        doc.text('Portieri', sidebarX + 2, formStartY + 5);
        doc.setFont(undefined, 'normal');
        doc.setFontSize(7);
        if (goalies && goalies.length > 0) {
            goalies.forEach((player, idx) => {
                const playerInfo = playerData[player] || {};
                const surname = playerInfo.surname || '';
                const name = playerInfo.name || '';
                const initial = name ? name.charAt(0) + '.' : '';
                doc.text(`${idx + 1} - ${surname} ${initial}`.trim(), sidebarX + 2, formStartY + 10 + (idx * 4));
            });
        }

        // Notes section
        const notesY = formStartY + 25;
        doc.setDrawColor(0);
        doc.setLineWidth(0.5);
        doc.line(sidebarX, notesY, sidebarX + sidebarWidth, notesY);
        doc.setFontSize(9);
        doc.setFont(undefined, 'bold');
        doc.text('Notes', sidebarX + 2, notesY + 5);



    } else if (currentFormat === 'format-3') {
        // Format 3 - Player Roster
        const table = document.getElementById('rosterTable');

        // Get visible columns
        const visibleColumns = Array.from(table.querySelectorAll('thead th'))
            .map((th, index) => ({ th, index, display: th.style.display }))
            .filter(({ display }) => display !== 'none');

        // Get headers
        const headers = visibleColumns.map(({ th }) =>
            th.textContent.trim().replace(/[⇅↑↓]/g, '').trim()
        );

        // Get rows data
        const rows = Array.from(table.querySelectorAll('tbody tr')).map(row => {
            return visibleColumns.map(({ index }) =>
                row.cells[index].textContent.trim()
            );
        });

        doc.setFontSize(14);
        doc.text('Player Roster', 14, yPos);
        yPos += 4;

        // Generate table
        doc.autoTable({
            head: [headers],
            body: rows,
            startY: yPos,
            theme: 'grid',
            styles: {
                fontSize: 10,
                cellPadding: 3,
            },
            headStyles: {
                fillColor: [13, 110, 253],
                textColor: 255,
                fontStyle: 'bold',
            },
            alternateRowStyles: {
                fillColor: [248, 249, 250],
            },
        });

        // Category summary
        const categoryY = doc.lastAutoTable.finalY + 10;
        doc.setFontSize(12);
        doc.text('Players by Category', 14, categoryY);

        // Get category counts from the page
        const categoryTable = document.querySelector('.format-3 .summary-table tbody');
        if (categoryTable) {
            const categoryRows = Array.from(categoryTable.querySelectorAll('tr')).map(row => {
                return Array.from(row.cells).map(cell => cell.textContent.trim());
            });

            doc.autoTable({
                head: [['Category', 'Count']],
                body: categoryRows,
                startY: categoryY + 4,
                theme: 'grid',
                styles: {
                    fontSize: 10,
                    cellPadding: 3,
                },
                headStyles: {
                    fillColor: [108, 117, 125],
                    textColor: 255,
                    fontStyle: 'bold',
                },
                columnStyles: {
                    0: { cellWidth: 50 },
                    1: { cellWidth: 30 },
                },
            });
        }
    }

    // Open PDF in new window instead of downloading
    window.open(doc.output('bloburl'), '_blank');
}
