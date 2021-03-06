import torch.optim as optim
import torch
import torch.nn as nn
from utils import myUtils
import collections
from .SRStereo import SRStereo
from .. import SR


class SRdispStereo(SRStereo):
    def __init__(self, maxdisp=192, dispScale=1, cuda=True, half=False, stage='unnamed', dataset=None,
                 saveFolderSuffix=''):
        super(SRdispStereo, self).__init__(maxdisp=maxdisp, dispScale=dispScale, cuda=cuda, half=half,
                                           stage=stage, dataset=dataset, saveFolderSuffix=saveFolderSuffix)
        self._getSr = lambda: SR.SRdisp(cuda=cuda, half=half, stage=stage, dataset=dataset, saveFolderSuffix=saveFolderSuffix)

    # imgL: RGB value range 0~1
    # output: RGB value range 0~1
    # mask: useless in this case
    def predict(self, batch, mask=(1,1)):
        myUtils.assertBatchLen(batch, 4)
        self.predictPrepare()

        cated, warpTos = self._sr.warpAndCat(batch)
        batch.highResRGBs(cated)
        outputs = super(SRdispStereo, self).predict(batch)
        outputsReturn = [[warpTo] + outputsSide for warpTo, outputsSide in zip(warpTos, outputs)]
        return outputsReturn

    def test(self, batch, evalType='l1', returnOutputs=False, kitti=False):
        scores, outputs, rawOutputs = super(SRdispStereo, self).test(batch, evalType, returnOutputs, kitti)
        for (warpTo, outSRs, (outDispHigh, outDispLow)), side in zip(rawOutputs, ('L', 'R')):
            if returnOutputs:
                if warpTo is not None:
                    outputs['warpTo' + side] = warpTo
        return scores, outputs, rawOutputs

    # weights: weights of
    #   SR output losses (lossSR),
    #   SR disparity map losses (lossDispHigh),
    #   normal sized disparity map losses (lossDispLow)
    def train(self, batch, returnOutputs=False, kitti=False, weights=(0, 1, 0), progress=0):
        myUtils.assertBatchLen(batch, (4, 8))
        if len(batch) == 4:
            batch = myUtils.Batch([None] * 4 + batch.batch)

        cated, warpTos = self._sr.warpAndCat(batch.lastScaleBatch())

        # if has no highResRGBs, use lowestResRGBs as GTs
        if all([sr is None for sr in batch.highResRGBs()]):
            batch.highResRGBs(batch.lowestResRGBs())

        batch.lowestResRGBs(cated)

        losses, outputs = super(SRdispStereo, self).train(
            batch, returnOutputs=returnOutputs, kitti=kitti, weights=weights
        )
        for warpTo, side in zip(warpTos, ('L', 'R')):
            if returnOutputs:
                if warpTo is not None:
                    outputs['warpTo' + side] = warpTo

        return losses, outputs



