import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import scipy.io as sio
import torch 

"""
Optics for the Rendering. Simulates a DOE on an animal. 
See Training/Implementaion details in https://drive.google.com/file/d/1ISWnM1NhrcNpu5vBtejTQdS9GNuiQyqW/view?pli=1 
code: https://github.com/YichengWu/PhaseCam3D/blob/master/depth_estimation.py#L96
"""

def normalize(img):
    return (img - np.min(img)) / (np.max(img) - np.min(img))

def fft2dshift(input):
    dim = input.shape[1]  # dimension of the data
    if dim % 2 == 0:
        raise ValueError('Please make the size of kernel odd')
    # pdb.set_trace()c
    
    channel1 = input.shape[0]  # channels for the first dimension
    # shift up and down
    # u = torch.slice(input, [0, 0, 0], [channel1, int((dim + 1) / 2), dim])
    u = input[0:channel1, 0:int((dim + 1) / 2), 0:dim]
    
    # d = torch.slice(input, [0, int((dim + 1) / 2), 0], [channel1, int((dim - 1) / 2), dim])
    d = input[0:channel1, int((dim + 1) / 2):int((dim + 1) / 2) + int((dim - 1) / 2), 0:dim]
    du = torch.concat([d, u], axis=1)
    
    # shift left and right
    # l = torch.slice(du, [0, 0, 0], [channel1, dim, int((dim + 1) / 2)])
    l = du[0:channel1, 0:dim, 0:int((dim + 1) / 2)]
    # r = torch.slice(du, [0, 0, int((dim + 1) / 2)], [channel1, dim, int((dim - 1) / 2)])
    r = du[0:channel1, 0:dim, int((dim + 1) / 2):int((dim + 1) / 2) + int((dim - 1) / 2)]
    output = torch.concat([r, l], axis=2)
    return output


class Optics():

    def __init__(self, psf_kernel_size, wvls, refractive_index, min_depth, max_depth, depth_bins) -> None:
        """
        Currently the optics component is set to fixed sizes: 
            psf_kernel_size:  
            wvls: np.array([610., 530., 470.]) * 1e-9
            min_depth: 
            max_depth : 
            depth_bins: 
        """
        self.psf_kernel_size = psf_kernel_size
        self.wvls = wvls
        self.depth_bins = depth_bins
        self.min_depth = min_depth
        self.max_depth = max_depth # min_depth + depth_bins
        self.refractive_index = refractive_index

        self.psf_kernel_size = 23 
        self.N_R = 31
        self.N_G = 27
        self.N_B = 23  # size of the blur kernel

        self.disc_depth_range = np.linspace(self.min_depth, self.max_depth, self.depth_bins, np.float32) 
        self.defocus_phase = self.generate_defocus_phase(self.disc_depth_range, self.psf_kernel_size, self.wvls)

    def render(self, rgb, depth):
        """
        rgb: np.array(H, W, 3, dtype=np.uint8)
        depth: np.array((H, W), dtype=np.float) between (self.min_depth, max_depth)
        """
        rgb_torch = torch.tensor(rgb).unsqueeze(0)/255.
        depth_torch = self.compute_disc_depths(depth, self.disc_depth_range).unsqueeze(0).permute(0,3,1,2)
        psfs = self.generate_psf_from_height_mask(self.height_mask, self.defocus_phase)
        rgb = self.blur_image(rgb_torch, depth_torch, psfs)
        return rgb

    def generate_defocus_phase(self, disc_depth_range, psf_kernel_size, wvls):
        """
        disc_depth_range: 
        psf_kernel_size: 
        wvls: wavelength that psf is suceptible to. 
        """
        # return (Phi_list,pixel,pixel,color)
        x0 = np.linspace(-1.1, 1.1, psf_kernel_size)
        xx, yy = np.meshgrid(x0, x0)
        defocus_phase = np.empty([len(disc_depth_range), psf_kernel_size, psf_kernel_size, len(wvls)], dtype=np.float32)
        for j in range(len(disc_depth_range)):
            phi = disc_depth_range[j]
            for k in range(len(wvls)):
                defocus_phase[j, :, :, k] = phi * (xx ** 2 + yy ** 2) * wvls[1] / wvls[k];
        return defocus_phase
    
    def _load_zernike_vars(self, path):
        # uncomment to load zernekie polynomials and height mask from scratch!
        zernike = sio.loadmat(path) # 'tools/zernike_basis.mat'
        self.u2 = zernike['u2']  # basis of zernike poly
        self.n_coeff_zernike = self.u2.shape[1]
        idx = zernike['idx']
        self.idx = idx.astype(np.float32)

    def get_height_mask_from_zernike_vars(self, path, init_func='random'):

        self._load_zernike_vars(path)

        if init_func == 'zeros':
            alpha_zernike = torch.zeros((self.n_coeff_zernike, 1), dtype=torch.float32)
        elif init_func == 'random':
            alpha_zernike = torch.rand((self.n_coeff_zernike, 1), dtype=torch.float32)
        else:
            raise ValueError("{} not found".format(init_func))

        clip_alphas = lambda x: torch.clip(x, - self.wvls[1] / 2, self.wvls[1] / 2)
        alpha_zernike = clip_alphas(alpha_zernike)
        g = torch.matmul(torch.tensor(self.u2), alpha_zernike)
        self.height_mask = torch.relu(g.reshape((self.psf_kernel_size, self.psf_kernel_size)) + self.wvls[1])
        
    def load_height_mask_from_file(self, zernike_path, height_mask_path): 
        self._load_zernike_vars(zernike_path)
        self.height_mask = np.loadtxt(height_mask_path).astype(np.float32)

    def generate_psf_from_height_mask(self, height_mask, defocus_phase):
        idx = torch.tensor(self.idx)
        height_mask = torch.tensor(height_mask)
        defocus_phase = torch.tensor(defocus_phase)
        
        defocus_phase_r = defocus_phase[:, :, :, 0]
        phase_R = torch.add(2 * np.pi / self.wvls[0] * (self.refractive_index - 1) * height_mask, defocus_phase_r)
        e_defocused_r = torch.mul(torch.complex(idx, torch.tensor(0.0)), torch.exp(torch.complex(torch.tensor(0.0), phase_R)))

        pad_r = ((self.N_R - self.N_B) // 2, (self.N_R - self.N_B) // 2, (self.N_R - self.N_B) // 2, (self.N_R - self.N_B) // 2)
        pupil_r = torch.nn.functional.pad(e_defocused_r, pad_r)
        norm_r = self.N_R * self.N_R * torch.sum(idx ** 2)
        fft_pupil_r = torch.fft.fft2(pupil_r); 
        psf_r = torch.divide(torch.square(torch.abs(fft2dshift(fft_pupil_r))), norm_r)

        defocus_phase_g = defocus_phase[:, :, :, 1]
        phase_G = torch.add(2 * np.pi / self.wvls[1] * (self.refractive_index - 1) * height_mask, defocus_phase_g)
        e_defocused_g = torch.mul(torch.complex(idx, torch.tensor(0.0)), torch.exp(torch.complex(torch.tensor(0.0), phase_G)))
        pad_g = ((self.N_G - self.N_B) // 2, (self.N_G - self.N_B) // 2, (self.N_G - self.N_B) // 2, (self.N_G - self.N_B) // 2)
        pupil_g = torch.nn.functional.pad(e_defocused_g, pad_g)
        norm_g = self.N_G * self.N_G * torch.sum(idx ** 2)
        fft_pupil_g = torch.fft.fft2(pupil_g)
        psf_g = torch.divide(torch.square(torch.abs(fft2dshift(fft_pupil_g))), norm_g)

        defocus_phase_b = defocus_phase[:, :, :, 2]
        phase_B = torch.add(2 * np.pi / self.wvls[2] * (self.refractive_index - 1) * height_mask, defocus_phase_b)
        pupil_b = torch.mul(torch.complex(idx, torch.tensor(0.0)), torch.exp(torch.complex(torch.tensor(0.0), phase_B)))
        norm_b = self.N_B * self.N_B * torch.sum(idx ** 2)
        fft_pupil_b = torch.fft.fft2(pupil_b)
        psf_b = torch.divide(torch.square(torch.abs(fft2dshift(fft_pupil_b))), norm_b)

        N_crop_R = int((self.N_R - self.N_B) / 2)  # Num of pixel need to cropped at each side for R
        N_crop_G = int((self.N_G - self.N_B) / 2)  # Num of pixel need to cropped at each side for G

        psfs = torch.stack(
            [psf_r[:, N_crop_R:-N_crop_R, N_crop_R:-N_crop_R], psf_g[:, N_crop_G:-N_crop_G, N_crop_G:-N_crop_G], psf_b], axis=3)
                
        return psfs

    def blur_image(self, RGBPhi, DPPhi, PSFs, apply_normalize=True):
        N_B = PSFs.shape[1]
        N_crop = np.int32((N_B - 1) / 2)
        N_Phi = PSFs.shape[0]

        sharp_R = RGBPhi[:, :, :, 0:1].permute(0,3,1,2)
        PSFs_R = torch.reshape(torch.permute(PSFs[:, :, :, 0], dims=(1, 2, 0)), [N_Phi, 1, N_B, N_B])
        blurAll_R = torch.nn.functional.conv2d(sharp_R, PSFs_R, stride=[1, 1], padding='valid')
        blur_R = torch.sum(torch.multiply(blurAll_R, DPPhi[:, :, N_crop:-N_crop, N_crop:-N_crop]), axis=1)
        
        sharp_G = RGBPhi[:, :, :, 1:2].permute(0,3,1,2)
        PSFs_G = torch.reshape(torch.permute(PSFs[:, :, :, 1], dims=[1, 2, 0]), [N_Phi, 1, N_B, N_B])
        blurAll_G = torch.nn.functional.conv2d(sharp_G, PSFs_G, stride=[1, 1], padding='valid')
        blur_G = torch.sum(torch.multiply(blurAll_G, DPPhi[:, :, N_crop:-N_crop, N_crop:-N_crop]), axis=1)


        sharp_B = RGBPhi[:, :, :, 2:3].permute(0,3,1,2)
        PSFs_B = torch.reshape(torch.permute(PSFs[:, :, :, 2], dims=[1, 2, 0]), [N_Phi, 1, N_B, N_B])
        blurAll_B = torch.nn.functional.conv2d(sharp_B, PSFs_B, stride=[1, 1], padding='valid')
        blur_B = torch.sum(torch.multiply(blurAll_B, DPPhi[:, :, N_crop:-N_crop, N_crop:-N_crop]), axis=1)

        blur = torch.stack([blur_R, blur_G, blur_B], axis=3).squeeze().numpy()
        # blur = np.clip(blur, 0., 1.)
        if apply_normalize:
            blur = normalize(blur) 
        return blur

    def compute_disc_depths(self, mj_depth, disc_depth_range):
        """
        mj_depth must be between (min, max)
        """
        disc_depth = []
        
        # append the first one 
        idx = np.where(mj_depth < disc_depth_range[0])
        disc_depth_i = np.zeros_like(mj_depth ,dtype=np.float32)
        disc_depth_i[idx] = 1
        disc_depth.append(torch.tensor(disc_depth_i).unsqueeze(-1))
        
        # for each depth value see if it's close to disc_depth_range[n] < x < disc_depth_range[n+1]
        for i in range(1, len(disc_depth_range)-1):
            _min = disc_depth_range[i] 
            _max = disc_depth_range[i+1]
            idx = np.where((mj_depth >= _min) & (mj_depth < _max))
            disc_depth_i = np.zeros_like(mj_depth ,dtype=np.float32)
            disc_depth_i[idx] = 1
            disc_depth.append(torch.tensor(disc_depth_i).unsqueeze(-1))

        # append the last one 
        idx = np.where(mj_depth >= disc_depth_range[-1])
        disc_depth_i = np.zeros_like(mj_depth ,dtype=np.float32)
        disc_depth_i[idx] = 1
        disc_depth.append(torch.tensor(disc_depth_i).unsqueeze(-1))

        disc_depth = torch.concat(disc_depth, -1)
        return disc_depth


if __name__ == "__main__": 
    import sys 
    rgb_path = sys.argv[1]
    depth_path = sys.argv[2]
    rgb = np.array(Image.open(rgb_path))
    depth = np.array(np.load(depth_path))

    # config
    DEPTH_BINS = 5
    DEPTH_MIN = 0
    DEPTH_MAX = 1
    N_R = 31
    N_G = 27
    N_B = 23  # size of the blur kernel
    WLVS = np.array([610., 530., 470.]) * 1e-9
    PSF_KERNEL_SIZE = 23 # we should probably 10 to keep the parameters small
    REFRACTIVE_INDEX = 1.5
    ZERNIKE_PATH = "./tools/zernike_basis.mat"
    HEIGHT_MASK_PATH = "tools/FisherMask_HeightMap.txt"

    # alpha_zernike = None

    optics = Optics(PSF_KERNEL_SIZE, WLVS, REFRACTIVE_INDEX, DEPTH_MIN, DEPTH_MAX, DEPTH_BINS)
    # height_mask = optics.get_height_map_from_zernike_vars(alpha_zernike, n_coeff_zernike, u2, psf_kernel_size, wvls)
    optics.load_height_mask_from_file(ZERNIKE_PATH, HEIGHT_MASK_PATH)
    img = optics.render(rgb, depth)

    fig = plt.figure(figsize=(10,10))
    ax1 = fig.add_subplot(2,2,1)
    ax1.imshow(rgb)
    ax1.set_title("Sampled RGB")
    ax2 = fig.add_subplot(2,2,2)
    ax2.imshow(depth)
    ax2.set_title("Sampled Depth")
    ax3 = fig.add_subplot(2,2,3)
    ax3.imshow(optics.height_mask)
    ax3.set_title("Fisher Height Mask")
    ax4 = fig.add_subplot(2,2,4)
    ax4.imshow(img)
    ax4.set_title("RGB after PSF based Convolution")
    plt.savefig("fisher.png")