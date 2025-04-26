let selectedFiles = [];
let batchChart = null;
let isProcessing = false;
let currentResults = [];

function handleFileSelect(files) {
    selectedFiles = [...files].filter(f => f.type.startsWith('image/'));
    document.querySelector('.file-count-badge').textContent = selectedFiles.length;
}

document.getElementById('folderInput').addEventListener('change', e => handleFileSelect(e.target.files));
document.getElementById('multiFileInput').addEventListener('change', e => handleFileSelect(e.target.files));

document.getElementById('startAnalysis').addEventListener('click', async () => {
    if (isProcessing) return;
    if (selectedFiles.length === 0) {
        alert('请先选择文件');
        return;
    }

    isProcessing = true;
    const loadingOverlay = document.getElementById('loadingOverlay');
    const totalCount = selectedFiles.length;
    let processedCount = 0;
    
    loadingOverlay.classList.add('active');
    document.getElementById('totalCount').textContent = totalCount;
    
    let startTime = Date.now();
    const updateInterval = setInterval(() => {
        const timeElapsed = (Date.now() - startTime) / 1000;
        const remainingTime = ((totalCount - processedCount) * (timeElapsed / processedCount)).toFixed(1);
        document.getElementById('estimatedTime').textContent = isNaN(remainingTime) ? '计算中...' : remainingTime;
    }, 1000);

    try {
        const fakeProcessing = setInterval(() => {
            processedCount = Math.min(processedCount + Math.floor(Math.random() * 3) + 1, totalCount);
            document.getElementById('processedCount').textContent = processedCount;
            if (processedCount >= totalCount) clearInterval(fakeProcessing);
        }, 500);

        const formData = new FormData();
        selectedFiles.forEach(file => formData.append('images', file));
        
        const response = await fetch('/batch_predict', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        clearInterval(fakeProcessing);

        updateTable(data.results);
        updateChart(data.results);

    } catch (error) {
        console.error('分析失败:', error);
        alert('处理过程中发生错误');
    } finally {
        clearInterval(updateInterval);
        loadingOverlay.classList.remove('active');
        isProcessing = false;
    }
});

function updateTable(results) {
    const tbody = document.getElementById('resultBody');
    currentResults = results;
    tbody.innerHTML = results.map(result => {
        // 判断是否为正常情况
        const isNormal = result.disease === "正常";
        const severityText = isNormal ? "正常" : result.level;
        const badgeClass = isNormal ? "badge-normal" : getSeverityBadge(result.level);
        return `
        <tr>
            <td class="text-truncate" style="max-width: 200px">${result.filename}</td>
            <td>${result.disease}</td>
            <td>${(result.probability * 100).toFixed(2)}%</td>
            <td>
                <span class="badge ${badgeClass}">
                    ${severityText}
                </span>
            </td>
        </tr>
        `;
    }).join('');
    // 添加点击事件
    document.querySelectorAll('#resultBody tr').forEach((row, index) => {
        row.style.cursor = 'pointer';
        row.addEventListener('click', () => showDetailModal(index));
    });
}

let detailChart = null; // 新增图表实例引用

function showDetailModal(index) {
    const result = currentResults[index];
    if (!result || !result.all_predictions) return;

    // 销毁之前的图表
    if (detailChart) {
        detailChart.destroy();
    }

    // 填充表格数据
    document.getElementById('modalFilename').textContent = result.filename;
    const predictionsHTML = result.all_predictions.map(pred => {
        // 修改点1：处理正常情况的显示
        const severityText = pred.disease === "正常" ? "正常" : pred.level;
        const badgeClass = pred.disease === "正常" ? 
            'badge-normal' : getSeverityBadge(pred.level);
        
        return `
        <tr>
            <td>${pred.disease}</td>
            <td>${(pred.probability * 100).toFixed(2)}%</td>
            <td><span class="badge ${badgeClass}">${severityText}</span></td>
        </tr>
        `;
    }).join('');
    document.getElementById('modalPredictions').innerHTML = predictionsHTML;

    // 准备图表数据
    const labels = result.all_predictions.map(p => p.disease);
    const data = result.all_predictions.map(p => p.probability * 100);
    
    // 修改点2：动态生成颜色数组
    const colors = result.all_predictions.map(p => {
        const probability = p.probability * 100;
        if (probability > 70) return '#FF4757';     // 红色
        if (probability > 25) return '#FFA502';     // 橙色
        return '#F1C40F';                          // 黄色
    });

    // 创建柱状图
    const ctx = document.getElementById('detailChart').getContext('2d');
    detailChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '概率 (%)',
                data: data,
                backgroundColor: colors,  // 使用动态生成的颜色
                borderWidth: 0,
                barThickness: 30
            }]
        },
        options: {
            indexAxis: 'y',
            maintainAspectRatio: false,
            responsive: true,
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { 
                        color: '#6c757d',
                        callback: function(value) {
                            return value + '%';  // 添加百分比符号
                        }
                    },
                    max: 100  // 固定最大值为100%
                },
                y: {
                    grid: { color: '#f1f3f5' },
                    ticks: {
                        color: '#495057',
                        font: { size: 14 }
                    }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(0,0,0,0.9)',
                    bodyFont: { size: 14 },
                    callbacks: {
                        title: () => '',
                        label: (ctx) => {
                            const value = ctx.parsed.x;
                            return ` ${value.toFixed(2)}%`;
                        }
                    }
                }
            }
        }
    });

    // 显示模态框
    new bootstrap.Modal('#detailModal').show();
}

document.getElementById('exportExcel').addEventListener('click', () => {
    if (currentResults.length === 0) {
        alert("没有可导出的数据");
        return;
    }

    // 创建工作簿
    const ws = XLSX.utils.json_to_sheet(currentResults.map(item => ({
        "文件名": item.filename,
        "疾病类型": item.disease,
        "概率": `${(item.probability * 100).toFixed(2)}%`,
        "严重程度": item.disease === "正常" ? "正常" : item.level
    })));

    // 添加表头
    XLSX.utils.sheet_add_aoa(ws, [["文件名", "疾病类型", "概率", "严重程度"]], { origin: "A1" });

    // 设置列宽
    const wscols = [
        { wch: 40 }, // 文件名列宽
        { wch: 20 }, // 疾病类型列宽
        { wch: 15 }, // 概率列宽
        { wch: 20 }  // 严重程度列宽
    ];
    ws['!cols'] = wscols;

    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "检测结果");

    // 生成文件名
    const date = new Date();
    const filename = `眼疾检测报告_${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}.xlsx`;
    
    // 执行下载
    XLSX.writeFile(wb, filename);
});

function updateChart(results) {
    const diseaseCount = results.reduce((acc, cur) => {
        acc[cur.disease] = (acc[cur.disease] || 0) + 1;
        return acc;
    }, {});

    const ctx = document.getElementById('batchChart').getContext('2d');
    if(batchChart) batchChart.destroy();

    batchChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: Object.keys(diseaseCount),
            datasets: [{
                data: Object.values(diseaseCount),
                backgroundColor: [
                    // 扩展后的颜色数组（共12种颜色）
                    '#00B894', '#0984E3', '#FDCB6E',  
                    '#6C5CE7', '#FF7675', '#55EFC4',  
                    '#D35400', '#8E44AD', '#2ECC71',  
                    '#E74C3C', '#3498DB', '#F1C40F',  
                    '#16A085', '#EB4D4B', '#9B59B6'   
                ],
                borderWidth: 0
            }]
        },
        options: {
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: { 
                        padding: 15,
                        font: { size: 14 }
                    }
                },
                tooltip: {
                    bodyFont: { size: 14 },
                    callbacks: {
                        label: ctx => {
                            const total = results.length;
                            const value = ctx.raw;
                            const percentage = (value / total * 100).toFixed(1);
                            return `${ctx.label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

function getSeverityBadge(level) {
    const map = {
        '正常': 'bg-success',        
        '轻度': 'bg-mild',     
        '中度': 'bg-caution',     
        '重度': 'bg-danger'       
    };
    return map[level] || 'bg-secondary';
}