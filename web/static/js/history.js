let currentResults = [];
let originalResults = [];
const chartDom = document.getElementById('chart');
const myChart = echarts.init(chartDom);
let sortState = {
    field: null,
    direction: 'none' // asc/desc/none
};

document.querySelectorAll('.sortable').forEach(header => {
    header.addEventListener('click', () => {
        const field = header.dataset.sort;
        handleSort(field);
    });
});

// 排序处理函数
function handleSort(field) {
    // 切换排序方向
    if (sortState.field === field) {
        sortState.direction = sortState.direction === 'asc' ? 'desc' : 'asc';
    } else {
        sortState.field = field;
        sortState.direction = 'asc';
    }

    // 执行排序
    const sorted = [...currentResults].sort((a, b) => {
        const valA = getSortValue(a, field);
        const valB = getSortValue(b, field);
        
        if (valA < valB) return sortState.direction === 'asc' ? -1 : 1;
        if (valA > valB) return sortState.direction === 'asc' ? 1 : -1;
        return 0;
    });

    // 更新状态指示
    updateSortIndicators();
    currentResults = sorted;
    updateTable(currentResults);
}

// 获取排序值
function getSortValue(record, field) {
    const severityOrder = { '正常': 0, '轻度': 1, '中度': 2, '重度': 3 };
    
    switch(field) {
        case 'probability':
            return record.top_disease.probability;
        case 'severity':
            return severityOrder[record.top_disease.level] || 0;
        default:
            return 0;
    }
}

// 更新排序指示器
function updateSortIndicators() {
    document.querySelectorAll('.sortable').forEach(header => {
        const arrow = header.querySelector('.sort-arrow');
        if (header.dataset.sort === sortState.field) {
            arrow.classList.add(sortState.direction);
            arrow.style.opacity = 1;
        } else {
            arrow.classList.remove('asc', 'desc');
            arrow.style.opacity = 0.5;
        }
    });
}

// 初始化页面
window.addEventListener('DOMContentLoaded', async () => {
    try {
        const response = await fetch('/predictions.json');
        const data = await response.json();
        originalResults = data; // 保存原始数据
        currentResults = data;
        updateTable(data);
        updateChart();
        
        // 添加搜索事件监听
        document.getElementById('searchInput').addEventListener('input', handleSearch);
    } catch (error) {
        console.error('数据加载失败:', error);
    }
});

function handleSearch() {
    const searchTerm = this.value.toLowerCase().trim();
    
    if (!searchTerm) {
        currentResults = originalResults;
    } else {
        currentResults = originalResults.filter(record => {
            const fileNameMatch = record.image_name.toLowerCase().includes(searchTerm);
            const diseaseMatch = record.top_disease.name.toLowerCase().includes(searchTerm);
            return fileNameMatch || diseaseMatch;
        });
    }
    
    updateTable(currentResults);
    updateChart();
}

function updateTable(results) {
    const tbody = document.getElementById('resultBody');
    currentResults = results;

    const totalCount = originalResults.length;
    const currentCount = results.length;
    const counterText = currentCount === totalCount ? 
        `共 ${totalCount} 条记录` : 
        `显示 ${currentCount} 条（共 ${totalCount} 条）`;
    
    document.getElementById('recordCount').textContent = counterText;
    
    tbody.innerHTML = results.map(record => { 
        const disease = record.top_disease;
        const isNormal = disease.name === "正常";
        const severityText = isNormal ? "正常" : disease.level;
        const badgeClass = getSeverityBadge(isNormal ? "正常" : disease.level);
        
        return `
        <tr>
            <td class="text-truncate" style="max-width: 200px">${record.image_name}</td>
            <td>${disease.name}</td>
            <td>${(disease.probability * 100).toFixed(2)}%</td>
            <td>
                <span class="badge ${badgeClass}">
                    ${severityText}
                </span>
            </td>
        </tr>
        `;
    }).join('');
}

function getSeverityBadge(level) {
    const map = {
        '正常': 'bg-normal',
        '轻度': 'bg-mild',
        '中度': 'bg-caution',
        '重度': 'bg-danger'
    };
    return map[level] || 'bg-secondary';
}

function updateChart() {
    const diseaseCount = currentResults.reduce((acc, record) => {
        const name = record.top_disease.name;
        acc[name] = (acc[name] || 0) + 1;
        return acc;
    }, {});

    const option = {
        title: {
            text: '疾病分布统计',
            left: 'center',
            textStyle: { fontSize: 18 }
        },
        tooltip: {
            trigger: 'item',
            formatter: '{a} <br/>{b}: {c} ({d}%)'
        },
        legend: {
            orient: 'vertical',
            left: 'left',
            top: 30
        },
        series: [{
            name: '疾病分布',
            type: 'pie',
            radius: '60%',
            data: Object.entries(diseaseCount).map(([name, value]) => ({
                name,
                value,
                itemStyle: {
                    borderRadius: 5,
                    borderColor: '#fff',
                    borderWidth: 2
                }
            })),
            // label: { show: true, formatter: '{b}: {c} ({d}%)' },
            emphasis: {
                itemStyle: {
                    shadowBlur: 10,
                    shadowOffsetX: 0,
                    shadowColor: 'rgba(0, 0, 0, 0.5)'
                }
            }
        }],
        color: ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452', '#9a60b4']
    };

    myChart.setOption(option);
    window.addEventListener('resize', () => myChart.resize());
}

// 新增点击事件处理
document.getElementById('resultBody').addEventListener('click', (event) => {
    const row = event.target.closest('tr');
    if (!row) return;

    const index = Array.from(row.parentNode.children).indexOf(row);
    showDetailModal(currentResults[index]);
});

let detailChart = null;

function showDetailModal(data) {
    // 更新文件名
    document.getElementById('modalFilename').textContent = data.image_name;

    // 生成详细预测表格
    const tbody = document.getElementById('modalPredictions');
    tbody.innerHTML = Object.entries(data.all_diseases)
        .sort((a, b) => b[1] - a[1])
        .map(([disease, prob]) => {
            // 修改点：传入疾病名称参数
            const level = getSeverityLevel(prob, disease);
            return `
            <tr>
                <td>${disease}</td>
                <td>
                    <div class="d-flex align-items-center">
                        <span class="me-2">${(prob * 100).toFixed(1)}%</span>
                        <div class="disease-progress w-75">
                            <div class="progress-bar ${getSeverityColor(level)}" 
                                    role="progressbar" 
                                    style="width: ${prob * 100}%">
                            </div>
                        </div>
                    </div>
                </td>
                <td>
                    <span class="badge ${getSeverityBadge(level)}">
                        ${level}
                    </span>
                </td>
            </tr>
            `;
        }).join('');

    // 更新图表
    if (detailChart) detailChart.destroy();
    
    const ctx = document.getElementById('detailChart').getContext('2d');
    const diseases = Object.keys(data.all_diseases);
    
    // 定义8种疾病的颜色（包含正常状态）
    const colorPalette = [
        '#5470c6', // 蓝色-疾病1
        '#91cc75', // 绿色-疾病2
        '#fac858', // 黄色-疾病3
        '#ee6666', // 红色-疾病4
        '#73c0de', // 浅蓝-疾病5
        '#3ba272', // 深绿-疾病6
        '#fc8452', // 橙色-疾病7
        '#9a60b4'  // 紫色-疾病8
    ];

    // 动态生成颜色数组（循环使用颜色）
    const backgroundColors = diseases.map((disease, index) => {
        // 如果是正常状态使用绿色（可单独设置）
        return disease === '正常' 
            ? '#28a745' 
            : colorPalette[index % colorPalette.length];
    });

    detailChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: diseases,
            datasets: [{
                label: '疾病概率',
                data: Object.values(data.all_diseases).map(v => v * 100),
                backgroundColor: backgroundColors, // 使用颜色数组
                borderWidth: 0,
                borderRadius: 5,
                barThickness: 35 // 控制柱子宽度
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    title: { 
                        text: '概率 (%)', 
                        display: true,
                        font: { weight: 'bold' }
                    },
                    ticks: { 
                        stepSize: 20,
                        font: { size: 12 }
                    }
                },
                x: {
                    grid: { display: false },
                    ticks: {
                        font: { 
                            size: 12,
                            weight: 'bold' 
                        }
                    }
                }
            },
            plugins: {
                legend: { 
                    display: false 
                },
                tooltip: {
                    titleFont: { size: 14 },
                    bodyFont: { size: 12 },
                    padding: 10
                }
            }
        }
    });

    const modal = new bootstrap.Modal(document.getElementById('detailModal'));
    modal.show();

}

// 修改后的严重程度判断函数
function getSeverityLevel(probability, diseaseName) {
    if (diseaseName === '正常') {
        return '正常';
    } else {
        if (probability < 0.3) return '轻度';
        else if (probability < 0.8) return '中度';
        else return '重度';
    }
}

// 颜色映射保持不变
function getSeverityColor(level) {
    const colors = {
        '正常': 'bg-success',
        '轻度': 'bg-warning',
        '中度': 'bg-orange',
        '重度': 'bg-danger'
    };
    return colors[level] || 'bg-secondary';
}

document.getElementById('exportExcel').addEventListener('click', exportToExcel);

function exportToExcel() {
    /* 创建主表数据 */
    const mainData = currentResults.map(record => ({
        '文件名': record.image_name,
        '疾病名称': record.top_disease.name,
        '概率 (%)': (record.top_disease.probability * 100).toFixed(2),
        '严重程度': record.top_disease.level
    }));

    /* 创建详细数据（展开所有疾病） */
    const detailData = currentResults.flatMap(record => 
        Object.entries(record.all_diseases).map(([disease, prob]) => ({
            '关联文件名': record.image_name,
            '疾病类型': disease,
            '概率 (%)': (prob * 100).toFixed(2),
            '严重程度': getSeverityLevel(prob, disease)
        }))
    );

    /* 创建工作簿 */
    const wb = XLSX.utils.book_new();
    
    /* 创建主表 */
    const mainSheet = XLSX.utils.json_to_sheet(mainData, {
        header: ['文件名', '疾病名称', '概率 (%)', '严重程度'],
        skipHeader: false
    });
    
    /* 创建详细表 */
    const detailSheet = XLSX.utils.json_to_sheet(detailData, {
        header: ['关联文件名', '疾病类型', '概率 (%)', '严重程度'],
        skipHeader: false
    });

    /* 添加样式 */
    const mainHeaderStyle = { font: { bold: true, color: { rgb: "FFFFFF" } }, fill: { fgColor: { rgb: "4F81BD" } } };
    const detailHeaderStyle = { font: { bold: true, color: { rgb: "FFFFFF" } }, fill: { fgColor: { rgb: "C0504D" } } };
    
    /* 设置列宽 */
    mainSheet['!cols'] = [{wch:35}, {wch:20}, {wch:15}, {wch:15}];
    detailSheet['!cols'] = [{wch:35}, {wch:20}, {wch:15}, {wch:15}];

    /* 添加工作表 */
    XLSX.utils.book_append_sheet(wb, mainSheet, '检测汇总');
    XLSX.utils.book_append_sheet(wb, detailSheet, '详细数据');

    /* 导出文件 */
    XLSX.writeFile(wb, `历史检测记录_${new Date().toISOString().slice(0,10)}.xlsx`);
}