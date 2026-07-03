"""PyTorch 회귀 — 커스텀 Dataset + DataLoader 패턴.
연구자들이 자체 데이터 다룰 때 쓰는 형태.
"""
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.datasets import make_regression

class RegDataset(Dataset):
    def __init__(self, X, y):
        self.X = torch.tensor(X, dtype=torch.float32)
        self.y = torch.tensor(y, dtype=torch.float32).unsqueeze(1)
    def __len__(self):
        return len(self.X)
    def __getitem__(self, i):
        return self.X[i], self.y[i]

def main():
    X, y = make_regression(n_samples=200, n_features=5, noise=0.1, random_state=0)
    loader = DataLoader(RegDataset(X, y), batch_size=16, shuffle=True)

    model = nn.Sequential(nn.Linear(5, 32), nn.ReLU(), nn.Linear(32, 1))
    opt = torch.optim.Adam(model.parameters(), lr=0.01)
    loss_fn = nn.MSELoss()

    for epoch in range(20):
        for xb, yb in loader:
            opt.zero_grad()
            loss = loss_fn(model(xb), yb)
            loss.backward()
            opt.step()
    print(f"final loss: {loss.item():.4f}")
    torch.save(model.state_dict(), "reg_model.pt")
    print("saved: reg_model.pt")

if __name__ == "__main__":
    main()
