#!/usr/bin/env python3
import json
import re
from pathlib import Path


HTML_PATH = Path("/Users/anders/Documents/Playground/basis.html")
DATA_PATH = Path("/tmp/jin10_basis_20260402.json")


NAME_MAP = {
    "LU": "低硫燃油",
    "燃油": "高硫燃油",
    "SC原油": "原油",
    "EB": "苯乙烯",
    "EG": "乙二醇",
    "32%液碱": "烧碱",
    "重质纯碱": "纯碱",
    "橡胶": "天然橡胶",
    "上证50股指期货(IH)": "上证50",
    "沪深300股指期货(IF)": "沪深300",
    "中证500股指期货(IC)": "中证500",
    "中证1000股指期货(IM)": "中证1000",
    "沪铜": "铜",
    "沪铝": "铝",
    "沪锌": "锌",
    "沪铅": "铅",
    "沪镍": "镍",
    "沪锡": "锡",
    "沪金": "黄金",
    "沪银": "白银",
}

SECTOR_MAP = {
    "黑色系": "黑色",
    "金属": "有色",
    "农产品": "农产品",
    "能源化工": "能化",
    "金融": "金融",
}


def transform_items():
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    rows = []
    for idx, item in enumerate(payload["items"], start=1):
        history = item["history"][-60:]
        rows.append(
            {
                "id": f"item-{idx:02d}",
                "name": NAME_MAP.get(item["category"], item["category"]),
                "sourceName": item["category"],
                "sector": SECTOR_MAP.get(item["group_name"], item["group_name"]),
                "groupName": item["group_name"],
                "spotPrice": item["spot_price"],
                "spotChange": item["spot_change"],
                "basis": item["basis"],
                "basisChange": item["basis_change"],
                "premiumRate": item["premium_rate"],
                "location": item["city"],
                "unit": item["unit"],
                "futuresPrice": item["futures_price"],
                "futuresChange": item["futures_change"],
                "sourceDate": item["source_date"],
                "publishedToday": item["published_today"],
                "history": history,
            }
        )
    return payload["report_date"], rows


def build_script(report_date: str, rows):
    raw_rows_json = json.dumps(rows, ensure_ascii=False, separators=(",", ":"))
    script = r'''
    <script>
        const reportDate = '__REPORT_DATE__';
        const reportTime = '金十期货基差日历';
        const reportSource = '金十期货基差日历';
        const rawRows = __RAW_ROWS__;

        function formatChineseDate(dateStr) {
            const [year, month, day] = dateStr.split('-').map(Number);
            return `${year}年${month}月${day}日`;
        }

        function isNumeric(value) {
            return value !== null && value !== undefined && value !== '' && !Number.isNaN(Number(value));
        }

        function formatNumber(num) {
            if (!isNumeric(num)) return '-';
            const n = Number(num);
            const decimals = Number.isInteger(n) ? 0 : 2;
            return n.toLocaleString('zh-CN', {
                minimumFractionDigits: 0,
                maximumFractionDigits: decimals
            });
        }

        function formatSignedValue(rawValue, numericFallback = null) {
            const value = rawValue !== undefined ? rawValue : numericFallback;
            if (!isNumeric(value)) return '-';
            const n = Number(value);
            const sign = n > 0 ? '+' : '';
            return `${sign}${formatNumber(n)}`;
        }

        function formatPercent(num) {
            if (!isNumeric(num)) return '-';
            const n = Number(num);
            const sign = n > 0 ? '+' : '';
            return `${sign}${n.toFixed(1)}%`;
        }

        function getColorClass(val) {
            if (!isNumeric(val) || Number(val) === 0) return 'text-gray-500';
            return Number(val) > 0 ? 'text-red-500' : 'text-green-500';
        }

        function getBgColorClass(val) {
            if (!isNumeric(val) || Number(val) === 0) return 'bg-gray-100 text-gray-500';
            return Number(val) > 0 ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-600';
        }

        function getDriverBgClass(driver) {
            if (driver === '现货驱动') return 'bg-blue-50 text-blue-700';
            if (driver === '期货驱动') return 'bg-purple-50 text-purple-700';
            if (driver === '双边共振') return 'bg-orange-50 text-orange-700';
            return 'bg-gray-100 text-gray-700';
        }

        function inferDriver(item) {
            const spotMove = Number(item.spotChange || 0);
            const futuresMove = Number(item.futuresChange || 0);
            const basisMove = Number(item.basisChange || 0);
            if (!isNumeric(item.spotChange) && isNumeric(item.futuresChange)) return '期货驱动';
            if (Math.abs(spotMove) > Math.abs(futuresMove) + 20) return '现货驱动';
            if (Math.abs(futuresMove) > Math.abs(spotMove) + 20) return '期货驱动';
            if (Math.abs(basisMove) >= 50) return '双边共振';
            return '双边共振';
        }

        function inferStatusTag(item) {
            if (item.premiumRate >= 10) return '高升水';
            if (item.premiumRate <= -10) return '深贴水';
            if (item.basisChange >= 100) return '基差走强';
            if (item.basisChange <= -100) return '基差走弱';
            if (item.premiumRate > 0) return '小幅升水';
            if (item.premiumRate < 0) return '小幅贴水';
            return '平水附近';
        }

        function computePercentile(history) {
            const recent = history.slice(-20).map(entry => Number(entry.basis)).filter(value => !Number.isNaN(value));
            if (!recent.length) return 50;
            const sorted = [...recent].sort((a, b) => a - b);
            const latest = recent[recent.length - 1];
            const rank = sorted.filter(value => value <= latest).length;
            return Math.round((rank / sorted.length) * 100);
        }

        function buildDriverDesc(item) {
            const spotText = isNumeric(item.spotChange)
                ? `现货${formatSignedValue(item.spotChange)}`
                : '现货持平';
            const futuresText = isNumeric(item.futuresChange)
                ? `期货${formatSignedValue(item.futuresChange)}`
                : '期货持平';
            const basisText = item.basisChange > 0 ? '基差走强' : item.basisChange < 0 ? '基差走弱' : '基差持稳';
            return `${formatChineseDate(item.sourceDate)} ${spotText}，${futuresText}，${basisText}。`;
        }

        function buildCaliber(item) {
            return {
                source: reportSource,
                region: item.location,
                frequency: '日度（15:00收盘）',
                tax: '按金十原始口径',
                conversion: `单位：${item.unit}`,
                contractMonth: '主力合约收盘价'
            };
        }

        const mockData = rawRows.map(item => ({
            ...item,
            statusTag: inferStatusTag(item),
            driver: inferDriver(item),
            driverDesc: buildDriverDesc(item),
            percentile20d: computePercentile(item.history),
            caliber: buildCaliber(item)
        }));

        const sectorOrder = ['黑色', '有色', '能化', '农产品', '金融'];
        const sectorData = sectorOrder
            .map(name => {
                const items = mockData.filter(item => item.sector === name);
                if (!items.length) return null;
                return {
                    name,
                    strong: items.filter(item => item.basisChange > 0).length,
                    weak: items.filter(item => item.basisChange < 0).length,
                    avgRate: items.reduce((sum, item) => sum + Number(item.premiumRate || 0), 0) / items.length,
                    top: [...items]
                        .sort((a, b) => Math.abs(Number(b.basisChange || 0)) - Math.abs(Number(a.basisChange || 0)))
                        .slice(0, 3)
                        .map(item => item.name)
                };
            })
            .filter(Boolean);

        let currentTab = 'widening';
        let currentDetailId = mockData[0] ? mockData[0].id : null;
        let chartType = 'basis';
        let chartTimeframe = 20;
        let myChart = null;
        let searchQuery = '';
        let searchSector = null;
        let searchStatus = null;
        const allSectors = [...new Set(mockData.map(d => d.sector))];
        const allStatuses = ['升水', '贴水', '走强', '走弱'];

        function buildMarketSummary(data) {
            const strong = data.filter(item => item.basisChange > 0).length;
            const weak = data.filter(item => item.basisChange < 0).length;
            const leaders = [...data]
                .sort((a, b) => Math.abs(Number(b.basisChange || 0)) - Math.abs(Number(a.basisChange || 0)))
                .slice(0, 3)
                .map(item => item.name);
            return `基于金十 ${formatChineseDate(reportDate)} 最新完整日度基差数据，共跟踪 ${data.length} 个品种；基差走强 ${strong} 个、走弱 ${weak} 个，${leaders.join('、')} 变动居前。`;
        }

        function buildAlerts(data) {
            return [...data]
                .sort((a, b) => Math.abs(Number(b.basisChange || 0)) - Math.abs(Number(a.basisChange || 0)))
                .slice(0, 2)
                .map(item => {
                    const nearText = item.percentile20d >= 80
                        ? '接近近20日高位'
                        : item.percentile20d <= 20
                            ? '接近近20日低位'
                            : `位于近20日 ${item.percentile20d}% 分位`;
                    return {
                        name: item.name,
                        text: `基差日变 ${formatSignedValue(item.basisChange)}，当前${item.premiumRate >= 0 ? '升水' : '贴水'}幅度 ${Math.abs(Number(item.premiumRate)).toFixed(1)}%，${nearText}。`
                    };
                });
        }

        function renderMarketOverview() {
            document.getElementById('current-date').innerText = formatChineseDate(reportDate);
            document.getElementById('market-summary').innerText = buildMarketSummary(mockData);

            const alertsHtml = buildAlerts(mockData).map(item => `
                <div class="flex items-start">
                    <div class="w-1.5 h-1.5 rounded-full bg-orange-400 mt-1.5 mr-2 shrink-0"></div>
                    <p class="text-sm text-orange-800">
                        <span class="font-semibold">${item.name}</span> ${item.text}
                    </p>
                </div>
            `).join('');
            document.getElementById('alerts-list').innerHTML = alertsHtml;
        }

        let countdownValue = 60;
        setInterval(() => {
            countdownValue--;
            if (countdownValue <= 0) {
                countdownValue = 60;
                renderHomeList();
            }
            document.getElementById('countdown').innerText = countdownValue;
        }, 1000);

        function switchView(viewId) {
            document.querySelectorAll('.view-section').forEach(el => el.classList.remove('active'));
            document.getElementById(`view-${viewId}`).classList.add('active');
            document.querySelectorAll('.nav-btn').forEach(btn => {
                if (btn.dataset.target === viewId) {
                    btn.classList.remove('text-gray-500');
                    btn.classList.add('text-blue-600');
                } else {
                    btn.classList.remove('text-blue-600');
                    btn.classList.add('text-gray-500');
                }
            });
            window.scrollTo(0, 0);
        }

        function goToHome() { switchView('home'); }
        function goToSearch() {
            switchView('search');
            renderSearchFilters();
            renderSearchList();
        }
        function goBack() { switchView('home'); }
        function goToDetail(id) {
            currentDetailId = id;
            renderDetailView();
            switchView('detail');
        }

        function renderHomeList() {
            let data = [...mockData];
            if (currentTab === 'widening') {
                data = data.filter(d => d.basisChange > 0).sort((a, b) => b.basisChange - a.basisChange);
            } else if (currentTab === 'narrowing') {
                data = data.filter(d => d.basisChange < 0).sort((a, b) => a.basisChange - b.basisChange);
            } else if (currentTab === 'premium') {
                data = data.filter(d => d.premiumRate > 0).sort((a, b) => b.premiumRate - a.premiumRate);
            } else if (currentTab === 'discount') {
                data = data.filter(d => d.premiumRate < 0).sort((a, b) => a.premiumRate - b.premiumRate);
            }

            const html = data.slice(0, 5).map(item => `
                <div class="p-4 active:bg-gray-50 transition-colors cursor-pointer" onclick="goToDetail('${item.id}')">
                    <div class="flex justify-between items-start mb-2">
                        <div class="flex items-center space-x-2">
                            <span class="font-semibold text-gray-900">${item.name}</span>
                            <span class="text-[10px] px-1.5 py-0.5 rounded-sm ${getBgColorClass(item.basisChange)}">${item.statusTag}</span>
                        </div>
                        <div class="text-right">
                            <div class="text-sm font-medium text-gray-900">${formatNumber(item.basis)}</div>
                            <div class="text-xs text-gray-400">主力基差</div>
                        </div>
                    </div>
                    <div class="flex justify-between text-xs mt-3">
                        <div>
                            <span class="text-gray-500">日变动: </span>
                            <span class="${getColorClass(item.basisChange)}">${formatSignedValue(item.basisChange)}</span>
                        </div>
                        <div>
                            <span class="text-gray-500">升贴水: </span>
                            <span class="${getColorClass(item.premiumRate)}">${formatPercent(item.premiumRate)}</span>
                        </div>
                        <div>
                            <span class="text-gray-500">现货变动: </span>
                            <span class="${getColorClass(item.spotChange)}">${formatSignedValue(item.spotChange)}</span>
                        </div>
                    </div>
                </div>
            `).join('');

            document.getElementById('home-list').innerHTML = html;
        }

        function renderSectorView() {
            const html = sectorData.map(sector => `
                <div class="bg-white p-3 rounded-xl shadow-sm border border-gray-100">
                    <div class="flex justify-between items-center mb-2">
                        <span class="font-medium text-gray-800">${sector.name}</span>
                        <span class="text-xs font-semibold ${getColorClass(sector.avgRate)}">均 ${formatPercent(sector.avgRate)}</span>
                    </div>
                    <div class="flex space-x-2 text-[10px] text-gray-500 mb-2">
                        <span class="text-red-500 bg-red-50 px-1 rounded">强 ${sector.strong}</span>
                        <span class="text-green-500 bg-green-50 px-1 rounded">弱 ${sector.weak}</span>
                    </div>
                    <div class="text-[10px] text-gray-400 truncate">异动: ${sector.top.join('、')}</div>
                </div>
            `).join('');
            document.getElementById('sector-list').innerHTML = html;
        }

        function renderDetailView() {
            const item = mockData.find(d => d.id === currentDetailId);
            if (!item) return;

            const isPremium = item.premiumRate > 0;
            document.getElementById('detail-title').innerText = item.name;
            document.getElementById('sub-name').innerText = item.name;
            document.getElementById('detail-basis').innerText = formatNumber(item.basis);
            document.getElementById('detail-basis').className = `text-3xl font-bold font-mono ${getColorClass(item.basis)}`;
            document.getElementById('detail-basis-change').innerText = formatSignedValue(item.basisChange);
            document.getElementById('detail-basis-change').className = getColorClass(item.basisChange);
            document.getElementById('detail-premium-label').innerText = isPremium ? '升水幅度' : '贴水幅度';
            document.getElementById('detail-premium').innerText = formatPercent(item.premiumRate);
            document.getElementById('detail-premium').className = `text-xl font-bold font-mono ${getColorClass(item.premiumRate)}`;
            document.getElementById('detail-update-time').innerText = `更新: ${item.sourceDate}`;

            document.getElementById('detail-spot-label').innerText = `现货价 (${item.location})`;
            document.getElementById('detail-spot').innerText = formatNumber(item.spotPrice);
            document.getElementById('detail-spot-change').innerText = formatSignedValue(item.spotChange);
            document.getElementById('detail-spot-change').className = `text-xs mt-0.5 ${getColorClass(item.spotChange)}`;

            document.getElementById('detail-futures-label').innerText = '主力期货 (收盘)';
            document.getElementById('detail-futures').innerText = formatNumber(item.futuresPrice);
            document.getElementById('detail-futures-change').innerText = formatSignedValue(item.futuresChange);
            document.getElementById('detail-futures-change').className = `text-xs mt-0.5 ${getColorClass(item.futuresChange)}`;

            document.getElementById('detail-status-text').innerText = `${isPremium ? '升水' : '贴水'}状态`;
            document.getElementById('detail-percentile').innerText = `当前位于近20日 ${item.percentile20d}% 分位`;
            document.getElementById('detail-driver-desc-short').innerText = item.driverDesc;

            document.getElementById('detail-driver-tag').innerText = item.driver;
            document.getElementById('detail-driver-tag').className = `px-2.5 py-1 text-xs font-medium rounded-md ${getDriverBgClass(item.driver)}`;
            document.getElementById('detail-driver-desc').innerText = item.driverDesc;

            document.getElementById('cal-source').innerText = item.caliber.source;
            document.getElementById('cal-region').innerText = item.caliber.region;
            document.getElementById('cal-freq').innerText = item.caliber.frequency;
            document.getElementById('cal-tax').innerText = item.caliber.tax;
            document.getElementById('cal-conv').innerText = item.caliber.conversion;
            document.getElementById('cal-contract').innerText = item.caliber.contractMonth;

            renderChart();
        }

        function setChartType(type) {
            chartType = type;
            document.querySelectorAll('.chart-tab').forEach(btn => {
                if (btn.dataset.type === type) {
                    btn.classList.remove('text-gray-500');
                    btn.classList.add('bg-white', 'text-blue-600', 'shadow-sm');
                } else {
                    btn.classList.remove('bg-white', 'text-blue-600', 'shadow-sm');
                    btn.classList.add('text-gray-500');
                }
            });
            renderChart();
        }

        function setChartTime(time) {
            chartTimeframe = time;
            document.querySelectorAll('.time-tab').forEach(btn => {
                if (parseInt(btn.dataset.time, 10) === time) {
                    btn.classList.remove('text-gray-400');
                    btn.classList.add('text-blue-600', 'font-medium');
                } else {
                    btn.classList.remove('text-blue-600', 'font-medium');
                    btn.classList.add('text-gray-400');
                }
            });
            renderChart();
        }

        function renderChart() {
            const item = mockData.find(d => d.id === currentDetailId);
            if (!item) return;

            const ctx = document.getElementById('detail-chart').getContext('2d');
            if (myChart) myChart.destroy();

            const dataSlice = item.history.slice(-chartTimeframe);
            const labels = dataSlice.map(d => d.date.substring(5));
            const dataPoints = dataSlice.map(d => d[chartType]);
            const color = chartType === 'basis' ? '#2563eb' : chartType === 'spot' ? '#dc2626' : '#16a34a';
            const labelName = chartType === 'basis' ? '基差' : chartType === 'spot' ? '现货' : '期货';

            myChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels,
                    datasets: [{
                        label: labelName,
                        data: dataPoints,
                        borderColor: color,
                        borderWidth: 2,
                        tension: 0.12,
                        pointRadius: 0,
                        pointHoverRadius: 4,
                        pointBackgroundColor: color
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { mode: 'index', intersect: false },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: 'rgba(255, 255, 255, 0.95)',
                            titleColor: '#6b7280',
                            bodyColor: '#111827',
                            borderColor: '#e5e7eb',
                            borderWidth: 1,
                            padding: 10,
                            displayColors: false,
                            callbacks: {
                                label: function(context) {
                                    return `${context.dataset.label}: ${formatNumber(context.raw)}`;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: { display: false },
                            ticks: { font: { size: 10 }, color: '#9ca3af', maxTicksLimit: 6 }
                        },
                        y: {
                            grid: { color: '#f3f4f6', drawBorder: false },
                            border: { dash: [3, 3] },
                            ticks: {
                                font: { size: 10 },
                                color: '#9ca3af',
                                maxTicksLimit: 5,
                                callback: function(value) { return formatNumber(value); }
                            }
                        }
                    }
                }
            });
        }

        function handleSearchInput() {
            searchQuery = document.getElementById('search-input').value;
            document.getElementById('clear-search-btn').classList.toggle('hidden', !searchQuery);
            renderSearchList();
        }

        function clearSearch() {
            document.getElementById('search-input').value = '';
            handleSearchInput();
        }

        function setSearchFilter(type, val) {
            if (type === 'sector') searchSector = val;
            if (type === 'status') searchStatus = val;
            renderSearchFilters();
            renderSearchList();
        }

        function renderSearchFilters() {
            const sectorHtml = `
                <button onclick="setSearchFilter('sector', null)" class="px-3 py-1 text-xs rounded-full transition-colors ${searchSector === null ? 'bg-blue-600 text-white' : 'bg-white border border-gray-200 text-gray-600'}">全板块</button>
                ${allSectors.map(s => `
                    <button onclick="setSearchFilter('sector', '${s}')" class="px-3 py-1 text-xs rounded-full transition-colors ${searchSector === s ? 'bg-blue-600 text-white' : 'bg-white border border-gray-200 text-gray-600'}">${s}</button>
                `).join('')}
            `;
            document.getElementById('filter-sectors').innerHTML = sectorHtml;

            const statusHtml = `
                <button onclick="setSearchFilter('status', null)" class="px-3 py-1 text-xs rounded-full transition-colors ${searchStatus === null ? 'bg-blue-600 text-white' : 'bg-white border border-gray-200 text-gray-600'}">全状态</button>
                ${allStatuses.map(s => `
                    <button onclick="setSearchFilter('status', '${s}')" class="px-3 py-1 text-xs rounded-full transition-colors ${searchStatus === s ? 'bg-blue-600 text-white' : 'bg-white border border-gray-200 text-gray-600'}">${s}</button>
                `).join('')}
            `;
            document.getElementById('filter-statuses').innerHTML = statusHtml;
        }

        function renderSearchList() {
            const filtered = mockData.filter(item => {
                const matchQuery = item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                    item.location.toLowerCase().includes(searchQuery.toLowerCase()) ||
                    item.sourceName.toLowerCase().includes(searchQuery.toLowerCase());
                const matchSector = searchSector ? item.sector === searchSector : true;
                let matchStatus = true;
                if (searchStatus === '升水') matchStatus = item.premiumRate > 0;
                if (searchStatus === '贴水') matchStatus = item.premiumRate < 0;
                if (searchStatus === '走强') matchStatus = item.basisChange > 0;
                if (searchStatus === '走弱') matchStatus = item.basisChange < 0;
                return matchQuery && matchSector && matchStatus;
            });

            if (filtered.length === 0) {
                document.getElementById('search-results').innerHTML = '';
                document.getElementById('search-empty').classList.remove('hidden');
                document.getElementById('search-empty').classList.add('flex');
            } else {
                document.getElementById('search-empty').classList.add('hidden');
                document.getElementById('search-empty').classList.remove('flex');

                const html = filtered.map(item => `
                    <div class="p-4 active:bg-gray-50 transition-colors cursor-pointer" onclick="goToDetail('${item.id}')">
                        <div class="flex justify-between items-start mb-2">
                            <div class="flex items-center space-x-2">
                                <span class="font-semibold text-gray-900">${item.name}</span>
                                <span class="text-[10px] text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded-sm">${item.sector}</span>
                                <span class="text-[10px] px-1.5 py-0.5 rounded-sm ${getBgColorClass(item.basisChange)}">${item.statusTag}</span>
                            </div>
                            <div class="text-right">
                                <div class="text-sm font-medium text-gray-900">${formatNumber(item.basis)}</div>
                                <div class="text-xs text-gray-400">主力基差</div>
                            </div>
                        </div>
                        <div class="flex justify-between text-xs mt-3">
                            <div>
                                <span class="text-gray-500">日变动: </span>
                                <span class="${getColorClass(item.basisChange)}">${formatSignedValue(item.basisChange)}</span>
                            </div>
                            <div>
                                <span class="text-gray-500">升贴水: </span>
                                <span class="${getColorClass(item.premiumRate)}">${formatPercent(item.premiumRate)}</span>
                            </div>
                            <div>
                                <span class="text-gray-500">现货地: </span>
                                <span class="text-gray-700">${item.location}</span>
                            </div>
                        </div>
                    </div>
                `).join('');
                document.getElementById('search-results').innerHTML = html;
            }
        }

        function switchTab(tabId) {
            currentTab = tabId;
            document.querySelectorAll('.home-tab').forEach(btn => {
                if (btn.dataset.tab === tabId) {
                    btn.classList.remove('text-gray-500');
                    btn.classList.add('text-blue-600');
                    btn.querySelector('.tab-indicator').classList.remove('hidden');
                } else {
                    btn.classList.remove('text-blue-600');
                    btn.classList.add('text-gray-500');
                    btn.querySelector('.tab-indicator').classList.add('hidden');
                }
            });
            renderHomeList();
        }

        function init() {
            renderMarketOverview();
            renderHomeList();
            renderSectorView();
            lucide.createIcons();
        }

        document.addEventListener('DOMContentLoaded', init);
    </script>
'''
    return script.replace("__REPORT_DATE__", report_date).replace("__RAW_ROWS__", raw_rows_json)


def main():
    report_date, rows = transform_items()
    html = HTML_PATH.read_text(encoding="utf-8")
    new_script = build_script(report_date, rows)
    pattern = re.compile(
        r"(\s*<!-- ==================== JavaScript 逻辑 ==================== -->\s*)<script>.*?</script>(\s*</body>)",
        re.S,
    )
    updated = pattern.sub(r"\1" + new_script + r"\2", html, count=1)
    if updated == html:
        raise RuntimeError("Failed to replace script block")
    HTML_PATH.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    main()
