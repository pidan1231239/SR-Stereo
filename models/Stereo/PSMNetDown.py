import os
import time
import torch.optim as optim
import torch
import torch.nn.functional as F
import torch.nn as nn
from evaluation import evalFcn
from utils import myUtils
from .RawPSMNet import stackhourglass as rawPSMNet
from .RawPSMNet_TieCheng import stackhourglass as rawPSMNet_TieCheng
from ..Model import Model
from .. import SR
import collections
import torch.nn.parallel as P
from .PSMNet import *


class RawPSMNetDown(RawPSMNetScale):
    def __init__(self, maxdisp, dispScale, multiple):
        super(RawPSMNetDown, self).__init__(maxdisp, dispScale, multiple)
        self.pool = nn.AvgPool2d((2, 2))

    # input: RGB value range 0~1
    # outputs: disparity range 0~self.maxdisp * self.dispScale / 2
    def forward(self, left, right):
        outDispHighs = super(RawPSMNetDown, self).forward(left, right)
        outDispLows = myUtils.forNestingList(outDispHighs, lambda disp: self.pool(disp) / 2)
        return outDispHighs, outDispLows


class PSMNetDown(PSMNet):

    # dataset: only used for suffix of saveFolderName
    def __init__(self, maxdisp=192, dispScale=1, cuda=True, half=False, stage='unnamed', dataset=None,
                 saveFolderSuffix=''):
        super(PSMNetDown, self).__init__(maxdisp, dispScale, cuda, half, stage, dataset, saveFolderSuffix)
        self.outputMaxDisp = self.outputMaxDisp // 2
        self.getModel = RawPSMNetDown

    def loss(self, outputs, gts, kitti=False, outputMaxDisp=None):
        if outputMaxDisp is not None:
            raise Exception('Error: outputMaxDisp of PSMNetDown has no use!')
        losses = []
        for output, gt, outputMaxDisp in zip(outputs, gts, (self.outputMaxDisp * 2, self.outputMaxDisp)):
            losses.append(super(PSMNetDown, self).loss(
                output, gt, kitti=kitti, outputMaxDisp=outputMaxDisp
            ) if gt is not None else None)
        return losses

    def trainOneSide(self, imgL, imgR, gts, returnOutputs=False, kitti=False, weights=(1, 0)):
        self.optimizer.zero_grad()
        outDispHighs, outDispLows = self.model.forward(imgL, imgR)
        losses = self.loss((outDispHighs, outDispLows), gts, kitti=kitti)
        loss = sum([weight * loss for weight, loss in zip(weights, losses) if loss is not None])
        with self.amp_handle.scale_loss(loss, self.optimizer) as scaled_loss:
            scaled_loss.backward()
        self.optimizer.step()

        dispOuts = []
        if returnOutputs:
            with torch.no_grad():
                dispOuts.append(outDispHighs[2].detach() / (self.outputMaxDisp * 2))
                dispOuts.append(outDispLows[2].detach() / self.outputMaxDisp)
        losses = [loss] + losses
        return [loss.data.item() for loss in losses], dispOuts

    def train(self, batch, returnOutputs=False, kitti=False, weights=(1, 0), progress=0):
        myUtils.assertBatchLen(batch, 8)
        self.trainPrepare()

        losses = myUtils.NameValues()
        outputs = collections.OrderedDict()
        imgL, imgR = batch.highResRGBs()
        for inputL, inputR, gts, process, side in zip(
                (imgL, imgR), (imgR, imgL),
                zip(batch.highResDisps(), batch.lowResDisps()),
                (lambda im: im, myUtils.flipLR),
                ('L', 'R')
        ):
            if not all([gt is None for gt in gts]):
                lossesList, outputsList = self.trainOneSide(
                    *process((inputL, inputR, gts)),
                    returnOutputs=returnOutputs,
                    kitti=kitti,
                    weights=weights
                )
                for suffix, loss in zip(('', 'DispHigh', 'Disp'), lossesList):
                    if loss is not None:
                        losses['loss' + suffix + side] = loss

                if returnOutputs:
                    for suffix, output in zip(('High', 'Low'), outputsList):
                        outputs['outputDisp' + suffix + side] = process(output)

        return losses, outputs

    def test(self, batch, evalType='l1', returnOutputs=False, kitti=False):
        myUtils.assertBatchLen(batch, 8)
        batch = myUtils.Batch(batch.highResRGBs() + batch.lowestResDisps(), cuda=batch.cuda, half=batch.half)
        scores, outputs, rawOutputs = super(PSMNetDown, self).test(batch, evalType, returnOutputs, kitti)
        for rawOutputsSide, side in zip(rawOutputs, ('L', 'R')):
            if rawOutputsSide is not None:
                (outDispHigh, outDispLow) = rawOutputsSide
                if returnOutputs:
                    if outDispHigh is not None:
                        outputs['outputDispHigh' + side] = outDispHigh / (self.outputMaxDisp * 2)
        return scores, outputs, rawOutputs


