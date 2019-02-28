import torch
import os
import argparse
from tensorboardX import SummaryWriter


class NameValues:
    def __init__(self, names, values, prefix='', suffix=''):
        self._pairs = []
        self._names = []
        self._values = []
        for name, value in zip(names, values):
            if value is not None:
                self._pairs.append((prefix + name + suffix, value))
                self._names.append(prefix + name + suffix)
                self._values.append(value)

    def strPrint(self, unit=''):
        str = ''
        for name, value in self._pairs:
            str += '%s: ' % (name)
            if hasattr(value, '__iter__'):
                for v in value:
                    str += '%.2f%s, ' % (v, unit)
            else:
                str += '%.2f%s, ' % (value, unit)

        return str

    def strSuffix(self):
        str = ''
        for name, value in self._pairs:
            str += '_%s' % (name)
            if hasattr(value, '__iter__'):
                for v in value:
                    str += '_%.0f' % (v)
            else:
                str += '_%.0f' % (value)
        return str

    def dic(self):
        dic = {}
        for name, value in self._pairs:
            dic[name] = value
        return dic

    def pairs(self):
        return self._pairs

    def values(self):
        return self._values

    def names(self):
        return self._names


class AutoPad:
    def __init__(self, imgs, multiple):
        self.N, self.C, self.H, self.W = imgs.size()
        self.HPad = ((self.H - 1) // multiple + 1) * multiple
        self.WPad = ((self.W - 1) // multiple + 1) * multiple

    def pad(self, imgs):
        if type(imgs) in (list, tuple):
            imgsPad = [self.pad(im) for im in imgs]
        else:
            imgsPad = torch.zeros([self.N, self.C, self.HPad, self.WPad], dtype=imgs.dtype,
                                  device=imgs.device.type)
            imgsPad[:, :, (self.HPad - self.H):, (self.WPad - self.W):] = imgs
        return imgsPad

    def unpad(self, imgs):
        if type(imgs) in (list, tuple):
            imgs = [self.unpad(im) for im in imgs]
        else:
            imgs = imgs[:, (self.HPad - self.H):, (self.WPad - self.W):]
        return imgs


# Flip among W dimension. For NCHW data type.
def flipLR(ims):
    if type(ims) in (list, tuple):
        return [flipLR(im) for im in ims]
    else:
        return ims.flip(-1)


def assertDisp(dispL=None, dispR=None):
    if (dispL is None or dispL.numel() == 0) and (dispR is None or dispR.numel() == 0):
        raise Exception('No disp input!')


# Log First n ims into tensorboard
# Log All ims if n == 0
def logFirstNIms(writer, name, im, range, global_step=None, n=0):
    if im is not None:
        n = min(n, im.size(0))
        if n > 0:
            im = im[:n]
        if im.dim() == 3 or (im.dim() == 4 and im.size(1) == 1):
            im[im > range] = range
            im[im < 0] = 0
            im = im / range
            im = gray2rgb(im)
        writer.add_images(name, im, global_step=global_step)


def gray2rgb(im):
    if im.dim() == 3:
        im = im.unsqueeze(1)
    return im.repeat(1, 3, 1, 1)


def checkDir(dir):
    if not os.path.exists(dir):
        os.makedirs(dir)


def getBasicParser(includeKeys=['all'], description='Stereo'):
    parser = argparse.ArgumentParser(description=description)

    addParams = {'outputFolder': lambda: parser.add_argument('--outputFolder', type=str, default=None,
                                                             help='output checkpoints and logs to foleder logs/outputFolder'),
                 'maxdisp': lambda: parser.add_argument('--maxdisp', type=int, default=192,
                                                        help='maximum disparity of unscaled model (or dataset in some module test)'),
                 'dispscale': lambda: parser.add_argument('--dispscale', type=float, default=1,
                                                          help='scale disparity when training (gtDisp/dispscale) and predicting (outputDisp*dispscale'),
                 'model': lambda: parser.add_argument('--model', default='PSMNet',
                                                      help='select model'),
                 'datapath': lambda: parser.add_argument('--datapath', default='../datasets/sceneflow/',
                                                         help='datapath'),
                 'loadmodel': lambda: parser.add_argument('--loadmodel', default=None,
                                                          help='load model'),
                 'no_cuda': lambda: parser.add_argument('--no_cuda', action='store_true', default=False,
                                                        help='enables CUDA training'),
                 'seed': lambda: parser.add_argument('--seed', type=int, default=1, metavar='S',
                                                     help='random seed (default: 1)'),
                 'eval_fcn': lambda: parser.add_argument('--eval_fcn', type=str, default='outlier',
                                                         help='evaluation function used in testing'),
                 'ndis_log': lambda: parser.add_argument('--ndis_log', type=int, default=1,
                                                         help='number of disparity maps to log'),
                 'dataset': lambda: parser.add_argument('--dataset', type=str, default='sceneflow',
                                                        help='(sceneflow/kitti2012/kitti2015/carla_kitti)'),
                 'load_scale': lambda: parser.add_argument('--load_scale', type=float, default=[1], nargs='+',
                                                           help='scaling applied to data during loading'),
                 'trainCrop': lambda: parser.add_argument('--trainCrop', type=float, default=(256, 512), nargs=2,
                                                          help='size of random crop (H x W) applied to data during training'),
                 'batchsize_test': lambda: parser.add_argument('--batchsize_test', type=int, default=3,
                                                               help='testing batch size'),
                 # training
                 'batchsize_train': lambda: parser.add_argument('--batchsize_train', type=int, default=3,
                                                                help='training batch size'),
                 'log_every': lambda: parser.add_argument('--log_every', type=int, default=10,
                                                          help='log every log_every iterations. set to 0 to stop logging'),
                 'test_every': lambda: parser.add_argument('--test_every', type=int, default=1,
                                                           help='test every test_every epochs. set to 0 to stop testing'),
                 'epochs': lambda: parser.add_argument('--epochs', type=int, default=10,
                                                       help='number of epochs to train'),
                 'lr': lambda: parser.add_argument('--lr', type=float, default=[0.001], help='', nargs='+'),
                 # submission
                 'subtype': lambda: parser.add_argument('--subtype', type=str, default='eval',
                                                        help='dataset type used for submission (eval/test)'),
                 # module test
                 'nsample_save': lambda: parser.add_argument('--nsample_save', type=int, default=1,
                                                             help='save n samples in module testing'),
                 # half precision
                 'half': lambda: parser.add_argument('--half', action='store_true', default=False,
                                                     help='enables half precision'),
                 # SRdisp specified param
                 'withMask': lambda: parser.add_argument('--withMask', action='store_true', default=False,
                                                         help='input 7 channels with mask to SRdisp instead of 6'),
                 }

    if len(includeKeys):
        if includeKeys[0] == 'all':
            for addParam in addParams.values():
                addParam()
        else:
            for key in includeKeys:
                addParams[key]()

    return parser


def adjustLearningRate(optimizer, epoch, lr):
    if len(lr) % 2 == 0:
        raise Exception('lr setting should be like \'0.001 300 0.0001 \'')
    nThres = len(lr) // 2 + 1
    for iThres in range(nThres):
        lrThres = lr[2 * iThres]
        if iThres < nThres - 1:
            epochThres = lr[2 * iThres + 1]
            if epoch <= epochThres:
                lr = lrThres
                break
        else:
            lr = lrThres
    print('lr = %f' % lr)
    for param_group in optimizer.param_groups:
        param_group['lr'] = lr
    return lr


def assertBatchLen(batch, length):
    if type(batch) is not Batch:
        raise Exception('Error: batch must be class Batch!')
    elif len(batch) != length:
        raise Exception(f'Error: input batch with length {len(batch)} doesnot match required {length}!')


def quantize(img, rgb_range):
    pixel_range = 255 / rgb_range
    return img.mul(pixel_range).clamp(0, 255).round().div(pixel_range)


class TensorboardLogger:
    def __init__(self):
        self.writer = None
        self._folder = None

    def __del__(self):
        if self.writer is not None:
            self.writer.close()

    def set(self, folder):
        if self.writer is None:
            self.writer = SummaryWriter(folder)
        else:
            if folder != self._folder:
                self.writer.close()
                self.writer = SummaryWriter(folder)
        self._folder = folder

    def logFirstNIms(self, name, im, range, global_step=None, n=0):
        if self.writer is None:
            raise Exception('Error: SummaryWriter is not initialized!')
        logFirstNIms(self.writer, name, im, range, global_step, n)


class Batch:
    def __init__(self, batch, cuda=None, half=None):
        if type(batch) not in (list, tuple, Batch):
            raise Exception('Error: batch must be class list, tuple or Batch!')
        if len(batch) % 4 != 0:
            raise Exception(f'Error: input batch with length {len(batch)} doesnot match required 4n!')

        if type(batch) in (list, tuple):
            self.batch = batch[:]  # deattach with initial list
        elif type(batch) is Batch:
            self.batch = batch.batch[:]

        if cuda is not None:
            self.batch = [(im.half() if half else im) if im.numel() else None for im in self.batch]
        if half is not None:
            self.batch = [(im.cuda() if cuda else im) if im is not None else None for im in self.batch]

    def __len__(self):
        return len(self.batch)

    def __getitem__(self, item):
        return self.batch[item]

    def __setitem__(self, key, value):
        self.batch[key] = value

    def deattach(self):
        return Batch(self)

    def lastScaleBatch(self):
        return Batch(self.batch[-4:])

    def firstScaleBatch(self):
        return Batch(self.batch[:4])

    def highResRGBs(self, set=None):
        if set is not None:
            self.batch[0:2] = set
        return self.batch[0:2]

    def highResDisps(self, set=None):
        if set is not None:
            self.batch[2:4] = set
        return self.batch[2:4]

    def lowResRGBs(self, set=None):
        if set is not None:
            self.batch[4:6] = set
        return self.batch[4:6]

    def lowResDisps(self, set=None):
        if set is not None:
            self.batch[6:8] = set
        return self.batch[6:8]

    def lowestResRGBs(self, set=None):
        if set is not None:
            self.batch[-4:-2] = set
        return self.batch[-4:-2]

    def lowestResDisps(self, set=None):
        if set is not None:
            self.batch[-2:] = set
        return self.batch[-2:]

    def allRGBs(self, set=None):
        if set is not None:
            self.batch[0::4] = set[:len(set) // 2]
            self.batch[1::4] = set[len(set) // 2:]
        return self.batch[0::4] + self.batch[1::4]

    def allDisps(self, set=None):
        if set is not None:
            self.batch[2::4] = set[:len(set) // 2]
            self.batch[3::4] = set[len(set) // 2:]
        return self.batch[2::4] + self.batch[3::4]
