"""
비윤리 판단 예측 스크립트
"""
import torch
import json
import sys
import io
from transformers import BertTokenizer
from ethics.ethics_train_model import EthicsClassifier

# Windows 환경에서 UTF-8 출력 설정
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

class EthicsPredictor:
    """비윤리 판단 예측기"""
    
    def __init__(self, model_path='models/binary_classifier.pth', 
                 config_path='models/config.json'):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # 설정 로드
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        self.model_name = config['model_name']
        self.max_len = config['max_len']
        
        # 토크나이저 로드
        self.tokenizer = BertTokenizer.from_pretrained(self.model_name)
        
        # 이진 분류 모델 로드
        checkpoint = torch.load(model_path, map_location=self.device)
        self.model = EthicsClassifier(self.model_name, num_classes=2)
        
        # state_dict 키 이름 변환 (fc -> classifier)
        state_dict = checkpoint['model_state_dict']
        new_state_dict = {}
        for key, value in state_dict.items():
            if key.startswith('fc.'):
                new_key = key.replace('fc.', 'classifier.')
                new_state_dict[new_key] = value
            else:
                new_state_dict[key] = value
        
        self.model.load_state_dict(new_state_dict)
        self.model = self.model.to(self.device)
        self.model.eval()
        
        print(f"[INFO] 모델 로드 완료 (정확도: {checkpoint.get('val_acc', 0):.4f})")
    
    def predict(self, text):
        """단일 텍스트 예측"""
        encoding = self.tokenizer.encode_plus(
            text,
            add_special_tokens=True,
            max_length=self.max_len,
            padding='max_length',
            truncation=True,
            return_attention_mask=True,
            return_tensors='pt'
        )
        
        input_ids = encoding['input_ids'].to(self.device)
        attention_mask = encoding['attention_mask'].to(self.device)
        
        with torch.no_grad():
            outputs = self.model(input_ids, attention_mask)
            probs = torch.softmax(outputs, dim=1)
            prediction = torch.argmax(probs, dim=1)
        
        return {
            'prediction': '비윤리적' if prediction.item() == 1 else '윤리적',
            'label': prediction.item(),
            'confidence': probs[0][prediction.item()].item(),
            'probabilities': {
                '윤리적': probs[0][0].item(),
                '비윤리적': probs[0][1].item()
            }
        }
    
    def predict_batch(self, texts):
        """여러 텍스트 일괄 예측"""
        results = []
        for text in texts:
            results.append(self.predict(text))
        return results

