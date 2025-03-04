import torch
from torch.utils.data import Dataset
import os
from natsort import natsorted
import cv2
import glob
import numpy as np
from PIL import Image
from skimage import io as img

class ImageAndMaskData(Dataset):

    def __init__(self, img_dir, mask_dir, transform=None):

        
        self.images = natsorted(glob.glob(img_dir + "/*"))
        self.masks = natsorted(glob.glob(mask_dir + "/*"))

        self.imgs_and_masks = list(zip(self.images, self.masks))

        self.transform = transform

    def __len__(self):

        return len(self.imgs_and_masks)

    def __getitem__(self, idx):

        data = self.imgs_and_masks[idx]

        img_path = data[0] # image
        mask_path = data[1] # mask 

        #img = cv2.imread(img_path)
        img = np.array(Image.open(img_path))
        mask = np.array(Image.open(mask_path))[:,:,0:1] # take only one channel from mask
        #print(mask.shape)
        #print(mask.sum())

        sample = np.concatenate((img, mask), axis=2)
        #sample = torch.tensor(sample).to(torch.float)

        #sample = img

        sample = Image.fromarray(sample)
        
        #sample = sample.permute((2, 0, 1))

        # convert to 0,1 range
        #sample = sample/255


        #print(sample.shape)

        #print(img.shape)
        #print(mask.shape)
        if self.transform:
            sample = self.transform(sample)
            


        return sample


# New functions to match with SinGAN-Seg process

def make_4_chs_img(image_path, mask_path):
    # Load images and ensure 3 channels for image
    im = img.imread(image_path)
    if len(im.shape) == 2:  # If grayscale, convert to RGB
        im = np.stack([im] * 3, axis=-1)
    elif im.shape[2] == 4:  # If RGBA, convert to RGB
        im = im[:, :, :3]
        
    # Load and process mask
    mask = img.imread(mask_path)
    
    # Force resize mask to match image dimensions exactly
    if im.shape[0:2] != mask.shape[0:2]:
        from skimage.transform import resize
        mask = resize(mask, 
                     output_shape=(im.shape[0], im.shape[1]),
                     preserve_range=True,
                     order=0,
                     anti_aliasing=False).astype(np.uint8)

    # Ensure mask is 2D and then add channel dimension
    if len(mask.shape) == 3:
        mask = mask[:, :, 0]  # Take first channel if multi-channel
    mask = (mask > 127).astype(np.uint8) * 255
    mask = mask[:, :, np.newaxis]  # Add channel dimension

    # Verify shapes before concatenation
    assert im.shape[2] == 3, f"Image should have 3 channels, got shape {im.shape}"
    assert mask.shape[2] == 1, f"Mask should have 1 channel, got shape {mask.shape}"
    
    # Concatenate and return
    return np.concatenate((im, mask), axis=2)

def norm(x):
    out = (x -0.5) *2
    return out.clamp(-1, 1)

def denorm(x):
    out = (x + 1) / 2
    return out.clamp(0, 1)

def np2torch(x):
    #if opt.nc_im == 3 or opt.nc_im == 4: # added opt.nc_im == 4 by vajira to handle 4 channel image
    x = x[:,:,:]
    x = x.transpose((2, 0, 1))/255
    
    x = torch.from_numpy(x)
    #if not(opt.not_cuda):
    #    x = move_to_gpu(x, opt.device)
    #x = x.type(torch.cuda.FloatTensor) if not(opt.not_cuda) else x.type(torch.FloatTensor)
    x = x.type(torch.FloatTensor)
    #x = x.type(torch.FloatTensor)
    x = norm(x)
    return x



class ImageAndMaskDataFromSinGAN(Dataset):

    def __init__(self, img_dir, mask_dir, transform=None):

        
        self.images = natsorted(glob.glob(img_dir + "/*.[jp][pn][g]"))  # supports jpg, png, jpeg
        self.masks = natsorted(glob.glob(mask_dir + "/*.[jp][pn][g]"))

        self.imgs_and_masks = list(zip(self.images, self.masks))

        self.transform = transform

        # Add validation for matching pairs
        assert len(self.images) == len(self.masks), "Number of images and masks must match"
        
    def preprocess(self, x):
        # Instead of lambda, define as method
        return x

    def __len__(self):

        return len(self.imgs_and_masks)

    def __getitem__(self, idx):

        data = self.imgs_and_masks[idx]

        image_path = data[0] # image
        mask_path = data[1] # mask 

        #img = cv2.imread(img_path)
        #img = np.array(Image.open(img_path))
       # mask = np.array(Image.open(mask_path))[:,:,0:1] # take only one channel from mask
        #print(mask.shape)
        #print(mask.sum())

        #sample = np.concatenate((img, mask), axis=2)
        #sample = torch.tensor(sample).to(torch.float)

        #sample = img

        sample = make_4_chs_img(image_path, mask_path)#Image.fromarray(sample)

        sample = np2torch(sample)

        sample = sample[0:4,:,:]
        
        # Add custom preprocessing
        sample = self.preprocess(sample)

        #sample = sample.permute((2, 0, 1))

        # convert to 0,1 range
        #sample = sample/255


        #print(sample.shape)

        #print(img.shape)
        #print(mask.shape)
        if self.transform:
            sample = self.transform(sample)
            


        return sample




if __name__ == "__main__":

    dataset = ImageAndMaskDataFromSinGAN("/Users/prachit/self/Working/OCT/generative/deepfake_gi_fastGAN/custom_dataset/images", 
                                "/Users/prachit/self/Working/OCT/generative/deepfake_gi_fastGAN/custom_dataset/masks")

    print(dataset[1].shape)

    #cv2.imwrite("test.png", dataset[1])


