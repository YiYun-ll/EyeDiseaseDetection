document.addEventListener('DOMContentLoaded', function() {
    // 元素引用
    const uploadBtn = document.getElementById('uploadBtn');
    const startDetectionBtn = document.getElementById('startDetectionBtn');
    const fileInput = document.getElementById('fileInput');
    const previewImage = document.getElementById('previewImage');
    const uploadPlaceholder = document.getElementById('uploadPlaceholder');
    const resultsContainer = document.getElementById('resultsContainer');
    const noResultsMessage = document.getElementById('noResultsMessage');
    const loadingOverlay = document.getElementById('loadingOverlay');
    const downloadReport = document.getElementById('downloadReport');

    let currentFile = null;
    let currentResults = null;
    let resultsChart = null;

    // 上传单个文件
    uploadBtn.addEventListener('click', function() {
        fileInput.click();
    });

    // 文件选择变化
    fileInput.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            currentFile = e.target.files[0];
            previewSelectedImage(currentFile);
        }
    });

    // 预览选择的图片
    function previewSelectedImage(file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            previewImage.src = e.target.result;
            previewImage.style.display = 'block';
            uploadPlaceholder.style.display = 'none';
        };
        reader.readAsDataURL(file);
    }

    // 开始检测
    startDetectionBtn.addEventListener('click', function() {
        if (currentFile) {
            // 单文件检测
            processFile(currentFile);
        } else {
            alert('请先上传图像');
        }
    });

    // 处理单个文件
    function processFile(file) {
        showLoading();
        
        const formData = new FormData();
        formData.append('file', file);
        
        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            hideLoading();
            if (data.success) {
                displayResults(data.results);
                currentResults = data;
                downloadReport.style.display = 'block';
            } else {
                alert('检测失败: ' + data.error);
            }
        })
        .catch(error => {
            hideLoading();
            alert('发生错误: ' + error);
        });
    }

    // 显示单个结果
    function displayResults(results) {
        resultsContainer.style.display = 'block';
        noResultsMessage.style.display = 'none';
        
        // 准备图表数据
        const labels = [];
        const data = [];
        const backgroundColors = [];
        
        // 添加详细结果
        results.forEach(result => {
            // 添加到图表数据
            labels.push(result.class);
            // 使用归一化后的概率值，并转换为百分比
            data.push(result.normalized_probability * 100);
            backgroundColors.push(result.predicted ? 'rgba(220, 53, 69, 0.8)' : 'rgba(0, 123, 255, 0.5)');
        });
        
        // 创建图表
        if (resultsChart) {
            resultsChart.destroy();
        }
        
        const ctx = document.getElementById('resultsChart').getContext('2d');
        resultsChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: '疾病概率',
                    data: data,
                    backgroundColor: backgroundColors,
                    borderColor: backgroundColors.map(color => color.replace('0.5', '1')),
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: '概率 (%)'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `概率: ${context.raw.toFixed(2)}%`;
                            }
                        }
                    },
                    datalabels: {
                        anchor: 'end',
                        align: 'top',
                        formatter: function(value) {
                            return value.toFixed(1) + '%';
                        },
                        font: {
                            weight: 'bold'
                        },
                        // 只显示非零值的标签
                        display: function(context) {
                            return context.dataset.data[context.dataIndex] > 0;
                        }
                    }
                }
            }
        });
    }

    // 下载单个报告
    downloadReport.addEventListener('click', function() {
        if (!currentResults) return;
        
        const reportData = {
            date: new Date().toLocaleString(),
            filename: currentFile.name,
            results: currentResults.results
        };
        
        const reportBlob = new Blob([JSON.stringify(reportData, null, 2)], {type: 'application/json'});
        const reportUrl = URL.createObjectURL(reportBlob);
        
        const a = document.createElement('a');
        a.href = reportUrl;
        a.download = `eye_report_${new Date().getTime()}.json`;
        a.click();
        
        URL.revokeObjectURL(reportUrl);
    });

    // 显示加载中
    function showLoading() {
        loadingOverlay.style.display = 'flex';
    }

    // 隐藏加载中
    function hideLoading() {
        loadingOverlay.style.display = 'none';
    }

    // 拖放功能
    const imagePreview = document.getElementById('imagePreview');
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        imagePreview.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    ['dragenter', 'dragover'].forEach(eventName => {
        imagePreview.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        imagePreview.addEventListener(eventName, unhighlight, false);
    });
    
    function highlight() {
        imagePreview.classList.add('highlight');
    }
    
    function unhighlight() {
        imagePreview.classList.remove('highlight');
    }
    
    imagePreview.addEventListener('drop', handleDrop, false);
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (files.length > 0) {
            currentFile = files[0];
            previewSelectedImage(currentFile);
        }
    }
});