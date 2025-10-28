"""
비윤리 판단 모델 클래스 정의
EthicsPredictor에서 사용하기 위한 최소 구현
"""
import torch.nn as nn
from transformers import BertModel


class EthicsClassifier(nn.Module):
    """비윤리 판단 분류기"""
    
    def __init__(self, model_name, num_classes=2, dropout=0.3):
        super(EthicsClassifier, self).__init__()
        self.bert = BertModel.from_pretrained(model_name)
        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Linear(self.bert.config.hidden_size, num_classes)
    
    def forward(self, input_ids, attention_mask):
        outputs = self.bert(
            input_ids=input_ids,
            attention_mask=attention_mask
        )
        pooled_output = outputs.pooler_output
        pooled_output = self.dropout(pooled_output)
        logits = self.classifier(pooled_output)
        return logits

