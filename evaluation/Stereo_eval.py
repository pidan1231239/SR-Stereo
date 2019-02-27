import time
import torch
import os
from models import Stereo
from utils import myUtils
from evaluation.Evaluation import Evaluation as Base


# Evaluation for any stereo model including SR-Stereo
class Evaluation(Base):
    def __init__(self, testImgLoader, evalFcn='outlier', ndisLog=1):
        super(Evaluation, self).__init__(testImgLoader, evalFcn, ndisLog)

    def _evalIt(self, batch, log):
        if len(batch) > 4:
            # use large scale for input and small scale for gt
            batch = batch[0:2] + batch[6:8]

        if log:
            scores, outputs = self.model.test(*batch, type=self.evalFcn, returnOutputs=True, kitti=self.testImgLoader.kitti)
            imgs = batch[2:4] + outputs

            # save Tensorboard logs to where checkpoint is.
            self.tensorboardLogger.set(self.model.logFolder)
            for name, disp in zip(('gtL', 'gtR', 'ouputL', 'ouputR'), imgs):
                self.tensorboardLogger.logFirstNIms('testImages/' + name, disp, self.model.maxdisp,
                                                    global_step=1, n=self.ndisLog)
        else:
            scores, _ = self.model.test(*batch, type=self.evalFcn, returnOutputs=False, kitti=self.testImgLoader.kitti)

        scoresPairs = myUtils.NameValues(('L', 'R'), scores, prefix=self.evalFcn)
        return scoresPairs


def main():
    parser = myUtils.getBasicParser(
        ['outputFolder', 'maxdisp', 'dispscale', 'model', 'datapath', 'loadmodel', 'no_cuda', 'seed', 'eval_fcn',
         'ndis_log', 'dataset', 'load_scale', 'batchsize_test', 'half'],
        description='evaluate Stereo net or SR-Stereo net')
    args = parser.parse_args()
    args.cuda = not args.no_cuda and torch.cuda.is_available()

    torch.manual_seed(args.seed)
    if args.cuda:
        torch.cuda.manual_seed(args.seed)

    # Dataset
    import dataloader
    _, testImgLoader = dataloader.getDataLoader(datapath=args.datapath, dataset=args.dataset,
                                                batchSizes=(0, args.batchsize_test),
                                                loadScale=args.load_scale, mode='testing')

    # Load model
    stage, _ = os.path.splitext(os.path.basename(__file__))
    stage = os.path.join(args.outputFolder, stage) if args.outputFolder is not None else stage
    stereo = getattr(Stereo, args.model)(maxdisp=args.maxdisp, dispScale=args.dispscale,
                                         half=args.half, cuda=args.cuda, stage=stage)
    if args.loadmodel is not None:
        stereo.load(args.loadmodel)

    # Test
    test = Evaluation(testImgLoader=testImgLoader, evalFcn=args.eval_fcn,
                      ndisLog=args.ndis_log)
    test(model=stereo)
    test.log()


if __name__ == '__main__':
    main()
