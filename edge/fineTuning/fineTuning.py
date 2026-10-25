import torch
import torchvision
import torch.optim as optim
import torch.nn as nn

LR = 0.0001
EPOCHS = 50
DROPOUT_RATE = 0.5

transform = torchvision.v2.transforms.Compose([
    torchvision.v2.transforms.Resize((224, 224)),
    torchvision.v2.transforms.ToTensor(),
    torchvision.v2.transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

dataset = torchvision.datasets.ImageFolder(root="../../FLAME3CV/train", transform=transform)

net = torchvision.models.mobilenet_v2(weights=torchvision.models.MobileNet_V2_Weights.DEFAULT)

for param in net.features.parameters():
    param.requires_grad = False

in_features = net.last_channel 

net.classifier = nn.Sequential(
    nn.AdaptiveAvgPool2d((1, 1)),  
    nn.Flatten(),
    nn.Linear(in_features, 128),   
    nn.ReLU(),                      
    nn.Dropout(p=DROPOUT_RATE),              
    nn.Linear(128, 1),               
    nn.Sigmoid()                   
)


criterion = nn.BinaryCrossEntropyLoss()
optimizer = optim.adam(net.parameters(), lr=LR)
trainloader = torch.utils.data.DataLoader(dataset, batch_size=32, shuffle=True, num_workers=2)

for epoch in range(EPOCHS):  
    running_loss = 0.0
    for i, data in enumerate(trainloader, 0):
        inputs, labels = data

        optimizer.zero_grad()

        outputs = net(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        running_loss += loss.item()
        if i % 2000 == 1999:    
            print(f'[{epoch + 1}, {i + 1:5d}] loss: {running_loss / 2000:.3f}')
            running_loss = 0.0

print('Finished Training')
