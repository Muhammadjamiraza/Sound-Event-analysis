import os
import sys
sys.path.insert(1, os.path.join(sys.path[0], '../utils'))
import numpy as np
import argparse
import h5py
import math
import time
import logging

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

from data_generator import DataGenerator, TestDataGenerator
from utilities import (create_folder, get_filename, create_logging,
                       calculate_confusion_matrix, calculate_accuracy, 
                       plot_confusion_matrix, print_accuracy, 
                       write_leaderboard_submission, write_evaluation_submission)
from models_pytorch import move_data_to_gpu, BaselineCnn, Vggish
import config
import csv
import pandas as pd

Model = Vggish
batch_size = 16
#!/bin/bash
# You need to modify this path
DATASET_DIR="/home/mura4197/Downloads/Scene_Detection/2018_data_1/"

# You need to modify this path as your workspace
WORKSPACE="/home/mura4197/Downloads/Scene_Detection/2018_data_1/data/"

DEV_SUBTASK_A_DIR="audio"
#DEV_SUBTASK_B_DIR="TUT-urban-acoustic-scenes-2018-mobile-development"
#LB_SUBTASK_A_DIR="TUT-urban-acoustic-scenes-2018-leaderboard"
#LB_SUBTASK_B_DIR="TUT-urban-acoustic-scenes-2018-mobile-leaderboard"
#EVAL_SUBTASK_A_DIR="TUT-urban-acoustic-scenes-2018-evaluation"
#EVAL_SUBTASK_B_DIR="TUT-urban-acoustic-scenes-2018-mobile-evaluation"

BACKEND="pytorch"	# "pytorch" | "keras"
HOLDOUT_FOLD=1
GPU_ID=0


def evaluate(model, generator, data_type, devices, max_iteration, cuda):
    """Evaluate
    
    Args:
      model: object.
      generator: object.
      data_type: 'train' | 'validate'.
      devices: list of devices, e.g. ['a'] | ['a', 'b', 'c']
      max_iteration: int, maximum iteration for validation
      cuda: bool.
      
    Returns:
      accuracy: float
    """
    
    # Generate function
    generate_func = generator.generate_validate(data_type=data_type, 
                                                devices=devices, 
                                                shuffle=True, 
                                                max_iteration=max_iteration)
            
    # Forward
    dict = forward(model=model, 
                   generate_func=generate_func, 
                   cuda=cuda, 
                   return_target=True)

    outputs = dict['output']    # (audios_num, classes_num)
    targets = dict['target']    # (audios_num, classes_num)
    
    predictions = np.argmax(outputs, axis=-1)   # (audios_num,)

    # Evaluate
    classes_num = outputs.shape[-1]
    
    loss = F.nll_loss(torch.Tensor(outputs), torch.LongTensor(targets)).numpy()
    loss = float(loss)
    
    confusion_matrix = calculate_confusion_matrix(
        targets, predictions, classes_num)
    
    accuracy = calculate_accuracy(targets, predictions, classes_num, 
                                  average='macro')

    return accuracy, loss


def forward(model, generate_func, cuda, return_target):
    """Forward data to a model.
    
    Args:
      generate_func: generate function
      cuda: bool
      return_target: bool
      
    Returns:
      dict, keys: 'audio_name', 'output'; optional keys: 'target'
    """
    
    outputs = []
    audio_names = []
    
    if return_target:
        targets = []
    
    # Evaluate on mini-batch
    for data in generate_func:
            
        if return_target:
            (batch_x, batch_y, batch_audio_names) = data
            
        else:
            (batch_x, batch_audio_names) = data
            
        batch_x = move_data_to_gpu(batch_x, cuda)

        # Predict
        model.eval()
        batch_output = model(batch_x)

        # Append data
        outputs.append(batch_output.data.cpu().numpy())
        audio_names.append(batch_audio_names)
        
        if return_target:
            targets.append(batch_y)

    dict = {}

    outputs = np.concatenate(outputs, axis=0)
    dict['output'] = outputs
    
    audio_names = np.concatenate(audio_names, axis=0)
    dict['audio_name'] = audio_names
    
    if return_target:
        targets = np.concatenate(targets, axis=0)
        dict['target'] = targets
        
    return dict


def train(args):

    # Arugments & parameters
    dataset_dir = args.dataset_dir
    subdir = args.subdir
    workspace = args.workspace
    filename = args.filename
    validate = args.validate
    holdout_fold = args.holdout_fold
    mini_data = args.mini_data
    cuda = args.cuda

    labels = config.labels

    if 'mobile' in subdir:
        devices = ['a', 'b', 'c']
    else:
        devices = ['a']

    classes_num = len(labels)

    # Paths
    #if mini_data:
        #hdf5_path = os.path.join(workspace, 'features', 'logmel', subdir,
                                 #'mini_development.h5')
   # else:
    hdf5_path = '/home/mura4197/Downloads/dcase2018_task1-master/features/logmel/TUT-urban-acoustic-scenes-2018-development/development.h5'
    if validate:
        
        dev_train_csv = os.path.join(dataset_dir, subdir, 'evaluation_setup',
                                     'fold{}_train_1.txt'.format(holdout_fold))
                                    
        dev_validate_csv = os.path.join(dataset_dir, subdir, 'evaluation_setup',
                                    'fold{}_evaluate_1.txt'.format(holdout_fold))
                              
        models_dir = os.path.join(workspace, 'models', subdir, filename,
                                  'holdout_fold={}'.format(holdout_fold))
                                        
    else:
        dev_train_csv = None
        dev_validate_csv = None
        
        models_dir = os.path.join(workspace, 'models', subdir, filename,
                                  'full_train')

    create_folder(models_dir)

    # Model
    model = Model(classes_num)

    if cuda:
        model.cuda()

    # Data generator
    generator = DataGenerator(hdf5_path=hdf5_path,
                              batch_size=batch_size,
                              dev_train_csv=None,
                              dev_validate_csv=None)

    # Optimizer
    optimizer = optim.Adam(model.parameters(), lr=1e-3, betas=(0.9, 0.999),
                           eps=1e-08, weight_decay=0.)

    train_bgn_time = time.time()

    # Train on mini batches
    for (iteration, (batch_x, batch_y)) in enumerate(generator.generate_train()):

        # Evaluate
        if iteration % 100 == 0:

            train_fin_time = time.time()

            (tr_acc, tr_loss) = evaluate(model=model,
                                         generator=generator,
                                         data_type='train',
                                         devices=devices,
                                         max_iteration=None,
                                         cuda=cuda)

            logging.info('tr_acc: {:.3f}, tr_loss: {:.3f}'.format(
                tr_acc, tr_loss))

            if validate:
                
                (va_acc, va_loss) = evaluate(model=model,
                                             generator=generator,
                                             data_type='validate',
                                             devices=devices,
                                             max_iteration=None,
                                             cuda=cuda)
                                
                logging.info('va_acc: {:.3f}, va_loss: {:.3f}'.format(
                    va_acc, va_loss))

            train_time = train_fin_time - train_bgn_time
            validate_time = time.time() - train_fin_time

            logging.info(
                'iteration: {}, train time: {:.3f} s, validate time: {:.3f} s'
                    ''.format(iteration, train_time, validate_time))

            logging.info('------------------------------------')

            train_bgn_time = time.time()

        # Save model
        if iteration % 1000 == 0 and iteration > 0:

            save_out_dict = {'iteration': iteration,
                             'state_dict': model.state_dict(),
                             'optimizer': optimizer.state_dict()
                             }
            save_out_path = os.path.join(
                models_dir, 'md_{}_iters.tar'.format(iteration))
            torch.save(save_out_dict, save_out_path)
            logging.info('Model saved to {}'.format(save_out_path))
            
        # Reduce learning rate
        if iteration % 200 == 0 > 0:
            for param_group in optimizer.param_groups:
                param_group['lr'] *= 0.9

        # Train
        batch_x = move_data_to_gpu(batch_x, cuda)
        batch_y = move_data_to_gpu(batch_y, cuda)

        model.train()
        batch_output = model(batch_x)
        loss = F.nll_loss(batch_output, batch_y)

        # Backward
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        # Stop learning
        if iteration == 10000:
            break


def inference_validation_data(args):

    # Arugments & parameters
    dataset_dir = args.dataset_dir
    subdir = args.subdir
    workspace = args.workspace
    holdout_fold = args.holdout_fold
    iteration = args.iteration
    filename = args.filename
    cuda = args.cuda

    labels = config.labels

    if 'mobile' in subdir:
        devices = ['a', 'b', 'c']
    else:
        devices = ['a']

    validation = True
    classes_num = len(labels)

    # Paths
    hdf5_path = '/home/mura4197/Downloads/dcase2018_task1-master/features/logmel/TUT-urban-acoustic-scenes-2018-development/development.h5'

    dev_train_csv = '/home/mura4197/Downloads/dcase2018_task1-master/pytorch/evaluation_setup/fold1_train_1.csv'
                                 
    dev_validate_csv = '/home/mura4197/Downloads/dcase2018_task1-master/pytorch/evaluation_setup/fold1_evaluate_1.csv'

    model_path = '/home/mura4197/Downloads/dcase2018_task1-master/models/TUT-urban-acoustic-scenes-2018-development/main_pytorch/holdout_fold=1/md_1000_iters.tar' 
    
    
    
    
    # Load model
    model = Model(classes_num)
    checkpoint = torch.load(model_path)
    model.load_state_dict(checkpoint['state_dict'])

    if cuda:
        model.cuda()

    # Predict & evaluate
    for device in devices:

        print('Device: {}'.format(device))

        # Data generator
        generator = DataGenerator(hdf5_path=hdf5_path,
                                  batch_size=batch_size,
                                  dev_train_csv=dev_train_csv,
                                  dev_validate_csv=dev_validate_csv)

        generate_func = generator.generate_validate(data_type='validate', 
                                                     devices=device, 
                                                     shuffle=False)

        # Inference
        dict = forward(model=model,
                       generate_func=generate_func, 
                       cuda=cuda, 
                       return_target=True)

        outputs = dict['output']    # (audios_num, classes_num)
        targets = dict['target']    # (audios_num, classes_num)

        predictions = np.argmax(outputs, axis=-1)

        classes_num = outputs.shape[-1]
        
        # Evaluate
        confusion_matrix = calculate_confusion_matrix(
            targets, predictions, classes_num)
            
        class_wise_accuracy = calculate_accuracy(targets, predictions, 
                                                 classes_num)

        # Print
        print_accuracy(class_wise_accuracy, labels)
        print('confusion_matrix: \n', confusion_matrix)

        # Plot confusion matrix
        plot_confusion_matrix(
            confusion_matrix,
            title='Device {}'.format(device.upper()), 
            labels=labels,
            values=class_wise_accuracy)
            
     
def inference_leaderboard_data(args):
    
    # Arugments & parameters
    dataset_dir = args.dataset_dir
    dev_subdir = args.dev_subdir
    leaderboard_subdir = args.leaderboard_subdir
    workspace = args.workspace
    iteration = args.iteration
    filename = args.filename
    cuda = args.cuda

    labels = config.labels
    ix_to_lb = config.ix_to_lb

    classes_num = len(labels)

    # Paths
    dev_hdf5_path = os.path.join(workspace, 'features', 'logmel', dev_subdir,
                                 'development.h5')

    test_hdf5_path = os.path.join(workspace, 'features', 'logmel', leaderboard_subdir,
                                 'leaderboard.h5')

    model_path = os.path.join(workspace, 'models', dev_subdir, filename,
                              'full_train', 
                              'md_{}_iters.tar'.format(iteration))

    submission_path = os.path.join(workspace, 'submissions', leaderboard_subdir, 
                                   filename, 'iteration={}'.format(iteration), 
                                   'submission.csv')
                                   
    create_folder(os.path.dirname(submission_path))

    # Load model
    model = Model(classes_num)
    checkpoint = torch.load(model_path)
    model.load_state_dict(checkpoint['state_dict'])

    if cuda:
        model.cuda()

    # Data generator
    generator = TestDataGenerator(dev_hdf5_path=dev_hdf5_path,
                                  test_hdf5_path=test_hdf5_path, 
                                  batch_size=batch_size)

    generate_func = generator.generate_test()

    # Predict
    dict = forward(model=model, 
                   generate_func=generate_func, 
                   cuda=cuda, 
                   return_target=False)
    
    audio_names = dict['audio_name']    # (audios_num,)
    outputs = dict['output']    # (audios_num, classes_num)
    
    predictions = np.argmax(outputs, axis=-1)    # (audios_num,)

    # Write result to submission csv
    write_leaderboard_submission(submission_path, audio_names, predictions)
    
            
def inference_evaluation_data(args):
    
    # Arugments & parameters
    dataset_dir = args.dataset_dir
    dev_subdir = args.dev_subdir
    eval_subdir = args.eval_subdir
    workspace = args.workspace
    iteration = args.iteration
    filename = args.filename
    cuda = args.cuda

    labels = config.labels
    ix_to_lb = config.ix_to_lb

    classes_num = len(labels)

    # Paths
    dev_hdf5_path = os.path.join(workspace, 'features', 'logmel', dev_subdir,
                                 'development.h5')

    test_hdf5_path = os.path.join(workspace, 'features', 'logmel', eval_subdir,
                                 'evaluation.h5')

    model_path = os.path.join(workspace, 'models', dev_subdir, filename,
                              'full_train', 
                              'md_{}_iters.tar'.format(iteration))

    submission_path = os.path.join(workspace, 'submissions', eval_subdir, 
                                   filename, 'iteration={}'.format(iteration), 
                                   'submission.csv')
                                   
    create_folder(os.path.dirname(submission_path))

    # Load model
    model = Model(classes_num)
    checkpoint = torch.load(model_path)
    model.load_state_dict(checkpoint['state_dict'])

    if cuda:
        model.cuda()

    # Data generator
    generator = TestDataGenerator(dev_hdf5_path=dev_hdf5_path,
                                  test_hdf5_path=test_hdf5_path, 
                                  batch_size=batch_size)

    generate_func = generator.generate_test()

    # Predict
    dict = forward(model=model, 
                     generate_func=generate_func, 
                     cuda=cuda, 
                     return_target=False)
    
    audio_names = dict['audio_name']    # (audios_num,)
    outputs = dict['output']    # (audios_num, classes_num)
    
    predictions = np.argmax(outputs, axis=-1)    # (audios_num,)

    # Write result to submission csv
    f = open(submission_path, 'w')	
    
    write_evaluation_submission(submission_path, audio_names, predictions)
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Example of parser. ')
    subparsers = parser.add_subparsers(dest='mode')

    parser_train = subparsers.add_parser('train')
    parser_train.add_argument('--dataset_dir', type=str, required=True)
    parser_train.add_argument('--subdir', type=str, required=True)
    parser_train.add_argument('--workspace', type=str, required=True)
    parser_train.add_argument('--validate', action='store_true', default=False)
    parser_train.add_argument('--holdout_fold', type=int)
    parser_train.add_argument('--cuda', action='store_true', default=False)
    parser_train.add_argument('--mini_data', action='store_true', default=False)
    
    parser_inference_validation_data = subparsers.add_parser('inference_validation_data')
    parser_inference_validation_data.add_argument('--dataset_dir', type=str, required=True)
    parser_inference_validation_data.add_argument('--subdir', type=str, required=True)
    parser_inference_validation_data.add_argument('--workspace', type=str, required=True)
    parser_inference_validation_data.add_argument('--holdout_fold', type=int, required=True)
    parser_inference_validation_data.add_argument('--iteration', type=int, required=True)
    parser_inference_validation_data.add_argument('--cuda', action='store_true', default=False)
                     
    parser_inference_leaderboard_data = subparsers.add_parser('inference_leaderboard_data')
    parser_inference_leaderboard_data.add_argument('--dataset_dir', type=str, required=True)
    parser_inference_leaderboard_data.add_argument('--dev_subdir', type=str, required=True)
    parser_inference_leaderboard_data.add_argument('--leaderboard_subdir', type=str, required=True)
    parser_inference_leaderboard_data.add_argument('--workspace', type=str, required=True)
    parser_inference_leaderboard_data.add_argument('--iteration', type=int, required=True)
    parser_inference_leaderboard_data.add_argument('--cuda', action='store_true', default=False)
                                            
    parser_inference_evaluation_data = subparsers.add_parser('inference_evaluation_data')
    parser_inference_evaluation_data.add_argument('--dataset_dir', type=str, required=True)
    parser_inference_evaluation_data.add_argument('--dev_subdir', type=str, required=True)
    parser_inference_evaluation_data.add_argument('--eval_subdir', type=str, required=True)
    parser_inference_evaluation_data.add_argument('--workspace', type=str, required=True)
    parser_inference_evaluation_data.add_argument('--iteration', type=int, required=True)
    parser_inference_evaluation_data.add_argument('--cuda', action='store_true', default=False)

    args = parser.parse_args()

    args.filename = get_filename(__file__)

    # Create log
    logs_dir = os.path.join(args.workspace, 'logs', args.filename)
    create_logging(logs_dir, filemode='w')
    logging.info(args)

    if args.mode == 'train':
        train(args)

    elif args.mode == 'inference_validation_data':
        inference_validation_data(args)

    elif args.mode == 'inference_leaderboard_data':
        inference_leaderboard_data(args)
        
    elif args.mode == 'inference_evaluation_data':
        inference_evaluation_data(args)

    else:
        raise Exception('Error argument!')
