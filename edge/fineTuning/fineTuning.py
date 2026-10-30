import torch
import torchvision
import torch.optim as optim
import torch.nn as nn
from torchvision.transforms import v2
import matplotlib.pyplot as plt

from edge.fineTuning.modelUtils import run_epoch

LR = 0.0001
EPOCHS = 50
DROPOUT_RATE = 0.5
DATASET_PATH = "../../FLAME3CV_Split"


train_transform = v2.Compose([
    v2.RandomResizedCrop(size=(224, 224), scale=(0.8, 1.0)),
    v2.RandomHorizontalFlip(p=0.5),
    v2.RandomRotation(degrees=15),
    v2.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
    v2.ToImage(),
    v2.ToDtype(torch.float32, scale=True),
    v2.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

eval_transform = v2.Compose([
    v2.Resize((224, 224)),
    v2.ToImage(),
    v2.ToDtype(torch.float32, scale=True),
    v2.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

trainData = torchvision.datasets.ImageFolder(root=DATASET_PATH + "/train", transform=train_transform)
evalData = torchvision.datasets.ImageFolder(root=DATASET_PATH + "/val", transform=eval_transform)

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

criterion = nn.BCELoss()
optimizer = optim.Adam(net.parameters(), lr=LR)
trainloader = torch.utils.data.DataLoader(trainData, batch_size=32, shuffle=True, num_workers=2)
evalloader = torch.utils.data.DataLoader(evalData, batch_size=32, shuffle=False, num_workers=2)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
net.to(device)

history = {
    'trainLoss': [],
    'trainAcc': [],
    'valLoss': [],
    'valAcc': []
}

for epoch in range(EPOCHS):
    trainLoss, trainAcc = run_epoch(net, trainloader, criterion, optimizer, device)
    valLoss, valAcc     = run_epoch(net, evalloader, criterion, device=device)
    
    for key, val in zip(['trainLoss', 'trainAcc', 'valLoss', 'valAcc'], [trainLoss, trainAcc, valLoss, valAcc]):
        history[key].append(val)
        
    print(f"Epoch [{epoch+1}/{EPOCHS}] - Train Loss: {trainLoss:.4f}, Train Acc: {trainAcc:.4f} | Val Loss: {valLoss:.4f}, Val Acc: {valAcc:.4f}")

print('Finished Training')

modelSavePath = 'mobilenet_v2_flame3.pth'
torch.save(net.state_dict(), modelSavePath)

epochs_range = range(1, len(history['trainLoss']) + 1)

plt.figure(figsize=(12, 5))
plt.subplot(1, 2, 1)
plt.plot(epochs_range, history['trainLoss'], label='Train Loss', color='blue')
plt.plot(epochs_range, history['valLoss'], label='Val Loss', color='red')
plt.title('Train vs Validation Loss')
plt.xlabel('Epochs')
plt.ylabel('Loss')
plt.legend()
plt.grid(True)

plt.subplot(1, 2, 2)
plt.plot(epochs_range, history['trainAcc'], label='Train Accuracy', color='blue')
plt.plot(epochs_range, history['valAcc'], label='Val Accuracy', color='red')
plt.title('Train vs Validation Accuracy')
plt.xlabel('Epochs')
plt.ylabel('Accuracy')
plt.legend()
plt.grid(True)

plt.tight_layout()
plt.savefig('training_metrics_plot.png', dpi=300)
plt.show()
