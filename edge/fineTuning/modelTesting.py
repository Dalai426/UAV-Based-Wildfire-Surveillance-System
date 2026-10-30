import torch
import torchvision
import torch.optim as optim
import torch.nn as nn
from torchvision.transforms import v2
import matplotlib.pyplot as plt

from edge.fineTuning.modelUtils import run_epoch

DATASET_PATH = "../../FLAME3CV_Split"
DROPOUT_RATE = 0.5

net = torchvision.models.mobilenet_v2(weights=torchvision.models.MobileNet_V2_Weights.DEFAULT)

for param in net.features.parameters():
    param.requires_grad = False

in_features = net.last_channel

net.classifier = nn.Sequential(
    nn.Linear(in_features, 128),
    nn.ReLU(),
    nn.Dropout(p=DROPOUT_RATE),
    nn.Linear(128, 1),
    nn.Sigmoid()
)

test_transform = v2.Compose([
    v2.Resize((224, 224)),
    v2.ToImage(),
    v2.ToDtype(torch.float32, scale=True),
    v2.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

testData = torchvision.datasets.ImageFolder(root=DATASET_PATH + "/test", transform=test_transform)
testloader = torch.utils.data.DataLoader(testData, batch_size=32, shuffle=False, num_workers=2)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
net.to(device)
criterion = nn.BCELoss()
_, testAcc, _, _ = run_epoch(net, testloader, criterion, device=device)

print(f"Test Accuracy: {testAcc * 100:.2f}%")