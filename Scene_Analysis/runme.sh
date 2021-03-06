#!/bin/bash
# You need to modify this path
DATASET_DIR="/home/mura4197/Downloads/Scene_Detection/2018_data_1/"

# You need to modify this path as your workspace
WORKSPACE="/home/mura4197/Downloads/dcase2018_task1-master/"

DEV_SUBTASK_A_DIR="TUT-urban-acoustic-scenes-2018-development"
DEV_SUBTASK_B_DIR="TUT-urban-acoustic-scenes-2018-mobile-development"
LB_SUBTASK_A_DIR="TUT-urban-acoustic-scenes-2018-leaderboard"
LB_SUBTASK_B_DIR="TUT-urban-acoustic-scenes-2018-mobile-leaderboard"
EVAL_SUBTASK_A_DIR="TUT-urban-acoustic-scenes-2018-evaluation"
EVAL_SUBTASK_B_DIR="TUT-urban-acoustic-scenes-2018-mobile-evaluation"

BACKEND="pytorch"	# "pytorch" | "keras"
HOLDOUT_FOLD=1
GPU_ID=0

############ Extract features ############
python utils/features.py logmel --dataset_dir=$DATASET_DIR --subdir=$DEV_SUBTASK_A_DIR --data_type=development --workspace=$WORKSPACE
#python utils/features.py logmel --dataset_dir=$DATASET_DIR --subdir=$DEV_SUBTASK_B_DIR --data_type=development --workspace=$WORKSPACE
#python utils/features.py logmel --dataset_dir=$DATASET_DIR --subdir=$LB_SUBTASK_A_DIR --data_type=leaderboard --workspace=$WORKSPACE
#python utils/features.py logmel --dataset_dir=$DATASET_DIR --subdir=$LB_SUBTASK_B_DIR --data_type=leaderboard --workspace=$WORKSPACE
#python utils/features.py logmel --dataset_dir=$DATASET_DIR --subdir=$EVAL_SUBTASK_A_DIR --data_type=evaluation --workspace=$WORKSPACE
#python utils/features.py logmel --dataset_dir=$DATASET_DIR --subdir=$EVAL_SUBTASK_B_DIR --data_type=evaluation --workspace=$WORKSPACE

############ Development subtask A ############
# Train model for subtask A
CUDA_VISIBLE_DEVICES=$GPU_ID python $BACKEND/main_$BACKEND.py train --dataset_dir=$DATASET_DIR --subdir=$DEV_SUBTASK_A_DIR --workspace=$WORKSPACE --validate --holdout_fold=$HOLDOUT_FOLD --cuda

# Evaluate subtask A
#CUDA_VISIBLE_DEVICES=$GPU_ID python $BACKEND/main_$BACKEND.py inference_validation_data --dataset_dir=$DATASET_DIR --subdir=$DEV_SUBTASK_A_DIR --workspace=$WORKSPACE --holdout_fold=$HOLDOUT_FOLD --iteration=5000 --cuda

############ Development subtask B ############
# Train model for subtask B
#CUDA_VISIBLE_DEVICES=$GPU_ID python $BACKEND/main_$BACKEND.py train --dataset_dir=$DATASET_DIR --subdir=$DEV_SUBTASK_B_DIR --workspace=$WORKSPACE --validate --holdout_fold=$HOLDOUT_FOLD --cuda

# Evaluate subtask B
#CUDA_VISIBLE_DEVICES=$GPU_ID python $BACKEND/main_$BACKEND.py inference_validation_data --dataset_dir=$DATASET_DIR --subdir=$DEV_SUBTASK_B_DIR --workspace=$WORKSPACE --holdout_fold=$HOLDOUT_FOLD --iteration=5000 --cuda


############ Full train subtask A ############
# Train on full development data
#CUDA_VISIBLE_DEVICES=$GPU_ID python $BACKEND/main_$BACKEND.py train --dataset_dir=$DATASET_DIR --subdir=$DEV_SUBTASK_A_DIR --workspace=$WORKSPACE --cuda

# Inference leaderboard data
#CUDA_VISIBLE_DEVICES=$GPU_ID python $BACKEND/main_$BACKEND.py inference_leaderboard_data --dataset_dir=$DATASET_DIR --dev_subdir=$DEV_SUBTASK_A_DIR --leaderboard_subdir=$LB_SUBTASK_A_DIR --workspace=$WORKSPACE --iteration=5000 --cuda

# Inference evaluation data
#CUDA_VISIBLE_DEVICES=$GPU_ID python $BACKEND/main_$BACKEND.py inference_evaluation_data --dataset_dir=$DATASET_DIR --dev_subdir=$DEV_SUBTASK_A_DIR --eval_subdir=$EVAL_SUBTASK_A_DIR --workspace=$WORKSPACE --iteration=5000 --cuda

############ Full train subtask B ############
# Trian on full development data
#CUDA_VISIBLE_DEVICES=$GPU_ID python $BACKEND/main_$BACKEND.py train --dataset_dir=$DATASET_DIR --subdir=$DEV_SUBTASK_B_DIR --workspace=$WORKSPACE --cuda

# Inference leaderboard data
#CUDA_VISIBLE_DEVICES=$GPU_ID python $BACKEND/main_$BACKEND.py inference_leaderboard_data --dataset_dir=$DATASET_DIR --dev_subdir=$DEV_SUBTASK_B_DIR --leaderboard_subdir=$LB_SUBTASK_B_DIR --workspace=$WORKSPACE --iteration=5000 --cuda

# Inference evaluation data
#CUDA_VISIBLE_DEVICES=$GPU_ID python $BACKEND/main_$BACKEND.py inference_evaluation_data --dataset_dir=$DATASET_DIR --dev_subdir=$DEV_SUBTASK_B_DIR --eval_subdir=$EVAL_SUBTASK_B_DIR --workspace=$WORKSPACE --iteration=5000 --cuda

