from flask import Flask, request, jsonify, render_template, send_from_directory, Response, stream_with_context
from werkzeug.utils import secure_filename
import os
import logging
from datetime import datetime
import time
import socket
from urllib.parse import unquote
from urllib3.connection import HTTPConnection
from functools import wraps
import torch
import numpy as np
from PIL import Image
from torchvision import transforms
import yaml
import requests
import json
from models.efficientnet import EyeDiseaseModel

# 配置TCP Keepalive（必须在应用初始化前设置）
HTTPConnection.default_socket_options = (
    HTTPConnection.default_socket_options + [
        (socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1),
        (socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 30),
        (socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60),
    ]
)

app = Flask(__name__, 
            static_folder='web/static',
            template_folder='web/templates')

app.config.update({
    'UPLOAD_FOLDER': 'static/uploads/',
    'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,
    'OLLAMA_TIMEOUT': 30000,
    "BATCH_LIMIT" : 150
})

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('EyeDiseaseAI')

# 创建必要目录
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# PyTorch模型配置
with open("configs/default.yaml", encoding='utf-8') as f:
    config = yaml.safe_load(f)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

class get_:
    def get_severity(probability: float) -> str:
        if probability >= 0.7:
            return '重度'
        elif probability >= 0.3:
            return '中度'
        return '轻度'

class DiseaseClassifier:
    def __init__(self):
        self.model = self._load_model()
        self.class_names = [
            '正常', '糖尿病', '青光眼', 
            '白内障', 'AMD', '高血压', 
            '近视', '其他'
        ]
        self.output_path = "predictions.json"
        
        # 配置日志
        self.logger = logging.getLogger("EyeDiseaseAI")
        self.logger.setLevel(logging.INFO)

    def _load_model(self):
        model = EyeDiseaseModel(**config['model']).to(device)
        checkpoint = torch.load("best_model.pth", map_location=device)
        model.load_state_dict(checkpoint['model_state_dict'])
        model.eval()
        return model

    def _safe_read_results(self):
        """安全读取现有结果文件"""
        if not os.path.exists(self.output_path):
            return []
            
        try:
            with open(self.output_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            self.logger.error(f"读取结果文件失败，将创建新文件。错误原因: {str(e)}")
            return []

    def _safe_write_results(self, data):
        """安全写入结果文件（带错误处理和原子写入）"""
        try:
            # 先写入临时文件
            temp_path = self.output_path + ".tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            
            # 替换原文件
            os.replace(temp_path, self.output_path)
        except Exception as e:
            self.logger.error(f"写入结果文件失败: {str(e)}")
            raise

    def preprocess(self, image_path):
        transform = transforms.Compose([
            transforms.Resize((config['data']['img_size'], config['data']['img_size'])),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        image = Image.open(image_path).convert('RGB')
        return transform(image).unsqueeze(0)

    def predict(self, image_path):
        try:
            # 预测流程
            image_tensor = self.preprocess(image_path).to(device)
            with torch.no_grad():
                outputs = self.model(image_tensor)
                probabilities = torch.sigmoid(outputs).cpu().numpy()[0]
                
            results = []
            for i, prob in enumerate(probabilities):
                results.append({
                    'disease': self.class_names[i],
                    'probability': float(prob),
                    'level': get_.get_severity(prob),
                })
            sorted_results = sorted(results, key=lambda x: x['probability'], reverse=True)
            
            # 构建输出数据
            output_data = {
                "image_name": os.path.basename(image_path),
                "top_disease": {
                    "name": sorted_results[0]['disease'],
                    "probability": sorted_results[0]['probability'],
                    "level": get_.get_severity(sorted_results[0]['probability'])
                },
                "all_diseases": {item['disease']: item['probability'] for item in sorted_results}
            }
            
            # 读写操作
            existing_data = self._safe_read_results()
            existing_data.append(output_data)
            self._safe_write_results(existing_data)
            
            return sorted_results
            
        except Exception as e:
            self.logger.error(f"预测失败: {str(e)}", exc_info=True)
            raise  # 向上抛出异常供web层捕获

classifier = DiseaseClassifier()


def generate_medical_prompt(
    diseases: list,
    age: str = None,
    gender: str = None,
    occupation: str = None,
    medical_history: str = None,
    additional_info: str = None
) -> str:
    """生成包含多疾病概率的专业医疗提示词"""
    # 过滤有效疾病数据（概率≥25%且非正常类别）
    significant_diseases = sorted([
        {
            "name": d["disease"].strip(),
            "prob": float(d["probability"])
        } for d in diseases
        if d.get("probability", 0) >= 0.25 
        and d.get("disease", "").strip() != "正常"
    ], key=lambda x: x["prob"], reverse=True)[:3]  # 取前3个最高概率

    # 构建基础提示
    base_prompt = [
        "我是一名三甲医院眼科主任医师，基于深度学习模型对患者眼底照片的分析结果如下："
    ]

    # 添加综合风险评估
    if significant_diseases:
        total_risk = min(sum(d["prob"] for d in significant_diseases) * 0.7, 1.0)
        base_prompt.append(
            f"\n综合病变风险指数：{total_risk*100:.0f}%（根据多标签检测结果加权计算）"
        )
        
        # 添加疾病明细
        base_prompt.append("\n显著异常检测结果（概率≥25%）：")
        for idx, disease in enumerate(significant_diseases, 1):
            base_prompt.append(
                f"{idx}. {disease['name']} - {disease['prob']*100:.0f}%可能性"
            )
        
        analysis_request = [
            "\n请基于以下要点进行专业分析(不要使用表格回答)：",
            "1. 各疾病间的病理关联性分析",
            "2. 可能的急性并发症预警",
            "3. 建议的鉴别诊断检查方案",
            "4. 分级诊疗建议（急诊/门诊/随访）",
            "5. 药物治疗与非药物干预方案"
        ]
    else:
        base_prompt.append("\n未检测到显著异常病变")
        analysis_request = [
            "\n请提供：",
            "1. 健康人群眼部保养建议",
            "2. 建议的常规检查频率",
            "3. 早期病变自查方法"
        ]

    # 添加患者信息
    if age or gender or occupation or medical_history or additional_info:
        base_prompt.append("以下是患者的一些基本信息：")
        # 动态添加有效信息字段
        if age and age.isdigit():
            base_prompt.append(f"• 年龄: {age}岁")
        if gender and gender.strip():
            base_prompt.append(f"• 性别: {gender.strip()}")
        if occupation and occupation.strip():
            base_prompt.append(f"• 职业: {occupation.strip()}")
        if medical_history and medical_history.strip():
            base_prompt.append(f"• 已知疾病史: {medical_history.strip()}")
        if additional_info and additional_info.strip():
            base_prompt.append(f"• 补充信息: {additional_info.strip()}")

    # 合并分析要求
    base_prompt.extend(analysis_request)

    # 添加临床注意事项
    base_prompt.extend([
        "\n注意事项：",
        "- 区分影像学特征与临床表现的差异",
        "- 注明需排除的鉴别诊断",
        "- 标注建议处理的紧急程度",
        "- 避免绝对化结论，保留临床判断空间"
    ])

    return "\n".join(base_prompt)

@app.route('/stream-analysis')
def stream_analysis():
    """流式分析端点（硅基流动API稳定版）"""
    try:
        # 解析疾病列表
        diseases_json = unquote(unquote(request.args.get('diseases', '[]')))
        try:
            diseases = json.loads(diseases_json)
            if not isinstance(diseases, list):
                raise ValueError
        except Exception as e:
            logger.error(f"疾病参数解析失败: {str(e)}")
            return jsonify({'error': '疾病数据格式错误'}), 400

        # 验证疾病数据格式
        required_keys = ['disease', 'probability']
        for d in diseases:
            if not all(k in d for k in required_keys):
                return jsonify({'error': '缺失必要疾病字段'}), 400
            if not (0 <= d['probability'] <= 1):
                return jsonify({'error': '概率值越界'}), 400

        # 获取患者信息
        patient_info = {
            'age': request.args.get('age', ''),
            'gender': request.args.get('gender', ''),
            'occupation': request.args.get('occupation', ''),
            'medical_history': request.args.get('medicalHistory', ''),
            'additional_info': request.args.get('additionalInfo', '')
        }

        # 生成专业提示词
        prompt = generate_medical_prompt(
            diseases=diseases,
            **patient_info
        )
        print(prompt)
        logger.info(f"生成提示词长度：{len(prompt)}字符")

        # @keep_alive
        def event_generator():
            start_time = time.monotonic()
            retry_count = 0
            MAX_RETRIES = 3
            STREAM_TIMEOUT = 120
            cot_buffer = ""  # COT缓冲区初始化
            is_formal_answer = False  # 正式回答状态标志

            while retry_count <= MAX_RETRIES:
                try:
                    # 构造API请求
                    payload = {
                        "model": "deepseek-ai/DeepSeek-R1",
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": True,
                        "temperature": 0.35,
                        "max_tokens": 2048,
                        "top_p": 0.9
                    }
                    headers = {
                        "Authorization": "Bearer your_api_key_here",
                        "Content-Type": "application/json"
                    }

                    with requests.post(
                        "https://api.siliconflow.cn/v1/chat/completions",
                        json=payload,
                        headers=headers,
                        stream=True,
                    ) as response:
                        response.raise_for_status()

                        # 流数据处理
                        think_flag = True
                        for chunk in response.iter_lines():
                            # 处理SSE格式
                            if chunk:
                                json_str = chunk.decode('utf-8').split('data:')[1]
                                    
                                # 结束标记
                                if json_str == "[DONE]":
                                    break

                                try:
                                    data = json.loads(json_str)
                                    content = ""
                                    if data.get('choices'):
                                        choice = data['choices'][0] if len(data['choices']) > 0 else {}
                                        delta = choice.get('delta', {})
                                        cot_content = delta.get('reasoning_content','')
                                        answer_content = delta.get('content', '') 
                                        # print (content, end='')  # 
                                        if cot_content:
                                            print(str(cot_content), end='', flush=True)
                                            yield f"data: {json.dumps({'think': cot_content})}\n\n"
                                        if answer_content:
                                            if think_flag:
                                                print('输出回答')
                                                yield f"data: {json.dumps({'flag': True})}\n\n"
                                                think_flag = False
                                            print(str(answer_content), end='', flush=True)
                                            yield f"data: {json.dumps({'response': answer_content})}\n\n"

                                except (json.JSONDecodeError, KeyError, IndexError) as e:
                                    logger.warning(f"数据解析异常: {str(e)}")
                                    continue

                        # 最终清理
                        if cot_buffer.strip():
                            yield f"data: {json.dumps({'response': cot_buffer})}\n\n"
                        yield "data: {\"status\": \"completed\"}\n\n"
                        logger.info(f"成功完成 | 耗时: {time.monotonic()-start_time:.2f}s")
                        return

                except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                    retry_count += 1
                    logger.warning(f"连接异常 | 第{retry_count}次重试 ({str(e)})")
                    time.sleep(min(5, 2 ** retry_count))
                    continue

                except requests.exceptions.HTTPError as e:
                    error_msg = f"API请求失败: {response.status_code}"
                    if response.content:
                        error_msg += f" {response.text[:200]}"
                    logger.error(error_msg)
                    yield "data: {\"error\": \"模型服务异常\"}\n\n"
                    return

                except Exception as e:
                    logger.error(f"未处理异常: {str(e)}", exc_info=True)
                    yield "data: {\"error\": \"流处理中断\"}\n\n"
                    return

            yield "data: {\"error\": \"超过最大重试次数\"}\n\n"

        return Response(
            stream_with_context(event_generator()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'
            }
        )

    except ValueError:
        return jsonify({'error': '概率参数类型错误'}), 400
    except Exception as e:
        logger.critical(f"全局异常: {str(e)}", exc_info=True)
        return jsonify({'error': '系统处理异常'}), 500

@app.route('/predict', methods=['POST'])
def predict():
    if 'image' not in request.files:
        return jsonify({'error': '缺少上传文件'}), 400
        
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': '空文件名'}), 400

    try:
        # 记录处理开始时间
        process_start = time.perf_counter()
        
        filename = secure_filename(file.filename)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)
        
        # 记录模型推理开始时间
        inference_start = time.perf_counter()
        results = classifier.predict(save_path)
        inference_time = time.perf_counter() - inference_start
        logger.info(f"模型推理耗时: {inference_time:.2f}s")
        top_result = results[0] if results else None

        # 计算总耗时（包括文件保存）
        total_time = time.perf_counter() - process_start
        logger.info(f"处理耗时: {total_time:.2f}s")
        return jsonify({
            'status': 'success',
            'result': results,
            'analysis_params': {
                'diseases': [
                    {
                        'disease': res['disease'],
                        'probability': res['probability']
                    } for res in results
                ],
                'image_url': f"/static/uploads/{filename}"
            }
        })
    except Exception as e:
        logger.error(f"预测失败: {str(e)}")
        return jsonify({'error': '处理失败'}), 500

@app.route('/batch_predict', methods=['POST'])
def batch_predict():
    if 'images' not in request.files:
        return jsonify({'error': '未上传任何文件'}), 400
    
    files = request.files.getlist('images')
    if len(files) > app.config['BATCH_LIMIT']:
        return jsonify({'error': f'超出最大处理数量'}), 400

    results = []
    for file in files:
        try:
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)
            
            preds = classifier.predict(save_path)
            all_preds = preds if preds else []
            top_pred = all_preds[0] if all_preds else None
            
            results.append({
                'filename': filename,
                'disease': top_pred['disease'],
                'probability': top_pred['probability'],
                'level': get_.get_severity(top_pred['probability']),
                'all_predictions': [  # 新增字段
                    {
                        'disease': p['disease'],
                        'probability': p['probability'],
                        'level': get_.get_severity(p['probability'])
                    } for p in all_preds
                ]
            })
        except Exception as e:
            logger.error(f"文件处理失败: {str(e)}")
            continue

    return jsonify({
        'status': 'success' if results else 'error',
        'processed_count': len(results),
        'results': results
    })

@app.route('/predictions.json')
def get_predictions():
    json_path = os.path.join(app.root_path, 'predictions.json')
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except FileNotFoundError:
        return jsonify([])

# 保留原有路由和模板
@app.route('/')
def index():
    return render_template('homepage.html')

@app.route('/system')
def system():
    return render_template('predict.html')

@app.route('/batch')
def batch():
    return render_template('batch.html')

@app.route('/history')
def history():
    return render_template('history.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

# def keep_alive(func):
#     @wraps(func)
#     def wrapper(*args, **kwargs):
#         with heartbeat_lock:
#             return func(*args, **kwargs)
#     return wrapper

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)