import torch
import torchvision
import torch.nn as nn
import cv2
from torchvision.transforms import v2

DROPOUT_RATE = 0.5

class CustomModel:
    def __init__(self, weights_path):
        self.weights_path = weights_path
        self.net = self.load_model()

    def load_model(self):
        net = torchvision.models.mobilenet_v2()

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

        net.load_state_dict(torch.load(self.weights_path, map_location="cpu"))

        net.eval()

        return net

    def predict(self, image):
        img_transform = v2.Compose([
            v2.Resize((224, 224)),
            v2.ToImage(),
            v2.ToDtype(torch.float32, scale=True),
            v2.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

        image = img_transform(cv2.cvtColor(image, cv2.COLOR_BGR2RGB)).unsqueeze(0)
        with torch.no_grad():
            output = self.net(image)
        return output.item() > 0.5
