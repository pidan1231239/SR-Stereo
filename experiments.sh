#!/usr/bin/env bash

## datasets
carla_kitti_dataset_moduletest=../datasets/carla_kitti/carla_kitti_sr_lowquality_moduletest
carla_kitti_dataset_overfit=../datasets/carla_kitti/carla_kitti_sr_lowquality_overfit
carla_kitti_dataset=../datasets/carla_kitti/carla_kitti_sr_lowquality/
sceneflow_dataset=../datasets/sceneflow/
kitti2015_dataset=../datasets/kitti/data_scene_flow/training/
kitti2015_sr_dataset=../datasets/kitti/data_scene_flow_sr/training/
kitti2015_dense_dataset=../datasets/kitti/data_scene_flow_dense/training/
kitti2012_dataset=../datasets/kitti/data_stereo_flow/training/

## dir setting
pretrained_dir=logs/pretrained
experiment_dir=logs/experiments
experiment_bak_dir=logs/experiments_bak

## pretrained models
pretrained_PSMNet_sceneflow=${pretrained_dir}/PSMNet_pretrained_sceneflow/PSMNet_pretrained_sceneflow.tar
pretrained_PSMNet_kitti2012=${pretrained_dir}/PSMNet_pretrained_model_KITTI2012/PSMNet_pretrained_model_KITTI2012.tar
pretrained_PSMNet_kitti2015=${pretrained_dir}/PSMNet_pretrained_model_KITTI2015/PSMNet_pretrained_model_KITTI2015.tar
pretrained_EDSR_DIV2K=${pretrained_dir}/EDSR_pretrained_DIV2K/EDSR_baseline_x2.pt

## GPU settings
export CUDA_VISIBLE_DEVICES=0,1,2,3
nGPUs=$(( (${#CUDA_VISIBLE_DEVICES} + 1) / 2 ))


## carla experiments

# experiment settings
pretrained_Stereo2_carla=${experiment_dir}/pretrain_Stereo1_Stereo2/Stereo_train/190312090325_PSMNetDown_loadScale_1.0_0.5_trainCrop_128_1024_batchSize_12_lossWeights_0.8_0.2_carla_kitti
pretrained_Stereo1_carla=${experiment_dir}/pretrain_Stereo1_Stereo2/Stereo_train/190309172438_PSMNet_loadScale_0.5_trainCrop_128_1024_batchSize_12_lossWeights_1_carla_kitti

pretrained_SR_carla=${experiment_dir}/pretrain_SR_SRdisp_carla/SR_train/190313084045_SR_loadScale_1_0.5_trainCrop_64_2040_batchSize_16_lossWeights_1_carla_kitti
pretrained_SRdisp_carla=${experiment_dir}/pretrain_SR_SRdisp_carla/SR_train/190312223712_SRdisp_loadScale_1_0.5_trainCrop_64_2040_batchSize_16_lossWeights_1_carla_kitti


# prepare: pretrain_Stereo1_Stereo2 (DONE)
# train Stereo2
#PYTHONPATH=./ python train/Stereo_train.py --model PSMNetDown --dispscale 2 --outputFolder experiments/pretrain_Stereo1_Stereo2 --datapath $carla_kitti_dataset --dataset carla_kitti  --trainCrop 128 1024 --epochs 10 --log_every 50 --test_every 2 --eval_fcn l1 --batchsize_train 12 --batchsize_test $nGPUs --lr 0.001 4 0.0005 6 0.00025 8 0.000125 --lossWeights 0.75 0.25 --loadmodel $pretrained_PSMNet_sceneflow --load_scale 1 0.5 --half
# train Stereo1
#PYTHONPATH=./ python train/Stereo_train.py --model PSMNet --dispscale 1 --outputFolder experiments/pretrain_Stereo1_Stereo2 --datapath $carla_kitti_dataset --dataset carla_kitti  --trainCrop 128 1024 --epochs 10 --log_every 50 --test_every 2 --eval_fcn l1 --batchsize_train 12 --batchsize_test $nGPUs --lr 0.001 4 0.0005 6 0.00025 8 0.000125 --loadmodel $pretrained_PSMNet_sceneflow --load_scale 0.5 --half


# experiment 1: SR_SRdisp_compare_carla (DONE)
# test subject: SRdisp > SR
# finetune SRdisp
#PYTHONPATH=./ python train/SR_train.py --model SRdisp --outputFolder experiments/SR_SRdisp_compare_carla --datapath $carla_kitti_dataset --dataset carla_kitti --trainCrop 96 1360 --epochs 20 --log_every 50 --test_every 2 --eval_fcn l1 --batchsize_train 4 --batchsize_test $(( 2 * $nGPUs)) --lr 0.0001 10 0.00005 15 0.00002 --loadmodel $pretrained_EDSR_DIV2K --half
# finetune SR
#PYTHONPATH=./ python train/SR_train.py --model SR --outputFolder experiments/SR_SRdisp_compare_carla --datapath $carla_kitti_dataset --dataset carla_kitti --trainCrop 96 1360 --epochs 20 --log_every 50 --test_every 2 --eval_fcn l1 --batchsize_train 4 --batchsize_test $(( 2 * $nGPUs))  --lr 0.0001 10 0.00005 15 0.00002 --loadmodel $pretrained_EDSR_DIV2K --half


## prepare: pretrain_SR_SRdisp_carla (DONE)
## note: In experiment 1, SR and SRdisp are trained with full precision. Here we pretrain both with half precision.
## finetune SR
#PYTHONPATH=./ python train/SR_train.py --model SR --outputFolder experiments/pretrain_SR_SRdisp_carla --datapath $carla_kitti_dataset --dataset carla_kitti --trainCrop 64 2040 --epochs 40 --log_every 50 --test_every 5 --eval_fcn l1 --batchsize_train 16 --batchsize_test $(( 2 * $nGPUs))  --lr 0.0001 25 0.00005 30 0.00002 35 0.00001 --loadmodel $pretrained_EDSR_DIV2K --half
## finetune SRdisp
#PYTHONPATH=./ python train/SR_train.py --model SRdisp --outputFolder experiments/pretrain_SR_SRdisp_carla --datapath $carla_kitti_dataset --dataset carla_kitti --trainCrop 64 2040 --epochs 40 --log_every 50 --test_every 5 --eval_fcn l1 --batchsize_train 16 --batchsize_test $(( 2 * $nGPUs)) --lr 0.0005 15 0.0002 20 0.0001 25 0.00005 30 0.00002 35 0.00001 --loadmodel $pretrained_EDSR_DIV2K --half


## experiment 2: Stereo1_Stereo2_compare_carla (DONE)
## test subject: Stereo2 (PSMNetDown，upbound) > Stereo1 (PSMNet)
## finetune Stereo1
#PYTHONPATH=./ python train/Stereo_train.py --model PSMNet --dispscale 1 --outputFolder experiments/Stereo1_Stereo2_compare_carla --datapath $carla_kitti_dataset --dataset carla_kitti  --trainCrop 128 1024 --epochs 5 --log_every 50 --test_every 1 --eval_fcn l1 --batchsize_train 12 --batchsize_test $nGPUs --lr 0.0001 --loadmodel $pretrained_Stereo1_carla --load_scale 0.5 --half
## finetune Stereo2
#PYTHONPATH=./ python train/Stereo_train.py --model PSMNetDown --dispscale 2 --outputFolder experiments/Stereo1_Stereo2_compare_carla --datapath $carla_kitti_dataset --dataset carla_kitti  --trainCrop 128 1024 --epochs 5 --log_every 50 --test_every 1 --eval_fcn l1 --batchsize_train 12 --batchsize_test $nGPUs --lr 0.0001 --lossWeights 0.75 0.25 --loadmodel $pretrained_Stereo2_carla --load_scale 1 0.5 --half


## experiment 3: SRStereo_Stereo1_compare_carla (DONE)
## test subject: SRStereo (baseline) > Stereo2 (PSMNet)
## finetune SRStereo
#PYTHONPATH=./ python train/Stereo_train.py  --model SRStereo --dispscale 2 --outputFolder experiments/SRStereo_Stereo1_compare_carla --datapath $carla_kitti_dataset --dataset carla_kitti --load_scale 1 0.5 --trainCrop 128 1024 --epochs 5 --log_every 50 --test_every 0 --eval_fcn l1 --batchsize_train 12 --batchsize_test $nGPUs --lr 0.0001 --lossWeights 0.5 0.375 0.125 --loadmodel $pretrained_SR_carla $pretrained_Stereo2_carla --half


## experiment 4: SRdispStereo_SRStereo_compare_carla (DONE)
## test subject: SRdispStereo (upbound) > SRStereo
## finetune SRdispStereo using same parameters with SRStereo_Stereo1_compare_carla
#PYTHONPATH=./ python train/Stereo_train.py  --model SRdispStereo --dispscale 2 --outputFolder experiments/SRdispStereo_SRStereo_compare_carla --datapath $carla_kitti_dataset --dataset carla_kitti --load_scale 1 0.5 --trainCrop 128 1024 --epochs 5 --log_every 50 --test_every 0 --eval_fcn l1 --batchsize_train 12 --batchsize_test $nGPUs --lr 0.0001 --lossWeights 0.5 0.375 0.125 --loadmodel $pretrained_SRdisp_carla $pretrained_Stereo2_carla --half


## experiment 5: SRdispStereoRefine_SRStereo_compare_carla (DONE)
## test subject: SRdispStereoRefine (proposed) > SRStereo
## finetune SRdispStereoRefine using same parameters with SRStereo_Stereo1_compare_carla
#PYTHONPATH=./ python train/Stereo_train.py  --model SRdispStereoRefine --dispscale 2 --outputFolder experiments/SRdispStereoRefine_SRStereo_compare_carla --datapath $carla_kitti_dataset --dataset carla_kitti --load_scale 1 0.5 --trainCrop 128 1024 --epochs 5 --log_every 50 --test_every 0 --eval_fcn l1 --itRefine 2 --batchsize_train 12 --batchsize_test $nGPUs --lr 0.0001 --lossWeights 0.5 0.375 0.125 --loadmodel $pretrained_SRdisp_carla $pretrained_Stereo2_carla --half


## kitti experiments

# experiment settings
finetuned_Stereo2_carla=${experiment_dir}/Stereo1_Stereo2_compare_carla/Stereo_train/190310025752_PSMNetDown_loadScale_1.0_0.5_trainCrop_128_1024_batchSize_12_lossWeights_0.8_0.2_carla_kitti
pretrained_Stereo2_kitti=${experiment_dir}/pretrain_Stereo2_kitti/Stereo_train/190316090420_PSMNetDown_loadScale_1.0_0.5_trainCrop_128_1024_batchSize_12_lossWeights_0.0_1.0_kitti2015

pretrained_SR_kitti=${experiment_dir}/pretrain_SR_kitti/SR_train/190316231816_SR_loadScale_1_0.5_trainCrop_64_512_batchSize_64_lossWeights_1_kitti2015
pretrained_PSMNet_kitti2015_trainSet=${experiment_dir}/SRStereo_PSMNet_compare_kitti/Stereo_train/190315145644_PSMNet_loadScale_1.0_trainCrop_256_512_batchSize_12_lossWeights_1_kitti2015
pretrained_SRStereo_kitti=${experiment_dir}/SRStereo_PSMNet_compare_kitti/Stereo_train/190317085332_SRStereo_loadScale_1.0_trainCrop_64_512_batchSize_12_lossWeights_-1.0_0.0_1.0_kitti2015
finetuned_SRStereo_kitti=${experiment_dir}/SRStereo_PSMNet_compare_kitti/Stereo_train/190317232241_SRStereo_loadScale_1.0_trainCrop_64_512_batchSize_12_lossWeights_0.5_0.0_0.5_kitti2015/checkpoint_epoch_0235_it_00014.tar

finetuned_SRdispStereoRefine_carla=${experiment_dir}/SRdispStereoRefine_SRStereo_compare_carla/Stereo_train/190313215524_SRdispStereoRefine_loadScale_1.0_0.5_trainCrop_128_1024_batchSize_12_lossWeights_0.5_0.4_0.1_carla_kitti
pretrained_SRdisp_kitti=${experiment_dir}/pretrain_SRdisp_kitti/SR_train/190318145359_SRdisp_loadScale_1_0.5_trainCrop_64_2040_batchSize_16_lossWeights_1_kitti2015_dense

## prepare: pretrain_SR_kitti (DONE: 190316231816)
## finetune SR on kitti2015
#PYTHONPATH=./ python train/SR_train.py --model SR --outputFolder experiments/pretrain_SR_kitti --datapath $kitti2015_dataset --dataset kitti2015 --trainCrop 64 512 --epochs 6000 --save_every 300 --log_every 50 --test_every 50 --eval_fcn l1 --batchsize_train 64 --batchsize_test $(( 4 * $nGPUs))  --lr 0.0001 --loadmodel $pretrained_EDSR_DIV2K --half


## experiment 6: SRStereo_PSMNet_compare_kitti (DONE)
## test subject: fintuning SRStereo with KITTI 2015
## create baseline PSMNet (DONE: 190315145644)
#PYTHONPATH=./ python train/Stereo_train.py  --model PSMNet --dispscale 1 --outputFolder experiments/SRStereo_PSMNet_compare_kitti --datapath $kitti2015_dataset --dataset kitti2015 --load_scale 1 --trainCrop 256 512 --epochs 1200 --save_every 50  --log_every 50 --test_every 10 --eval_fcn outlier --batchsize_train 12 --batchsize_test $nGPUs --lr 0.001 200 0.0001 --loadmodel $pretrained_PSMNet_sceneflow
## finetune SRStereo initialized with PSMNet pretrained with KITTI and SR finetuned with KITTI without updating SR (DONE: 190317085332)
#PYTHONPATH=./ python train/Stereo_train.py  --model SRStereo --dispscale 2 --outputFolder experiments/SRStereo_PSMNet_compare_kitti --datapath $kitti2015_dataset --dataset kitti2015 --load_scale 1 --trainCrop 64 512 --epochs 1200 --save_every 50 --log_every 50 --test_every 10 --eval_fcn outlier --batchsize_train 12 --batchsize_test $nGPUs --lr 0.001 300 0.0005 450 0.0002 600 0.0001 --lossWeights -1 0 1 --loadmodel $pretrained_SR_kitti $pretrained_PSMNet_kitti2015_trainSet --half
## finetune SRStereo initialized with 190317085332 with updating SR (DONE: 190317232241)
#PYTHONPATH=./ python train/Stereo_train.py  --model SRStereo --dispscale 2 --outputFolder experiments/SRStereo_PSMNet_compare_kitti --datapath $kitti2015_dataset --dataset kitti2015 --load_scale 1 --trainCrop 64 512 --epochs 300 --save_every 1 --log_every 50 --test_every 1 --eval_fcn outlier --batchsize_train 12 --batchsize_test $nGPUs --lr 0.0001 --lossWeights 0.5 0 0.5 --loadmodel $pretrained_SRStereo_kitti --half
## finetune PSMNet with the same settings as last 300 epochs of SRStereo(DONE)
#PYTHONPATH=./ python train/Stereo_train.py  --model PSMNet --dispscale 1 --outputFolder experiments/SRStereo_PSMNet_compare_kitti --datapath $kitti2015_dataset --dataset kitti2015 --load_scale 1 --trainCrop 256 512 --epochs 300 --save_every 1  --log_every 50 --test_every 1 --eval_fcn outlier --batchsize_train 12 --batchsize_test $nGPUs --lr 0.0001 --loadmodel $pretrained_PSMNet_kitti2015_trainSet


## prepare: pretrain_SRdisp_kitti (DONE)
## generate GTs of SR and dense disparity map with finetuned SRStereo
#PYTHONPATH=./ python submission/SR_sub.py --datapath $kitti2015_dataset --dataset kitti2015 --loadmodel $finetuned_SRStereo_kitti --load_scale 2 1 --subtype subTrainEval --half
#PYTHONPATH=./ python submission/Stereo_sub.py --model SRStereo --dispscale 2 --datapath $kitti2015_dataset --dataset kitti2015 --loadmodel $finetuned_SRStereo_kitti --load_scale 1 --subtype subTrainEval --half
## finetune SRdisp on kitti2015_dense: compare different initialization checkpoints (DONE: 190318145359)
#PYTHONPATH=./ python train/SR_train.py --model SRdisp --outputFolder experiments/pretrain_SRdisp_kitti --datapath $kitti2015_dense_dataset --dataset kitti2015_dense --trainCrop 64 2040 --epochs 1500 --save_every 50 --log_every 50 --test_every 10 --eval_fcn l1 --batchsize_train 16 --batchsize_test $(( 2 * $nGPUs)) --lr 0.0005 300 0.0002 500 0.0001 700 0.00005 900 0.00002 1100 0.00001 --loadmodel $finetuned_SRdispStereoRefine_carla --half


## experiment 7: SRdispStereoRefine_PSMNet_compare_kitti (DOING)
## test subject: fintuning SRdispStereoRefine with KITTI 2015
## fintune SRdispStereoRefine with updating SRdisp
# (DONE: 190319082201)
#PYTHONPATH=./ python train/Stereo_train.py  --model SRdispStereoRefine --dispscale 2 --outputFolder experiments/SRdispStereoRefine_PSMNet_compare_kitti --datapath $kitti2015_dataset --dataset kitti2015 --load_scale 1 --trainCrop 64 512 --epochs 300 --save_every 50 --log_every 10 --test_every -30 --eval_fcn outlier --itRefine 2 --batchsize_train 12 --batchsize_test $nGPUs --lr 0.0001 --lossWeights 0.5 0 0.5 --loadmodel $pretrained_SRdisp_kitti $finetuned_SRStereo_kitti --half
# (DONE: 190319175407)
#PYTHONPATH=./ python train/Stereo_train.py  --model SRdispStereoRefine --dispscale 2 --outputFolder experiments/SRdispStereoRefine_PSMNet_compare_kitti --datapath $kitti2015_dataset --dataset kitti2015 --load_scale 1 --trainCrop 64 512 --epochs 300 --save_every 50 --log_every 10 --test_every -30 --eval_fcn outlier --itRefine 2 --batchsize_train 12 --batchsize_test $nGPUs --lr 0.00002 --lossWeights 0.5 0 0.5 --loadmodel $pretrained_SRdisp_kitti $finetuned_SRStereo_kitti --half
# initialize SRdisp wirh $finetuned_SRdispStereoRefine_carla. finetune with updating SRdisp (DONE: 190320081959)
#PYTHONPATH=./ python train/Stereo_train.py  --model SRdispStereoRefine --dispscale 2 --outputFolder experiments/SRdispStereoRefine_PSMNet_compare_kitti --datapath $kitti2015_dataset --dataset kitti2015 --load_scale 1 --trainCrop 64 512 --epochs 300 --save_every 50 --log_every 10 --test_every -30 --eval_fcn outlier --itRefine 2 --batchsize_train 12 --batchsize_test $nGPUs --lr 0.0001 --lossWeights 0.5 0 0.5 --loadmodel $finetuned_SRdispStereoRefine_carla $finetuned_SRStereo_kitti --half
# initialize SRdisp wirh $finetuned_SRdispStereoRefine_carla. finetune without updating SRdisp (DONE: 190320102041)
PYTHONPATH=./ python train/Stereo_train.py  --model SRdispStereoRefine --dispscale 2 --outputFolder experiments/SRdispStereoRefine_PSMNet_compare_kitti --datapath $kitti2015_dataset --dataset kitti2015 --load_scale 1 --trainCrop 64 512 --epochs 300 --save_every 50 --log_every 10 --test_every -30 --eval_fcn outlier --itRefine 2 --batchsize_train 12 --batchsize_test $nGPUs --lr 0.0001 --lossWeights -1 0 1 --loadmodel $finetuned_SRdispStereoRefine_carla $finetuned_SRStereo_kitti --half

