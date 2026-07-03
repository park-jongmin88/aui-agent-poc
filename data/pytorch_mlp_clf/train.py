"""PyTorch 분류 — nn.Module 정의 + 학습 루프 → state_dict 저장.
가장 전형적인 PyTorch 형태.
"""
import torch
import torch.nn as nn
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split

class MLP(nn.Module):
    def __init__(self, in_dim=4, hidden=16, n_class=3):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden), nn.ReLU(),
            nn.Linear(hidden, n_class),
        )
    def forward(self, x):
        return self.net(x)

def main():
    X, y = load_iris(return_X_y=True)
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)
    X_tr = torch.tensor(X_tr, dtype=torch.float32)
    y_tr = torch.tensor(y_tr, dtype=torch.long)

    model = MLP()
    opt = torch.optim.Adam(model.parameters(), lr=0.01)
    loss_fn = nn.CrossEntropyLoss()

    for epoch in range(50):
        opt.zero_grad()
        loss = loss_fn(model(X_tr), y_tr)
        loss.backward()
        opt.step()
    print(f"final loss: {loss.item():.4f}")

    torch.save(model.state_dict(), "model.pt")
    print("saved: model.pt")

if __name__ == "__main__":
    main()
