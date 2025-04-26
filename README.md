# EyeDiseaseDetection
pytorch+Flask
## 功能
### 单张图片检测+deepseek分析
检测：
![image](https://github.com/user-attachments/assets/d93901b6-2f2d-4f85-b109-ddb62672171b)
deepseek分析：
![image](https://github.com/user-attachments/assets/4c1ccd8e-5170-44a3-a953-2d64de8783e4)

### 批量图片检测,支持结果导出Excel
![image](https://github.com/user-attachments/assets/ab861c2b-da64-4eb9-93c5-a664522ca3eb)

### 历史检测记录查看，支持详细记录导出为Execl
![image](https://github.com/user-attachments/assets/258e0bf4-4ebb-426e-a7d5-8b6b535d5a10)

## 使用方法
提供ollama本地部署和硅基流动API双版本大模型调用
```python
python app.py  #调用本地ollama
```

```python
python app_api.py #调用API(需要配置密钥)
```
