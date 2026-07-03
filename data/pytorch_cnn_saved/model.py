"""CNN 모델 구조 정의 (가중치는 cnn_weights.pth 에서 로드)."""
import torch.nn as nn

class SmallCNN(nn.Module):
    def __init__(self, n_class=10):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 8, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(8, 16, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
        )
        self.classifier = nn.Linear(16 * 7 * 7, n_class)
    def forward(self, x):
        x = self.features(x)
        x = x.flatten(1)
        return self.classifier(x)
