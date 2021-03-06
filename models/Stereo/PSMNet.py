import torch
import torch.nn.functional as F
import torch.nn as nn
from utils import myUtils
from .RawPSMNet import stackhourglass as rawPSMNet
import collections
from .Stereo import Stereo
import torch.optim as optim


class RawPSMNetScale(rawPSMNet):
    def __init__(self, maxdisp, dispScale, multiple):
        super(RawPSMNetScale, self).__init__(maxdisp, dispScale)
        self.multiple = multiple
        self.__imagenet_stats = {'mean': [0.485, 0.456, 0.406],
                                 'std': [0.229, 0.224, 0.225]}

    # input: RGB value range 0~1
    # outputs: disparity range 0~self.maxdisp * self.dispScale
    def forward(self, left, right):
        def normalize(nTensor):
            nTensorClone = nTensor.clone()
            for tensor in nTensorClone:
                for t, m, s in zip(tensor, self.__imagenet_stats['mean'], self.__imagenet_stats['std']):
                    t.sub_(m).div_(s)
            return nTensorClone

        left, right = normalize(left), normalize(right)

        if self.training:
            outputs = super(RawPSMNetScale, self).forward(left, right)
        else:
            autoPad = myUtils.AutoPad(left, self.multiple)

            left, right = autoPad.pad((left, right))
            outputs = super(RawPSMNetScale, self).forward(left, right)
            outputs = autoPad.unpad(outputs)
        return outputs

    def load_state_dict(self, state_dict, strict=False):
        match = True
        newModelDict = self.state_dict()
        selectedModelDict = {}
        for loadName, loadValue in state_dict.items():
            posiblePrefix = 'stereo.module.'
            if loadName.startswith(posiblePrefix):
                loadName = loadName[len(posiblePrefix):]
                match = False
            if loadName in newModelDict and newModelDict[loadName].size() == loadValue.size():
                selectedModelDict[loadName] = loadValue
            else:
                message = 'Warning! While copying the parameter named {}, ' \
                          'whose dimensions in the model are {} and ' \
                          'whose dimensions in the checkpoint are {}.' \
                    .format(
                    loadName, newModelDict[loadName].size() if loadName in newModelDict else '(Not found)',
                    loadValue.size()
                )
                if strict:
                    raise Exception(message)
                else:
                    print(message)
        newModelDict.update(selectedModelDict)
        super(RawPSMNetScale, self).load_state_dict(newModelDict, strict=False)
        return match

class PSMNet(Stereo):
    # dataset: only used for suffix of saveFolderName
    def __init__(self, maxdisp=192, dispScale=1, cuda=True, half=False, stage='unnamed', dataset=None,
                 saveFolderSuffix=''):
        super(PSMNet, self).__init__(maxdisp, dispScale, cuda, half, stage, dataset, saveFolderSuffix)

        self.getModel = RawPSMNetScale

    def initModel(self):
        self.model = self.getModel(maxdisp=self.maxdisp, dispScale=self.dispScale, multiple=16)
        self.optimizer = optim.Adam(self.model.parameters(), lr=0.001, betas=(0.9, 0.999))
        if self.cuda:
            self.model = nn.DataParallel(self.model)
            self.model.cuda()

    # input disparity maps: disparity range 0~self.maxdisp * self.dispScale
    def loss(self, outputs, gts, kitti=False, outputMaxDisp=None):
        outputs = [output.unsqueeze(1) for output in outputs]
        # for kitti dataset, only consider loss of none zero disparity pixels in gt
        mask = (gts > 0).detach() if kitti else (gts < outputMaxDisp).detach()
        loss = 0.5 * F.smooth_l1_loss(outputs[0][mask], gts[mask], reduction='mean') + 0.7 * F.smooth_l1_loss(
            outputs[1][mask], gts[mask], reduction='mean') + F.smooth_l1_loss(outputs[2][mask], gts[mask],
                                                                              reduction='mean')
        return loss

    def trainOneSide(self, imgL, imgR, gt, returnOutputs=False, kitti=False):
        self.optimizer.zero_grad()
        outputs = self.model.forward(imgL, imgR)
        loss = self.loss(outputs, gt, kitti=kitti, outputMaxDisp=self.outputMaxDisp)
        with self.amp_handle.scale_loss(loss, self.optimizer) as scaled_loss:
            scaled_loss.backward()
        self.optimizer.step()

        output = outputs[2].detach() / self.outputMaxDisp if returnOutputs else None
        return loss.data.item(), output

    def train(self, batch, returnOutputs=False, kitti=False, weights=(), progress=0):
        myUtils.assertBatchLen(batch, 4)
        self.trainPrepare()
        imgL, imgR = batch.highResRGBs()

        losses = myUtils.NameValues()
        outputs = collections.OrderedDict()
        for inputL, inputR, gt, process, side in zip(
                (imgL, imgR), (imgR, imgL),
                batch.highResDisps(),
                (lambda im: im, myUtils.flipLR),
                ('L', 'R')
        ):
            if gt is not None:
                loss, dispOut = self.trainOneSide(
                    *process([inputL, inputR, gt]),
                    returnOutputs=returnOutputs,
                    kitti=kitti
                )
                losses['lossDisp' + side] = loss
                if returnOutputs:
                    outputs['outputDisp' + side] = process(dispOut)

        return losses, outputs



