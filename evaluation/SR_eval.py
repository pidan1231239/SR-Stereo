import time
import torch
import os
from models import SR
from utils import myUtils
from evaluation.Evaluation import Evaluation as Base


# Evaluation for any stereo model including SR-Stereo
class Evaluation(Base):
    def __init__(self, testImgLoader, evalFcn='l1', ndisLog=1):
        super(Evaluation, self).__init__(testImgLoader, evalFcn, ndisLog)

    def _evalIt(self, batch, log):

        if log:
            scores, outputs = self.model.test(batch, type=self.evalFcn, returnOutputs=True)
            imgs = batch[4:6] + batch[0:2] + outputs

            # save Tensorboard logs to where checkpoint is.
            self.tensorboardLogger.set(self.model.logFolder)
            for imsSide, side in zip((imgs[0::2], imgs[1::2]), ('L', 'R')):
                for name, im in zip(('input', 'gt', 'output'), imsSide):
                    self.tensorboardLogger.logFirstNIms('testImages/' + name + side, im, 1,
                                                        global_step=1, n=self.ndisLog)
        else:
            scores, _ = self.model.test(batch, type=self.evalFcn, returnOutputs=False)

        scoresPairs = myUtils.NameValues(('L', 'R'), scores, prefix=self.evalFcn)
        return scoresPairs


def main():
    parser = myUtils.getBasicParser(
        ['outputFolder', 'maxdisp', 'dispscale', 'model', 'datapath', 'loadmodel', 'no_cuda', 'seed', 'eval_fcn',
         'ndis_log', 'dataset', 'load_scale', 'batchsize_test', 'half', 'withMask'],
        description='evaluate Stereo net or SR-Stereo net')
    args = parser.parse_args()
    args.cuda = not args.no_cuda and torch.cuda.is_available()

    torch.manual_seed(args.seed)
    if args.cuda:
        torch.cuda.manual_seed(args.seed)

    # Dataset
    import dataloader
    if args.model in ('SR',):
        mask = (1, 1, 0, 0)
        cInput = 3
    elif args.model in ('SRdisp',):
        mask = (1, 1, 1, 1)
        cInput = cInput = 7 if args.withMask else 6
    else:
        raise Exception('Error: No model named \'%s\'!' % args.model)
    _, testImgLoader = dataloader.getDataLoader(datapath=args.datapath, dataset=args.dataset,
                                                batchSizes=(0, args.batchsize_test),
                                                loadScale=(args.load_scale[0], args.load_scale[0] / 2),
                                                mode='testing',
                                                preprocess=False,
                                                mask=mask)

    # Load model
    stage, _ = os.path.splitext(os.path.basename(__file__))
    stage = os.path.join(args.outputFolder, stage) if args.outputFolder is not None else stage
    sr = getattr(SR, args.model)(cInput=cInput, cuda=args.cuda,
                                 half=args.half, stage=stage,
                                 dataset=args.dataset)
    if args.loadmodel is not None:
        sr.load(args.loadmodel)

    # Test
    test = Evaluation(testImgLoader=testImgLoader, evalFcn=args.eval_fcn,
                      ndisLog=args.ndis_log)
    test(model=sr)
    test.log()


if __name__ == '__main__':
    main()
