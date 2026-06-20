let currentStrategy = 'main';

async function loadDashboard() {
    if (currentStrategy !== 'main') return;
    
    try {
        const res = await fetch('/api/recommendations');
        const data = await res.json();
        
        if(!data.stocks || data.stocks.length === 0) {
            document.getElementById('tableBody').innerHTML = '<tr><td colspan="8" style="text-align:center; color:#94a3b8;">No scan data found. Run the python scanner script.</td></tr>';
            return;
        }
        
        document.getElementById('regimeBadge').innerText = `HMM State ${data.regime_state} (Mult: ${data.regime_mult})`;
        if(data.last_updated) document.getElementById('lastUpdated').innerText = `Live Data As Of: ${data.last_updated}`;
        
        const tbody = document.getElementById('tableBody');
        tbody.innerHTML = '';
        
        let buyCount = 0, holdCount = 0, rejectCount = 0;
        
        data.stocks.slice(0, 100).forEach(s => {
            if(s.decision === 'BUY') buyCount++;
            else if(s.decision === 'HOLD') holdCount++;
            else rejectCount++;
            
            let trajColor = s.decision === 'BUY' ? 'color: var(--accent-green);' : s.decision === 'REJECT' ? 'color: var(--accent-red);' : 'color: var(--accent-blue);';
            let badgeClass = s.decision;
            
            let slText = s.stop_loss ? `₹${s.stop_loss.toLocaleString('en-IN')}` : '—';
            let tpText = s.target_price ? `₹${s.target_price.toLocaleString('en-IN')}` : '—';
            let posText = s.position_size_pct ? `${s.position_size_pct}%` : '—';
            
            let roeText = (s.roe !== undefined && s.roe !== null) ? `${s.roe}%` : '—';
            let marginText = (s.margin !== undefined && s.margin !== null) ? `${s.margin}%` : '—';
            let roeColor = s.roe > 15 ? 'var(--accent-green)' : s.roe > 8 ? 'var(--accent-blue)' : 'var(--accent-red)';
            
            tbody.innerHTML += `
                <tr>
                    <td class="t-ticker">${s.ticker}</td>
                    <td class="t-price">₹${s.current_price.toLocaleString('en-IN', {minimumFractionDigits: 2})}</td>
                    <td style="font-size: 12px; font-weight: 600; ${trajColor}">${s.trajectory}</td>
                    <td class="t-score">${s.final_score.toFixed(1)}</td>
                    <td><span class="badge ${badgeClass}">${s.decision}</span></td>
                    <td style="font-size: 12px; color: ${roeColor};">${roeText} <span style="color:#475569; font-size:10px;">ROE</span></td>
                    <td style="font-size: 12px;">
                        <span style="color: var(--accent-red);">SL: ${slText}</span><br>
                        <span style="color: var(--accent-green);">TP: ${tpText}</span>
                    </td>
                    <td style="font-size: 13px; font-weight: 600; color: var(--accent-blue);">${posText}</td>
                </tr>
            `;
        });
        
        const summaryEl = document.getElementById('scanSummary');
        if(summaryEl) {
            summaryEl.innerHTML = `<span style="color: var(--accent-green);">● ${buyCount} BUY</span> &nbsp; <span style="color: var(--accent-blue);">● ${holdCount} HOLD</span> &nbsp; <span style="color: var(--accent-red);">● ${rejectCount} REJECT</span>`;
        }
    } catch (error) {
        console.error("Error loading dashboard:", error);
    }
}

async function loadSmallCapDashboard() {
    if (currentStrategy !== 'smallcap') return;
    
    try {
        const response = await fetch('/api/smallcap');
        const data = await response.json();
        
        if (data.last_updated) {
            document.getElementById('lastUpdated').innerText = `Last Updated: ${data.last_updated}`;
        }
        
        const tbody = document.getElementById('tableBody');
        tbody.innerHTML = '';
        
        if (!data.candidates || data.candidates.length === 0) {
            tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 40px;">No small-cap candidates passed the quality gates today.</td></tr>`;
            document.getElementById('scanSummary').innerText = `Module Active: 0 Matches`;
            return;
        }
        
        document.getElementById('scanSummary').innerText = `Module Active: ${data.candidates.length} Alpha Patterns Found`;
        
        data.candidates.forEach(stock => {
            const tr = document.createElement('tr');
            
            // Score styling
            let scoreColor = 'var(--text-main)';
            if (stock.score >= 80) scoreColor = 'var(--accent-green)';
            else if (stock.score >= 60) scoreColor = '#f59e0b';
            else scoreColor = 'var(--accent-red)';
            
            // Liquidity Status badge
            let liqBadge = 'HOLD';
            if (stock.status === 'SAFE') liqBadge = 'BUY';
            else if (stock.status === 'CAUTION') liqBadge = 'HOLD';
            else liqBadge = 'REJECT';
            
            tr.innerHTML = `
                <td class="t-ticker">${stock.ticker}</td>
                <td class="t-price">₹${stock.current_price.toFixed(2)}</td>
                <td><span style="color: var(--accent-blue); font-weight: 500;">${stock.pattern}</span></td>
                <td class="t-score" style="color: ${scoreColor}">${stock.score}</td>
                <td><span class="badge ${liqBadge}">${stock.status}</span></td>
                <td style="font-family: monospace;">${stock.liquidity_ratio.toFixed(2)}x Avg Vol</td>
                <td>${stock.max_holding_days ? stock.max_holding_days + ' Days Max' : 'Indefinite'}</td>
                <td>
                    <button class="action-btn" onclick="addPosition('${stock.ticker}', ${stock.current_price}, 100, '${stock.pattern}')">
                        + Add Pos (₹${stock.position_size.toLocaleString()})
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
        
    } catch (error) {
        console.error("Error loading smallcap dashboard:", error);
    }
}

function switchStrategy(strategy) {
    currentStrategy = strategy;
    
    // Update active tab UI
    document.getElementById('btnMain').className = strategy === 'main' ? 'tab-btn active' : 'tab-btn';
    document.getElementById('btnSmall').className = strategy === 'smallcap' ? 'tab-btn active' : 'tab-btn';
    
    // Update Headers
    const tableHead = document.getElementById('tableHead');
    const tableTitle = document.getElementById('tableTitle');
    
    if (strategy === 'main') {
        tableTitle.innerText = "Top 100 Live Market Scanner (Core)";
        tableHead.innerHTML = `
            <tr>
                <th>TICKER</th>
                <th>CURRENT PRICE</th>
                <th>PREDICTED TRAJECTORY</th>
                <th>SCORE</th>
                <th>SIGNAL</th>
                <th>FUNDAMENTALS</th>
                <th>SL / TARGET</th>
                <th>POSITION</th>
            </tr>
        `;
        loadDashboard();
    } else {
        tableTitle.innerText = "Small-Cap Alpha Momentum (Module 2)";
        tableHead.innerHTML = `
            <tr>
                <th>TICKER</th>
                <th>CURRENT PRICE</th>
                <th>PATTERN</th>
                <th>SCORE</th>
                <th>STATUS</th>
                <th>LIQ. RATIO</th>
                <th>MAX HOLDING</th>
                <th>POSITION</th>
            </tr>
        `;
        loadSmallCapDashboard();
    }
}

async function loadPortfolio() {
    const res = await fetch('/api/portfolio');
    const items = await res.json();
    
    const list = document.getElementById('portfolioList');
    list.innerHTML = items.length === 0 ? '<div style="color: #94a3b8; font-size: 14px; margin-top: 10px;">No active positions.</div>' : '';
    
    items.forEach(i => {
        list.innerHTML += `
            <div class="portfolio-item">
                <div>
                    <div class="p-ticker">${i.ticker}</div>
                    <div class="p-detail">${i.quantity} shares @ ₹${i.buy_price.toFixed(2)} | ${i.term_category}</div>
                </div>
                <button class="btn-sell" onclick="sellPosition(${i.id})">SELL</button>
            </div>
        `;
    });
}

async function addPosition(ticker, price, qty, term) {
    const pTicker = ticker || document.getElementById('pTicker').value;
    const pPrice = price || document.getElementById('pPrice').value;
    const pQty = qty || document.getElementById('pQty').value;
    const pTerm = term || document.getElementById('pTerm').value;
    
    if(!pTicker || !pPrice || !pQty) return alert("Please fill all fields.");
    
    await fetch('/api/portfolio', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ticker: pTicker, buy_price: parseFloat(pPrice), quantity: parseInt(pQty), term_category: pTerm})
    });
    
    if(!ticker) {
        document.getElementById('pTicker').value = '';
        document.getElementById('pPrice').value = '';
        document.getElementById('pQty').value = '';
    }
    
    loadPortfolio();
}

async function sellPosition(id) {
    await fetch(`/api/portfolio/${id}`, {method: 'DELETE'});
    loadPortfolio();
}

loadDashboard();
loadPortfolio();

async function updateLivePrices() {
    const rows = document.querySelectorAll('#tableBody tr');
    const tickers = [];
    rows.forEach(r => {
        const tCell = r.querySelector('.t-ticker');
        if(tCell) tickers.push(tCell.innerText);
    });
    
    if(tickers.length === 0) return;
    
    const res = await fetch('/api/live_prices', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({tickers: tickers})
    });
    const livePrices = await res.json();
    
    rows.forEach(r => {
        const t = r.querySelector('.t-ticker').innerText;
        if(livePrices[t]) {
            const priceCell = r.querySelector('.t-price');
            const oldPrice = parseFloat(priceCell.innerText.replace('₹', '').replace(/,/g, ''));
            const newPrice = livePrices[t];
            
            if(Math.abs(newPrice - oldPrice) > 0.01) {
                priceCell.innerText = '₹' + newPrice.toLocaleString('en-IN', {minimumFractionDigits: 2});
                
                priceCell.style.color = newPrice > oldPrice ? 'var(--accent-green)' : 'var(--accent-red)';
                priceCell.style.transition = 'color 0.2s';
                
                setTimeout(() => { 
                    priceCell.style.color = 'inherit'; 
                }, 2000);
            }
        }
    });
}

setInterval(updateLivePrices, 60000);

function filterTable() {
    let input = document.getElementById("searchInput");
    let filter = input.value.toUpperCase();
    let tableBody = document.getElementById("tableBody");
    let tr = tableBody.getElementsByTagName("tr");

    for (let i = 0; i < tr.length; i++) {
        let tdTicker = tr[i].getElementsByClassName("t-ticker")[0];
        if (tdTicker) {
            let txtValue = tdTicker.textContent || tdTicker.innerText;
            if (txtValue.toUpperCase().indexOf(filter) > -1) {
                tr[i].style.display = "";
            } else {
                tr[i].style.display = "none";
            }
        }       
    }
}
