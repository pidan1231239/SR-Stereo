from __future__ import print_function
import torch.utils.data
import time
import os
from models import Stereo
from evaluation import Stereo_eval
from utils import myUtils
import sys
from train.Train import Train as Base


class Train(Base):
    def __init__(self, trainImgLoader, nEpochs, lr=(0.001,), logEvery=1, testEvery=1, ndisLog=1, Test=None,
                 lossWeights=(1,), startEpoch=1, saveEvery=1):
        super(Train, self).__init__(trainImgLoader, nEpochs, lr, logEvery, testEvery, ndisLog, Test, startEpoch, saveEvery)
        self.lossWeights = lossWeights

    def _trainIt(self, batch, log):
        super(Train, self)._trainIt(batch, log)
        progress = self.global_step / (len(self.trainImgLoader) * self.nEpochs)
        losses, outputs = self.model.train(batch.detach(),
                                           returnOutputs=log,
                                           kitti=self.trainImgLoader.kitti,
                                           weights=self.lossWeights,
                                           progress=progress)
        if log:
            for disp, input, sr, side in zip(
                    batch.lowestResDisps(),
                    batch.lowestResRGBs(),
                    batch.highResRGBs() if len(batch) == 8 else (None, None),
                    ('L', 'R')):
                if disp is not None:
                    outputs['gtDisp' + side] = disp / self.model.outputMaxDisp
                if sr is not None:
                    outputs['gtSr' + side] = sr
                outputs['input' + side] = input # lowestResRGBs should be input in most cases

        return losses, outputs

    def log(self, additionalValue=(), endMessage=None):
        super(Train, self).log(additionalValue=myUtils.NameValues(['lossWeights'], [self.lossWeights]))


def main():
    parser = myUtils.getBasicParser(
        ['outputFolder', 'maxdisp', 'dispscale', 'model', 'datapath', 'loadmodel', 'no_cuda', 'seed', 'eval_fcn',
         'ndis_log', 'dataset', 'load_scale', 'trainCrop', 'batchsize_test', 'subValidSet',
         'batchsize_train', 'log_every', 'test_every', 'save_every', 'epochs', 'lr', 'half',
         'lossWeights', 'randomLR', 'resume', 'itRefine', 'subtype'],
        description='train or finetune Stereo net')

    args = parser.parse_args()
    args.cuda = not args.no_cuda and torch.cuda.is_available()

    torch.manual_seed(args.seed)
    if args.cuda:
        torch.cuda.manual_seed(args.seed)

    # Dataset
    import dataloader
    trainImgLoader, testImgLoader = dataloader.getDataLoader(datapath=args.datapath, dataset=args.dataset,
                                                             trainCrop=args.trainCrop,
                                                             batchSizes=(args.batchsize_train, args.batchsize_test),
                                                             loadScale=args.load_scale,
                                                             mode='training' if args.subtype is None else args.subtype,
                                                             randomLR=args.randomLR,
                                                             subValidSet=args.subValidSet)

    # Load model
    stage, _ = os.path.splitext(os.path.basename(__file__))
    stage = os.path.join(args.outputFolder, stage) if args.outputFolder is not None else stage
    saveFolderSuffix = myUtils.NameValues(('loadScale', 'trainCrop', 'batchSize','lossWeights'),
                                          (trainImgLoader.loadScale,
                                           trainImgLoader.trainCrop,
                                           args.batchsize_train,
                                           args.lossWeights))
    stereo = getattr(Stereo, args.model)(maxdisp=args.maxdisp, dispScale=args.dispscale,
                                         cuda=args.cuda, half=args.half,
                                         stage=stage,
                                         dataset=args.dataset,
                                         saveFolderSuffix=saveFolderSuffix.strSuffix())
    if hasattr(stereo, 'itRefine'):
        stereo.itRefine = args.itRefine
    epoch, iteration = stereo.load(args.loadmodel)

    # Train
    test = Stereo_eval.Evaluation(testImgLoader=testImgLoader, evalFcn=args.eval_fcn,
                                  ndisLog=args.ndis_log) if testImgLoader is not None else None
    train = Train(trainImgLoader=trainImgLoader, nEpochs=args.epochs, lr=args.lr,
                  logEvery=args.log_every, ndisLog=args.ndis_log,
                  testEvery=args.test_every, Test=test, lossWeights=args.lossWeights,
                  startEpoch=epoch + 1 if args.resume else 0, saveEvery=args.save_every)
    train(model=stereo)


if __name__ == '__main__':
    main()
