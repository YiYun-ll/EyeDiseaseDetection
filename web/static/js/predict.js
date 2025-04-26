let isProcessing = false; 
let resultChart = null;
let analysisData = null;
let eventSource = null;


// 初始化默认图片虚化效果
document.addEventListener('DOMContentLoaded', () => {
    const previewImage = document.getElementById('preview-image');
    previewImage.classList.remove('active'); // 确保默认图片保持虚化
});

function updateChart(data) {
    if (!Array.isArray(data) || data.length === 0) {
        throw new Error('无效的图表数据');
    }

    if (resultChart instanceof Chart) {
        resultChart.destroy();
        resultChart = null;
    }

    const sortedData = [...data].sort((a, b) => b.probability - a.probability);
    const labels = sortedData.map(item => item.disease);
    const values = sortedData.map(item => (item.probability * 100).toFixed(4));
    const levels = sortedData.map(item => item.level);

    const ctx = document.getElementById('resultChart').getContext('2d');
    if (!ctx) throw new Error('无法获取图表画布');

    const professionalPalette = {
        highRisk: { // 高风险区间（70%-100%）
            main: '#ff6b6b',
            light: '#ff8787',
            border: '#cc5555'
        },
        mediumRisk: { // 中风险区间（50%-70%）
            main: '#ffd93d',
            light: '#ffea83',
            border: '#ccb032'
        },
        lowRisk: { // 低风险区间（0%-50%）
            main: '#4cc9f0',
            light: '#8be9fd',
            border: '#3aa3c0'
        }
    };
    
    resultChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '检测概率 (%)',
                data: values,
                backgroundColor: values.map(v => {
                    const num = parseFloat(v);
                    if (num >= 70) return professionalPalette.highRisk.main;
                    if (num >= 50) return professionalPalette.mediumRisk.main;
                    return professionalPalette.lowRisk.main;
                }),
                borderColor: values.map(v => {
                    const num = parseFloat(v);
                    if (num >= 70) return professionalPalette.highRisk.border;
                    if (num >= 50) return professionalPalette.mediumRisk.border;
                    return professionalPalette.lowRisk.border;
                }),
                borderWidth: 2,
                borderRadius: 6,
                barPercentage: 0.85,
                categoryPercentage: 0.9,
                shadowOffsetX: 3,
                shadowOffsetY: 3,
                shadowBlur: 8,
                shadowColor: 'rgba(0,0,0,0.2)'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    title: { display: true, text: '概率百分比 (%)' },
                    ticks: { callback: value => `${value}%`, color: '#666' },
                    grid: { color: '#eee' }
                },
                x: {
                    title: { display: true, text: '疾病类型'},
                    ticks: {
                        autoSkip: false,
                        maxRotation: 45,
                        minRotation: 45,
                        color: '#444',
                        font: { size: 12 }
                    },
                    grid: { display: false }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    enabled: true,
                    callbacks: {
                        title: (context) => `${context[0].label}`,
                        label: (context) => {
                            const idx = context.dataIndex;
                            return [`概率: ${values[idx]}%`, `严重程度: ${levels[idx]}`];
                        }
                    },
                    backgroundColor: 'rgba(0,0,0,0.8)',
                    titleFont: { size: 14 },
                    bodyFont: { size: 12 }
                },
            
                datalabels: {
                    anchor: 'end',
                    align: 'top',
                    formatter: (value) => {
                        const num = parseFloat(value);
                        return num < 0.0001 ? '< 0.0001%' : `${num.toFixed(2)}%`;
                    },
                    font: { 
                        weight: '600', 
                        size: 12,
                        family: 'Poppins'
                    },
                    color: context => {
                        const value = parseFloat(context.dataset.data[context.dataIndex]);
                        return value > 50 ? 'white' : '#3a0ca3';
                    }
                }
            }
        }
    });
    resultChart.options.onClick = (e, elements) => {
        if (elements.length > 0) {
            const index = elements[0].index;
            const disease = sortedData[index];
            showDiseaseDetail(disease);
        }
    };

    // 添加详情弹窗函数
    function showDiseaseDetail(disease) {
        // 获取疾病详细信息
        const info = diseaseInfo[disease.disease] || {
            description: '相关信息未收录',
            symptoms: '数据更新中',
            advice: '请咨询专业眼科医生'
        };

        const modalContent = `
            <div class="modal-header">
                <h5 class="modal-title">${disease.disease} 详情</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <p class="lead">${info.description}</p>
                <hr>
                <p>检测概率：<strong>${(disease.probability * 100).toFixed(1)}%</strong></p>
                <p>严重程度：<span class="badge ${getSeverityClass(disease.level)}">${disease.level}</span></p>
                
                <div class="mt-3">
                    <h6>常见症状：</h6>
                    <ul class="list-unstyled">
                        ${info.symptoms.split('、').map(s => `<li>• ${s}</li>`).join('')}
                    </ul>
                    
                    <h6>医疗建议：</h6>
                    <div class="alert alert-success">
                        ${info.advice}
                    </div>
                </div>
                
                <div class="alert alert-info mt-3">
                    <i class="bi bi-info-circle"></i> 此结果需结合临床表现综合判断
                </div>
            </div>
        `;

        const modal = new bootstrap.Modal('#detailModal');
        document.getElementById('detailModal').querySelector('.modal-content').innerHTML = modalContent;
        modal.show();
    }

    // 严重程度样式映射
    function getSeverityClass(level) {
        const map = {
            '重度': 'bg-danger',
            '中度': 'bg-warning text-dark',
            '轻度': 'bg-primary'
        };
        return map[level] || 'bg-secondary';
    }
    analysisData = data;
    document.getElementById('analyze-btn').disabled = false;
}

// 图片上传处理
document.getElementById('image-input').addEventListener('change', function(e) {
    const previewImage = document.getElementById('preview-image');
    previewImage.classList.remove('active'); // 先重置虚化状态
    
    const file = e.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            previewImage.src = e.target.result;
            // 添加延迟效果提升用户体验
            setTimeout(() => {
                previewImage.classList.add('active');
            }, 300);
        }
        reader.readAsDataURL(file);
    }
});

// 重置虚化效果当重新选择文件时
document.getElementById('image-input').addEventListener('click', function() {
    document.getElementById('preview-image').classList.remove('active');
});

// 表单提交处理
document.getElementById('upload-form').addEventListener('submit', async function(e) {
    e.preventDefault();
    if (isProcessing) return;
    
    const formData = new FormData(this);
    const loadingElement = document.getElementById('loading');
    const submitButton = document.getElementById('submit-btn');
    
    // 新增：清除之前的分析结果
    const analysisSection = document.querySelector('.analysis-section');
    const chartCanvas = document.getElementById('resultChart');
    const outputDiv = document.getElementById('analysis-output');
    const copyBtn = document.getElementById('copy-btn');

    try {
        // 重置分析区域
        if (resultChart) {
            resultChart.destroy();
            resultChart = null;
        }
        chartCanvas.style.opacity = '0';
        chartCanvas.style.display = 'none';
        analysisSection.style.display = 'none';
        outputDiv.innerHTML = '';
        copyBtn.style.display = 'none';
        
        // 关闭现有SSE连接
        if (eventSource) {
            eventSource.close();
            eventSource = null;
        }
        
        if (!document.getElementById('image-input').files[0]) {
            alert('请先选择图片文件');
            return;
        }
        
        isProcessing = true;
        loadingElement.style.display = 'block';
        submitButton.disabled = true;
        
        // 显示图表容器
        chartCanvas.parentElement.style.height = '560px'; // 恢复默认高度
        setTimeout(() => {
            chartCanvas.style.display = 'block';
            chartCanvas.style.opacity = '1';
        }, 50);

        const response = await fetch('/predict', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) throw new Error(`请求失败: ${response.status}`);
        

        const data = await response.json();
        if (data.result?.length) {
            updateChart(data.result);
            // 新增：存储分析参数
            window.currentAnalysisParams = {
                diseases: data.result.filter(d => d.probability >= 0.25), // 过滤低概率结果
                image_url: data.analysis_params.image_url
            };
            
            // 自动滚动到图表区域
            // setTimeout(() => {
            //     chartCanvas.scrollIntoView({ 
            //         behavior: 'smooth',
            //         block: 'start'
            //     });
            // }, 500);
        } else {
            throw new Error('无效的响应数据');
        }
    } catch (error) {
        console.error('Error:', error);
        alert(error.message);
        
        // 错误时隐藏图表容器
        chartCanvas.style.opacity = '0';
        setTimeout(() => {
            chartCanvas.style.display = 'none';
        }, 300);
    } finally {
        isProcessing = false;
        loadingElement.style.display = 'none';
        submitButton.disabled = false;
    }
});

document.getElementById('analyze-btn').addEventListener('click', () => {
    if (!window.currentAnalysisParams?.diseases?.length) {
        alert('请先完成有效的检测分析');
        return;
    }
    
    // 显示模态框（使用Bootstrap 5）
    const patientModal = new bootstrap.Modal('#patientModal', {
        keyboard: false,
        backdrop: 'static'
    });
    patientModal.show();
});

// 分析按钮点击处理（适配Ollama版本）
document.getElementById('patientForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const patientInfo = {
        age: formData.get('age') || '',
        gender: formData.get('gender') || '',
        occupation: formData.get('occupation') || '',
        medicalHistory: formData.get('medicalHistory') || '',
        additionalInfo: formData.get('additionalInfo') || ''
    };

    // 关闭模态框
    bootstrap.Modal.getInstance('#patientModal').hide();

    // 合并参数
    const diseaseParams = {
        diseases: JSON.stringify(
            window.currentAnalysisParams.diseases
                .filter(d => d.probability >= 0.25) // 再次过滤确保数据安全
                .map(d => ({
                    disease: d.disease,
                    probability: d.probability
                }))
        )
    };
    try{
        // 获取界面元素
        const analysisSection = document.querySelector('.analysis-section');
        const outputDiv = document.getElementById('analysis-output');
        const cotDiv = document.getElementById('cot-output');
        const copyBtn = document.getElementById('copy-btn');

        // 重置界面状态
        outputDiv.innerHTML = '<div class="text-center py-3"><div class="spinner-border spinner-border-sm text-primary"></div> 思考中...</div>';
        copyBtn.style.display = 'none';
        analysisSection.style.display = 'block';
        analysisSection.style.opacity = '1';
        const chartCanvas = document.getElementById('resultChart');
        if (resultChart) {
            resultChart.destroy();
            resultChart = null;
            chartCanvas.style.opacity = '0';
            setTimeout(() => {
                chartCanvas.style.display = 'none'; // 仅隐藏图表本身
                chartCanvas.parentElement.style.height = 'auto'; // 保持容器高度
            }, 300);
        }
        // 关闭现有连接
        if (window.eventSource) {
            window.eventSource.close();
        }

        // 创建新的EventSource连接
        const params = new URLSearchParams({
            diseases: JSON.stringify(  // 直接传JSON字符串
                window.currentAnalysisParams.diseases
                    .filter(d => d.probability >= 0.25)
                    .map(d => ({
                        disease: d.disease,
                        probability: d.probability
                    }))
            ),
            ...Object.fromEntries(
                Object.entries(patientInfo)
                    .filter(([_, v]) => v !== undefined && v !== null) // 过滤无效值
                    .map(([k, v]) => [k === 'medicalHistory' ? 'medicalHistory' : k, v]) // 参数名调整
            )
        });
        window.eventSource = new EventSource(`/stream-analysis?${params}`);

        let cot_full_response = '';
        let answer_full_response = '';
        let cot_buffer = '';
        let answer_buffer = '';
        let isProcessing = false;

        // 处理消息事件（优化后的流式渲染）
        window.eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                
                if (data.error) {
                    outputDiv.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
                    window.eventSource.close();
                    return;
                }
        
                // 创建Markdown到HTML的转换函数（支持H2-H4）
                const mdToHtml = (text) => {
                    return text
                        // 转换四级标题（必须放在三級标题前）
                        .replace(/####\s*(.*?)\n/g, '<h4 class="md-header">$1</h4>')
                        // 转换三级标题（原逻辑保持不变）
                        .replace(/###\s*(.*?)\n/g, '<h3 class="md-header">$1</h3>')
                        // 转换二级标题
                        .replace(/##\s*(.*?)\n/g, '<h2 class="md-header">$1</h2>')
                        // 转换强调文本
                        .replace(/\*\*(.*?)\*\*/g, '<strong class="md-bold">$1</strong>')
                        // 保持列表间隔
                        .replace(/\n\s*-\s/g, '\n• ');
                };
        
                if (data.think) {
                    cot_buffer += data.think;
                    
                    if (!isProcessing) {
                        isProcessing = true;
                        requestAnimationFrame(() => {
                            const fragment = document.createDocumentFragment();
                            const content = document.createElement('div');
                            
                            // 转换Markdown并设置HTML
                            content.innerHTML = mdToHtml(cot_full_response + cot_buffer)
                                // 保留换行符
                                .replace(/\n/g, '<br>');
                            
                            const cursor = document.createElement('span');
                            cursor.className = 'stream-cursor';
                            
                            fragment.appendChild(content.cloneNode(true));
                            fragment.appendChild(cursor);
                            
                            cotDiv.innerHTML = '';
                            cotDiv.appendChild(fragment);
                            cotDiv.scrollTop = cotDiv.scrollHeight;
                            
                            isProcessing = false;
                        });
                    }
                }
                
                if (data.flag) {
                    cotDiv.querySelectorAll('.stream-cursor').forEach(el => el.remove());
                }
                
                if (data.response) {
                    answer_buffer += data.response;
                    
                    if (!isProcessing) {
                        isProcessing = true;
                        requestAnimationFrame(() => {
                            const tempDiv = document.createElement('div');
                            tempDiv.className = 'md-content'; // 添加统一样式类
                            
                            // 转换Markdown格式
                            const formattedContent = mdToHtml(answer_full_response + answer_buffer)
                                // 处理换行和段落
                                .replace(/\n{2,}/g, '</p><p>')
                                .replace(/\n/g, '<br>');
                            
                            tempDiv.innerHTML = `<p>${formattedContent}</p>`;
                            
                            const isScrolledToBottom = outputDiv.scrollHeight - outputDiv.clientHeight <= outputDiv.scrollTop + 50;
                            
                            const cursor = document.createElement('span');
                            cursor.className = 'stream-cursor';
                            
                            outputDiv.innerHTML = '';
                            outputDiv.appendChild(tempDiv);
                            if (isScrolledToBottom) {
                                outputDiv.scrollTop = outputDiv.scrollHeight;
                            }
                            outputDiv.appendChild(cursor);
                            
                            isProcessing = false;
                        });
                    }
                }
        
                if (data.status === 'completed') {
                    // 最终渲染时保证完整样式
                    const finalContent = mdToHtml(answer_full_response + answer_buffer)
                        .replace(/\n/g, '<br>');
                    
                    outputDiv.innerHTML = `<div class="md-final">${finalContent}</div>`;
                    copyBtn.style.display = 'inline-block';
                    window.eventSource.close();
                }
            } catch (err) {
                console.error('解析错误:', err);
            }
        };


    } catch (err) {
        console.error('分析失败:', err);
        document.getElementById('analysis-output').innerHTML = 
            `<div class="alert alert-danger">系统错误: ${err.message}</div>`;
    }
});


// 复制功能增强
document.getElementById('copy-btn').addEventListener('click', () => {
    const text = document.getElementById('analysis-output').innerText;
    navigator.clipboard.writeText(text)
        .then(() => {
            const btn = document.getElementById('copy-btn');
            btn.innerHTML = '<i class="bi bi-check2"></i> 已复制';
            setTimeout(() => {
                btn.innerHTML = '<i class="bi bi-clipboard"></i> 复制结果';
            }, 2000);
        })
        .catch(err => console.error('复制失败:', err));
});