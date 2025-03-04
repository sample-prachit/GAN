import torch
from torch import nn
from torch import optim
import torch.nn.functional as F
from torchvision.datasets import ImageFolder
from torch.utils.data import DataLoader
from torchvision import utils as vutils
from huggingface_hub import PyTorchModelHubMixin

import os
import random
import argparse
from tqdm import tqdm

from models import Generator


def load_params(model, new_param):
    for p, new_p in zip(model.parameters(), new_param):
        p.data.copy_(new_p)

def resize(img):
    return F.interpolate(img, size=256)

def batch_generate(zs, netG, batch=8):
    g_images = []
    with torch.no_grad():
        for i in range(len(zs)//batch):
            g_images.append( netG(zs[i*batch:(i+1)*batch]).cpu() )
        if len(zs)%batch>0:
            g_images.append( netG(zs[-(len(zs)%batch):]).cpu() )
    return torch.cat(g_images)

def batch_save(images, folder_name):
    if not os.path.exists(folder_name):
        os.mkdir(folder_name)
    for i, image in enumerate(images):
        vutils.save_image(image.add(1).mul(0.5), folder_name+'/%d.jpg'%i)

# To push the model to Huggingface model hub
class MyFastGanModel(nn.Module, PyTorchModelHubMixin):

    def __init__(self, config: dict) -> None:
        super().__init__()

        self.model = Generator( ngf=config["ngf"], nz=config["noise_dim"], nc=config["nc"], im_size=config["im_size"])

    def forward(self, x):
        return self.model(x)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='generate images'
    )
    parser.add_argument('--ckpt', type=str, default="/work/vajira/DL/FastGAN-pytorch/train_results/test1_4ch/models/all_50000.pth")
    parser.add_argument('--artifacts', type=str, default=".", help='path to artifacts.')
    parser.add_argument('--cuda', type=int, default=0, help='index of gpu to use')
    parser.add_argument('--start_iter', type=int, default=6)
    parser.add_argument('--end_iter', type=int, default=10)

    parser.add_argument('--dist', type=str, default='test_out')
    parser.add_argument('--size', type=int, default=256)
    parser.add_argument('--batch', default=1, type=int, help='batch size')
    parser.add_argument('--n_sample', type=int, default=1)
    parser.add_argument('--big', action='store_true')
    parser.add_argument('--im_size', type=int, default=256)
    parser.add_argument("--save_option", default="image_and_mask", help="Options to svae output, image_only, mask_only, image_and_mask", choices=["image_only","mask_only", "image_and_mask"])
    parser.set_defaults(big=False)
    args = parser.parse_args()

    noise_dim = 256

    # Replace device initialization
    if args.cuda:
        if torch.backends.mps.is_available():
            device = torch.device("mps")
        elif torch.cuda.is_available():
            device = torch.device(f"cuda:{args.cuda}")
        else:
            device = torch.device("cpu")
    else:
        device = torch.device("cpu")

    # adding the model to the model hub
    config={"ngf":64, "noise_dim":noise_dim, "nc":4, "im_size":args.im_size}
    net_ig = MyFastGanModel(config=config)     

    

    # exit
    #exit()    
    
    #net_ig = model #Generator( ngf=64, nz=noise_dim, nc=4, im_size=args.im_size)#, big=args.big )
    net_ig.to(device)

    #for epoch in [10000*i for i in range(args.start_iter, args.end_iter+1)]:
    ckpt = args.ckpt #f"{args.artifacts}/models/{epoch}.pth"
    #checkpoint = torch.load(ckpt, map_location=lambda a,b: a)
    checkpoint = torch.load(ckpt)
    # Remove prefix `module`.
    checkpoint['g'] = {k.replace('module.', ''): v for k, v in checkpoint['g'].items()}
    net_ig.model.load_state_dict(checkpoint['g'])
    #load_params(net_ig, checkpoint['g_ema'])

    #net_ig.eval()
    print("load checkpoint success")

    net_ig.to(device)
    # Save locally
    net_ig.save_pretrained("pre_trained_checkpoint_4ch", config=config)  # Save the model locally
    print("Model saved locally. Pushing to Huggingface model hub...")

    # Push to the Huggingface model hub
    # push to the hub
    net_ig.push_to_hub("deepsynthbody/deepfake_gi_fastGAN", config=config)


    print("pushed to the Huggingface model hub. Done.")
    exit()  


    del checkpoint

    #dist = 'eval_%d'%(epoch)
    #dist = os.path.join(args.dist, 'img')
    dist = args.dist
    os.makedirs(dist, exist_ok=True)

    with torch.no_grad():
        for i in tqdm(range(args.n_sample//args.batch)):
            noise = torch.randn(args.batch, noise_dim).to(device)
            g_imgs = net_ig(noise)[0]
            g_imgs = F.interpolate(g_imgs, 512)
            
            
            for j, g_img in enumerate( g_imgs ):
                #print("img sahpe=", g_img.shape)
                g_mask = g_img.add(1).mul(0.5)[-1, :, :].expand(3, -1, -1)
                g_img = g_img.add(1).mul(0.5)[0:3, :, :]

                # Clean generated data using clamping
                g_mask = torch.clamp(g_mask, min=0, max=1)
                g_img = torch.clamp(g_img, min=0, max=1)
                #print(g_mask.type())
                g_mask = (g_mask > 0.5) * 1.0
                #print(g_mask.type())

                #print("gmask_min:", g_mask.min())
                #print("gmask_max:", g_mask.max())
                #exit()
                
                #print("img sahpe=", g_img.shape)

                if args.save_option == "image_and_mask":
                    vutils.save_image(g_img, 
                        os.path.join(dist, '%d_img.png'%(i*args.batch+j)))#, normalize=True, range=(-1,1))
                    vutils.save_image(g_mask, 
                        os.path.join(dist, '%d_mask.png'%(i*args.batch+j))) #, normalize=True, range=(0,1))

                elif args.save_option == "image_only":
                    vutils.save_image(g_img, 
                        os.path.join(dist, '%d_img.png'%(i*args.batch+j)))#, normalize=True, range=(-1,1))
                    
                elif args.save_option == "mask_only":
                    vutils.save_image(g_mask, 
                        os.path.join(dist, '%d_mask.png'%(i*args.batch+j)))#, normalize=True, range=(-1,1))
                else:
                    print("wrong choise to save option.")
